import ftplib
import glob
import os

import click
import sqlalchemy

from phd import tools


# Default database URI if none is provided through CLI arguments
URI = 'postgresql://postgres:admin@localhost:5432/imdb'


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
@click.argument('uri', default=URI)
def runimdb(uri):

    # Connect to the database
    engine = sqlalchemy.create_engine(uri)

    # Retrieve the metadata
    metadata = tools.retrieve_metadata(engine)
    print(metadata.sorted_tables)

    return

    # Load the JOB queries
    queries = [
        open(f).read()
        for f in glob.glob('job/*.sql')
        if f not in ('fkindexes.sql', 'schema.sql')
    ]

    # Run the queries one by one
    for query in queries[:1]:
        plan = tools.explain_query(query, conn)
        print(plan)
    conn.close()


if __name__ == '__main__':
    cli()
