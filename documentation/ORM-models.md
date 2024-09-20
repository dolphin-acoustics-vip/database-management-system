# Data Model

## Overview

The data is stored in a MariaDB database using SQLAlchemy. Each table is represented by a class in Python, defined in [models.py](../models.py). 

## Unique IDs

Most tables use unique IDs as primary keys, generated using MariaDB's UUID() method. This creates a 36-character string in the format `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`. Unique constraints are also defined separately on specific attributes to ensure data integrity.

## File Storage

Files are stored in unique paths, with each file represented by a `File` class object. The following techniques are used for file storage:

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