from collections import defaultdict
import functools
import itertools
import operator
import re

import sqlalchemy

from . import relationship
from . import tools


class Estimator():

    def __init__(self):

        self.rel_cards = None
        self.att_cards = None
        self.null_fracs = None
        self.rel_names = None
        self.att_types = None

    def setup(self, engine: sqlalchemy.engine.base.Engine):

        # Retrieve the metadata to know what tables and joins are available
        metadata = tools.get_metadata(engine)
        self.rel_names = tuple(metadata.tables.keys())

        # Create a connection to the database
        conn = engine.connect()

        # Retrieve relation cardinalities
        self.rel_cards = {}
        query = '''
        SELECT relname, reltuples
        FROM pg_class
        WHERE relname IN :rel_names
        '''
        rows = conn.execute(sqlalchemy.text(query), rel_names=self.rel_names)
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
        rows = conn.execute(sqlalchemy.text(query), rel_names=self.rel_names)
        for (rel_name, att_name, card, null_frac) in rows:
            self.att_cards[rel_name][att_name] = -card * self.rel_cards[rel_name] if card < 0 else card
            self.null_fracs[rel_name][att_name] = null_frac

        # Retrieve the type of each attribute
        self.att_types = defaultdict(dict)
        query = '''
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name IN :rel_names
        '''
        rows = conn.execute(sqlalchemy.text(query), rel_names=self.rel_names)
        for (rel_name, att_name, att_type) in rows:
            self.att_types[rel_name][att_name] = att_type

        # Close the connection to the database
        conn.close()

    def calc_cartesian_prod_card(self, rel_names):
        return functools.reduce(operator.mul, [self.rel_cards[name] for name in rel_names])

    def calc_join_selectivity(self, relationships):
        join_selectivity = 1
        for r in relationships:
            left_key_density = 1 / self.att_cards[r.left][r.left_on]
            right_key_density = 1 / self.att_cards[r.right][r.right_on]
            join_selectivity *= min(left_key_density, right_key_density)
        return join_selectivity

    def parse_join_query(self, join_query: str):

        def join_to_relation(join: str) -> relationship.Relationship:
            left, right = join.split(' == ')
            left, left_on = left.split('.')
            right, right_on = right.split('.')
            return relationship.Relationship(left, right, left_on, right_on)

        return list(filter(
            None.__ne__,
            [
                join_to_relation(part)
                if len(part) > 0
                else None
                for part in ' '.join(join_query.replace('\n', '').split()).split(' and ')
            ]
        ))

    def parse_filter_query(self, filter_query: str):

        filter_query = ' '.join(filter_query.replace('\n', '').split())

        if len(filter_query) == 0:
            return {}

        return dict(
            (k, ' and '.join([re.sub('\w+\.', '', v[1]) for v in g]))
            for k, g in itertools.groupby(
                [
                    (re.split(' (==|in) ', part)[0].split('.')[0], part)
                    for part in filter_query.split(' and ')
                ],
                lambda x: x[0]
            )
        )

    def parse_query(self, join_query, filter_query):
        relationships = self.parse_join_query(join_query)
        filters = self.parse_filter_query(filter_query)
        relation_names = set(itertools.chain.from_iterable([(r.left, r.right) for r in relationships]))
        relation_names = relation_names.union(set(filters.keys()))
        return relationships, filters, relation_names

    def estimate_selectivity(self, join_query: str, filter_query: str, relation_names=None):
        raise NotImplementedError
