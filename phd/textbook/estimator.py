import random
import time

import pandas as pd
import sqlalchemy

from phd import distribution
from phd import tools
from phd.estimator import Estimator


class TextbookEstimator(Estimator):

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
            'parameters': {}
        }

        # Create histograms per attribute
        self.histograms = {}
        self.n_in_bin = {}
        sampling_method = {True: 'SYSTEM', False: 'BERNOULLI'}[self.block_sampling]

        for rel_name in self.rel_names:

            self.histograms[rel_name] = {}
            self.n_in_bin[rel_name] = {}

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
                if '_id' in att
                or 'id_' in att
                or att == 'id'
                or '_sk' in att
                or self.att_types[rel_name][att] == 'character varying'
                or round(rel_card * self.null_fracs[rel_name][att] + self.att_cards[rel_name][att]) == rel_card
            ]

            # Create one histogram per attribute
            tic = time.time()
            for att in set(rel.columns) - set(blacklist):
                rel[att], self.n_in_bin[rel_name][att] = tools.discretize_series(
                    rel[att],
                    n_mcv=self.n_mcv,
                    n_bins=self.n_bins
                )
                self.histograms[rel_name][att] = distribution.Distribution(on=att, by=None)
                self.histograms[rel_name][att].build_from_df(rel, types=self.att_types[rel_name])

            duration['parameters'][rel_name] = time.time() - tic

        # Close the connection to the database
        conn.close()

        return duration

    def estimate_selectivity(self, join_query: str, filter_query: str, relation_names=None):

        relationships, filters, rel_names = self.parse_query(join_query, filter_query)

        cartesian_prod_card = self.calc_cartesian_prod_card(relation_names if relation_names else rel_names)
        join_selectivity = self.calc_join_selectivity(relationships)

        attribute_selectivity = 1
        for rel_name, f in filters.items():
            rel_p = 1
            for att, op in tools.parse_filter(f).items():
                hist = self.histograms[rel_name][att]
                relevant_hist = hist.subset(att, op)
                pp = 0
                for val, p in relevant_hist.items():
                    if isinstance(val, pd.Interval):
                        n_in_bin = self.n_in_bin[rel_name][att][str(val)]
                        p *= op.calc_coverage(val, n_in_bin)
                    pp += p
                rel_p *= pp
            print(rel_name, rel_p)
            attribute_selectivity *= rel_p

        return cartesian_prod_card * join_selectivity * attribute_selectivity
