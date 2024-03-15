create or replace table test_database.species (
	id UUID primary key not null default UUID(),
	classification VARCHAR(100) not null unique,
	name VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.encounter (
    id UUID primary key not null default UUID(),
    location VARCHAR(100) not null,
	notes VARCHAR(1000) not null,
    species_id UUID not null,
    constraint foreign key (species_id) references test_database.species (id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

create or replace table test_database.recording (
	id UUID primary key not null default UUID(),
	time_start DATETIME not null,
	time_end DATETIME,
	recording_file TEXT,
	selection_file TEXT,
	encounter_id UUID not null,
	constraint unique (time_start,encounter_id),
	constraint foreign key (encounter_id) references test_database.encounter (id)
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