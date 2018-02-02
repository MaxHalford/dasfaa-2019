from collections import defaultdict
import functools
import itertools
import operator
from typing import List

from phd import relation
from phd import relationship

from . import chow_liu


class Estimator():

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
            blacklist = self.keys[r.name]
            bn = chow_liu.chow_liu_tree_from_df(df=r, blacklist=blacklist)
            bn.update_cpds(r)
            self.bayes_nets[r.name] = bn

        # Determine relation cardinalities
        self.relation_cards = {r.name: len(r) for r in relations}

        # Determine key cardinalities
        self.key_cards = {
            r.name: {key: r[key].nunique() for key in self.keys[r.name]}
            for r in relations
        }

    def estimate_selectivity(self, query_join='', query_filter=''):

        # Parse the join conditions and the filter conditions
        joins_conditions = query_join.split(' AND ')
        filter_conditions = query_filter.split(' AND ')

        # Determine which relations are involved
        relation_names = list(set(itertools.chain(*[
            [side.split('.')[0] for side in jc.split(' = ')]
            for jc in joins_conditions
        ])))

        # Compute the size of the cartesian product
        cardinalities = [self.relation_cards[name] for name in relation_names]
        cartesian_prod_card = functools.reduce(operator.mul, cardinalities)

        # Compute the join selectivity
        join_selectivities = []
        for jc in joins_conditions:
            left_side, right_side = jc.split(' = ')
            left, left_on = left_side.split('.')
            right, right_on = right_side.split('.')
            join_selectivities.append(min(
                1 / (self.key_cards[left][left_on]),
                1 / (self.key_cards[right][right_on]),
            ))
        join_selectivity = functools.reduce(operator.mul, join_selectivities)

        return cartesian_prod_card * join_selectivity
