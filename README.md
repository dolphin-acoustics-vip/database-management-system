
<style>
.green {
    color: green;
    font-weight:700;
    font-size: 30px;
}
.warning {
    border-left: 5px solid red;
}
</style>

> ⚠️ **warning:** this project is still in a developmental stage. Some sections of the code and/or documentation may be incomplete.

# Dolphin Acoustics VIP Database Management System

This Database Management System (DBMS) is a project that aims to streamline the data pipeline of the Dolphin Acoustics VIP (the Project) at the University of St Andrews.

<a name="dependencies"></a>
## Dependencies
- Python 3.10.12 (Linux) from [here](https://www.python.org/downloads/release/python-31012/)
- All Python extensions in [requirements.txt](requirements.txt)
- MariaDB 11.3.2 from [here](https://mariadb.org/download/?t=mariadb&p=mariadb&r=11.3.2&os=windows&cpu=x86_64&pkg=msi&mirror=heanet-ltd)

## Glossary



## Project description
The DBMS was developed to store a range of files at various spots in the data pipeline of the Project (for more specific details on each file please view the project report):
- storage of raw audio recordings (wav)
- storage of selections of the recordings (wav)
- storage of summary selection tables (csv)
- storage of contours of the selections (csv) and their statistics
- export of contour files in contour
- quality assurance at each stage of the pipeline

The storage of data was split into two separate streams which were then brought together by a web application:
- storing file metadata in a database (the MetaBase)
- storing the files themselves in a file heirarchy (the File Space)


![alt text](image.png)

## Structure and setup
This repository includes all Webapp code, as well as helper code and documentation to setup the MetaBase and File Space.

<a name="setting-up-the-metabase"></a>
### Setting Up the MetaBase
The MetaBase was developed in MariaDB, which needs to be installed on a Linux machine or virtual machine before the Webapp can be run successfully (see [dependencies](#dependencies)).

Once downloaded, the MetaBase may be initialised and a new database created. The database must then be populated by running the script in [create_database.sql](create_database.sql).

### Setting Up the Python virtual environment
The Webapp was developed using Flask in Python, which needs to be installed on a Linux machine or virtual machine before the Webapp can be run successfully (see [dependencies](#dependencies)). 

To setup the virtual environment with all the required packages, run the following command from the root directory of the Webapp.

`python3 virtualenv venv && venv/bin/pip install -r requirements.txt`

<a name="setting-up-the-file-space"></a>
### Setting Up the File Space
The File Space is simply a designated path on the file system of the server (the machine running the Webapp). To set this folder, insert the relative or absolute path into [file_space_path.txt](file_space_path.txt) in the program root. For testing purposes it is recommended to use a relative path such as `filespace` as the File Space.

### Connecting the Web App to the MetaBase
The python script [db.py](db.py) handles all database connection. For security reasons, all database connection parameters were required to be stored in the global environment variables. 

The following are the parameters that must be set:
- `STADOLPHINACOUSTICS_HOST` to set the host of the database (usually `localhost` for local development environment)
- `STADOLPHINACOUSTICS_USER` to set the user of the database (usually `root` for local development environment)
- `STADOLPHINACOUSTICS_PASSWORD` to set the password of the database (must be set in the MariaDB shell)
- `STADOLPHINACOUSTICS_DATABASE` to set the name of the database (must be created in the MariaDB shell)

While it is recommended to set these variables manually, [set_os_variables.py](set_os_variables.py) was written to set these environemnt variables. Please read and understand the code beforehand and use with caution.

### Other setup instructions
If Google Maps are desired to view encounter coordinates, a Maps Embed API key is required to be placed in [google_api_key.txt](google_api_key.txt) in the program root. See [here](https://developers.google.com/maps/documentation/embed/get-api-key) for more details.

To start the server, run [app.py](app.py) from within the Python virtual environment from the root directory.


## The MetaBase
The metadata for each file was stored in a MariaDB database, otherwise called the MetaBase. See [Setting Up the Metabase](#setting-up-the-metabase).

The MetaBase currently models most data from the point of an audio recording to storing selections. An entity relationship diagram for the current MetaBase is shown below, where each entity contains attributes and foreign key references to other tables.

![ER Diagram](er_diagram.png)



Each entity was given a Universally Unique Identifier ([uuid](https://www.cockroachlabs.com/blog/what-is-a-uuid/)) such that foreign key references could be simplified. Additional unique and nullity constraints were therefore defined in each table to standardise data quality assurance.

The following subsections describe the tables from the ER diagram in more detail. Note that particular implemention details are found in [create_database.sql](). 

#### Encounter
Stores information on a marine animal encounter. Categorical information was stored in separate entities (*species*, *data_source*, and *recording_platform*) while other information in entity attributes.

#### File
Stores general metadata on a file stored in the File Space, such as the filename, extension, and upload date. Each file was given a unique ID that could be referenced by other entities that required file storage.

#### Recording
Stores information on each recording in an encounter. Intuitively, each *recording* references an *encounter* (many-to-one). 

#### Selection
Stores a particular selection (otherwise known as clip) from a recording. Intuitively, each *selection* references a *recording*.


## The File Space
All data files stored by the user in the DBMS are placed in the File Space. The File Space should already be initialised [above](#setting-up-the-file-space).

<blockquote class="warning">Warning: the File Space should rarely be manually modified by the Developer and never by the User. This is because changing file paths would invalidate the file references in the MetaBase.
</blockquote><br>

An important aspect of the File Space is its heirarchical structure that can be understood by the user. Namely, when a file is added to the DBMS, it is placed in an intuitive location within the File Space 