# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

#  Standard library imports
from io import StringIO
import io
import os
import tempfile
import uuid
import datetime
import warnings

# Third-party imports
from flask import Response
from sqlalchemy.event import listens_for
from sqlalchemy.sql import func
from flask_login import UserMixin
import csv
import scipy.io
import numpy as np
import pandas as pd
import librosa
import matplotlib
import wave
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename

# Local application imports
from . import contour_statistics
from . import database_handler
from . import exception_handler
from . import utils
from .interfaces import imodels
from .logger import logger



### UNUSED ###
SYSTEM_GMT_OFFSET = 0
def convert_to_gmt_time(system_time: datetime.datetime) -> datetime.datetime:
    """
    Converts a system time to GMT time by adding the system GMT offset.
    
    Parameters:
        system_time (datetime.datetime): The system time to be converted.
    
    Returns:
        datetime.datetime: The GMT time equivalent to the provided system time.
    """
    gmt_offset = datetime.timedelta(hours=SYSTEM_GMT_OFFSET)
    gmt_time = system_time + gmt_offset
    return gmt_time

def convert_from_gmt(gmt_time: datetime.datetime) -> datetime.datetime:
    """
    Converts a GMT time to a system time by subtracting the system GMT offset.
    
    Parameters:
        gmt_time (datetime.datetime): The GMT time to be converted.
    
    Returns:
        datetime.datetime: The system time equivalent to the provided GMT time.
    """
    gmt_offset = datetime.timedelta(hours=SYSTEM_GMT_OFFSET)
    system_time = gmt_time - gmt_offset
    return system_time

class Species(imodels.ISpecies):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        self.species_name = form['species_name']
        self.genus_name = form['genus_name']
        self.common_name = form['common_name']

    def delete(self):
        return

    def unique_name(self):
        return self.species_name

    def _get_children(self, session):
        return session.query(Encounter).filter_by(species_id=self.id).all()

    def prepare_for_delete(self):
        with database_handler.get_session() as session:
            if len(self._get_children(session)) > 0:
                raise exception_handler.WarningException("Cannot delete species as it has dependencies.")

    @property
    def folder_name(self) -> str:
        return f"Species-{self.species_name}"

