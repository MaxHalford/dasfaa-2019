import ast
import json
import numbers

import pandas as pd
import sqlalchemy

from . import operator as op


def print_json(d, indent=4, sort_keys=True):
    """Pretty prints a dictionary."""
    print(json.dumps(d, indent=indent, sort_keys=sort_keys))


def explain_query(query, engine):
    """Executes a query against a connection and returns the execution plan."""

    # Connect to the database
    conn = engine.connect()

    # Set the prefix
    explain_prefix = 'EXPLAIN (ANALYZE true, FORMAT JSON, VERBOSE true)'

    # Run the query and retrieve the query plan
    result = conn.execute(sqlalchemy.text('{} {}'.format(explain_prefix, query)))
    plan = result.first()[0]
    result.close()

    return plan


def get_metadata(engine):
    """Returns metadata from a database given a database URI."""
    metadata = sqlalchemy.MetaData(bind=engine)
    metadata.reflect(bind=engine)
    return metadata


def categorical_qcut(series, q):
    """Computes categorical quantiles of a pandas.Series objects."""
    bin_freq = 1 / q
    value_counts = series.value_counts(normalize=True).sort_index()
    bins = {}

    values_in_bin = []
    cum_freq = 0

    for i, (val, freq) in enumerate(value_counts.iteritems()):

        values_in_bin.append(val)
        cum_freq += freq

        if cum_freq >= bin_freq or (i+1) == len(value_counts):
            values_in_bin = sorted(values_in_bin)
            interval = pd.Interval(left=values_in_bin[0], right=values_in_bin[-1], closed='both')
            for v in values_in_bin:
                bins[v] = interval
                values_in_bin = []
                cum_freq = 0

    return series.apply(lambda x: bins.get(x))


def calc_interval_overlap(a: pd.Interval, b: pd.Interval):
    """Computes the overlap ratio of a on b."""
    if b.left == b.right:
        return 1 if b.left in a else 0
    if a.left > b.right:
        return 0
    if a.right < b.left:
        return 0

    if type(a.left) == str:
        return 0.3

    return min(1, (a.right - a.left) / (b.right - b.left))


def format_interval(x):
    if isinstance(x, pd.Interval):
        if x.closed_left:
            if x.closed_right:
                return '[{} %,% {}]'.format(x.left, x.right)
            return '[{} %,% {})'.format(x.left, x.right)
        if x.closed_right:
            return '({} %,% {}]'.format(x.left, x.right)
        return '({} %,% {})'.format(x.left, x.right)
    return str(x)


def discretize_series(series: pd.Series, n_mcv: int, n_bins: int) -> pd.Series:

    s = series.copy()

    # Remove trailing whitespace
    if s.dtype == 'object':
        s = s.str.rstrip()

    # Treat most common values
    value_counts = s.value_counts()
    n_mcv = len(value_counts) if n_mcv == -1 else n_mcv
    n_largest = value_counts.nlargest(n_mcv)
    most_common_vals = set(n_largest.index)
    most_common_mask = s.isin(most_common_vals)

    # Treat least common values
    n_least_common = s[~most_common_mask].nunique()
    n_bins = min(n_least_common, n_bins)
    if n_least_common > 0:
        # Histogram for categorical data
        if not isinstance(s.iloc[0], numbers.Number):
            s[~most_common_mask] = categorical_qcut(s[~most_common_mask], q=n_bins)
        # Histogram for continuous data
        else:
            s[~most_common_mask] = pd.qcut(s[~most_common_mask], q=n_bins, duplicates='drop')

    # Replace np.nan with None
    s = s.where((pd.notnull(s)), None)

    # Count the number of distinct values per bin
    n_distinct = {}
    for hist_bin in s[~most_common_mask].unique():
        if hist_bin is not None:
            n_distinct[str(hist_bin)] = len(set(
                x
                for x in series
                if x and x in hist_bin and
                x not in most_common_vals
            ))

    # I hate this shit
    s = s.apply(format_interval)

    return s, n_distinct


def parse_filter(f: str) -> dict:

    ops = {
        '==': op.Equal,
        'in': op.In
    }

    def part_to_op(part: str) -> op.Operator:

        op_start = part.find(' ') + 1
        att = part[:op_start-1]
        op_end = part[op_start:].find(' ')
        op_name = part[op_start:op_start+op_end]
        operand = part[op_start+op_end+1:]

        if operand.startswith('"') or operand.startswith("'"):
            operand = operand[1:-1]

        if operand.startswith('[') or operand.startswith("("):
            operand = ast.literal_eval(operand)
        elif operand.isdigit():
            operand = float(operand)

        return att, ops[op_name](operand)

    return dict(
        part_to_op(part)
        for part in f.split(' and ')
    )
