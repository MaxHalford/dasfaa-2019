## Setup

1. [Install PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads#windows) (remember the credentials you choose!)
2. Create a database in PostgreSQL called `imdb`
3. [Install Anaconda for Python 3](https://conda.io/docs/user-guide/install/index.html)
4. Run the following commands.

```sh
cd path/to/phd

# Setup Python virtual environment
conda create -n phd python=3.6
source activate phd # drop the "source" if you are on Windows

# Install Python libraries
cd imdbpy
python setup.py install
cd ..
pip install -r requirements.txt

# Populate IMDB database
python cli.py dlimdb
python imdbpy/bin/imdbpy2sql.py -d data/imdb -u URI # takes a butload of time
python cli.py runimdb URI
```

`URI` has to be a valid database string, such as `postgresql://user:password@localhost:5432/imdb`.

## Papers

- [Duke database course](https://www.cs.duke.edu/courses/compsci516/)
- [Is query optimization a "solved" problem?](http://wp.sigmod.org/?p=1075)
- [Access Path Selection in a Relational Database Management System](https://www.cs.duke.edu/courses/compsci516/cps216/spring03/papers/selinger-etal-1979.pdf)
- [The Red Book](http://www.redbook.io/) (specifically the [chapter on query optimization](http://www.redbook.io/ch7-queryoptimization.html))
