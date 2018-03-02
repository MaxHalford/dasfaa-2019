from collections import defaultdict
import itertools
import random
import re
import time
from typing import List

import pandas as pd
import sqlalchemy

from phd import relation
from phd import relationship
from phd import tools
from phd.estimator import Estimator


class SamplingEstimator(Estimator):

    def __init__(self, sampling_ratio=0.1, block_sampling=True, min_rows=10000, seed=None):

        super().__init__()

        self.sampling_ratio = sampling_ratio
        self.min_rows = min_rows
        self.block_sampling = block_sampling
        self.seed = seed if seed else random.randint(0, 2 ** 32)
        self.bayes_nets = None

    def build_from_engine(self, engine: sqlalchemy.engine.base.Engine) -> dict:

        self.setup(engine)

        # Create a connection to the database
        conn = engine.connect()

        # Record the time spent
        duration = {
            'querying': {},
        }

        # Sample each relation
        self.relations = {}
        sampling_method = {True: 'SYSTEM', False: 'BERNOULLI'}[self.block_sampling]
        for rel_name in self.rel_names:

            # Sample the relation if the number of rows is high enough
            query = 'SELECT * FROM {}'.format(rel_name)
            # Add a sampling statement if the sampling ratio is lower than 1
            sampling_ratio = max(self.sampling_ratio, self.min_rows / self.rel_cards[rel_name])
            if sampling_ratio < 1:
                # Make sure there won't be less samples then the minimum number of allowed rows
                query += ' TABLESAMPLE {} ({}) REPEATABLE ({})'.format(
                    sampling_method,
                    sampling_ratio,
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

            # Store the relation
            self.relations[rel_name] = rel

        # Close the connection to the database
        conn.close()

        return duration

    def estimate_selectivity(self, join_query: str, filter_query: str):

        relationships, filters, rel_names = self.parse_query(join_query, filter_query)

        cartesian_prod_card = self.calc_cartesian_prod_card(rel_names)
        join_selectivity = self.calc_join_selectivity(relationships)

        attribute_selectivity = 1
        for rel_name in filters:
            rel = self.relations[rel_name]
            attribute_selectivity *= len(rel.query(filters[rel_name])) / len(rel)

        return cartesian_prod_card * join_selectivity * attribute_selectivity
