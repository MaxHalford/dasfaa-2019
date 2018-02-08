from collections import defaultdict
import functools
import itertools
import operator
from typing import List
import re

import sqlalchemy

from phd import relation
from phd import relationship
from phd import tools

from . import chow_liu


class Estimator():

    def __init__(self, n_most_frequent=30, sampling=1.0):
        self.n_most_frequent = n_most_frequent
        self.sampling = sampling

        self.keys = None
        self.bayes_nets = None
        self.relation_cards = None
        self.key_cards = None

    def build_from_relations_and_relationships(self,
                                               relations: List[relation.Relation],
                                               relationships: List[relationship.Relationship]):

        # Determine the set of keys in each relation
        self.keys = defaultdict(list)
        for d in [{r.left: r.left_on, r.right: r.right_on} for r in relationships]:
            for k, v in d.items():
                self.keys[k].append(v)

        # Compute each relation's BN
        self.bayes_nets = {}
        for r in relations:
            blacklist = set(self.keys[r.name] + ['id'])
            bn = chow_liu.chow_liu_tree_from_df(df=r, blacklist=blacklist)
            bn.update_cpds(r, n_most_frequent=self.n_most_frequent)
            self.bayes_nets[r.name] = bn

        # Determine relation cardinalities
        self.relation_cards = {r.name: len(r) for r in relations}

        # Determine key cardinalities
        self.key_cards = {
            r.name: {key: r[key].nunique() for key in self.keys[r.name]}
            for r in relations
        }

    def build_from_engine(self, engine: sqlalchemy.engine.base.Engine):

        # Retrieve the metadata to know what tables and joins are available
        metadata = tools.retrieve_metadata(engine)

    def estimate_selectivity(self, query_join='', query_filter=''):

        # Parse the join conditions and the filter conditions; this creates a
        # dict that maps relations to a list of filters that are relevant to
        # the relation and whose attribute names are not prefixed by the name
        # of the relation. For example this can give
        #
        # filters = {
        #     title: ['name == "Casablanca"'],
        #     cast_info: ['node == "some note"']
        # }
        joins_conditions = query_join.lower().split(' and ')
        filters = dict(
            (k, ' and '.join([re.sub('\w+\.', '', v[1]) for v in g]))
            for k, g in itertools.groupby(
                [
                    (re.split(' (==|in) ', query)[0].split('.')[0], query)
                    for query in query_filter.lower().split(' and ')
                ],
                lambda x: x[0]
            )
        )

        # Determine which relations are involved by looking at the join
        # conditions
        relation_names = list(set(itertools.chain(*[
            [side.split('.')[0] for side in jc.split(' = ')]
            for jc in joins_conditions
        ])))

        # Compute the size of the cartesian product by multiplying each
        # involved relation's number of rows with each other
        cardinalities = [self.relation_cards[name] for name in relation_names]
        cartesian_prod_card = functools.reduce(operator.mul, cardinalities)

        # Compute the join selectivity as the product of each particular join
        # selectivity; a join selectivity is estimated as the lowest density
        # between the two attributes involved in the join (usually these
        # attributes are keys)
        join_selectivity = 1
        for jc in joins_conditions:
            left_side, right_side = jc.split(' = ')
            left, left_on = left_side.split('.')
            right, right_on = right_side.split('.')
            left_key_density = 1 / self.key_cards[left][left_on]
            right_key_density = 1 / self.key_cards[right][right_on]
            join_selectivity *= min(left_key_density, right_key_density)

        # Compute the overall attribute selectivity by multiplying the
        # attribute selectivity of each relation that contains filter
        # conditions
        attribute_selectivity = 1
        for relation_name, filter_conditions in filters.items():
            attribute_selectivity *= self.bayes_nets[relation_name].infer(filter_conditions)

        return cartesian_prod_card * join_selectivity * attribute_selectivity
