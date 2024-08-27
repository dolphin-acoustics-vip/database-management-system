> ⚠️ **Warning:** this project is still in a developmental stage. Some sections of the code and documentation may be incomplete.

[Wiki page](wiki/).

# Dolphin Acoustics VIP Database Management System

The Database Management System (DBMS) is a project that aims to streamline the data pipeline of the Dolphin Acoustics Vertically Integrated Project at the University of St Andrews (the Project).

The ensuing documentation details the installation and structure of the code written for the DBMS.

Familiarity with the data pipeline and implementation strategy found in the April 2024 DBMS handover document are required. General computer science competency, as well as more specific familiarity with the [requirements](#requirements) are also prerequesite.

<a name="requirements"></a>
<a name="dependencies" depracated></a>
## Requirements

The Web App has been developed on, and for, a Lunix based system (Debian 12). It is recommended to continue development on a Linux machine, whether physical or virtual. Listed below are dependencies of the DBMS:

- Python 3.10.12 (Linux) from [here](https://www.python.org/downloads/release/python-31012/)
- All Python libraries in [requirements.txt](requirements.txt)
- MariaDB 11.3.2 from [here](https://mariadb.org/download/?t=mariadb&p=mariadb&r=11.3.2&os=windows&cpu=x86_64&pkg=msi&mirror=heanet-ltd)

Note: MariaDB version **must** be of the stated version. Tables use the UUID package which is not available in some versions of maria db. See [here](https://mariadb.com/kb/en/installing-mariadb-deb-files/).

Note: mysqlclient must have its dependencies installed before pip3 installing itself. See [here](https://pypi.org/project/mysqlclient/)

### Installing Maria DB v10.5.23 on Linux

Maria DB 10.5.23 is an old version that is used to maintain compatability with the intended production environment of OCEAN. The best way to set up your test environment with this version is to use a container such as Docker. See details below on how to install the required MariaDB version using Docker.

Note that this guide was made using Ubuntu 22.04 (Jammy)

Ensure all current MariaDB servers are removed

`sudo apt-get purge mariadb-server*`

Install Docker

`sudo apt-get update`
`sudo apt-get install docker.io`

Pull the MariaDB image

`sudo docker pull mariadb:10.5.23`

Start a Maria DB container using the image and persist it

`docker run --name mariadb-10.5.23 -e MYSQL_ROOT_PASSWORD=<Password> -v </my/own/datadir>:/var/lib/mysql -p 3306:3306 -d mariadb:10.5.23`

Note: replace <Password> with the password that will be used to access the database.
Note: replace </my/own/datadir> with the desired persistent container location on your drive (this will be mapped to the SQL path, /var/lib/mysql).

Access the MariaDB server environment

`sudo docker exec -it mariadb-10.5.23 mysql -u root -p`
Note: you will be prompted to enter the password you made above.





## Project description
The DBMS was developed to store data with its metadata in a homogenised system that could be easily interacted with by members of the Project (the Team). Certain functionalities of the DBMS include:
- storage of raw audio recordings (wav)
- storage of selections of the recordings (wav)
- storage of aggregate selection tables (csv)
- storage of contours of the selections (csv)
- Storage of aggregate contour statistics (csv)
- export of contour files in a different format (ctr)
- quality assurance at each stage of the pipeline
> **Note:** not all functionalities listed above have been implemented. In addition, the list above is neither detailed nor exhaustive. For a live record of all feature requests, please view the GitHub issues page. For more detail  on the design of each of these stages, please view the DBMS April 2024 handover document.

The storage of such data was split into two separate streams which were then managed by a Web App:
- storing file metadata in a database (the Meta Base)
- storing the files themselves in a file heirarchy (the File Space)


![alt text](documentation/readme-resources/data-flow-high-level.png)

*High level data flow diagram of the DBMS*

<a name="structure-and-setup"></a>
## Structure and setup
> ⚠️ **Warning** development must be completed on a native linux system or linux subsystem.

This repository includes all code pertaining to the Web App. Instructions exist below for setting up the python virtual environment to successfully run the Web App, as well as initialising the Meta Base and File Space so it can run in tandem with the Web App.

<a name="initialising-the-meta-base"></a>
### Initialising the Meta Base
> Please consult MariaDB documentation for instructions on how to complete the the following actions.

The Meta Base uses MariaDB as its server technology, which needs to be installed on a Linux machine or virtual machine before the Web App can be run successfully (see [dependencies](#dependencies)).

Once downloaded, the Meta Base may be initialised and a new database created. The database must then be populated by running the script in [create_database.sql](create_database.sql).

<a name="creating-the-virtual-development-environment"></a>
### Creating the virtual development environment
The Web App was developed using an array of libraries defined [above](#requirements). To create a virtual environment and install all the required libraries, the following code must be run in the Web App root folder:

`python3 virtualenv venv && venv/bin/pip install -r requirements.txt`

From the root folder, the virtual environment can then be started using the following command:

 `source venv/bin/activate`

> ⚠️ **Warning:** to prevent clutter on the git repository, please ensure the virtual environment folder name is placed in the [gitignore](.gitignore) file.

<a name="setting-up-the-file-space"></a>
### Setting up the File Space
The File Space is simply a designated path on the file system of the server (the machine running the Web App). To set this folder, insert the relative or absolute path into [file_space_path.txt](file_space_path.txt) in the program root. For testing purposes it is recommended to use a relative path such as `filespace` as the File Space.

### Connecting the Web App to the Meta Base
The python script [db.py](db.py) handles all database connection. For security reasons, all database connection parameters are stored in global environment variables. 

The following are the variables that must be set:
- `STADOLPHINACOUSTICS_HOST` to set the host of the database (usually `localhost` for development environment)
- `STADOLPHINACOUSTICS_USER` to set the user of the database (usually `root` for development environment)
- `STADOLPHINACOUSTICS_PASSWORD` to set the password of the database (must be set in the MariaDB shell)
- `STADOLPHINACOUSTICS_DATABASE` to set the name of the database (must be created in the MariaDB shell)

While it is recommended to set these variables manually, [set_os_variables.py](set_os_variables.py) was written to set them automatically. Please read and understand the code beforehand and use with caution.

The password for a particular host and user can be set using the following command:

`ALTER USER '<user>'@'<host>' IDENTIFIED BY '<password>';
`

### Other setup instructions
To start the server, run [app.py](app.py) from within the Python virtual environment from the root directory.


# The Web App
The Web App brings together the Meta Base and the File Space into a single user interface. The Web App utilises the Flask library.

The following folders exist in the Web App's root directory (note that a *module* refers to a compartamentalised section of code pertaining to a specific functionality such as encounter, recording or selection):
- [resources](resources) contains additional files required in the Web App such as images.
- [routes](routes) contains all the Flask route blueprints for separate modules.
- [static](static) contains all CSS scripts used in the user interface.
- [templates](templates) contains all HTML scripts used in the user interface.
- [db.py](db.py) handles database connection and the loading of external files such as [file_space_path.txt](file_space_path.txt) and [google_api_key.txt](google_api_key.txt).
- [app.py](app.py) is the mainline which calls `db.py` and loads all `routes`.

## Templates and static files
Templates are pre-designed layouts that arrange content on a webpage, usually written in HTML. Found in the `templates` folder, templates are structured into modular sub-categories for set functions.

The template [templates/partials/header.html]() defines a reusable header at the top of each page.

Styling (or CSS) and Javascript files are stored in the `static` folder. These files are referenced in each of the templates through a resource route specified in [app.py](app.py).

## Routes
Routes are a server-side URL schema which describe interfaces through which a client can interact with a web app. Routes follow a Hypertext Transfer Protocol (HTTP) through which requests such as `GET` and `POST` can be made. Any request sent to the server that matches a defined URL schema is handed to the associated method defined in [routes](). 

> The majority of routes exist in the folder [routes](), however the mainline [app.py]() also contains some basic routes such as `/home` and `/`, where the latter redirects to the prior.

### Requests
HTTP has a large number of possible request types. For simplicity, the Web App uses:
- `GET` to load templates and/or send information to the client;
- `POST` to send information from the client to the server, usually to complete a CRUD operation in the Meta Base.

### Object relational mapping
When interacting with the Meta Base, an object relational mapping (ORM) is implemented. This allows all the database relations to be lazily and effortlessly loaded in a familiar object-oriented structure in Python.

The classes for each relation are written in [models.py](models.py) using the [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/). This library offers seamless integration with the Flask library, that used to create the Web App. The structure of each model closely matches the Meta Base schema. 

Additional methods also exist within each ORM class as to provide APIs for the program to interact with the database, such as:

### Session handling
As data must be synchronised between the File Space and Meta Base, atomicity is crucial. An atomic database transaction is one where either all required operations occur or none at all.

To implement atomicity in the Web App, all database operations are bundled into sessions. If an error is produced in interacting with the File Space, any metadata changes pertaining to the request are rolled back. 

To prevent orphaned files from appearing in the database, all database changes are flushed (`flush()`) before any files are moved. This way, any issues appearing due to the flush are caught and handled (or passed to the user) before creating irreversible file changes.

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


