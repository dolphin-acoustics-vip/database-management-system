<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a>
    <img src="ocean/app/resources/OCEAN-banner.png" alt="Logo" width="150" height="80">
  </a>

  <h3 align="center">Odontocete Call Environment and Archival Network</h3>

  <p align="center">
    A database management system for dolphin acoustic research at the University of St Andrews
    <br />
    <a href="https://github.com/dolphin-acoustics-vip/database-management-system/wiki"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/dolphin-acoustics-vip/database-management-system/issues">Report Bug</a>
    &middot;
    <a href="https://github.com/dolphin-acoustics-vip/database-management-system/issues/new?template=feature_request.md">Request Feature</a>
  </p>
</div>

## About The Project

The Odontocete Call Environment and Archival Network (OCEAN) is a web application that streamlines the storage and processing of acoustic data (specifically, recordings of dolphin whistles).

The software facilitates the storage of passive acoustic recording files, selections from those recording files and contour traces of the selections.

Familiarity with the data pipeline and implementation strategy found in the [user documentation](https://github.com/dolphin-acoustics-vip/database-management-system/wiki) is essential.

## Getting Started

OCEAN is a web application that manages both a database and a filespace. These **must** be correctly installed before attempting to modify the code.

We provide a docker image for the development environment. Ensure you have docker installed on your local system, then run the following command in the root directory of OCEAN.

```
docker compose up --build
```

This will create 2 volumes: one for the database and one for the filespace. By default, the
filespace is mounted to `/app/filespace` and the database is mounted to `/var/lib/mysql`. This
allows you to build new containers without having to re-initialise the database nor filespace.

If you want to wipe the database and and filespace, run the following command.

```
docker compose down -v
docker compose up --build
```

By default, OCEAN runs on port 5000 accessible at `http://localhost:5000`. You will be logged into
an admin account with username `Admin` (see [init_roles_and_admin.sql](/db-init/init_roles_and_admin.sql)).
If you make any changes to the database, these changes need to be manually applied to the docker database
container. Alternatively, reset the container and ensure up-to-date sql exists in the [db-init](/db-init) folder.

If you don't have docker installed, follow the manual installation instructions below.

### Prerequisites

OCEAN was developed in Python 3. It was built to work with a standard install of the MariaDB Server of the version stated below.

- Python 3.10.12 from [here](https://www.python.org/downloads/release/python-31012/)
- MariaDB 10.5.23 from [here](https://mariadb.org/download/?t=mariadb&o=true&p=mariadb&r=10.5.23&os=Linux&cpu=x86_64&i=systemd&mirror=archive)

If you are developing on Windows, install the [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/about) before continuing. Development on MacOS is not recommended, however can work - please take extra care installing MariaDB propertly using `brew`.

To install MariaDB on windows, simply use the installer found in the link above. 

To install MariaDB on MacOS use Homebrew (ensure `mysql` is removed before installing `mariadb` as they contain conflicting binaries)
```
brew remove mysql
brew install mariadb

# to auto-start the server on startup
brew services start mariadb
```

To install MariaDB on Ubuntu/Debian

```
sudo apt update
sudo apt install mariadb-server
sudo mysql_secure_installation
```

#### Verifying your MariaDB Installation

In the [Installation](#installation) section, below, you will initialise all the required tables for OCEAN to operate in MariaDB. Before preceeding, however, it is good to check that you can access MariaDB on your system. This means you should have a MariaDB client installed. This may have been packaged with your installation of the server, so see if you can access the client with the command

```
mariadb -u root -p
```

Note the `-u root` tells the client to access the server through the `root` user and `-p` says you will provide it with a password. If you set up MariaDB without a password, you don't need to include `-p`.

If you get a connection error to the server, you may need to start or restart the server.

On Windows (with Administrator permissions)
```
net stop mariadb
net start mariadb
```

On Ubuntu/Debian
```
sudo systemctl stop mariadb
sudo systemctl start mariadb
```

On MacOS (if installed with `brew`) - [More info](https://mariadb.com/kb/en/installing-mariadb-on-macos-using-homebrew/)
```
mysql.server start

# To auto-start the service on start-up
brew services stop mariadb
brew services start mariadb
```

<a name="initialising-the-mariadb-database"></a>
#### Initialising the MariaDB Database

If you have a fresh install of MariaDB or have not previously used OCEAN on your system before, you will need to create a new database from the MariaDB client (in the example before the name of the database is `ocean` but this can be whatever you prefer - this will be configured in [Variables](#variables)).

```
CREATE DATABASE ocean;
use ocean;
```

All the required tables will need to be created. Do this by copying the entirety of [create_database.sql](/db-init/create_database.sql) into the MariaDB client. This will create all tables.

To access OCEAN you will need to insert a user into the `user` table of the database. The command below should be run to create an `admin` user (this assumes the script above has been run).

```
INSERT INTO user (login_id, name, role_id, is_active) VALUES ('admin', 'Admin', 1, 1);
```

<a name="installation"></a>
### Installation

1. Clone the repository (the example below uses HTTPS, but SSH works too provided it is set up on your system)
   
   ```
   git clone https://github.com/dolphin-acoustics-vip/database-management-system.git

2. Create a virtual environment in the cloned folder
   
   ```
   python -m venv venv

3. Activate the virtual environment
   ```
   // On MacOS and Linux
   source venv/bin/activate
   // On Windows
   venv\Scripts\activate.bat
  
4. Use the PIP package manager to install all the dependencies in [requirements.txt](requirements.txt) (see [Installing `mysqlclient`](#installing-mysqlclient) below)
   ```
   pip install -r requirements.txt

5. **Before** this step ensure you have followed the instructions in [Initialising the MariaDB Database](#initialising-the-mariadb-database)
   
   Link the `database` and `filespace` by setting the following environment variables (note: see Production Setup instead if installing OCEAN in a production environment). On MacOS/Linux run the following commands (see [Variables](#variables) for definitions for all `<x>`):
   ```
   # export is used on MacOS/Linux
   # on Windows replace export with SET
   export DEV_STADOLPHINACOUSTICS_HOST=<host>
   export DEV_STADOLPHINACOUSTICS_USER=<user>
   export DEV_STADOLPHINACOUSTICS_DATABASE=<database>
   export DEV_STADOLPHINACOUSTICS_PASSWORD=<password>
   export OCEAN_FILESPACE_PATH=<filespace>
   ```

6. Authenticate access to OCEAN. In the production environment OCEAN reads an email from the `HTTP_EPPN` environment variable. In the development environment you need to define the following environment variable (assuming the `admin` user was added to the database in [Initialising the MariaDB Database](#initialising-the-mariadb-database)):
   ```
   # export is used on MacOS/Linux
   # on Windows replace export with SET
   export OCEAN_SSO_OVERRIDE=admin
   ```

    > WARNING: THIS MUST NEVER BE USED ON THE PRODUCTION ENVIRONMENT. IT WILL ALLOW ANY INDIVIDUAL TO ACCESS OCEAN WITHOUT PROPER AUTHENTICATION.

<a name="variables"></a>
#### Variables
`host` is the database host (for local instances of MariaDB this will be `localhost`)

`user` is the name of the user profile through which the database should be accessed (for local instances of MariaDB this will be `root`). To check if you can access MariaDB through the `root` user run `mariadb -u root -p` in the command line utility.

`database` is the name of the database that should be accessed by OCEAN (see [Initialising Database]())

`password` is the password used by `user` to access the database (even if you don't have a password, define the environment variable as empty)

`filespace` is the ABSOLUTE path to the filespace on the system (use `/` on MacOS and Linux and `\` on Windows). The entire path up to and including the outer-most folder of the filespace must be stored in this variable

<a name="installing-mysqlclient"></a>
#### Installing `mysqlclient`

Depending on the way you installed MariaDB onto your system, certain flags may not be correctly configured for mysqlclient to install. The following commands mayn eed to be run.

On Debian/Ubuntu:

```
sudo apt-get update sudo apt-get install gcc libmysqlclient-dev python3-dev
pip install mysqlclient
```

On MacOS:

```
brew install mysql pkg-config
pip install mysqlclient
```


### Usage

To start the Web App on the server, activate the virtual environment and run `python ocean/run.py` from the root directory.

A production server should use the [wsgi.py](/ocean/wsgi.py) script provided (which automatically configures the application for a production environment)

## Maintaining and Operating the Web App
The Web App brings together the database and the filespace into a single user interface. The Flask framework in Python is used to do this.

OCEAN can be roughly split into the following key components:

1. `Models` are the ORM representations of the tables in the MariaDB database. Most of the insertion, updating and deleting of data are handled in each model.
2. `Routes` are the API endpoints which are accessed by the user. Routes are restricted to only be accessible by users with certain roles.
3. `Utilities` are aditional files found in [/ocean/app](/ocean/app/) that contain custom exceptions, calculations, utility methods, and filespace (IO) utilities. 
4. `Templates` are the HTML, CSS and JS frontend files that are rendered by the `Routes` on request.


# Data Model

## Overview

The data is stored in a MariaDB database using SQLAlchemy. Each table is represented by a class in Python, defined in [models.py](../models.py). 

## Unique IDs

Most tables use unique IDs as primary keys, generated using MariaDB's UUID() method. This creates a 36-character string in the format `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`. Unique constraints are also defined separately on specific attributes to ensure data integrity.

## File Storage

> ⚠️ **Warning:** the File Space should rarely be manually modified by the Developer and never by the User. This is because changing file paths would invalidate the file references in the Meta Base.

![File Space](documentation/readme-resources/file-space.png)

*The File Space shown in a diagramattic form. Note that the naming conventions are for demonstration purposes only and do not accurately reflect the implementation of the File Space*

Files are stored in unique paths, with each file represented by a `File` class object. All data files stored by the user in the DBMS are placed in the File Space. The File Space should already be initialised [above](#setting-up-the-file-space). The following techniques are used for file storage:

### Creating a Unique Path

When a file needs to be saved, a new `File` object is created and referenced as a foreign key in its parent class. The parent class provides the path (directory and filename) to the `File` object. This ensures that each file is associated with a specific parent object and can be easily retrieved.

* Filenames are generated using methods in the parent class. This allows for consistent naming conventions and ensures that filenames are unique within a given directory.
* Directories are generated using methods in the parent class. This allows for a hierarchical organization of files and ensures that files are stored in a logical and consistent manner.

The directory and filename are then passed to the `File` object using `insert_path_and_filename()`. This method updates the `File` object with the generated path and filename, ensuring that the file is stored in the correct location.

### Changing Paths

When metadata changes, the file location must be updated to reflect the new metadata. The `Encounter`, `Recording`, and `Selection` classes are responsible for updating their file locations using the `update_call()` method.

* The `update_call()` method is called when metadata changes, such as when the `Encounter` name is updated.
* The `update_call()` method calls the `move_file()` method in child `File` objects, which updates the file location to reflect the new metadata.

This ensures that files are always stored in a location that reflects the current metadata, and that files can be easily retrieved using the updated metadata.

### Handling Duplicate Files

If a file already exists in the target path, the existing file is renamed using `File.rename_loose_file()`. This prefixes a unique ID to the existing file, allowing the file to be moved to the desired location.

>Note: This should never happen, as file paths are chosen to be unique alongside the database metadata. However, in the unlikely event that a duplicate file is detected, this mechanism ensures that the file is renamed and can be stored in the desired location. An error is written to the log in this case, indicating that a duplicate file was detected and renamed. This allows for easy identification and resolution of any issues related to duplicate files.

### Handling File Deletion

The `delete()` method prevents foreign key error references upon delete. Upon the deletion request of a master object (by calling `delete()` in the master), the  `delete()` method in each child is added to the call stack, which ensures all slaves are removed from the database before a master.

The `delete()` method in `Encounter`, `Recording`, and `Selection` are responsible for removing all their own files before returning to the master.

> ⚠️ **Warning:** cascading delete is dangerous, and where it is implemented the user should always be warned before execution.

## Testing
Testing is found in the [tests](/tests) folder. Python files exist there within the [pytest](https://docs.pytest.org/en/stable/) framework. Tests can be run with `python3 -m pytest tests` from the root directory.

The test environment is automatically created, and is effectively an instance of the Flask application. This means all setup instructions **MUST** be followed before running tests.

The following tests are included in the [tests](/tests) folder. Some require files to exist in the [tests/resources](/tests/resources) directory:

**Test Contour Stats**

[test_contour_stats.py](/tests/test_contour_stats.py) tests the calculation of contour statistics. The running of these tests requires a number of resources to exist in [tests/resources/contour-stats](/tests/resources/contour-stats/):
* A sub-folder prefixed with `test#` exactly (e.g., test1, test8, test15) should be made for each recording that is to be tested. 
* In this folder, a file, `RoccaContourStats.xlsx` (exactly) must exist with the expected values of the contour statistics calculations.
* Any number of CSV contour files must exist, prefixed with `sel_#` exactly (e.g., sel_1, sel_01, sel_10, sel_100). 
* A column in `RoccaContourStats.xlsx` must be made, `SelectionNumber` with the same integer value that is used in the previous step to name the CSV contour files. The test will fail if there exist CSV files without a respective row in `RoccaContourStats.xslx`

An example of this setup is shown here:
![alt text](/documentation/readme-resources/contour-stats-test-example.png)

**Test Encounter**

[tests/test_encounter.py](/tests/test_encounter.py) tests the Encounter class in [models.py](/models.py). 

**Test Errors**

[tests/test_errors.py](/tests/test_errors.py) tests methods and classes in [exception_handler.py](/exception_handler.py).

**Test Recording**

[tests/test_recording.py](/tests/test_recording.py) tests the Recording class in [models.py](/models.py).

**Test Restricted Routes**

[tests/test_restricted_routes.py](/tests/test_restricted_routes.py) tests whether access is forbidden to the required routes for users without certain access permissions.

**Test Utils**

[tests/test_utils.py](/tests/test_utils.py) tests a number of general utilities classes stored in [utils.py](/utils.py). 

Certain tests (testing the reading of CSV, TSV and XLSX files into Pandas) require the following files to exist in [tests/resources/utils](/tests/resources/utils/):
* `dataframe-3-rows.csv` a CSV file with 3 data rows (any number of columns allowed).
* `dataframe-3-rows.txt` a TSV file with 3 data rows (any number of columns allowed).
* `dataframe-3-rows.xlsx` an Excel file with 3 data rows (any number of columns allowed).
* `dataframe-empty.csv` a CSV file with no rows.
* `dataframe-empty.txt` a TSV file with no rows.
* `dataframe-empty.xlsx` an Excel file with no rows.

This should look like:
![alt text](documentation/readme-resources/utils-test-example.png)
