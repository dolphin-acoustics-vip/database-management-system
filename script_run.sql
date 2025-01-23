SET @@session.system_versioning_alter_history = 1;

ALTER TABLE file RENAME COLUMN path TO directory;
ALTER TABLE file ADD COLUMN to_be_deleted BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE species RENAME COLUMN species_name TO scientific_name;

ALTER TABLE file DROP COLUMN duration;
ALTER TABLE file DROP COLUMN uploaded_date;
ALTER TABLE file DROP COLUMN temp;

ALTER TABLE encounter DROP COLUMN encounter_date;

ALTER TABLE recording DROP COLUMN duration;
ALTER TABLE recording DROP COLUMN ignore_selection_table_warnings;

ALTER TABLE selection DROP CONSTRAINT fk_plot_file_id;
ALTER TABLE selection DROP COLUMN plot_file_id;
ALTER TABLE selection DROP CONSTRAINT fk_spectogram_file_id;
ALTER TABLE selection DROP COLUMN spectogram_file_id;
ALTER TABLE selection DROP COLUMN deactivate_selection;

ALTER TABLE user MODIFY COLUMN login_id VARCHAR(100) NOT NULL;
ALTER TABLE user DROP COLUMN password;