import random
import time

import pandas as pd
import sqlalchemy

from phd import tools
from phd.estimator import Estimator

from . import chow_liu


class BayesianNetworkEstimator(Estimator):

    def __init__(self, n_mcv=30, n_bins=30, sampling_ratio=1.0, block_sampling=True,
                 min_rows=10000, seed=None):
        self.n_mcv = n_mcv
        self.n_bins = n_bins
        self.sampling_ratio = sampling_ratio
        self.min_rows = min_rows
        self.block_sampling = block_sampling
        self.seed = seed if seed else random.randint(0, 2 ** 32)

    def build_from_engine(self, engine: sqlalchemy.engine.base.Engine) -> dict:

        self.setup(engine)

        # Create a connection to the database
        conn = engine.connect()

        # Record the time spent
        duration = {
            'querying': {},
            'structure': {},
            'parameters': {}
        }

        # Create a Bayesian network per relation
        self.bayes_nets = {}
        self.mutual_infos = {}
        sampling_method = {True: 'SYSTEM', False: 'BERNOULLI'}[self.block_sampling]
        for rel_name in self.rel_names:

            rel_card = self.rel_cards[rel_name]

            # Sample the relation if the number of rows is high enough
            query = 'SELECT * FROM {}'.format(rel_name)
            # Add a sampling statement if the sampling ratio is lower than 1
            sampling_ratio = max(self.sampling_ratio, self.min_rows / rel_card)
            if sampling_ratio < 1:
                # Make sure there won't be less samples then the minimum number of allowed rows
                query += ' TABLESAMPLE {} ({}) REPEATABLE ({})'.format(
                    sampling_method,
                    sampling_ratio * 100,
                    self.seed
                )
            date_atts = [att for att, typ in self.att_types[rel_name].items() if typ == 'date']
            tic = time.time()
            rel = pd.read_sql_query(sql=query, con=conn, parse_dates=date_atts)
            duration['querying'][rel_name] = time.time() - tic

            # Convert the datetimes to ISO formatted strings
            for att in date_atts:
                rel[att] = rel[att].map(lambda x: x.isoformat())

            # Strip the whitespace from the string columns
            for att in rel.columns:
                if rel[att].dtype == 'object':
                    rel[att] = rel[att].str.rstrip()

            # Blacklist the ID columns
            blacklist = [
                att for att in rel.columns
                if '_id' in att or
                'id_' in att or
                att == 'id' or
                '_sk' in att or
                self.att_types[rel_name][att] == 'character varying' or
                round(rel_card * self.null_fracs[rel_name][att] + self.att_cards[rel_name][att]) == rel_card
            ]

            # Find the structure of the Bayesian network
            tic = time.time()
            bn, self.mutual_infos[rel_name] = chow_liu.chow_liu_tree_from_df(
                df=rel,
                blacklist=blacklist
            )
            duration['structure'][rel_name] = time.time() - tic

            # Compute the network's parameters
            tic = time.time()
            bn.update_distributions(
                rel,
                n_mcv=self.n_mcv,
                n_bins=self.n_bins,
                types=self.att_types[rel_name]
            )
            duration['parameters'][rel_name] = time.time() - tic

            # Store the network
            self.bayes_nets[rel_name] = bn

        # Close the connection to the database
        conn.close()

        return duration

    def estimate_selectivity(self, join_query: str, filter_query: str, relation_names=None):

        relationships, filters, rel_names = self.parse_query(join_query, filter_query)

        cartesian_prod_card = self.calc_cartesian_prod_card(relation_names if relation_names else rel_names)
        join_selectivity = self.calc_join_selectivity(relationships)

        attribute_selectivity = 1
        for rel_name in filters:
            bn = self.bayes_nets[rel_name]
            p = bn.infer(tools.parse_filter(filters[rel_name]))
            print(rel_name, p)
            attribute_selectivity *= p

        return cartesian_prod_card * join_selectivity * attribute_selectivity
