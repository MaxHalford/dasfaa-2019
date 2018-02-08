CREATE TABLE aka_name (
    id integer NOT NULL PRIMARY KEY,
    person_id integer NOT NULL FOREIGN KEY (fk_aka_name_person_id) REFERENCES name(id),
    name text NOT NULL,
    imdb_index character varying(12),
    name_pcode_cf character varying(5),
    name_pcode_nf character varying(5),
    surname_pcode character varying(5),
    md5sum character varying(32)
);

CREATE TABLE aka_title (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_aka_title_person_id) REFERENCES title(id),
    title text NOT NULL,
    imdb_index character varying(12),
    kind_id integer NOT NULL FOREIGN KEY (fk_aka_title_kind_id) REFERENCES kind_type(id),
    production_year integer,
    phonetic_code character varying(5),
    episode_of_id integer,
    season_nr integer,
    episode_nr integer,
    note text,
    md5sum character varying(32)
);

CREATE TABLE cast_info (
    id integer NOT NULL PRIMARY KEY,
    person_id integer NOT NULL FOREIGN KEY (fk_cast_info_person_id) REFERENCES name(id),
    movie_id integer NOT NULL FOREIGN KEY (fk_cast_info_movie_id) REFERENCES title(id),
    person_role_id integer FOREIGN KEY (fk_cast_info_person_role_id) REFERENCES char_name(id),
    note text,
    nr_order integer,
    role_id integer NOT NULL FOREIGN KEY (fk_cast_info_role_id) REFERENCES role_type(id)
);

CREATE TABLE char_name (
    id integer NOT NULL PRIMARY KEY,
    name text NOT NULL,
    imdb_index character varying(12),
    imdb_id integer,
    name_pcode_nf character varying(5),
    surname_pcode character varying(5),
    md5sum character varying(32)
);

CREATE TABLE comp_cast_type (
    id integer NOT NULL PRIMARY KEY,
    kind character varying(32) NOT NULL
);

CREATE TABLE company_name (
    id integer NOT NULL PRIMARY KEY,
    name text NOT NULL,
    country_code character varying(255),
    imdb_id integer,
    name_pcode_nf character varying(5),
    name_pcode_sf character varying(5),
    md5sum character varying(32)
);

CREATE TABLE company_type (
    id integer NOT NULL PRIMARY KEY,
    kind character varying(32) NOT NULL
);

CREATE TABLE complete_cast (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer FOREIGN KEY (fk_complete_cast_movie_id) REFERENCES title(id),
    subject_id integer NOT NULL FOREIGN KEY (fk_complete_cast_subject_id) REFERENCES comp_cast_type(id),
    status_id integer NOT NULL FOREIGN KEY (fk_complete_cast_status_id) REFERENCES comp_cast_type(id)
);

CREATE TABLE info_type (
    id integer NOT NULL PRIMARY KEY,
    info character varying(32) NOT NULL
);

CREATE TABLE keyword (
    id integer NOT NULL PRIMARY KEY,
    keyword text NOT NULL,
    phonetic_code character varying(5)
);

CREATE TABLE kind_type (
    id integer NOT NULL PRIMARY KEY,
    kind character varying(15) NOT NULL
);

CREATE TABLE link_type (
    id integer NOT NULL PRIMARY KEY,
    link character varying(32) NOT NULL
);

CREATE TABLE movie_companies (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_movie_companies_movie_id) REFERENCES title(id),
    company_id integer NOT NULL FOREIGN KEY (fk_movie_companies_company_id) REFERENCES company_name(id),
    company_type_id integer NOT NULL FOREIGN KEY (fk_movie_companies_company_type_id) REFERENCES company_type(id),
    note text
);

CREATE TABLE movie_info (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_movie_info_movie_id) REFERENCES title(id),
    info_type_id integer NOT NULL FOREIGN KEY (fk_movie_info_info_type_id) REFERENCES info_type(id),
    info text NOT NULL,
    note text
);

CREATE TABLE movie_info_idx (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_movie_info_idx_movie_id) REFERENCES title(id),
    info_type_id integer NOT NULL FOREIGN KEY (fk_movie_info_idx_info_type_id) REFERENCES info_type(id),
    info text NOT NULL,
    note text
);

CREATE TABLE movie_keyword (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_movie_keyword_movie_id) REFERENCES title(id),
    keyword_id integer NOT NULL FOREIGN KEY (fk_movie_keyword_keyword_id) REFERENCES keyword(id)
);

CREATE TABLE movie_link (
    id integer NOT NULL PRIMARY KEY,
    movie_id integer NOT NULL FOREIGN KEY (fk_movie_link_movie_id) REFERENCES title(id),
    linked_movie_id integer NOT NULL FOREIGN KEY (fk_movie_link_linked_movie_id) REFERENCES title(id),
    link_type_id integer NOT NULL FOREIGN KEY (fk_movie_link_link_type_id) REFERENCES link_type(id)
);

CREATE TABLE name (
    id integer NOT NULL PRIMARY KEY,
    name text NOT NULL,
    imdb_index character varying(12),
    imdb_id integer,
    gender character varying(1),
    name_pcode_cf character varying(5),
    name_pcode_nf character varying(5),
    surname_pcode character varying(5),
    md5sum character varying(32)
);

CREATE TABLE person_info (
    id integer NOT NULL PRIMARY KEY,
    person_id integer NOT NULL FOREIGN KEY (fk_person_info_person_id) REFERENCES name(id),
    info_type_id integer NOT NULL FOREIGN KEY (fk_person_info_info_type_id) REFERENCES info_type(id),
    info text NOT NULL,
    note text
);

CREATE TABLE role_type (
    id integer NOT NULL PRIMARY KEY,
    role character varying(32) NOT NULL
);

CREATE TABLE title (
    id integer NOT NULL PRIMARY KEY,
    title text NOT NULL,
    imdb_index character varying(12),
    kind_id integer NOT NULL FOREIGN KEY (fk_person_info_kind_id) REFERENCES kind_type(id),
    production_year integer,
    imdb_id integer,
    phonetic_code character varying(5),
    episode_of_id integer,
    season_nr integer,
    episode_nr integer,
    series_years character varying(49),
    md5sum character varying(32)
);
