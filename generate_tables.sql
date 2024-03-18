create or replace table test_database.species (
	id UUID primary key not null default UUID(),
	species_name VARCHAR(100) not null unique,
	genus_name VARCHAR(100),
	common_name VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE OR REPLACE TABLE test_database.data_source (
    id UUID primary key not null default UUID(),
    name VARCHAR(255),
    phone_number1 VARCHAR(20) UNIQUE,
    phone_number2 VARCHAR(20) UNIQUE,
    email1 VARCHAR(255) NOT NULL UNIQUE,
    email2 VARCHAR(255) UNIQUE,
    address TEXT,
    notes TEXT,
    type ENUM('person', 'organisation')
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

CREATE OR REPLACE TABLE test_database.recording_platform (
	id UUID primary key not null default UUID(),
	name VARCHAR(100) not null unique
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.encounter (
    id UUID primary key not null default UUID(),
	encounter_name VARCHAR(100) not null,
    location VARCHAR(100) not null,
	species_id UUID not null,
	origin VARCHAR(100),
	longitude VARCHAR(20),
	latitude VARCHAR(20),
	notes VARCHAR(1000),
	date_received DATE, 
	data_source_id UUID,
	recording_platform_id UUID,
    constraint foreign key (species_id) references test_database.species (id),
	constraint foreign key (data_source_id) references test_database.data_source (id),
	constraint foreign key (recording_platform_id) references test_database.recording_platform (id),
	constraint unique (encounter_name,location)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.file (
    id UUID PRIMARY KEY NOT NULL DEFAULT (UUID()),
    path TEXT NOT NULL,
    filename VARCHAR(255) NOT NULL,
	extension VARCHAR(10) NOT NULL,
    uploaded_date DATETIME,
	uploaded_by VARCHAR(100),
	duration INT
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


create or replace table test_database.selection (
	id UUID primary key not null default UUID(),
	selection_number INT not null,
	selection_file_id TEXT not null,
	recording_id UUID not null,
	constraint unique (selection_number,recording_id),
	constraint foreign key (recording_id) references test_database.recording (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.contour (
	id UUID primary key not null default UUID(),
	
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;




