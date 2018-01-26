import json

import sqlalchemy


def print_json(d, indent=4, sort_keys=True):
    print(json.dumps(d, indent=indent, sort_keys=sort_keys))


def explain_query(query, conn):
    """Executes a query against a connection and returns the execution plan."""

    # Determine the appropriate prefix
    prefixes = {
        'postgresql': 'EXPLAIN (ANALYZE true, FORMAT JSON)',
        'sqlite': 'EXPLAIN QUERY PLAN'
    }
    prefixes['postgres'] = prefixes['postgresql']
    explain_prefix = prefixes[conn.engine.name]

    result = conn.execute(sqlalchemy.text('{} {}'.format(explain_prefix, query)))
    print(query)
    print_json(result.first()[0])
    #plan = '\n'.join([row['QUERY PLAN'] for row in result])
    result.close()

    return None


def get_metadata(uri):
    """Returns metadata from a database given a database URI."""
    engine = sqlalchemy.create_engine(uri)
    metadata = sqlalchemy.MetaData()
    metadata.reflect(bind=engine)
    return metadata
