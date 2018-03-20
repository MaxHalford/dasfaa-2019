import fileinput
import ftplib
import glob
import os

import click
import sqlalchemy

from phd import tools


# Default database URI if none is provided through CLI arguments
URI = 'postgresql://postgres:admin@localhost:5432/tpcds'


@click.group()
def cli():
    pass


@cli.command()
def dlimdb():
    """Connects to the Free University of Berlin's FTP server and retrieves the
    IMDB data necessary used in the JOB benchmark. The retrieved data is stored
    in the data/imdb directory as a bunch of .gz files that can be ingested by
    the imdbpy2sql command."""

    # Connect to the FTP server and list it's content
    ftp = ftplib.FTP('ftp.fu-berlin.de')
    ftp.login()
    ftp.cwd('pub/misc/movies/database/frozendata')
    files = ftp.nlst()
    gz_files = [f for f in files if f.endswith('.gz')]

    # Make sure the output folder exists
    if not os.path.exists('data/imdb'):
        os.makedirs('data/imdb')

    # Download the files one by one
    for gz_file in gz_files:
        if os.path.exists('data/imdb/{}'.format(gz_file)):
            click.echo('{} has already been downloaded'.format(gz_file))
            continue
        file = open('data/imdb/{}'.format(gz_file), 'wb')
        click.echo('Downloading {}...'.format(gz_file))
        ftp.retrbinary('RETR {}'.format(gz_file), file.write)


@cli.command()
@click.argument('sql')
@click.argument('uri', default=URI)
def runsql(sql, uri):

    # Connect to the database
    engine = sqlalchemy.create_engine(uri)
    conn = engine.connect()

    # Read the SQL query is the argument is a file path
    if os.path.exists(sql):
        with open(sql, 'r') as query:
            conn.execute(sqlalchemy.text(query.read()).execution_options(autocommit=True))
    # If not execute the given argument
    else:
        conn.execute(sqlalchemy.text(sql).execution_options(autocommit=True))


@cli.command()
@click.argument('directory')
def cleantpcds(directory):

    for i, f in enumerate(glob.glob(os.path.join(directory, '*.dat'))):
        print('Cleaning {}...'.format(f))
        for line in fileinput.input(f, inplace=True):
            print(line.replace('|\n', ''))


@cli.command()
@click.argument('directory')
@click.argument('uri', default=URI)
def loadtpcds(directory, uri):

    # Connect to the database
    engine = sqlalchemy.create_engine(uri)
    conn = engine.connect().connection
    cursor = conn.cursor()

    for f in glob.glob(os.path.join(directory, '*.dat')):
        _, file = os.path.split(f)
        # Extract the table name
        table_name = file.split('.')[0]
        print('Loading {} data...'.format(table_name))
        # Truncate the table to make sure nothing is there
        cursor.execute('TRUNCATE TABLE {} CASCADE;'.format(table_name))
        # Run the copy query
        with open(os.path.abspath(f), 'rb') as sql_file:
            cursor.copy_from(sql_file, table_name, sep='|', null='')
    conn.commit()


@cli.command()
@click.argument('queries_dir')
@click.argument('uri', default=URI)
def run_queries(queries_dir, uri):

    # Connect to the database
    engine = sqlalchemy.create_engine(uri)

    # Load the JOB queries
    queries = [
        open(f).read()
        for f in glob.glob('{}/*.sql'.format(queries_dir))
        if f not in ('fkindexes.sql', 'schema.sql')
    ]

    # Run the queries one by one
    for query in queries[:1]:
        plan = tools.explain_query(query, engine)
        print(query)
        tools.print_json(plan)


@cli.command()
@click.argument('uri', default=URI)
def rmdb(uri):
    """Tread lightly."""
    engine = sqlalchemy.create_engine(uri)
    metadata = tools.get_metadata(engine)
    metadata.drop_all()


if __name__ == '__main__':
    cli()
