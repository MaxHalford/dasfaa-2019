import json

import pandas as pd
import sqlalchemy


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

    for val, freq in value_counts.iteritems():

        values_in_bin.append(val)
        cum_freq += freq

        if cum_freq >= bin_freq:
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