class RecordingPlatform(imodels.IRecordingPlatform):
    __tablename__ = 'recording_platform'
    
    def unique_name(self):
        return self.name

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        self.name = form["name"]

    def delete(self):
        return

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DataSource(imodels.IDataSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def unique_name(self):
        return self.name

    def delete(self):
        return

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        if "name" in form: self.name = form["name"]
        if "phone_number1" in form: self.phone_number1 = form["phone_number1"]
        if "phone_number2" in form: self.phone_number2 = form["phone_number2"]
        self.email1 = form["email1"]
        if "email2" in form: self.email2 = form["email2"]
        if "address" in form: self.address = form["address"]
        if "notes" in form: self.notes = form["notes"]
        if new: self.type = form["type"]

class Encounter(imodels.IEncounter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        for key, value in form.items():
            setattr(self, key, value)

    def _get_children(self, session):
        return session.query(Recording).with_for_update().filter_by(encounter_id=self.id).all()

    def delete(self):
        self._delete_children()

    @property
    def recording_count(self):
        return database_handler.db.session.query(Recording).filter_by(encounter_id=self.id).count()
    
    @property
    def relative_directory(self):
        return os.path.join(utils.secure_fname(self.species.folder_name),utils.secure_fname(self.location_folder_name),utils.secure_fname(self.folder_name))

    @property
    def folder_name(self):
        return utils.secure_fname(f"Encounter-{self.encounter_name}")
    
    @property
    def location_folder_name(self):
        return utils.secure_fname(f"Location-{self.location}")


class File(database_handler.db.Model):
    __tablename__ = 'file'

    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    path = database_handler.db.Column(database_handler.db.String(255), nullable=False)
    filename = database_handler.db.Column(database_handler.db.String(255), nullable=False)
    uploaded_date = database_handler.db.Column(database_handler.db.DateTime(timezone=True))
    upload_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True))

    extension = database_handler.db.Column(database_handler.db.String(10), nullable=False)
    duration = database_handler.db.Column(database_handler.db.Integer)
    deleted = database_handler.db.Column(database_handler.db.Boolean, default=False)
    original_filename = database_handler.db.Column(database_handler.db.String(255))
    temp = database_handler.db.Column(database_handler.db.Boolean, default=False)
    hash = database_handler.db.Column(database_handler.db.LargeBinary)

    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    def get_extension(self):
        return '' if self.extension is None else self.extension
    
    def get_deleted(self):
        return self.deleted
    
    def get_original_filename(self):
        return '' if self.original_filename is None else self.original_filename
    
    def get_updated_by_id(self):
        return '' if self.updated_by_id is None else self.updated_by_id

    def to_dict(self, attributes=None):
        """
        Convert the File object to a dictionary representation.

        Args:
            attributes (list[str]|None): List of attribute names to include in the dictionary representation. If None, all attributes are included.

        Returns:
            dict: A dictionary containing the File object's attributes.
        """
        retrievable_attributes = {
            'path': self.get_path,
            'filename': self.get_filename,
            'uploaded_date': self.get_uploaded_date_utc,
            'extension': self.get_extension,
            'deleted': self.get_deleted,
            'original_filename': self.get_original_filename,
            'hash': self.get_hash,
            'updated_by_id': self.get_updated_by_id,
            'absolute_path': self.get_full_absolute_path
        }

        if attributes is None:
            attributes = retrievable_attributes
        else:
            utils.verify_subarray_of_dict(attributes, retrievable_attributes)

        return utils.serialise_object(attributes)
    
    @classmethod
    def has_record(cls, session, file_path, deleted = False, temp = False):
        comparison_path = file_path
        comparison_dir = os.path.dirname(comparison_path)
        comparison_file = os.path.splitext(os.path.basename(comparison_path))[0]
        comparison_ext = os.path.splitext(comparison_path)[1].replace('.', '')

        return session.query(cls).filter(
            cls.path == comparison_dir,
            cls.filename == comparison_file,
            cls.extension == comparison_ext,
            cls.deleted == deleted,
            cls.temp == temp
        ).first() is not None

    def __init__(self, filename=None):
        self.filename, self.extension = os.path.splitext(filename) if filename != None else (None, None)

    def get_hash(self):
        if self.hash == None:
            self.hash = self.calculate_hash()
        return self.hash.hex()

    def calculate_hash(self):
        import hashlib
        if os.path.exists(self.get_full_absolute_path()) == False:
            return None
        with open(self.get_full_absolute_path(), 'rb') as file:
            hash_value = hashlib.sha256(file.read()).digest()
        return hash_value
    
    def verify_hash(self, fix:bool=True):
        """
        Compare the stored has value of the file in the database to the re-calculated hash value of the file
        on the server. If they match return True, if not then False. If there is no stored hash value in the
        database then calculate one, store it, and return None (so that next time the function is called an
        accurate comparison can be made). Note that the parameter fix (default True) can be set to False if
        a None hash value should not be populated.
        """
        if self.hash != None:
            return self.hash == self.calculate_hash()
        if fix == True: 
            # Need to create a new session to separate the hashing context from that which called the method
            with database_handler.get_session() as session:
                file_obj = session.query(File).filter(File.id == self.id).first()
                if file_obj != None:
                    file_obj.hash = self.calculate_hash()
                session.commit()
            
        return None
    


    def rollback(self, session):
        """
        If the current File object has not been committed to the database yet,
        remove the file from the file space. This enacts a hard delete as the
        assumption is that the file should not have been uploaded in the first
        place.

        Warning: this does not delete the File object from a future commit.

        :param session: the SQLAlchemy session
        """
        if self not in session.identity_map:
            try:
                os.remove(self.get_full_absolute_path())
            except Exception:
                pass
    def get_uploaded_date_utc(self):
        """
        This method should return the uploaded date in UTC timezone, however has not yet been implemented
        """
        return self.upload_datetime

    def delete(self):
        """
        Enact a soft delete for the file in this File object and commit the new trash path
        to the database.
        """
        self.move_to_trash()
    
    def update_call(self):
        """
        No other classes have dependencies on File so this method merely exists as
        a placeholder in case one of File's dependencies call it.
        """
        pass

    def get_filename(self):
        """
        :return: the filename (without extension) of the file represented by the object
        """
        return self.filename
    
    def get_directory(self):
        """
        :return: the folder directory (without filename or extension) in which the file
        represented by the object lies
        """
        return self.path  

    def get_path(self):
        """
        DEPRACATED. Use self.get_directory()
        """
        return self.get_directory()
    
    def get_full_relative_path(self):
        """
        :return: the full path in the filespace, including the directory, filename and
        extension of the file represented by the object
        """
        return os.path.join(self.path, f"{self.filename}.{self.extension}")
    
    
    def set_updated_by_id(self, user_id: str):
        """Set the user ID of the user who is updating the recording.

        Args:
            user_id (str): The user ID who is updating the recording.
        """
        self.updated_by_id = user_id


    def get_full_absolute_path(self):
        """
        :return: the full absolute path of the filespace joined with the directory, 
        filename and extension of the file represented by the object
        """
        if self.deleted:
            root = database_handler.get_trash_path()
        elif self.temp:
            root = database_handler.get_tempdir()
        else:
            root = database_handler.get_file_space_path()
        return os.path.join(root, self.get_full_relative_path())
    
    # def get_absolute_directory(self):
    #     return os.path.join(database_handler.get_file_space_path(), self.path)

    def insert_path_and_filename_file_already_in_place(self, session, new_directory:str, new_filename:str, new_extension:str):
        """
        Store a path, filename and extension. This assumes the file is already in place.
        It is recommended unless absolutely necessary to use insert_path_and_filename()
        to let this class handle the movement of files within the file space.

        :param session: the SQLAlchemy session
        :param new_directory: the directory (no filename)
        :param new_filename: the filename (without extension)
        :param new_extension: the file's extension (without a '.')
        """
        self.path=new_directory
        self.filename=new_filename
        self.extension=new_extension
        self.hash = self.calculate_hash()
        session.flush()
        logger.info(f"Inserted directory and filename for {self.path} with hash {self.get_hash()}.")


    def rename_loose_file(self,loose_file_directory:str, loose_file_name:str, loose_file_extension:str) -> None:
        """
        In the event that a file needs to be saved in a path in which a file already exists,
        give the existing file (the 'loose file') a new name in the same directory. This 
        method will create an error in the logger as the cause of this error is usually 
        manual manipulation of the filespace. 

        A file is renamed by adding 'Dupl#_' to the start of the name (where # is the lowest
        available integer in the directory to ensure no duplicate file names).

        :param loose_file_directory: the relative directory (folder) in which the loose file
        exists
        :param loose_file_name: the name of the loose file that is contested and needs to be
        renamed (without extension)
        :param loose_file_extension: the extension (without '.') of the loose file
        """
        import re
        loose_file_path = os.path.join(database_handler.get_file_space_path(),loose_file_directory, loose_file_name + '.' + loose_file_extension)
        if os.path.exists(loose_file_path):
            # Find the highest counter integer in the existing filenames
            counter_regex = re.compile(r'Dupl(\d+)_{}\.{}'.format(re.escape(loose_file_name), re.escape(loose_file_extension)))
            highest_counter = 0
            for existing_file in os.listdir(os.path.dirname(loose_file_path)):
                match = counter_regex.search(existing_file)
                if match:
                    counter = int(match.group(1))
                    highest_counter = max(highest_counter, counter)
            
            # Increment the counter and generate a new filename
            new_counter = highest_counter + 1
            new_filename = f"Dupl{new_counter}_{loose_file_name}"
            new_path = os.path.join(os.path.dirname(loose_file_path), new_filename + '.' + loose_file_extension)
            os.rename(loose_file_path, new_path)
            logger.error(f"Attempting to save file in the following path, but a file already exists: {loose_file_path}. Renamed existing file to {new_path}")


    def append_chunk(self, chunk):
        # Save the chunk to a temporary file
        chunk_path = self.get_full_absolute_path()

        if os.path.exists(chunk_path):
            with open(chunk_path, 'ab') as f:
                f.write(chunk.read())


    # TODO: find the datatype of file
    # TODO: remove root_path requirement as it is automatically generated in the method
    def insert_path_and_filename(self, file, new_directory:str, new_filename:str, override_extension:str=None, root_path=None):
        """
        Insert a file into the filespace. Automatically save the file on the server and
        store (and commit) its directory, filename and extension in the database. If 
        successful write an informational message to the logger.

        :param session: the SQLAlchemy session
        :param file: TBD
        :param new_directory: the relative directory in which to store the file
        :param new_filename: the full filename (including extension) to rename the file to
        """


        root_path = database_handler.get_file_space_path() if root_path is None else root_path
        # Extract filename and stream depending on whether `file` is a path or a file-like object
        if isinstance(file, str):  # If `file` is a file path string
            file_path = file
            file_basename = os.path.basename(file_path)
            file_extension = file_basename.split('.')[-1]
            file_stream = open(file_path, 'rb')  # Open the file stream
        elif hasattr(file, 'stream'):  # If `file` is a file-like object with `.stream` (Flask file)
            file_stream = file.stream
            file_basename = file.filename
            file_extension = file.filename.split('.')[-1]
        elif hasattr(file, 'read'):  # If [file](cci:1://file:///home/sulli/code/database-management-system/ocean/app/interfaces/imodels.py:887:4-892:33) is a file-like object
            file_stream = file
            file_basename = "automatically generated"
            if not override_extension: raise ValueError("When passing a stream, an override_extension must be provided.")
        else:
            raise ValueError("The `file` parameter must be either a file path or a file-like object with a `stream`.")

        self.path = new_directory
        self.filename = secure_filename(new_filename)  # filename without extension
        self.original_filename = file_basename
        self.extension = override_extension if override_extension else file_extension
        
        destination_path = os.path.join(root_path, self.get_full_relative_path())
        self.rename_loose_file(self.path, self.filename, self.extension)
        os.makedirs(os.path.join(root_path, self.path), exist_ok=True)

        # Save the file to the destination in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(destination_path, 'wb') as dest_file:
            while True:
                chunk = file_stream.read(chunk_size)
                if chunk:
                    dest_file.write(chunk)
                else:
                    break
        self.hash = self.calculate_hash()
        logger.info(f"Saved file to {destination_path} with hash {self.get_hash()}.")
        
        from .filespace_handler import clean_filespace_temp
        clean_filespace_temp()

    def move_to_trash(self):
        """
        Moves the file to the trash folder.

        This function moves the file to the trash folder by renaming the file and adding a unique identifier to its name.
        TODO: keep a record of deleted file metadata
        """
        unique_name = str(uuid.uuid4())
        file_name = self.filename
        if not self.deleted:
            self.move_file(self.get_directory(), file_name + '_' +  unique_name, move_to_trash=True)

    def delete_file(self):
        if os.path.exists(self.get_full_absolute_path()):
            logger.info(f"Parmanently deleted file {self.get_full_absolute_path()}.")
            os.remove(self.get_full_absolute_path())

    def save_permanently(self, new_directory, new_filename):
        if (self.temp == True and os.path.exists(self.get_full_absolute_path())):
            self.move_file(new_directory, new_filename)
            self.temp = False
        else:
            raise exception_handler.WarningException(f"An unexpected error ocurred while trying to save the file.")

    def move_file(self, new_directory, new_filename, move_to_trash=False, override_extension=None):
        """
        Move a file to a new location with the provided session.

        Parameters:
        - session: The session object to use for the database transaction
        - new_relative_file_path: The new relative file path to move the file to
        - return: False if the file already exists at the new location, None otherwise
        
        """
        
        new_relative_file_path = os.path.join(new_directory, secure_filename(new_filename))
            
        current_relative_file_path = self.get_full_absolute_path()
        
        if move_to_trash: 
            root_path = database_handler.get_trash_path()
            self.deleted = True
        else: root_path = database_handler.get_file_space_path()

        new_relative_file_path_with_root = os.path.join(root_path, new_relative_file_path) # add the root path to the relative path
        


        if override_extension:
            self.extension = override_extension
            new_relative_file_path_with_root = new_relative_file_path_with_root + '.' + self.extension
        else:
            new_relative_file_path_with_root = new_relative_file_path_with_root + '.' + self.extension
        

        # make the directory of the new_relative_file_path_with_root
        if not os.path.exists(os.path.dirname(new_relative_file_path_with_root)):
            os.makedirs( os.path.dirname(new_relative_file_path_with_root))
            logger.info(f"Created directory: {os.path.dirname(new_relative_file_path_with_root)}")

        # if the new and current file paths are not the same
        if new_relative_file_path_with_root != current_relative_file_path:
            self.path = os.path.dirname(new_relative_file_path)
            self.filename = secure_filename(os.path.basename(new_relative_file_path).split(".")[0])
            self.rename_loose_file(self.path, self.filename, self.extension)
            if os.path.exists(current_relative_file_path):
                os.rename(current_relative_file_path, new_relative_file_path_with_root)
                logger.info(f"Moved file from {current_relative_file_path} to {new_relative_file_path_with_root}")
                self.temp = False
            else:
                logger.warning(f"Attempted to move file from {current_relative_file_path} to {new_relative_file_path_with_root} but file does not exist")
 
            
            parent_dir = os.path.dirname(current_relative_file_path)

            if os.path.exists(parent_dir):
                while parent_dir != root_path and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    parent_dir = os.path.dirname(parent_dir)
                
        else:
            pass
            return False

    def get_binary(self):
        """
        Reads and returns the binary content of the file represented by this object.

        :return: The binary content of the file.
        :raises FileNotFoundError: If the file does not exist.
        :raises IOError: If there is an issue reading the file.
        """
        absolute_path = self.get_full_absolute_path()
        
        try:
            with open(absolute_path, 'rb') as file:
                return file.read()
        except IOError as e:
            logger.error(f"Failed to read the file at {absolute_path}: {e}")
            raise exception_handler.WarningException(f"Unable to access file. This issue has been logged.")
        except FileNotFoundError as e:
            logger.error(f"File not found at {absolute_path}: {e}")
            raise exception_handler.WarningException(f"Unable to access file. This issue has been logged.")

