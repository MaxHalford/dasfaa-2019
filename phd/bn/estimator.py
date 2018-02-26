from collections import defaultdict
import functools
import itertools
import operator
import random
import re
import time
from typing import List

import pandas as pd
import sqlalchemy

from phd import relation
from phd import relationship
from phd import tools

from . import chow_liu


class Estimator():

    def __init__(self, n_mcv=30, n_bins=30, sampling_ratio=1.0, block_sampling=True,
                 min_rows=10000, seed=None):
        self.n_mcv = n_mcv
        self.n_bins = n_bins
        self.sampling_ratio = sampling_ratio
        self.min_rows = min_rows
        self.block_sampling = block_sampling
        self.seed = seed if seed else random.randint(0, 2 ** 32)

        self.bayes_nets = None
        self.rel_cards = None
        self.att_cards = None
        self.null_fracs = None

    def build_from_relations_and_relationships(self,
                                               relations: List[relation.Relation],
                                               relationships: List[relationship.Relationship]):

        # Determine relation cardinalities
        self.rel_cards = {r.name: len(r) for r in relations}

        # Determine each attribute's cardinality
        self.att_cards = {
            r.name: {att: r[att].nunique() for att in r.columns}
            for r in relations
        }

        # Compute each relation's BN
        self.bayes_nets = {}
        for r in relations:
            blacklist = [
                att
                for att in r.columns
                if '_id' in att or 'id_' in att or att == 'id' or '_sk' in att
            ]
            bn = chow_liu.chow_liu_tree_from_df(df=r, blacklist=blacklist)
            bn.update_cpds(r, n_mcv=self.n_mcv, n_bins=n_bins)
            self.bayes_nets[r.name] = bn

    def build_from_engine(self, engine: sqlalchemy.engine.base.Engine) -> dict:

        # Retrieve the metadata to know what tables and joins are available
        metadata = tools.get_metadata(engine)
        rel_names = tuple(metadata.tables.keys())

        # Create a connection to the database
        conn = engine.connect()

        # Retrieve relation cardinalities
        self.rel_cards = {}
        query = '''
        SELECT relname, reltuples
        FROM pg_class
        WHERE relname IN :rel_names
        '''
        rows = conn.execute(sqlalchemy.text(query), rel_names=rel_names)
        for (rel_name, card) in rows:
            self.rel_cards[rel_name] = card

        # Retrieve attribute cardinalities and number of nulls
        self.att_cards = defaultdict(dict)
        self.null_fracs = defaultdict(dict)
        query = '''
        SELECT tablename, attname, n_distinct, null_frac
        FROM pg_stats
        WHERE tablename IN :rel_names
        '''
        rows = conn.execute(sqlalchemy.text(query), rel_names=rel_names)
        for (rel_name, att_name, card, null_frac) in rows:
            self.att_cards[rel_name][att_name] = -card * self.rel_cards[rel_name] if card < 0 else card
            self.null_fracs[rel_name][att_name] = null_frac

        # Retrieve the type of each attribute
        att_types = defaultdict(dict)
        query = '''
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name IN :rel_names
        '''
        rows = conn.execute(sqlalchemy.text(query), rel_names=rel_names)
        for (rel_name, att_name, att_type) in rows:
            att_types[rel_name][att_name] = att_type

        # Record the time spent
        duration = {
            'querying': {},
            'structure': {},
            'parameters': {}
        }

        # Create a Bayesian network per relation
        self.bayes_nets = {}
        sampling_method = {True: 'SYSTEM', False: 'BERNOULLI'}[self.block_sampling]
        for rel_name, card in self.rel_cards.items():

            # Sample the relation if the number of rows is high enough
            query = 'SELECT * FROM {}'.format(rel_name)
            # Add a sampling statement if the sampling ratio is lower than 1
            sampling_ratio = max(self.sampling_ratio, self.min_rows / card)
            if sampling_ratio < 1:
                # Make sure there won't be less samples then the minimum number of allowed rows
                query += ' TABLESAMPLE {} ({}) REPEATABLE ({})'.format(
                    sampling_method,
                    sampling_ratio,
                    self.seed
                )
            date_atts = [att for att, typ in att_types[rel_name].items() if typ == 'date']
            tic = time.time()
            rel = pd.read_sql_query(sql=query, con=conn, parse_dates=date_atts)
            duration['querying'][rel_name] = time.time() - tic

            # Convert the datetimes to ISO formatted strings
            for att, typ in att_types[rel_name].items():
                if typ == 'date':
                    rel[att] = rel[att].map(lambda x: x.isoformat())

            # Strip the whitespace from the string columns
            for att in rel.columns:
                if rel[att].dtype == 'object':
                    rel[att] = rel[att].str.rstrip()

            # Blacklist the ID columns
            blacklist = [
                att for att in rel.columns
                if '_id' in att or 'id_' in att or att == 'id' or '_sk' in att
            ]

            # Find the structure of the Bayesian network
            tic = time.time()
            bn = chow_liu.chow_liu_tree_from_df(df=rel, blacklist=blacklist)
            duration['structure'][rel_name] = time.time() - tic

            # Compute the network's parameters
            tic = time.time()
            bn.update_cpds(rel, n_mcv=self.n_mcv, n_bins=self.n_bins)
            duration['parameters'][rel_name] = time.time() - tic

            self.bayes_nets[rel_name] = bn

        return duration

    def estimate_selectivity(self, join='', conditions=dict()):

        # Parse the join conditions and the filter conditions; this creates a
        # dict that maps relations to a list of filters that are relevant to
        # the relation and whose attribute names are not prefixed by the name
        # of the relation. For example this can give
        #
        # filters = {
        #     title: ['name == "Casablanca"'],
        #     cast_info: ['node == "some note"']
        # }
        # filters = dict(
        #     (k, ' and '.join([re.sub('\w+\.', '', v[1]) for v in g]))
        #     for k, g in itertools.groupby(
        #         [
        #             (re.split(' (==|in) ', query)[0].split('.')[0], query)
        #             for query in query_filter.lower().split(' and ')
        #         ],
        #         lambda x: x[0]
        #     )
        # )

        # Parse the join conditions
        join_conditions = join.lower().split(' and ') if join else []

        # Determine which relations are involved by looking at the join
        # conditions
        rel_names = list(set(itertools.chain(*[
            [side.split('.')[0] for side in jc.split(' = ')]
            for jc in join_conditions
        ]))) if join_conditions else list(conditions.keys())

        # Compute the size of the cartesian product by multiplying each
        # involved relation's number of rows with each other
        cardinalities = [self.rel_cards[name] for name in rel_names]
        cartesian_prod_card = functools.reduce(operator.mul, cardinalities)

        # Compute the join selectivity as the product of each particular join
        # selectivity; a join selectivity is estimated as the lowest density
        # between the two attributes involved in the join (usually these
        # attributes are keys)
        join_selectivity = 1
        for jc in join_conditions:
            left_side, right_side = jc.split(' = ')
            left, left_on = left_side.split('.')
            right, right_on = right_side.split('.')
            left_key_density = 1 / self.att_cards[left][left_on]
            right_key_density = 1 / self.att_cards[right][right_on]
            join_selectivity *= min(left_key_density, right_key_density)

        # Compute the overall attribute selectivity by multiplying the
        # attribute selectivity of each relation that contains filter
        # conditions
        attribute_selectivity = 1
        for rel_name, condition in conditions.items():
            attribute_selectivity *= self.bayes_nets[rel_name].infer(condition)

        return cartesian_prod_card * join_selectivity * attribute_selectivity
