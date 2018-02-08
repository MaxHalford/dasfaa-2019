from typing import Callable

import pandas as pd


class Interval(pd.Interval):

    def __eq__(self, other):
        if isinstance(other, (int, float, str)):
            return other in self
        return super().__eq__(other)


def split_common_uncommon(df: pd.DataFrame, on: str, n_most_common: int, n_bins: int) -> (pd.DataFrame, pd.DataFrame):
    most_common_vals = set(df[on].value_counts().nlargest(n_most_common).index)
    most_common_mask = df[on].isin(most_common_vals)
    common = df[most_common_mask]

    uncommon = df[~most_common_mask].copy()
    if not uncommon.empty:
        uncommon[on] = pd.qcut(uncommon[on], min(uncommon[on].nunique(), n_bins))

    return common, uncommon


class CPD():

    def __init__(self, on: str, by: str, n_most_common: int, n_bins: int):
        self.on = on
        self.by = by
        self.n_most_common = n_most_common
        self.n_bins = n_bins

        self.mcv = None
        self.lcv = None

    def __str__(self):
        return 'P({}|{})'.format(self.on, self.by) if self.by else 'P({})'.format(self.on)

    def __repr__(self):
        return str(self)

    def build_from_df(self, df: pd.DataFrame):

        on = self.on
        by = self.by
        n_most_common = self.n_most_common
        n_bins = self.n_bins

        if by:
            common, uncommon = split_common_uncommon(df, by, n_most_common, n_bins)
            self.mcv = pd.Series({
                k: CPD(on, None, n_most_common, n_bins).build_from_df(g)
                for k, g in common.groupby(by)
            })
            self.mcv.index.name = self.by
            self.lcv = pd.Series({
                k: CPD(on, None, n_most_common, n_bins).build_from_df(g)
                for k, g in uncommon.groupby(by)
            })
            self.lcv.index.name = self.by
        else:
            common, uncommon = split_common_uncommon(df, on, n_most_common, n_bins)
            self.mcv = pd.Series(common.groupby(on).size() / len(df))
            self.mcv.index.name = self.on
            self.lcv = pd.Series({
                k: len(set([x for x in df[on] if x in k]))
                for k, g in uncommon.groupby(on)
            })
            self.lcv.index.name = self.on

        return self

    def filter(self, f: Callable):
        filtered = CPD(on=self.on, by=self.by, n_most_common=self.n_most_common, n_bins=self.n_bins)
        filtered.mcv = self.mcv[self.mcv.index.map(f).values].copy()
        g = lambda x: f(Interval(x.left, x.right, x.closed))
        filtered.lcv = self.lcv[self.lcv.index.map(g).values].copy()
        return filtered
