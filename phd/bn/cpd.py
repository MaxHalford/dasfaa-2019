import numbers
from typing import Callable

import numpy as np
import pandas as pd

from phd import operator
from phd import tools


def discretize_series(series: pd.Series, n_mcv: int, n_bins: int) -> pd.Series:

    series = series.copy()

    # Treat most common values
    value_counts = series.value_counts()
    n_largest = value_counts.nlargest(n_mcv)
    most_common_vals = set(n_largest.index)
    most_common_mask = series.isin(most_common_vals)
    if series.dtype == 'datetime64[ns]':
        series[most_common_mask] = series[most_common_mask].apply(lambda x: pd.Interval(x, x, 'both'))
        series[~most_common_mask] = pd.to_datetime(series[~most_common_mask], unit='ns')
    else:
        series[most_common_mask] = series[most_common_mask].apply(lambda x: pd.Interval(x, x, 'both'))

    # Treat least common values
    n_least_common = series[~most_common_mask].nunique()
    n_bins = min(n_least_common, n_bins)
    if n_least_common > 0:
        # Histogram for categorical data
        if not isinstance(series.iloc[0], numbers.Number):
            series[~most_common_mask] = tools.categorical_qcut(series[~most_common_mask], q=n_bins)
        # Histogram for continuous data
        else:
            series[~most_common_mask] = pd.qcut(series[~most_common_mask], q=n_bins, duplicates='drop')
            # The intervals have to be closed for groupby purposes
            first_interval = series[~most_common_mask].iloc[0]
            close = lambda x: pd.Interval(x.left + 0.000001, x.right, 'both') if isinstance(x, pd.Interval) else x
            series[~most_common_mask] = series[~most_common_mask].apply(close)
            series[~most_common_mask].iloc[0] = first_interval

    bin_freq = (1 - n_largest.sum() / len(series)) / n_bins if n_bins > 0 else 0
    return series, most_common_vals, bin_freq


class CPD(pd.Series):

    # We want these properties to be kept when slicing or copying a CPD
    # Read more here: https://stackoverflow.com/a/35619846
    _metadata = ['on', 'by', 'n_mcv', 'n_bins', 'bin_freq', 'sub_bin_freqs']

    def __init__(self, *args, **kwargs):
        on = kwargs.pop('on', None)
        by = kwargs.pop('by', None)
        n_mcv = kwargs.pop('n_mcv', None)
        n_bins = kwargs.pop('n_bins', None)
        super().__init__(*args, **kwargs)
        self.on = on
        self.by = by
        self.n_mcv = n_mcv
        self.n_bins = n_bins
        self.bin_freq = None
        self.sub_bin_freqs = {}

    def build_from_df(self, df: pd.DataFrame):

        on = self.on
        by = self.by
        n_mcv = self.n_mcv
        n_bins = self.n_bins

        if by:
            subset = df[[on, by]].dropna()
            subset[by], _, self.bin_freq = discretize_series(
                series=subset[by],
                n_mcv=n_mcv,
                n_bins=n_bins
            )
            inner_cpds = []
            for k, g in subset.groupby(by):
                inner_cpd = CPD(on=on, by=None, n_mcv=n_mcv, n_bins=n_bins)
                inner_cpd.build_from_df(g)
                inner_cpd.index = pd.MultiIndex.from_tuples(
                    [(k, idx) for idx in inner_cpd.index],
                    names=[by, on],
                )
                self.sub_bin_freqs[k] = inner_cpd.bin_freq
                inner_cpds.append(inner_cpd)
            counts = pd.concat(inner_cpds) if len(inner_cpds) > 0 else pd.Series()
        else:
            col = df[self.on].dropna()
            series, most_common_vals, self.bin_freq = discretize_series(
                series=col,
                n_mcv=n_mcv,
                n_bins=n_bins
            )
            def count(g):
                interval = g.name
                if interval.left == interval.right:
                    return len(g) / len(df)
                return len(set([x for x in col if x in interval and x not in most_common_vals]))
            counts = series.groupby(series).apply(count)

        # In some cases a groupby followed by an apply can return a DataFrame
        if isinstance(counts, pd.DataFrame):
            counts = counts.stack()

        super().__init__(counts)

        return self

    def subset(self, on: str, op: operator.Operator):

        # Maybe nothing has to be done
        if not op or isinstance(op, operator.Identity) or on not in self.index.names:
            return self

        # Vanilla index
        if len(self.index.names) == 1:
            if isinstance(op, operator.Equal):
                matches = self[self.index == op.operand]
                if not matches.empty:
                    return matches
            return self[self.index.map(lambda interval: op.calc_coverage(interval, 2)).values > 0]

        # MultiIndex
        on_idx_pos = self.index.names.index(on)
        if isinstance(op, operator.Equal):
            matches = self[self.index.map(lambda x: x[on_idx_pos] == op.operand).values]
            if not matches.empty:
                return matches
        return self[self.index.map(lambda x: op.calc_coverage(x[on_idx_pos], 2)).values > 0]

    @property
    def _constructor(self):
        return CPD
