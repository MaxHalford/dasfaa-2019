# join-order-benchmark
 This PACKAGE CONTAINS the
JOIN
ORDER Benchmark (JOB) queries
FROM: "How Good Are Query Optimizers, Really?" BY Viktor Leis,
                                                  Andrey Gubichev,
                                                  Atans Mirchev,
                                                  Peter Boncz,
                                                  Alfons Kemper,
                                                  Thomas Neumann PVLDB Volume 9,
                                                                              No. 3,
                                                                                  2015 [http://www.vldb.org/pvldb/vol9/p204-leis.pdf](http://www.vldb.org/pvldb/vol9/p204-leis.pdf) ### IMDB DATA
SET The CSV files used IN the paper,
                          which ARE
FROM May 2013,
         can be FOUND AT [http://homepages.cwi.nl/~boncz/job/imdb.tgz](http://homepages.cwi.nl/~boncz/job/imdb.tgz) The license
AND links TO the CURRENT VERSION IMDB DATA
SET can be FOUND AT [http://www.imdb.com/interfaces](http://www.imdb.com/interfaces) ### Step-BY-step instructions 1. download `*gz` files (unpacking NOT necessary) ```sh
  wget ftp://ftp.fu-berlin.de/pub/misc/movies/database/*gz
  ``` 2. download
AND unpack `imdbpy`
AND the `imdbpy2sql.py` script ```sh
  wget https://bitbucket.org/alberanid/imdbpy/get/5.0.zip
  ``` 3.
CREATE PostgreSQL DATABASE (e.g.,
                            name imdbload): ```sh
  createdb imdbload
  ``` 4.
TRANSFORM `*gz` files TO relational SCHEMA (takes a WHILE) ```sh
  imdbpy2sql.py -d PATH_TO_GZ_FILES -u postgres://username:password@hostname/imdbload
  ``` Now you should have a PostgreSQL DATABASE named `imdbload` WITH the imdb data. Note that this DATABASE has SOME secondary INDEXES (but NOT ON ALL
                                                                                                                                         FOREIGN KEY attributes). You can export ALL TABLES TO CSV: ```sql
\copy aka_name to 'PATH/aka_name.csv' csv
\copy aka_title to 'PATH/aka_title.csv' csv
\copy cast_info to 'PATH/cast_info.csv' csv
\copy char_name to 'PATH/char_name.csv' csv
\copy comp_cast_type to 'PATH/comp_cast_type.csv' csv
\copy company_name to 'PATH/company_name.csv' csv
\copy company_type to 'PATH/company_type.csv' csv
\copy complete_cast to 'PATH/complete_cast.csv' csv
\copy info_type to 'PATH/info_type.csv' csv
\copy keyword to 'PATH/keyword.csv' csv
\copy kind_type to 'PATH/kind_type.csv' csv
\copy link_type to 'PATH/link_type.csv' csv
\copy movie_companies to 'PATH/movie_companies.csv' csv
\copy movie_info to 'PATH/movie_info.csv' csv
\copy movie_info_idx to 'PATH/movie_info_idx.csv' csv
\copy movie_keyword to 'PATH/movie_keyword.csv' csv
\copy movie_link to 'PATH/movie_link.csv' csv
\copy name to 'PATH/name.csv' csv
\copy person_info to 'PATH/person_info.csv' csv
\copy role_type to 'PATH/role_type.csv' csv
\copy title to 'PATH/title.csv' csv
``` TO import the CSV files TO another DATABASE,
CREATE ALL TABLES (see `schema.sql`
                   AND optionally `fkindexes.sql`)
AND run the same COPY AS above statements but
REPLACE the keyword "to" BY "from". ### Questions Contact Viktor Leis (leis@in.tum.de) IF you have ANY questions.