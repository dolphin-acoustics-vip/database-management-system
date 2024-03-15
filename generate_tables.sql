create or replace table test_database.species (
	id UUID primary key not null default UUID(),
	species_name VARCHAR(100) not null unique,
	genus_name VARCHAR(100),
	common_name VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.encounter (
    id UUID primary key not null default UUID(),
	encounter_name VARCHAR(100) not null,
    location VARCHAR(100) not null,
	species_id UUID not null,
	origin VARCHAR(100),
	notes VARCHAR(1000),
    constraint foreign key (species_id) references test_database.species (id),
	constraint unique (encounter_name,location)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.file (
    id UUID PRIMARY KEY NOT NULL DEFAULT (UUID()),
    path TEXT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_date DATETIME,
	uploaded_by VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE TABLE IF NOT EXISTS test_database.recording (
    id UUID PRIMARY KEY NOT NULL DEFAULT (UUID()),
    start_time DATETIME NOT NULL,
    duration INT, 
    recording_file_id UUID,
    selection_file_id UUID,
    encounter_id UUID NOT NULL,
    CONSTRAINT unique_time_encounter_id UNIQUE (start_time, encounter_id),
    CONSTRAINT fk_encounter_id FOREIGN KEY (encounter_id) REFERENCES test_database.encounter (id),
    CONSTRAINT fk_recording_file_id FOREIGN KEY (recording_file_id) REFERENCES test_database.file (id),
    CONSTRAINT fk_selection_file_id FOREIGN KEY (selection_file_id) REFERENCES test_database.file (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;


create or replace table test_database.clip (
	id UUID primary key not null default UUID(),
	selection INT not null,
	clip_file TEXT,
	recording_id UUID not null,
	constraint unique (selection,recording_id),
	constraint foreign key (recording_id) references test_database.recording (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.roccaoutput (
	id UUID primary key not null default UUID(),
	csv_file TEXT,
	ctr_file TEXT
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;