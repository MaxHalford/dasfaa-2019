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
