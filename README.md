# An Approach Based on Bayesian Networks for Query Selectivity Estimation

This contains the code used for the DASFAA 2019 paper entitled "*[An Approach Based on Bayesian Networks for Query Selectivity Estimation](https://link.springer.com/chapter/10.1007/978-3-030-18579-4_1)*". Disclaimer: the code is a bit more messy than what I'm used to producing. I've also been working on an improved version of this code since writing this paper, but it hasn't been published yet.

## Setup

1. [Install PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads#windows) (remember the credentials you choose!)
2. [Install Anaconda for Python 3](https://conda.io/docs/user-guide/install/index.html)
3. Run the following commands.

```sh
cd path/to/phd

# Setup Python virtual environment
conda create -n phd python=3.6
source activate phd # drop the "source" if you are on Windows
pip install -r requirements.txt
conda install pygraphviz
```

## TPC-DS

Create a database called `tpcds` in PostgreSQL.

```sh
cd tpcds-kit/tools
make OS=LINUX
./dsdgen -scale 3 -force
cd ...
python cli.py runsql tpcds-kit/tools/tpcds.sql URI
python cli.py cleantpcds tpcds-kit/tools
python cli.py loadtpcds tpcds-kit/tools
python cli.py runsql ANALYZE URI
```

## Join Order Benmarch (JOB)

```sh
# Install imdbpy
cd imdbpy
python setup.py install
cd ..

# Populate IMDB database
python cli.py dlimdb
python imdbpy/bin/imdbpy2sql.py -d data/imdb -u URI # takes a butload of time
python cli.py runsql job/foreign_keys.sql URI # Add the foreign key information
python cli.py runsql ANALYZE URI # Runs the ANALYZE command inside the DB
python cli.py run_queries URI job/queries
```

`URI` has to be a valid database string, such as `postgresql://user:password@localhost:5432/imdb`.

13, 41, 18, 26, 27, 28, 34, 48, 49, 53, 54, 63, 64, 7, 85, 89, 91
