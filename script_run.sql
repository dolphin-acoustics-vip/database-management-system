ALTER TABLE file RENAME COLUMN path TO directory;
ALTER TABLE file ADD COLUMN to_be_deleted BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE species RENAME COLUMN species_name TO scientific_name;