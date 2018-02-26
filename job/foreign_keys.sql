ALTER TABLE aka_name ADD FOREIGN KEY (person_id) REFERENCES name(id);

ALTER TABLE aka_title ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE aka_title ADD FOREIGN KEY (kind_id) REFERENCES kind_type(id);

ALTER TABLE cast_info ADD FOREIGN KEY (person_id) REFERENCES name(id);
ALTER TABLE cast_info ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE cast_info ADD FOREIGN KEY (person_role_id) REFERENCES role_type(id);

ALTER TABLE complete_cast ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE complete_cast ADD FOREIGN KEY (subject_id) REFERENCES comp_cast_type(id);
ALTER TABLE complete_cast ADD FOREIGN KEY (status_id) REFERENCES comp_cast_type(id);

ALTER TABLE movie_companies ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE movie_companies ADD FOREIGN KEY (company_id) REFERENCES company_name(id);
ALTER TABLE movie_companies ADD FOREIGN KEY (company_type_id) REFERENCES company_type(id);

ALTER TABLE movie_info ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE movie_info ADD FOREIGN KEY (info_type_id) REFERENCES info_type(id);

ALTER TABLE movie_info_idx ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE movie_info_idx ADD FOREIGN KEY (info_type_id) REFERENCES info_type(id);

ALTER TABLE movie_keyword ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE movie_keyword ADD FOREIGN KEY (keyword_id) REFERENCES keyword(id);

ALTER TABLE movie_link ADD FOREIGN KEY (movie_id) REFERENCES title(id);
ALTER TABLE movie_link ADD FOREIGN KEY (linked_movie_id) REFERENCES title(id);
ALTER TABLE movie_link ADD FOREIGN KEY (link_type_id) REFERENCES link_type(id);

ALTER TABLE person_info ADD FOREIGN KEY (person_id) REFERENCES name(id);
ALTER TABLE person_info ADD FOREIGN KEY (info_type_id) REFERENCES info_type(id);

ALTER TABLE title ADD FOREIGN KEY (kind_id) REFERENCES kind_type(id);
