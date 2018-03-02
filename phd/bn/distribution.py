import itertools
import numbers
from typing import Callable

import numpy as np
import pandas as pd

from phd import operator
from phd import tools


class Distribution(dict):

    def __init__(self, *args, **kwargs):
        on = kwargs.pop('on', None)
        by = kwargs.pop('by', None)
        super().__init__(*args, **kwargs)
        self.on = on
        self.by = by

    def from_df(self, df: pd.DataFrame, types: dict):

        if self.by:
            calc_inner_dist = lambda g: Distribution(on=self.on).from_df(g, types)
            counts = df.groupby(self.by, sort=False).apply(calc_inner_dist)
        else:
            counts = df.groupby(self.on, sort=False).size() / len(df)

        # In some cases a groupby followed by an apply can return a DataFrame
        if isinstance(counts, pd.DataFrame):
            counts = counts.stack()

        # I hate this shit

        on = self.by if self.by else self.on

        if types[on] in ('integer', 'numeric', 'double precision', 'real'):
            def convert(x):
                if x.startswith("["):
                    left, right = x[1:-1].split(' %,% ')
                    return pd.Interval(float(left), float(right), 'both')
                return float(x) if x != 'None' else x
        else:
            def convert(x):
                if x.startswith("["):
                    left, right = x[1:-1].split(' %,% ')
                    return pd.Interval(left, right, 'both')
                return x

        super().__init__({convert(k): v for k, v in counts.items()})

        return self

    def subset(self, on: str, op: operator.Operator):

        # Maybe nothing has to be done
        if not op or isinstance(op, operator.Identity) or on not in (self.by, self.on):
            return self

        # Outer keys
        if not self.by or on == self.by:
            return Distribution(
                {k: self[k] for k in op.keep_relevant(self.keys())},
                on=self.on,
                by=self.by
            )

        # Inner keys
        relevant = op.keep_relevant(itertools.chain(*self.values()))
        clean = lambda x: {k: v for k, v in x.items() if v}
        return Distribution(
            clean({
                k1: {
                    k2: self[k1][k2]
                    for k2 in relevant.intersection(v1.keys())
                }
                for k1, v1 in self.items()
            }),
            on=self.on,
            by=self.by
        )

    @property
    def _constructor(self):
        return Distribution