class Recording(imodels.IRecording):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_children(self, session):
        """Returns a list of the child objects of this object.
        
        Children count as any reference from this object to another object in the database. Or
        any foreign key reference from another object in the database to this object. For `Recording`
        children are `Selection` (0 or more) and `File` ( 1`selection_table_file` and 1 
        `recording_file`) objects.
        """
        children = []
        if self.recording_file_id is not None:
            recording_file = session.query(File).with_for_update().get(self.recording_file_id)
            children.append(recording_file)
        if self.selection_table_file is not None:
            selection_table_file = session.query(File).with_for_update().get(self.selection_table_file_id)
            children.append(selection_table_file)
        selections = session.query(Selection).with_for_update().filter_by(recording_id=self.id).all()
        children.extend(selections)
        assignments = session.query(Assignment).with_for_update().filter_by(recording_id=self.id).all()
        children.extend(assignments)
        return children
    
    def _insert_or_update(self, form, new):
        from .filespace_handler import get_complete_temporary_file
        attr_form = utils.parse_form(form, self._form_dict())
        for key, value in attr_form.items():
            setattr(self, key, value)

    
    def recording_file_insert(self, session, stream):
        if self.recording_file: raise exception_handler.CriticalException("Recording already has a recording file")
        file = File()
        file.insert_path_and_filename(stream, self.relative_directory, self.recording_file_name)
        session.add(file)
        self.recording_file = file


    @property
    def start_time_pretty(self):
        return utils.pretty_date(self.start_time)
            
    @property
    def folder_name(self):
        return utils.secure_fname(f"Recording-{utils.secure_datename(self.start_time)}")

    @property
    def recording_file_name(self):
        return utils.secure_fname(f"Rec-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{utils.secure_datename(self.start_time)}")

    @property
    def selection_table_file_name(self):
        return utils.secure_fname(f"SelTable-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{utils.secure_datename(self.start_time)}")

    @property
    def relative_directory(self):
        if not self.encounter: raise exception_handler.CriticalException("Recording has no encounter")
        return os.path.join(self.encounter.relative_directory, utils.secure_fname(self.folder_name))

    @property
    def unique_name(self):
        return self.encounter.unique_name + ', Recording: ' + str(self.start_time)
    
    def is_reviewed(self):
        return self.status == 'Reviewed'

    def is_on_hold(self):
        return self.status == "On Hold"
    
    def is_awaiting_review(self):
        return self.status == 'Awaiting Review'
    
    def is_in_progress(self):
        return self.status == 'In Progress'
    
    def is_unassigned(self):
        return self.status == 'Unassigned'

    def _update_status(self, override=None, assignments=[]):
        new_status = ""
        if override is None and not self.is_on_hold() and not self.is_reviewed():
            # Calculate the new status based on the assignments
            if len(assignments) == 0:
                new_status = 'Unassigned'
            else:
                new_status = 'Awaiting Review'
                if assignments is not None:
                    # If there is one or more incomplete assignments assing In Progress
                    for assignment in assignments:
                        print(assignment.completed_flag)
                        if assignment.completed_flag is False:
                            new_status = 'In Progress'
        elif override is None:
            # Keep the status the same if it is currently On Hold or Reviewed and no override
            new_status = self.status
        else:
            new_status = override

        if self.status != new_status:
            self.status = new_status
            self.status_change_datetime = datetime.datetime.now()
            return True
        return False


    def update_status(self, session, override=None) -> bool:
        """Update the recording's status. If the newly calculated or overriden status is different
        the `status_change_datetime` is updated. The session must be committed by the caller for the
        changes to take effect. Returns True if the status was changed, False otherwise.

        If the current status is `Unassigned`, `In Progress` or `Awaiting Review` the new status
        will be automatically determined based on the recording's assignments.
        - no assignments results in `Unassigned`
        - one or more assignments (with at least one incomplete) results in `In Progress`
        - one or more assignments (with all complete) results in `Awaiting Review`
        
        The `override` argument (default `None`) can be used to assign the status `Reviewed` and
        `On Hold`. Override to `Unassigned`, `In Progress` or `Awaiting Review` is also possible.
        Using `override` with any other status will result in an error and no change to the status.
        """

        assignments = session.query(Assignment).filter_by(recording_id=self.id).all()
        return self._update_status(assignments=assignments, override=override)

    def get_selections(self, session, filters={}):
        filters["recording_id"] = self.id
        return database_handler.create_system_time_request(session, Selection, order_by="selection_number", filters=filters)

    @property
    def selection_count(self):
        return len(self.get_selections(database_handler.db.session))

    @property
    def selection_file_count(self):
        return len(database_handler.db.session.query(Selection).filter_by(recording_id=self.id).filter(Selection.selection_file != None).all())

    @property
    def contour_file_count(self):
        return len(database_handler.db.session.query(Selection).filter_by(recording_id=self.id).filter(Selection.contour_file != None).all())

    def _update_filespace(self):
        if self.recording_file_id is not None:
            with database_handler.get_session() as recording_file_session:
                recording_file = recording_file_session.query(File).with_for_update().get(self.recording_file_id)
                recording_file.move_file(self.relative_directory, self.recording_file_name)
                recording_file_session.commit()
        if self.selection_table_file_id is not None:
            with database_handler.get_session() as selection_table_file_session:
                selection_table_file = selection_table_file_session.query(File).with_for_update().get(self.selection_table_file_id)
                selection_table_file.move_file(self.relative_directory, self.selection_table_file_name)
                selection_table_file_session.commit()

    def _selection_table_apply(self, dataframe, selections):
        """Helper method to `selection_table_apply`.

        Args:
            dataframe (pandas.DataFrame): the dataframe containing the selection table
            selections (dict): all existing selections for the recording {id: object}

        Returns:
            List[Selection]: the list of new selections (this need to be added to the session)
        """

        if dataframe is None or dataframe.empty:
            raise exception_handler.WarningException("The selection table provided is empty")
        if 'Selection' not in dataframe.columns:
            raise exception_handler.WarningException("Missing required columns: Selection")

        selection_table_selection_numbers = dataframe.Selection.to_list()
        new_selections = []
        
        for selection_number in selection_table_selection_numbers:
            if selection_number not in selections:
                new_selection = Selection(recording=self, selection_number=selection_number)
                new_selection.upload_selection_table_data(dataframe.loc[dataframe['Selection'] == selection_number, :])
                new_selections.append(new_selection)
            else:
                selections[selection_number].upload_selection_table_data(dataframe.loc[dataframe['Selection'] == selection_number, :])
        return new_selections

    def selection_table_apply(self, session):
        selections = {selection.selection_number: selection for selection in session.query(Selection).filter_by(recording_id=self.id).all()}
        selection_table_df = utils.extract_to_dataframe(path=self.selection_table_file.get_full_absolute_path())
        new_selections = self._selection_table_apply(selection_table_df, selections)
        for selection in new_selections:
            session.add(selection)
    
    def selection_table_data_delete(self, session):
        for selection in self.get_selections(session):
            selection.reset_selection_table_values()
            
    def delete(self):
        self._delete_children()
        self.recording_file = None
        self.selection_table_file = None

    def generate_relative_path_for_selections(self):
        # TODO: REMOVE
        folder_name = self.start_time.strftime("Selections-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.relative_directory, folder_name)

    def update_selection_traced_status(self, session):
        selections = self.get_selections(session)
        for selection in selections:
            selection.update_traced()

    def selection_table_export(self, session, export_format):
        headers = ['Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Delta Time (s)', 'Delta Freq (Hz)', 'Avg Power Density (dB FS/Hz)', 'Annotation']

        selections = database_handler.create_system_time_request(session, Selection, {"recording_id": self.id}, order_by="selection_number", one_result=False)
        encounter = database_handler.create_system_time_request(session, Encounter, {"id":self.encounter_id},one_result=True)
        
        csv_data = StringIO()
        if export_format == 'csv':
            writer = csv.writer(csv_data, delimiter=',')
        else:
            writer = csv.writer(csv_data, delimiter='\t')
        
        writer.writerow(headers)
        for selection in selections:
            writer.writerow([
                selection.selection_number,
                selection.view,
                selection.channel,
                selection.begin_time,
                selection.end_time,
                selection.low_frequency,
                selection.high_frequency,
                selection.delta_time,
                selection.delta_frequency,
                selection.average_power,
                selection.annotation
            ])

        csv_data.seek(0)

        if export_format == 'csv':
            mimetype = 'text/csv'
            file_name = f'selection-table-{encounter.encounter_name}-rec-{self.start_time_pretty}.csv'
        else:
            mimetype = 'text/plain'
            file_name = f'selection-table-{encounter.encounter_name}-rec-{self.start_time_pretty}.txt'

        response = Response(csv_data.getvalue(), mimetype=mimetype, headers={'Content-Disposition': f'attachment; filename={file_name}'})
        
        return response

class Role(imodels.IRole):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class Selection(imodels.ISelection):

    def __init__(self, recording, *args, **kwargs):
        super().__init__(recording = recording, *args, **kwargs)

    def delete(self):
        self.selection_file_delete()
        self.contour_file_delete()

    @property
    def unique_name(self):
        if self.recording == None: raise exception_handler.CriticalException("Encounter is not linked to a recording.")
        return f"{self.recording.unique_name}, Selection: {self.selection_number}"

    @property
    def relative_directory(self):
        folder_name = self.recording.start_time.strftime("Selections-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.recording.relative_directory, folder_name)

    @property
    def selection_file_name(self):
        return utils.secure_fname(f"Selection-{self.selection_number}-{utils.secure_datename(self.recording.start_time)}")

    @property
    def contour_file_name(self):
        return utils.secure_fname(f"Contour-{self.selection_number}-{utils.secure_datename(self.recording.start_time)}")

    @property
    def ctr_file_name(self):
        return utils.secure_fname(f"CTR-{self.selection_number}-{utils.secure_datename(self.recording.start_time)}")

    def selection_file_insert(self, session, stream):
        if self.selection_file: raise exception_handler.WarningException(f"Selection file for selection {self.selection_number} already exists.")
        file = File()
        file.insert_path_and_filename(stream, self.relative_directory, self.selection_file_name)
        session.add(file)
        self.selection_file = file
    
    def contour_file_insert(self, session, stream):
        if self.contour_file or self.contour_file_id: raise exception_handler.WarningException(f"Contour file for selection {self.selection_number} already exists.")
        file = File()
        file.insert_path_and_filename(stream, self.relative_directory, self.contour_file_name)
        session.add(file)
        self.contour_file = file
        self.ctr_file_generate(session)
        self.contour_statistics_calculate()

    def contour_file_delete(self):
        if self.contour_file_id is not None:
            self.contour_file.delete()
            self.contour_file = None
        self.ctr_file_delete()
        self.update_traced()
        self.clear_contour_statistics_attrs()

    def selection_file_delete(self):
        if self.selection_file:
            self.selection_file.delete()
            self.selection_file = None

    def ctr_file_delete(self):
        if self.ctr_file is not None:
            self.ctr_file.delete()
            self.ctr_file = None

    def ctr_file_generate(self, session):
        contour_file_handler = self.get_contour_file_handler()
        if contour_file_handler:
            mat_data = contour_file_handler.get_ctr_data()
            self.ctr_file_delete()
            if mat_data:
                file = File()
                session.add(file)
                self.ctr_file = file
                with io.BytesIO() as f:
                    scipy.io.savemat(f, mat_data)
                    f.seek(0)
                    file.insert_path_and_filename(f, self.relative_directory, self.ctr_file_name, override_extension="ctr")

    def clear_contour_statistics_attrs(self):
        for attr in imodels.ISelection.get_contour_statistics_attrs():
            setattr(self, attr, None)

    def _get_children(self, session):
        """Returns a list of the child objects of this object.
        
        Children count as any reference from this object to another object in the database. Or
        any foreign key reference from another object in the database to this object. For `Recording`
        children are `Selection` (0 or more) and `File` ( 1`selection_table_file` and 1 
        `recording_file`) objects.
        """
        children = []
        if self.selection_file is not None: children.append(self.selection_file)
        if self.contour_file is not None: children.append(self.contour_file)
        return children

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        if new:
            self.selection_number = form['selection_number']
        else:
            raise exception_handler.CriticalException("Cannot update selections.")

    def contour_statistics_calculate(self):
        self.clear_contour_statistics_attrs()
        if self.contour_file is not None:
            try:
                contour_statistics_obj = contour_statistics.ContourFile(self.contour_file.get_full_absolute_path(), self.selection_number)
                contour_statistics_obj.calculate_statistics(self)
            except ValueError as e:
                raise exception_handler.WarningException(f"Error processing contour {self.selection_number}: " + str(e))
            except FileNotFoundError as e:
                raise exception_handler.WarningException(f"Error processing contour {self.selection_number} (file no longer exists)")

    def _calculate_sampling_rate(self):
        if self.selection_file:
            with wave.open(self.selection_file.get_full_absolute_path(), "rb") as wave_file:
                self.sampling_rate = wave_file.getframerate()
        else: raise exception_handler.WarningException("Unable to calculate sampling rate as the selection file does not exist.")

    def deactivate(self):
        self.traced = None
        self.deactivated = True

    def reactivate(self):
        self.traced = None
        self.deactivated = False

    def clear_selection_table_attrs(self):
        for attr in self.selection_table_attrs:
            setattr(self, attr, None)

    def update_traced(self):
        if self.contour_file and (self.annotation == "Y" or self.annotation == "M"): self.traced = True
        elif not self.contour_file and (self.annotation == "N"): self.traced = False
        else: self.traced = None
            
    def create_temp_plot(self, session, temp_dir, fft_size=None, hop_size=None, update_permissions=False):
        
        warning = ""
        
        # Set default FFT and hop sizes if not provided
        if fft_size is None:
            n_fft = self.default_fft_size if self.default_fft_size else 2048
            if not self.default_fft_size:
                self.default_fft_size = n_fft
        else:
            self.default_fft_size = fft_size
            n_fft = fft_size

        if hop_size is None:
            hop_length = self.default_hop_size if self.default_hop_size else 512
            if not self.default_hop_size:
                self.default_hop_size = hop_length
        else:
            self.default_hop_size = hop_size
            hop_length = hop_size
        
        if update_permissions:
            session.commit()

        # Load the audio file
        with open(self.selection_file.get_full_absolute_path(), 'rb') as selection_file:
            audio, sr = librosa.load(selection_file)

        # Increase the resolution of the spectrogram
        spectrogram = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)

        # Create a figure with one or two subplots
        if self.contour_file:
            fig, axs = plt.subplots(2, 1, figsize=(30, 10))
        else:
            fig, axs = plt.subplots(1, 1, figsize=(30, 5))

        spectogram_axs = axs[0] if self.contour_file else axs

        # Plot the spectrogram
        spectogram_axs.imshow(librosa.amplitude_to_db(np.abs(spectrogram), ref=np.max), cmap='inferno', origin='lower', aspect='auto')
        spectogram_axs.set_xlabel('Time', fontsize=20)
        spectogram_axs.set_ylabel('Frequency (hz)', fontsize=20)
        spectogram_axs.tick_params(axis='both', labelsize=14)

        # Plot the contour if it exists
        if self.contour_file_id:
            contour_file_handler = self._read_contour_file()
            contour_rows = contour_file_handler.contour_rows
            min_time_ms = min([unit.time_milliseconds for unit in contour_rows])
            axs[1].plot([unit.time_milliseconds - min_time_ms for unit in contour_rows], [unit.peak_frequency for unit in contour_rows])
            axs[1].set_xlabel('Time (ms)', fontsize=20)
            axs[1].set_ylabel('Frequency (hz)', fontsize=20)
            axs[1].tick_params(axis='both', labelsize=14)

            # Adjust the y-axis limits of the spectrogram to match the y-axis limits of the contour plot
            contour_y_min = min([unit.peak_frequency for unit in contour_rows])
            contour_y_max = max([unit.peak_frequency for unit in contour_rows])
            contour_y_range = contour_y_max - contour_y_min
            spectogram_y_min = axs[0].get_ylim()[0]
            spectogram_y_max = axs[0].get_ylim()[1]
            spectogram_y_range = spectogram_y_max - spectogram_y_min
            range_diff = spectogram_y_range - contour_y_range

            if range_diff < 0:
                warning = ". Warning: contour y-axis range larger than spectogram y-axis range."
            else:
                contour_y_min_new = contour_y_min - (range_diff / 2)
                contour_y_max_new = contour_y_max + (range_diff / 2)
                axs[1].set_ylim(contour_y_min_new, contour_y_max_new)

            contour_x_min = min([unit.time_milliseconds - min_time_ms for unit in contour_rows])
            contour_x_max = max([unit.time_milliseconds - min_time_ms for unit in contour_rows])
            contour_x_range = contour_x_max - contour_x_min
            spectogram_x_min = axs[0].get_xlim()[0]
            spectogram_x_max = axs[0].get_xlim()[1]
            spectogram_x_range = spectogram_x_max - spectogram_x_min
            range_x_diff = contour_x_range - spectogram_x_range
            contour_x_min_new = contour_x_min - (range_x_diff / 2)
            contour_x_max_new = contour_x_max + (range_x_diff / 2)
            axs[1].set_xlim(contour_x_min_new, contour_x_max_new)
            fig.suptitle(f'Spectrogram (FFT Size: {n_fft}, Hop Size: {hop_length}){warning if warning else ""}', fontsize=26)
        else:
            fig.suptitle(f'Spectrogram (FFT Size: {n_fft}, Hop Size: {hop_length})', fontsize=26)

        # Layout so plots do not overlap
        fig.tight_layout()

        # Save the plot as a PNG
        plot_path = os.path.join(temp_dir, self.plot_file_name() + ".png")
        plt.savefig(plot_path, bbox_inches='tight')

        plt.close('all')

        return plot_path

    def __contour_file_load_dataframe(self) -> pd.DataFrame:
        """Read the `contour_file` into a pandas dataframe, validating columns and their types."""
        if self.contour_file:
            try:
                self.contour_file.get_binary()
                if self.contour_file.extension.lower() == "csv":
                    df = pd.read_csv(self.contour_file.get_full_absolute_path())
                elif self.contour_file.extension.lower() == "xlsx":
                    df = pd.read_excel(self.contour_file.get_full_absolute_path())
                else:
                    raise exception_handler.WarningException(f"Unable to parse contour file as it is in the wrong format. Require CSV or XLSX")
                return df
            except FileNotFoundError as e:
                raise exception_handler.WarningException(f"Contour file for selection {self.selection_number} no longer exists.")
        else:
            raise exception_handler.WarningException(f"Contour file for selection {self.selection_number} does not exist.")

    def get_contour_file_handler(self) -> contour_statistics.ContourFileHandler:
        if not self.contour_file: return None
        # Get contour file dataframe
        df = self.__contour_file_load_dataframe()
        if df:
            # Populate contour file handler with values from the dataframe
            handler = contour_statistics.ContourFileHandler()
            handler.insert_dataframe(df)
            return handler

    def generate_contour_stats_dict(self):
        if not self.contour_statistics_calculated: return None
        headers = ['Encounter', 'Location', 'Project', 'Recording', 'Species', 'SamplingRate', 'SELECTIONNUMBER']
        values = [self.recording.encounter.encounter_name, self.recording.encounter.location, self.recording.encounter.project, self.recording.start_time_pretty, self.recording.encounter.species.species_name, self.sampling_rate, self.selection_number]
        contour_statistics_attrs = imodels.ISelection.get_contour_statistics_attrs()
        for attr in contour_statistics_attrs:
            if contour_statistics_attrs[attr][2]:
                headers.append(attr)[1]
                values.append(getattr(self, attr))
        return dict(zip(headers, values))

    def contour_statistics_calculate(self):
        self.clear_contour_statistics_attrs()
        contour_file_handler = self.get_contour_file_handler()
        contour_file_handler.calculate_statistics(self)

    def upload_selection_table_data(self, st_df):
        missing_columns = []

        for required_column in ('Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Annotation'):
            if required_column not in st_df.columns:
                missing_columns.append(required_column)
            else:
                column_dtype = st_df[required_column].dtype
                if required_column == ('Selection','Channel'):
                    if column_dtype != 'int64':
                        raise exception_handler.WarningException(f"Column '{required_column}' must be int.")

                if required_column in ('Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)'):
                    if column_dtype != 'float64':
                        raise exception_handler.WarningException(f"Column '{required_column}' must be float.")

        selection_index = st_df.columns.get_loc('Selection')
        if len(missing_columns) > 0:
            raise exception_handler.WarningException(f"Missing required columns: {', '.join(missing_columns)}")

        selection_index = st_df.columns.get_loc('Selection')
        annotation_index = st_df.columns.get_loc('Annotation')

        # Get the values for the 'Selection' and 'Annotation' columns
        selection_number = st_df.iloc[0, selection_index]
        annotation = st_df.iloc[0, annotation_index]


        if isinstance(annotation, str):
            if annotation.upper() == "Y" or annotation.upper() == "N" or annotation.upper() == "M":
                self.annotation = annotation.upper()
            elif annotation.upper().startswith("Y"):
                self.annotation = "Y"
            elif annotation.upper().startswith("N"):
                self.annotation = "N"
            else:
                self.annotation = "M"
        else:
            self.annotation = "M"

        # Check if the selection number matches the expected value
        if selection_number != self.selection_number:
            raise exception_handler.WarningException("Invalid selection number")

        # Set the other fields based on the available columns
        self.view = str(st_df.iloc[0, st_df.columns.get_loc('View')])
        self.channel = str(st_df.iloc[0, st_df.columns.get_loc('Channel')])
        self.begin_time = float(st_df.iloc[0, st_df.columns.get_loc('Begin Time (s)')])
        self.end_time = float(st_df.iloc[0, st_df.columns.get_loc('End Time (s)')])
        self.low_frequency = float(st_df.iloc[0, st_df.columns.get_loc('Low Freq (Hz)')])
        self.high_frequency = float(st_df.iloc[0, st_df.columns.get_loc('High Freq (Hz)')])
        self.delta_time = float(st_df.iloc[0, st_df.columns.get_loc('Delta Time (s)')]) if 'Delta Time (s)' in st_df.columns else None
        self.delta_frequency = float(st_df.iloc[0, st_df.columns.get_loc('Delta Freq (Hz)')]) if 'Delta Freq (Hz)' in st_df.columns else None
        self.average_power = float(st_df.iloc[0, st_df.columns.get_loc('Avg Power Density (dB FS/Hz)')]) if 'Avg Power Density (dB FS/Hz)' in st_df.columns else None

        if not self.delta_time: self.delta_time = self.end_time - self.begin_time
        if not self.delta_frequency: self.delta_frequency = self.high_frequency - self.low_frequency

    def _update_filespace(self):
        if self.selection_file is not None:
            with database_handler.get_session() as session:
                selection_file = session.query(File).with_for_update().get(self.selection_file_id)
                selection_file.move_file(self.relative_directory,self.selection_file_name)
                session.commit()
        if self.contour_file is not None:
            with database_handler.get_session() as session:
                contour_file = session.query(File).with_for_update().get(self.contour_file_id)
                contour_file.move_file(self.relative_directory,self.contour_file_name)
                session.commit()
        if self.ctr_file is not None:
            with database_handler.get_session() as session:
                ctr_file = session.query(File).with_for_update().get(self.ctr_file_id)
                ctr_file.move_file(self.relative_directory,self.ctr_file_name)
                session.commit()

    @property
    def plot_file_name(self):
        from . import filespace_handler
        return f"Plot-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.start_time)}"

class User(imodels.IUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def delete(self):
        return

    @property
    def unique_name(self):
        return self.login_id

    def _insert_or_update(self, form, new, current_user=None):
        form = utils.parse_form(form, self._form_dict())

        if new:
            self.login_id = form['login_id']

        self.name = form['name']

        if self == current_user:
            if str(form['role_id']) != "1":
                raise exception_handler.WarningException("You cannot change your own role.")
        self.role_id = form['role_id']

        expiry_date = datetime.datetime.strptime(form['expiry'], '%Y-%m-%d')
        if self == current_user and expiry_date < datetime.datetime.now():
            raise exception_handler.WarningException("Expiry date cannot be in the past for the current logged in user.")
        self.expiry = expiry_date

        if 'is_active' in form:
            self.activate()
        elif self != current_user:
            self.deactivate()
        else:
            raise exception_handler.WarningException("You cannot deactivate yourself.")
    def update(self, form: dict, current_user):
        self._insert_or_update(form, False, current_user)


    def set_login_id(self, value: str) -> None:
        warnings.warn("User.set_login_id() is deprecated. Use User.login_id instead.", DeprecationWarning, stacklevel=2)
        if self.login_id == None:
            self.login_id = utils.parse_string_notempty(value, 'Login ID')
        elif value != self.login_id:
            raise exception_handler.WarningException("Login ID cannot be changed.")
        
    def get_role_id(self):
        warnings.warn("User.get_role_id() is deprecated. Use User.role_id instead.", DeprecationWarning, stacklevel=2)
        return self.role_id
    
    def get_role(self):
        warnings.warn("User.get_role() is deprecated. Use User.role instead.", DeprecationWarning, stacklevel=2)
        return self.role
    
    def set_role_id(self, value: int | str):
        """Set the role ID of this user. Must either be an integer
        or an integer-convertable string. This method does not verify
        foreign key constraints.

        Args:
            value (int | str): the new value

        Raises:
            exception_handler.WarningException: `value` is not of the type stated above
            exception_handler.WarningException: `value` is `None`
        """
        warnings.warn("User.set_role_id() is deprecated. Use User.role_id instead.", DeprecationWarning, stacklevel=2)
        if value is None or str(value).strip() is None: raise exception_handler.WarningException("Field 'Role' cannot be empty or None.")
        try:
            value = int(float(value))
        except Exception:
            raise exception_handler.WarningException("Field 'role' must be of type integer (a whole number).")
        self.role_id = value
    
    def set_role(self, value: Role):
        warnings.warn("User.set_role() is deprecated. Use User.role instead.", DeprecationWarning, stacklevel=2)
        self.role = utils.validate_type(value=value, target_type=Role, field="Role", allow_none=False)
    
    def set_expiry(self, value):
        warnings.warn("User.set_expiry() is deprecated. Use User.expiry instead.", DeprecationWarning, stacklevel=2)
        self.expiry = value
    
    def set_name(self, value):
        warnings.warn("User.set_name() is deprecated. Use User.name instead.", DeprecationWarning, stacklevel=2)
        self.name = utils.validate_string(value, field="Name", allow_none=False)
    
    def get_name(self):
        warnings.warn("User.get_name() is deprecated. Use User.name instead.", DeprecationWarning, stacklevel=2)
        return utils.validate_string(self.name, field="Name", allow_none=True)
    
    def get_login_id(self):
        warnings.warn("User.get_login_id() is deprecated. Use User.login_id instead.", DeprecationWarning, stacklevel=2)
        # NOTE: the login ID must never be altered or formatted
        return self.login_id

    def set_login_id(self, value: str):
        warnings.warn("User.set_login_id() is deprecated. Use User.login_id instead.", DeprecationWarning, stacklevel=2)
        if value is None or str(value).strip() is None: raise exception_handler.WarningException("Field 'Login ID' cannot be None.")
        self.login_id = str(value)

    def activate(self):
        self.is_active = True
    
    def deactivate(self):
        self.is_active = False

    def get_is_active(self):
        warnings.warn("User.get_is_active() is deprecated. Use User.is_active instead.", DeprecationWarning, stacklevel=2)
        return self.is_active if self.is_active else False

    def get_expiry(self):
        warnings.warn("User.get_expiry() is deprecated. Use User.expiry instead.", DeprecationWarning, stacklevel=2)
        return utils.validate_datetime(value=self.expiry, field="Expiry", allow_none=True)
    
    def get_expiry_pretty(self):
        warnings.warn("User.get_expiry_pretty() is deprecated. Use User.pretty_expiry_date instead.", DeprecationWarning, stacklevel=2)
        return utils.pretty_date(self.get_expiry())
    
    def set_expiry(self, value):
        warnings.warn("User.set_expiry() is deprecated. Use User.expiry instead.", DeprecationWarning, stacklevel=2)
        self.expiry = utils.validate_datetime(value=value, field="Expiry", allow_none=False)

class Assignment(imodels.IAssignment):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        recording_id = form['recording_id']
        user_id = form['user_id']
        if new:
            self.recording_id = recording_id
            self.user_id = user_id
        else:
            raise Exception("Assignment does not support update.")
    
    def delete(self):
        return

    def complete(self):
        self.completed_flag = True

    def incomplete(self):
        self.completed_flag = False

    @property
    def unique_name(self):
        return f"{self.recording.unique_name}_{self.user.unique_name}"