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
import os
import uuid
import datetime

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
import matplotlib.pyplot as plt

# Local application imports
from . import contour_statistics
from . import database_handler
from . import exception_handler
from . import utils
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



class Species(database_handler.db.Model):
    __tablename__ = 'species'
    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, default=uuid.uuid4)
    # TODO rename to scientific_name (refactor with actual database)
    species_name = database_handler.db.Column(database_handler.db.String(100), nullable=False, unique=True)
    genus_name = database_handler.db.Column(database_handler.db.String(100))
    common_name = database_handler.db.Column(database_handler.db.String(100))
    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    def update_call(self):
        """
        Call update_call() in all Encounter objects linked to the Species object.
        This method should be called when a metadata change occurs in the Species
        object that requires files (in Recording and Selection) be given a new
        path based on that metadata.
        """
        with database_handler.get_session() as session:
            encounters = session.query(Encounter).with_for_update().filter_by(species_id=self.id).all()
            for encounter in encounters:
                encounter.update_call()
    
    def set_updated_by_id(self, user_id: str):
        """Set the `updated_by_id` attribute of the Species object. This attribute is used to record
        the user who is making any changes. There should be a method in `database_handler.py` which
        calls this method automatically when changes are flushed or committed to the ORM model.

        Args:
            user_id (str): The `id` of the `User` object who is making the changes
        """
        self.updated_by_id = user_id

    def get_species_name(self) -> str:
        """Get the `species_name` of a particular species. If the `species_name` is None, return an empty string.

        Returns:
            str: the species' name
        """
        return '' if self.species_name is None else self.species_name

    def set_species_name(self, value: str) -> None:
        """Set the `species_name` of a particular species. The given value is converted to a string and stripped
        of whitespace at the start and end. This value cannot be empty or None. This method does not commit or 
        flush the changes in any ORM context.

        Args:
            value (str): the name of the species

        Raises:
            ValueError: if `value` is None or empty
        """
        if value is None or value.strip() == '': raise ValueError("Species name cannot be empty")
        self.species_name = str(value).strip()
    
    def get_genus_name(self) -> str:
        """Get the `genus_name` of a particular species. If the `genus_name` is None, return an empty string.

        Returns:
            str: the species' genus name
        """
        return '' if self.genus_name is None else self.genus_name
    
    def set_genus_name(self, value: str | None) -> None:
        """Set the `genus_name` of a particular species. The given value is converted to a string and
        stripped of whitespace at the start and end. This method does not commit or flush the changes
        in any ORM context. If None or an empty string is passed, the `genus_name` is set to None.

        Args:
            value (str): the genus name
        """
        self.genus_name = None if not value or str(value).strip() == "" else str(value).strip()

    def get_common_name(self) -> str:
        """Get the `common_name` of a particular species. If the `common_name` is None, return an empty string.

        Returns:
            str: the species' common name
        """
        return '' if self.common_name is None else self.common_name
    
    def set_common_name(self, value: str | None) -> None:
        """Set the `common_name` of a particular species. The given value is converted to a string and
        stripped of whitespace at the start and end. This method does not commit or flush the changes 
        in any ORM context. If None or an empty string is passed, the `genus_name` is set to None.

        Args:
            value (str): the common name
        """
        self.common_name = None if not value or str(value).strip() == "" else str(value).strip()



class RecordingPlatform(database_handler.db.Model):
    __tablename__ = 'recording_platform'

    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = database_handler.db.Column(database_handler.db.String(100), unique=True, nullable=False)
    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<RecordingPlatform %r>' % self.name
    
    def get_name(self):
        """Return the name of the recording platform"""
        return str(self.name) if self.name is not None else ""
    
    def set_name(self, value):
        """Sets the name of the recording platform. The passed value
        cannot be an empty string or None as this would violate the
        database primary key constraint.

        Args:
            value (str): the value to set

        Raises:
            exception_handler.WarningException: if an empty string or null is passed
            ValueError: if a non-string is passed
        """
        
        if (not value) or (value and str(value).strip() == ""): raise exception_handler.WarningException("Field 'name' for recording platform cannot be empty.")
        if type(value) != str: raise ValueError(f"Field 'name' for RecordingPlatform requires must be a string (for {type(value)}).")
        self.name = str(value)
    
    def set_updated_by_id(self, user_id: uuid.UUID | str):
        """Set the user ID of the user who is updating the recording.

        Args:
            user_id (str): The user ID who is updating the recording.
        """
        self.updated_by_id = utils.validate_id(value=user_id, field="name")


class DataSource(database_handler.db.Model):
    __tablename__ = 'data_source'

    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = database_handler.db.Column(database_handler.db.String(255))
    phone_number1 = database_handler.db.Column(database_handler.db.String(20), unique=True)
    phone_number2 = database_handler.db.Column(database_handler.db.String(20), unique=True)
    email1 = database_handler.db.Column(database_handler.db.String(255), nullable=False, unique=True)
    email2 = database_handler.db.Column(database_handler.db.String(255), unique=True)
    address = database_handler.db.Column(database_handler.db.Text)
    notes = database_handler.db.Column(database_handler.db.Text)
    type = database_handler.db.Column(database_handler.db.Enum('person', 'organisation'))

    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<DataSource %r>' % self.name
    


class Encounter(database_handler.db.Model):
    __tablename__ = 'encounter'
    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, default=uuid.uuid4)
    encounter_name = database_handler.db.Column(database_handler.db.String(100), nullable=False)
    location = database_handler.db.Column(database_handler.db.String(100), nullable=False)
    species_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('species.id'), nullable=False)
    project = database_handler.db.Column(database_handler.db.String(100), nullable=False)
    latitude = database_handler.db.Column(database_handler.db.Double)
    longitude = database_handler.db.Column(database_handler.db.Double)
    data_source_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('data_source.id'), nullable=False)
    recording_platform_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('recording_platform.id'), nullable=False)
    notes = database_handler.db.Column(database_handler.db.String(1000))
    file_timezone = database_handler.db.Column(database_handler.db.Integer)
    local_timezone = database_handler.db.Column(database_handler.db.Integer)
    species = database_handler.db.relationship("Species")
    data_source = database_handler.db.relationship("DataSource")
    recording_platform = database_handler.db.relationship("RecordingPlatform")
    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    __table_args__ = (
        database_handler.db.UniqueConstraint('encounter_name', 'location', 'project'),
    )
    
    def set_updated_by_id(self, user_id: str):
        """Set the user ID of the user who is updating the recording.

        Args:
            user_id (str): The user ID who is updating the recording.
        """
        self.updated_by_id = user_id

    def get_unique_name(self, delimiter='-'):
        """
        Generate a unique name using encounter_name, location and project which are defined in
        the schema as a unique constraint. The name is of the format:

        'Encounter {encounter_name}-{location}-{project}', where - can be replaced by any delimiter.

        :param delimiter: the delimiter used to separate unique variables
        :type delimiter: str
        """
        return f"{self.encounter_name}{delimiter}{self.location}{delimiter}{self.project}"

    def get_number_of_recordings(self):
        """
        Calculate the number of recordings associated with the encounter and return the count
        """
        num_recordings = database_handler.db.session.query(Recording).filter_by(encounter_id=self.id).count()
        return num_recordings

    def generate_relative_directory(self):
        from . import filespace_handler
        return os.path.join(f"Species-{filespace_handler.validate(self.species.species_name)}",f"Location-{filespace_handler.validate(self.location)}",f"Encounter-{filespace_handler.validate(self.encounter_name)}")

    def update_call(self):
        """
        Call update_call() in all Recording objects linked to the Encounter object.
        This method should be called when a metadata change occurs in the Encounter
        object that requires files (in Recording and Selection) be given a new
        path based on that metadata.
        """
        with database_handler.get_session() as session:
            recordings = session.query(Recording).with_for_update().filter_by(encounter_id=self.id).all()
            for recording in recordings:
                recording.update_call()

    def delete_children(self):
        """
        Cascade delete all recordings in the encounter. Note this method will not delete the encounter itself.
        Ensure you call session.delete() after calling this method in the caller.
        """
        with database_handler.get_session() as session:
            recordings = session.query(Recording).with_for_update().filter_by(encounter_id=self.id).all()
            for recording in recordings:
                recording.delete_children(keep_file_reference=True)
                session.delete(recording)

    def get_latitude(self) -> float:
        try:
            return float(self.latitude)
        except (TypeError,ValueError):
            return None
    
    def set_latitude(self, value: float):
        self.latitude = utils.validate_latitude(value, field="latitude", allow_none=True)
    
    def set_longitude(self, value: float):
        self.longitude = utils.validate_longitude(value, field="longitude", allow_none=True)

    def get_longitude(self) -> float:
        try:
            return float(self.longitude)
        except (TypeError,ValueError):
            return None
        
    def get_encounter_name(self) -> str:
        return '' if self.encounter_name is None else self.encounter_name

    def set_encounter_name(self, value: str):
        """Set the encounter name of the recording. If the value is empty, raise an error.

        Args:
            value (str): _description_
        """
        if value is None or value.strip() == '': raise exception_handler.WarningException("Encounter name cannot be empty")
        self.encounter_name = utils.parse_string_notempty(value, 'Encounter name')

    def get_location(self) -> str:
        return '' if self.location is None else self.location

    def set_location(self, value: str):
        self.location = utils.parse_string_notempty(value, 'Location')

    def get_project(self) -> str:
        return '' if self.project is None else self.project

    def set_project(self, value: str):
        self.project = utils.parse_string_notempty(value, 'Project')

    def get_notes(self) -> str:
        return '' if self.notes is None else self.notes

    def set_notes(self, value: str) -> None:
        """ Set the notes of the recording. If `value` is empty or `None`, set it to `None`.
        If a non-string `value` is passed, convert it to a string.

        Args:
            value (str): the new value of notes
        """
        if value is not None and str(value).strip() == '': self.notes = None
        elif value is None: self.notes = None
        else: self.notes = str(value).strip()

    def get_species(self):
        return self.species

    def set_species(self, value: Species):
        """Set the species of the recording.

        Args:
            value (Species): The species to set.

        Raises:
            ValueError: If the value is not of type Species
        """
        self.species = utils.validate_type(value, Species, "species")


    def set_species_id(self, species_id: str):
        self.species_id = utils.validate_id(species_id, field="species")
    
    def set_data_source_id(self, value):
        self.data_source_id = utils.validate_id(value, field="data_source", allow_none=True)

    def set_data_source(self, value: DataSource):
        """Set the data source of the recording.

        Args:
            value (DataSource): the new data source
            
        Raises:
            ValueError: the the new value is None or not of the correct type
        """
        self.data_source = utils.validate_type(value, DataSource, "data_source", allow_none=True)

    def set_recording_platform_id(self, recording_platform_id: str | uuid.UUID):
        """Set the recording platform ID of the recording

        Args:
            recording_platform_id (str | uuid.UUID): the new recording platform ID (if given as a string it must be a valid UUID)
        
        Raises:
            ValueError: the new value is None or not of uuid.UUID or convertable str type
        """
        self.recording_platform_id = utils.validate_id(recording_platform_id, field="Recording Platform", allow_none=True)

    def set_recording_platform(self, value: RecordingPlatform):
        """Set the recording platform of the recording

        Args:
            value (RecordingPlatform): the new recording platform
            
        Raises:
            ValueError: the new value is None or not the correct type
        """
        self.recording_platform = utils.validate_type(value, RecordingPlatform, "recording_platform", allow_none=True)

    def set_file_timezone(self, value: int | str):
        """Set the timezone of the file

        Args:
            value (int | str): The new timezone. If given as a string, it must be a valid timezone string.
        
        Raises:
            ValueError: the new value is None or not of int or valid timezone string type
        """
        self.file_timezone = utils.validate_timezone(value, field="file_timezone", allow_none=True)
    
    def get_file_timezone(self) -> int:
        try:
            return int(self.file_timezone)
        except Exception:
            return None
    
    def set_local_timezone(self, value: int | str):
        self.local_timezone = utils.validate_timezone(value, field="local_timezone", allow_none=True)
    
    def get_local_timezone(self) -> int:
        try:
            return int(self.local_timezone)
        except Exception:
            return None

    def get_species_id(self) -> uuid.UUID:
        """ Get the species ID of the recording. Note that if
        the species ID is not a valid UUID or is`None`, then `None`
        is returned.

        Returns:
            uuid.UUID: the species ID
        
        Raises:
            ValueError: when the Species ID is not Null and not in UUID format
        """
        return utils.validate_id(value=self.species_id, field="Species", allow_none=True)
        
    def get_data_source_id(self) -> uuid.UUID:
        """ Get the species ID of the recording. Note that if
        the species ID is not a valid UUID or is`None`, then `None`
        is returned.

        Returns:
            uuid.UUID: the species ID
        
        Raises:
            WarningException: when the Species ID is not Null and not in UUID format
        """
        return utils.validate_id(value=self.data_source_id, field="Data Source", allow_none=True)

    def get_recording_platform_id(self) -> uuid.UUID:
        """ Get the species ID of the recording. Note that if
        the species ID is not a valid UUID or is`None`, then `None`
        is returned.

        Returns:
            uuid.UUID: the species ID
        
        Raises:
            WarningException: when the Species ID is not Null and not in UUID format
        """
        return utils.validate_id(value=self.recording_platform_id, field="Recording Platform", allow_none=True)


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


    @classmethod
    def has_record(cls, session, file_path, deleted = False, temp = False):
        root_path = database_handler.get_root_directory(deleted, temp) 
        comparison_path = os.path.relpath(file_path, root_path)
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

    def calculate_hash(self):
        import hashlib
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
        if self in session.new:
            os.remove(self.get_full_absolute_path())

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
        self.verify_hash()
    

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
    def insert_path_and_filename(self, session, file, new_directory:str, new_filename:str, override_extension:str=None, root_path=None):
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
        else:
            raise ValueError("The `file` parameter must be either a file path or a file-like object with a `stream`.")

        self.path = new_directory
        self.filename = new_filename  # filename without extension
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

        logger.info(f"Saved file to {destination_path}.")
        self.verify_hash()
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
        
        new_relative_file_path = os.path.join(new_directory, new_filename)
            
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
            os.makedirs(os.path.dirname(new_relative_file_path_with_root))
            logger.info(f"Created directory: {os.path.dirname(new_relative_file_path_with_root)}")

        # if the new and current file paths are not the same
        if new_relative_file_path_with_root != current_relative_file_path:
            self.path = os.path.dirname(new_relative_file_path)
            self.filename = os.path.basename(new_relative_file_path).split(".")[0]
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

class Recording(database_handler.db.Model):
    __tablename__ = 'recording'

    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    start_time = database_handler.db.Column(database_handler.db.DateTime(timezone=True), nullable=False)
    recording_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    selection_table_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    encounter_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('encounter.id'), nullable=False)
    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    created_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    recording_file = database_handler.db.relationship("File", foreign_keys=[recording_file_id])
    selection_table_file = database_handler.db.relationship("File", foreign_keys=[selection_table_file_id])
    encounter = database_handler.db.relationship("Encounter", foreign_keys=[encounter_id])
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    status = database_handler.db.Column(database_handler.db.Enum('Unassigned','In Progress','Awaiting Review','Reviewed','On Hold'), nullable=False, default='Unassigned')
    status_change_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True))
    notes = database_handler.db.Column(database_handler.db.Text)
    row_start = database_handler.db.Column(database_handler.db.DateTime(timezone=True), server_default=func.current_timestamp())
    
    
    __table_args__ = (
        database_handler.db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )

    def get_unique_name(self, delimiter="-") -> str:
        """Generate a unique name for the recording based on its encounter and the start time.
        The format of the unique name is `<ENCOUNTER>:<D>Recording<D>'%Y-%m-%dT%H:%M'`
        See `encounter.get_unique_name()` for for more information on `<ENCOUNTER>`. The
        delimiter (optional parameter) populates all `<D>`.

        Args:
            delimiter (str, optional): the delimiter splits values. Defaults to "-".

        Raises:
            ValueError: if there is no encounter associated with this recording

        Returns:
            str: the unique name (see above for formatting)
        """
        if self.encounter == None: raise ValueError("Unable to generate unique name as the recording does not have an encounter.")
        return f"{self.encounter.get_unique_name(delimiter)}{delimiter}Recording{delimiter}{self.get_start_time_pretty()}"

    def is_complete(self) -> bool:
        """Check if the recording has been reviewed or not.

        Returns:
            bool: True if the recording has been 'Reviewed' and False if not.
        """
        return True if self.status == 'Reviewed' else False

    def is_on_hold(self):
        """Check if the recording has been rejected (placed on hold) or not.

        Returns:
            bool: True if the recording is 'On Hold' and False if not.
        """
        """Check if the recording has been rejected (placed on hold) or not.

        Returns:
            bool: True if the recording is 'On Hold' and False if not.
        """
        return True if self.status == 'On Hold' else False

    def set_updated_by_id(self, user_id: str):
        """Set the user id of the user who is updating the recording.

        Args:
            user_id (str): The user ID who is updating the recording.
        """
        self.updated_by_id = user_id

    def set_status_change_datetime(self, value: str | datetime.datetime):
        """Set the status_change_datetime. Can pass the value as either a
        formatted string or datetime.datetime object. Note that if passing
        as a formatted string it must conform to the requirements of `utils.validate_datetime()`

        Args:
            value (str | datetime.datetime): the value to set
        """
        self.status_change_datetime = utils.validate_datetime(value, "Status Change Timestamp")

    def set_status(self, value: str):
        """Set the status of the recording. The status must be one of
        `Unassigned`, `In Progress`, `Awaiting Review`, `Reviewed`, `On Hold`.
        This method will automatically update a timestamp of when the status changed.

        Args:
            status (str): The new status of the recording.
        """
        if str(value).lower() == "unassigned": new_status = "Unassigned"
        elif str(value).lower() == "in progress": new_status = "In Progress"
        elif str(value).lower() == "awaiting review": new_status = "Awaiting Review"
        elif str(value).lower() == "reviewed": new_status = "Reviewed"
        elif str(value).lower() == "on hold": new_status = "On Hold"
        else:
            raise exception_handler.WarningException("New recording status invalid.")
        
        if self.status != new_status:
            self.set_status_change_datetime(datetime.datetime.now(datetime.timezone.utc))
            self.status = new_status

    def update_status(self):
        """Update the status of the recording based on the assignment flags. 
        If the recording is not 'On Hold' or 'Reviewed', it will be set to 'Awaiting Review'. 
        If any individual user assignment is not completed, the status will be set to 'In Progress' (overrides previous requirement).
        If the status has changed, the status_change_datetime will be set to the current datetime.datetime.
        """       
        with database_handler.get_session() as session:
            assignments = session.query(Assignment).filter_by(recording_id=self.id).all()
            new_status = ""
            if self.status != 'On Hold' and self.status != 'Reviewed':
                if len(assignments) == 0:
                    new_status = 'Unassigned'
                else:
                    new_status = 'Awaiting Review'
                    for assignment in assignments:
                        if assignment.completed_flag is False:
                            new_status = 'In Progress'
            else:
                new_status = self.status

            self.set_status(new_status)

    def set_status_on_hold(self):
        """Set the status of the recording to 'On Hold'."""
        self.set_status('On Hold')
    
    def set_status_reviewed(self):
        """Set the status of the recording to 'Reviewed'."""
        self.set_status('Reviewed')

        with database_handler.get_session() as session:
            assignments = session.query(Assignment).filter_by(recording_id=self.id).all()
            new_status = ""
            if self.status != 'On Hold' and self.status != 'Reviewed':
                if len(assignments) == 0:
                    new_status = 'Unassigned'
                else:
                    new_status = 'Awaiting Review'
                    for assignment in assignments:
                        if assignment.completed_flag is False:
                            new_status = 'In Progress'
            else:
                new_status = self.status

            self.set_status(new_status)

    def set_status_on_hold(self):
        """Set the status of the recording to 'On Hold'."""
        self.set_status('On Hold')
    
    def set_status_reviewed(self):
        """Set the status of the recording to 'Reviewed'."""
        self.set_status('Reviewed')

    def get_number_of_selections(self):
        selections = database_handler.create_system_time_request(database_handler.db.session, Selection, {"recording_id":self.id}, order_by="selection_number")
        return len(selections)

    def get_number_of_contours(self):
        contours = database_handler.db.session.query(Selection).filter_by(recording_id=self.id).filter(Selection.contour_file != None).all()
        return len(contours)

    def update_call(self):
        if self.recording_file is not None:
            with database_handler.get_session() as session:
                recording_file = session.query(File).with_for_update().get(self.recording_file_id)
                recording_file.move_file(self.generate_relative_directory(), self.generate_recording_file_name())
                session.commit()
        if self.selection_table_file is not None:
            with database_handler.get_session() as session:
                selection_table_file = session.query(File).with_for_update().get(self.selection_table_file_id)
                selection_table_file.move_file(self.generate_relative_directory(), self.generate_selection_table_file_name())
                session.commit()
        
        with database_handler.get_session() as session:
            selections = session.query(Selection).with_for_update().filter_by(recording_id=self.id).all()
            for selection in selections:
                selection.update_call()
            session.commit()
        
    def load_and_validate_selection_table(self, custom_file:str=None):
        """
        Parse a selection table file, automatically creating a Selection object for each row
        with data from the selection table file. If the Selection object already exists then
        simply insert the selection table data in the existing datastructure.

        :raises exception_handler.WarningException: if there is a formatting issue with the
        selection table or it does not exist.

        :param custom_file: the path a seleciton file to be parsed (default is None causing
        the method to access the path of the object's selection table file)
        """
        with database_handler.get_session() as session:
            try:
                st_df = pd.DataFrame()
                if custom_file is not None: st_df = utils.extract_to_dataframe(path=custom_file)
                else: st_df = utils.extract_to_dataframe(path=self.selection_table_file.get_full_absolute_path())
                self.unpack_selection_table(session, st_df)
                
                session.commit()
            
            except ValueError as e:
                raise exception_handler.WarningException("The given selection table is invalid: " + str(e))
            except FileNotFoundError as e:
                raise exception_handler.WarningException("Unable to extract data from selection table due to file system error. Please try again later.")

            

    def unpack_selection_table(self, session, st_df):
        if st_df.empty: 
            raise exception_handler.WarningException("The selection table provided is empty")
        
        if 'Selection' not in st_df.columns:
            raise exception_handler.WarningException("Missing required columns: Selection")

        selection_table_selection_numbers = st_df.Selection.to_list()
        
        for selection_number in selection_table_selection_numbers:
            selection = session.query(Selection).filter_by(recording_id=self.id, selection_number=selection_number).first()
            if selection is None:
                new_selection = Selection(recording_id=self.id, selection_number=selection_number)
                session.add(new_selection)
                new_selection.upload_selection_table_data(st_df.loc[st_df['Selection'] == selection_number, :])
            else:
                selection.upload_selection_table_data(st_df.loc[st_df['Selection'] == selection_number, :])
    

    def find_missing_selections(self, session, st_df):
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
        missing_selections = []
        selection_numbers = [selection.selection_number for selection in selections]
        if self.selection_table_file != None:
            # Validate files exist for all selections within the Selection Table
            selections_array = sorted(st_df['Selection'].to_list())
            for selection_num in selections_array:
                if selection_num not in selection_numbers:
                    missing_selections.append({"selection_number":selection_num})
        return missing_selections

    def delete_children(self, keep_file_reference=False):
        """
        Delete all files and selections associated to this recording. Note this will not delete the recording
        itself. Make sure you call session.delete() after calling this method in the caller.
        """        
        with database_handler.get_session() as session:
            assignments = session.query(Assignment).with_for_update().filter_by(recording_id=self.id).all()
            for assignment in assignments:
                session.delete(assignment)
                session.commit()
        with database_handler.get_session() as session:
            if self.recording_file_id is not None:
                recording_file = session.query(File).with_for_update().get(self.recording_file_id)
                recording_file.delete()
                if not keep_file_reference: self.recording_file = None  # Remove the reference to the recording file
                session.commit()
        with database_handler.get_session() as session:
            if self.selection_table_file_id is not None:
                selection_table_file = session.query(File).with_for_update().get(self.selection_table_file_id)
                selection_table_file.delete()
                if not keep_file_reference: self.selection_table_file = None  # Remove the reference to the selection file
                session.commit()
        with database_handler.get_session() as session:
            selections = session.query(Selection).with_for_update().filter_by(recording_id=self.id).all()
            for selection in selections:
                selection.delete_children(keep_file_reference=keep_file_reference)
                session.delete(selection)
                session.commit()

    def generate_relative_directory(self) -> str:
        """Generate the relative directory as part of the filespace hierarchy.
        All files pertaining to this recording (including the recording file
        and selection table files) will be stored in this directory.

        Raises:
            ValueError: corrupt database schema (cannot access the metadata required)

        Returns:
            str: the directory for the recording (relative, not including the directory of the filespace itself)
        """
        from .filespace_handler import format_date_for_filespace
        if not self.encounter or type(self.encounter) != Encounter: raise ValueError("The recording database schema is corrupt. Cannot generate relative directory")
        return os.path.join(self.encounter.generate_relative_directory(), f"Recording-{format_date_for_filespace(self.get_start_time())}")

    def generate_selection_table_file_name(self) -> str:
        """Generate the file name allocated to the selection table file for this
        recording in the file space. It is unique based on the metadata of this
        recording object and the encounter it is a part of.
        
        The format of the selection table file name is given below where {} signifies a variable:
        
        `SelTable-{species.species_name}-{encounter.location}-{encounter.encounter_name}-{recording.start_time}`

        Raises:
            ValueError: corrupt database schema (cannot access the metadata required)

        Returns:
            str: the selection table file name (no extension)
        """
        from . import filespace_handler
        if not self.encounter or type(self.encounter) != Encounter: raise ValueError("The recording database schema is corrupt. Cannot generate recording file name.")
        return filespace_handler.validate(f"SelTable-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{filespace_handler.format_date_for_filespace(self.start_time)}")

    def generate_recording_file_name(self) -> str:
        """Generate the file name allocated to the recording file for this
        recording in the file space. It is unique based on the metadata of this
        recording object and the encounter it is a part of.
        
        The format of the recording file name is given below where {} signifies a variable:

        `Rec-{species.species_name}-{encounter.location}-{encounter.encounter_name}-{recording.start_time}`

        Raises:
            ValueError: corrupt database schema (cannot access the metadata required)

        Returns:
            str: the recording file name (no extension)
        """
        from . import filespace_handler
        if not self.encounter or type(self.encounter) != Encounter: raise ValueError("The recording database schema is corrupt. Cannot generate recording file name.")
        return filespace_handler.validate(f"Rec-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{filespace_handler.format_date_for_filespace(self.start_time)}")

    def generate_relative_path_for_selections(self):
        folder_name = self.start_time.strftime("Selections-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.generate_relative_path(), folder_name)

    def get_start_time(self):
        return self.start_time

    def get_start_time_pretty(self):
        return utils.pretty_date(self.get_start_time())

    def set_start_time(self, value: datetime.datetime | str):
        self.start_time = utils.validate_datetime(value, "Start Time")

    def match_start_time(self, match_datetime):
        return self.start_time == match_datetime

    def get_start_time_string(self, long_format=False):
        if long_format:
            return self.start_time.strftime('%A, %B %d, %Y at %H:%M:%S')
        else:
            return self.start_time.strftime('%Y-%m-%dT%H:%M:%S')

    def set_encounter_id(self, session, encounter_id):
        encounter_id = utils.validate_id(encounter_id, field="Encounter", allow_empty=False)
    
    def update_selection_traced_status(self):
        with database_handler.get_session() as session:
            selections = database_handler.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
            for selection in selections:
                selection.update_traced_status()
                session.commit()
    
    def reset_selection_table_values(self,session):
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
        for selection in selections:
            selection.reset_selection_table_values(session)

    def export_selection_table(self, session, export_format):
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
            file_name = f'selection-table-{encounter.encounter_name}-rec-{self.get_start_time_string()}.csv'
        else:
            mimetype = 'text/plain'
            file_name = f'selection-table-{encounter.encounter_name}-rec-{self.get_start_time_string()}.txt'

        response = Response(csv_data.getvalue(), mimetype=mimetype, headers={'Content-Disposition': f'attachment; filename={file_name}'})
        
        return response

    def remove_recording_file(self) -> File:
        """Remove the recording file.

        Returns:
            File: the removed recording file (or None if nothing changed)
        """
        old_recording_file = self.recording_file
        self.recording_file_id = None
        self.recording_file = None
        return old_recording_file

    def set_recording_file_id(self, value: str | uuid.UUID):
        """ A method to populate the recording_file_id attribute. For safety reasons
        the function to replace (either with None or a new ID) an existing recording file
        is disabled. In order to populate the recording_file_id if one already exists
        please use `remove_recording_file()` first.

        Args:
            value (str | UUID): the new ID

        Raises:
            ValueError: the `recording_file_id` is already populated
            WarningException: if the given ID is not of type UUID or is of type str that cannot be converted to UUID
        """
        if self.recording_file_id or self.recording_file_id: raise ValueError('Please delete the existing recording file before inserting a new one.')
        self.recording_file_id = utils.validate_id(value, field="Recording File")

    def set_recording_file(self, value: File):
        if self.recording_file or self.recording_file_id: raise ValueError('Please delete the existing recording file before inserting a new one.')
        self.recording_file = utils.validate_type(value = value, target_type = File, field = "Recording File")

    def set_encounter_id(self, value: str | uuid.UUID):
        self.encounter_id = utils.validate_id(value=value, field="Encounter")

    def set_encounter(self, value: Encounter):
        self.encounter = utils.validate_type(value=value, target_type=Encounter, field="Encounter")

    def set_notes(self, value: str) -> None:
        """ Set the notes of the recording. If `value` is empty or `None`, set it to `None`.
        If a non-string `value` is passed, convert it to a string.

        Args:
            value (str): the new value of notes
        """
        if value is not None and str(value).strip() == '': self.notes = None
        elif value is None: self.notes = None
        else: self.notes = str(value).strip()

    def get_row_start(self) -> datetime.datetime:
        if type(self.row_start) != datetime.datetime:
            raise ValueError(f"Recording.row_start is of type {type(self.row_start)}, not datetime.datetime.")
        return self.row_start
    
    def get_row_start_pretty(self):
        utils.pretty_date(self.get_row_start())
    
    def get_created_datetime(self) -> datetime.datetime:
        if type(self.created_datetime) != datetime.datetime:
            raise ValueError(f"Recording.created_datetime is of type {type(self.created_datetime)}, not datetime.datetime.")
        return self.created_datetime
    
    def get_created_datetime_pretty(self):
        return utils.pretty_date(self.get_created_datetime())
    
    def get_recording_file_id(self) -> uuid.UUID | None:
        """ Get the recording file id in UUID format. Returns None
        if there is no recording file id.

        Returns:
            uuid.UUID: the recording file id (or None)
        
        Raises:
            WarningException: when a non-Null recording file id is not in UUID format
        """
        return utils.validate_id(value=self.recording_file_id, field="Recording File", allow_none=True)

    def get_recording_file(self) -> File | None:
        return utils.validate_type(value=self.recording_file, target_type=File, field="Recording File", allow_none=True)

    def get_encounter_id(self) -> str | None:
        return utils.validate_id(value=self.encounter_id, field="Encounter", allow_none=True)

    def get_encounter(self) -> Encounter | None:
        return utils.validate_type(value=self.encounter, target_type=Encounter, field="Encounter", allow_none=True)

    def get_status(self) -> str | None:
        return str(self.status) if self.status else None

    def get_status_change_datetime(self):
        return utils.validate_datetime(self.status_change_datetime, field="Status Change Datetime", allow_none=True)

    def get_status_change_datetime_pretty(self):
        return utils.pretty_date(self.get_status_change_datetime())
    

    def get_notes(self):
        return '' if self.notes is None else self.notes


class Role(database_handler.db.Model):
    id = database_handler.db.Column(database_handler.db.Integer, primary_key=True)
    name = database_handler.db.Column(database_handler.db.String(100))

"""

class RecordingAudit(Audit, Recording, database_handler.db.Model):
    __tablename__ = 'recording_audit'

    record_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('recording.id'), nullable=False)
    record = database_handler.db.relationship("Recording", foreign_keys=[record_id])
"""
class Selection(database_handler.db.Model):
    __tablename__ = 'selection'

    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    selection_number = database_handler.db.Column(database_handler.db.Integer, nullable=False)
    selection_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'), nullable=False)
    recording_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('recording.id'), nullable=False)
    contour_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    ctr_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    spectogram_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    plot_file_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('file.id'))
    sampling_rate = database_handler.db.Column(database_handler.db.Float, nullable=False)
    traced = database_handler.db.Column(database_handler.db.Boolean, nullable=True, default=None)
    deactivated = database_handler.db.Column(database_handler.db.Boolean, nullable=True, default=False)
    row_start = database_handler.db.Column(database_handler.db.DateTime(timezone=True), server_default=func.current_timestamp())
    default_fft_size = database_handler.db.Column(database_handler.db.Integer)
    default_hop_size = database_handler.db.Column(database_handler.db.Integer)
    created_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


    ### Selection Table data ###
    view = database_handler.db.Column(database_handler.db.Text)
    channel = database_handler.db.Column(database_handler.db.Integer)
    begin_time = database_handler.db.Column(database_handler.db.Float)
    end_time = database_handler.db.Column(database_handler.db.Float)
    low_frequency = database_handler.db.Column(database_handler.db.Float)
    high_frequency = database_handler.db.Column(database_handler.db.Float)
    delta_time = database_handler.db.Column(database_handler.db.Float)
    delta_frequency = database_handler.db.Column(database_handler.db.Float)
    average_power = database_handler.db.Column(database_handler.db.Float)
    annotation = database_handler.db.Column(database_handler.db.Text, nullable=False)

    ### Contour Statistics data ###
    freq_max = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_min = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    duration = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_begin = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_end = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_range = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_standarddeviation = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_standarddeviation = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_median = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_center = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_relbw = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_maxminratio = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_begendratio = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_quarter1 = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_quarter2 = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_quarter3 = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_spread = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_quarter1mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_quarter2mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_quarter3mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    dc_quarter4mean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_cofm = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_stepup = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_stepdown = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_numsteps = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_slopemean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_absslopemean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_posslopemean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_negslopemean = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_sloperatio = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_begsweep = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_begup = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_begdown = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_endsweep = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_endup = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_enddown = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsupdown = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsdownup = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsupflat = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsdownflat = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsflatup = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    num_sweepsflatdown = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    freq_sweepuppercent = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_sweepdownpercent = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    freq_sweepflatpercent = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    num_inflections = database_handler.db.Column(database_handler.db.Integer, nullable=True, default=None)
    inflection_maxdelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_mindelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_maxmindelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_mediandelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_meandelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_standarddeviationdelta = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    inflection_duration = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    step_duration = database_handler.db.Column(database_handler.db.Float, nullable=True, default=None)
    
    contour_file = database_handler.db.relationship("File", foreign_keys=[contour_file_id])
    selection_file = database_handler.db.relationship("File", foreign_keys=[selection_file_id])
    recording = database_handler.db.relationship("Recording", foreign_keys=[recording_id])
    ctr_file = database_handler.db.relationship("File", foreign_keys=[ctr_file_id])
    spectogram_file = database_handler.db.relationship("File", foreign_keys=[spectogram_file_id])
    plot_file = database_handler.db.relationship("File", foreign_keys=[plot_file_id])
    
    updated_by_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])


    __table_args__ = (
        database_handler.db.UniqueConstraint('selection_number', 'recording_id', name='unique_selection_number_recording'),
        {"mysql_engine": "InnoDB", "mysql_charset": "latin1", "mysql_collate": "latin1_swedish_ci"}
    )


    def get_row_start(self) -> datetime.datetime:
        if type(self.row_start) != datetime.datetime:
            raise ValueError(f"Recording.row_start is of type {type(self.row_start)}, not datetime.datetime.")
        return self.row_start
    
    def get_row_start_pretty(self):
        utils.pretty_date(self.get_row_start())
    
    def get_created_datetime(self) -> datetime.datetime:
        if type(self.created_datetime) != datetime.datetime:
            raise ValueError(f"Recording.created_datetime is of type {type(self.created_datetime)}, not datetime.datetime.")
        return self.created_datetime
    
    def get_created_datetime_pretty(self):
        return utils.pretty_date(self.get_created_datetime())
    

    def get_freq_max(self) -> float:
        return utils.validate_float(self.freq_max, field="freq_max", allow_none = True)
    def set_freq_max(self, value: float):
        self.freq_max = utils.validate_float(value, field="freq_max", allow_none = False)

    def get_freq_min(self) -> float:
        return utils.validate_float(self.freq_min, field="freq_min", allow_none = True)
    def set_freq_min(self, value: float):
        self.freq_min = utils.validate_float(value, field="freq_min", allow_none = False)

    def get_duration(self) -> float:
        return utils.validate_float(self.duration, field="duration", allow_none = True)
    def set_duration(self, value: float):
        self.duration = utils.validate_float(value, field="duration", allow_none = False)

    def get_freq_begin(self) -> float:
        return utils.validate_float(self.freq_begin, field="freq_begin", allow_none = True)
    def set_freq_begin(self, value: float):
        self.freq_begin = utils.validate_float(value, field="freq_begin", allow_none = False)

    def get_freq_end(self) -> float:
        return utils.validate_float(self.freq_end, field="freq_end", allow_none = True)
    def set_freq_end(self, value: float):
        self.freq_end = utils.validate_float(value, field="freq_end", allow_none = False)

    def get_freq_range(self) -> float:
        return utils.validate_float(self.freq_range, field="freq_range", allow_none = True)
    def set_freq_range(self, value: float):
        self.freq_range = utils.validate_float(value, field="freq_range", allow_none = False)

    def get_dc_mean(self) -> float:
        return utils.validate_float(self.dc_mean, field="dc_mean", allow_none = True)
    def set_dc_mean(self, value: float):
        self.dc_mean = utils.validate_float(value, field="dc_mean", allow_none = False)

    def get_dc_standarddeviation(self) -> float:
        return utils.validate_float(self.dc_standarddeviation, field="dc_standarddeviation", allow_none = True)
    def set_dc_standarddeviation(self, value: float):
        self.dc_standarddeviation = utils.validate_float(value, field="dc_standarddeviation", allow_none = False)

    def get_freq_mean(self) -> float:
        return utils.validate_float(self.freq_mean, field="freq_mean", allow_none = True)
    def set_freq_mean(self, value: float):
        self.freq_mean = utils.validate_float(value, field="freq_mean", allow_none = False)

    def get_freq_standarddeviation(self) -> float:
        return utils.validate_float(self.freq_standarddeviation, field="freq_standarddeviation", allow_none = True)
    def set_freq_standarddeviation(self, value: float):
        self.freq_standarddeviation = utils.validate_float(value, field="freq_standarddeviation", allow_none = False)

    def get_freq_median(self) -> float:
        return utils.validate_float(self.freq_median, field="freq_median", allow_none = True)
    def set_freq_median(self, value: float):
        self.freq_median = utils.validate_float(value, field="freq_median", allow_none = False)

    def get_freq_center(self) -> float:
        return utils.validate_float(self.freq_center, field="freq_center", allow_none = True)
    def set_freq_center(self, value: float):
        self.freq_center = utils.validate_float(value, field="freq_center", allow_none = False)

    def get_freq_relbw(self) -> float:
        return utils.validate_float(self.freq_relbw, field="freq_relbw", allow_none = True)
    def set_freq_relbw(self, value: float):
        self.freq_relbw = utils.validate_float(value, field="freq_relbw", allow_none = False)

    def get_freq_maxminratio(self) -> float:
        return utils.validate_float(self.freq_maxminratio, field="freq_maxminratio", allow_none = True)
    def set_freq_maxminratio(self, value: float):
        self.freq_maxminratio = utils.validate_float(value, field="freq_maxminratio", allow_none = False)

    def get_freq_begendratio(self) -> float:
        return utils.validate_float(self.freq_begendratio, field="freq_begendratio", allow_none = True)
    def set_freq_begendratio(self, value: float):
        self.freq_begendratio = utils.validate_float(value, field="freq_begendratio", allow_none = False)

    def get_freq_quarter1(self) -> float:
        return utils.validate_float(self.freq_quarter1, field="freq_quarter1", allow_none = True)
    def set_freq_quarter1(self, value: float):
        self.freq_quarter1 = utils.validate_float(value, field="freq_quarter1", allow_none = False)

    def get_freq_quarter2(self) -> float:
        return utils.validate_float(self.freq_quarter2, field="freq_quarter2", allow_none = True)
    def set_freq_quarter2(self, value: float):
        self.freq_quarter2 = utils.validate_float(value, field="freq_quarter2", allow_none = False)

    def get_freq_quarter3(self) -> float:
        return utils.validate_float(self.freq_quarter3, field="freq_quarter3", allow_none = True)
    def set_freq_quarter3(self, value: float):
        self.freq_quarter3 = utils.validate_float(value, field="freq_quarter3", allow_none = False)

    def get_freq_spread(self) -> float:
        return utils.validate_float(self.freq_spread, field="freq_spread", allow_none = True)
    def set_freq_spread(self, value: float):
        self.freq_spread = utils.validate_float(value, field="freq_spread", allow_none = False)

    def get_dc_quarter1mean(self) -> float:
        return utils.validate_float(self.dc_quarter1mean, field="dc_quarter1mean", allow_none = True)
    def set_dc_quarter1mean(self, value: float):
        self.dc_quarter1mean = utils.validate_float(value, field="dc_quarter1mean", allow_none = False)

    def get_dc_quarter2mean(self) -> float:
        return utils.validate_float(self.dc_quarter2mean, field="dc_quarter2mean", allow_none = True)
    def set_dc_quarter2mean(self, value: float):
        self.dc_quarter2mean = utils.validate_float(value, field="dc_quarter2mean", allow_none = False)

    def get_dc_quarter3mean(self) -> float:
        return utils.validate_float(self.dc_quarter3mean, field="dc_quarter3mean", allow_none = True)
    def set_dc_quarter3mean(self, value: float):
        self.dc_quarter3mean = utils.validate_float(value, field="dc_quarter3mean", allow_none = False)

    def get_dc_quarter4mean(self) -> float:
        return utils.validate_float(self.dc_quarter4mean, field="dc_quarter4mean", allow_none = True)
    def set_dc_quarter4mean(self, value: float):
        self.dc_quarter4mean = utils.validate_float(value, field="dc_quarter4mean", allow_none = False)

    def get_freq_cofm(self) -> float:
        return utils.validate_float(self.freq_cofm, field="freq_cofm", allow_none = True)
    def set_freq_cofm(self, value: float):
        self.freq_cofm = utils.validate_float(value, field="freq_cofm", allow_none = False)

    def get_freq_slopemean(self) -> float:
        return utils.validate_float(self.freq_slopemean, field="freq_slopemean", allow_none = True)
    def set_freq_slopemean(self, value: float):
        self.freq_slopemean = utils.validate_float(value, field="freq_slopemean", allow_none = False)

    def get_freq_absslopemean(self) -> float:
        return utils.validate_float(self.freq_absslopemean, field="freq_absslopemean", allow_none = True)
    def set_freq_absslopemean(self, value: float):
        self.freq_absslopemean = utils.validate_float(value, field="freq_absslopemean", allow_none = False)

    def get_freq_posslopemean(self) -> float:
        return utils.validate_float(self.freq_posslopemean, field="freq_posslopemean", allow_none = True)
    def set_freq_posslopemean(self, value: float):
        self.freq_posslopemean = utils.validate_float(value, field="freq_posslopemean", allow_none = False)

    def get_freq_negslopemean(self) -> float:
        return utils.validate_float(self.freq_negslopemean, field="freq_negslopemean", allow_none = True)
    def set_freq_negslopemean(self, value: float):
        self.freq_negslopemean = utils.validate_float(value, field="freq_negslopemean", allow_none = False)

    def get_freq_sloperatio(self) -> float:
        return utils.validate_float(self.freq_sloperatio, field="freq_sloperatio", allow_none = True)
    def set_freq_sloperatio(self, value: float):
        self.freq_sloperatio = utils.validate_float(value, field="freq_sloperatio", allow_none = False)

    def get_freq_sweepuppercent(self) -> float:
        return utils.validate_float(self.freq_sweepuppercent, field="freq_sweepuppercent", allow_none = True)
    def set_freq_sweepuppercent(self, value: float):
        self.freq_sweepuppercent = utils.validate_float(value, field="freq_sweepuppercent", allow_none = False)

    def get_freq_sweepdownpercent(self) -> float:
        return utils.validate_float(self.freq_sweepdownpercent, field="freq_sweepdownpercent", allow_none = True)
    def set_freq_sweepdownpercent(self, value: float):
        self.freq_sweepdownpercent = utils.validate_float(value, field="freq_sweepdownpercent", allow_none = False)

    def get_freq_sweepflatpercent(self) -> float:
        return utils.validate_float(self.freq_sweepflatpercent, field="freq_sweepflatpercent", allow_none = True)
    def set_freq_sweepflatpercent(self, value: float):
        self.freq_sweepflatpercent = utils.validate_float(value, field="freq_sweepflatpercent", allow_none = False)

    def get_inflection_maxdelta(self) -> float:
        return utils.validate_float(self.inflection_maxdelta, field="inflection_maxdelta", allow_none = True)
    def set_inflection_maxdelta(self, value: float):
        self.inflection_maxdelta = utils.validate_float(value, field="inflection_maxdelta", allow_none = False)

    def get_inflection_mindelta(self) -> float:
        return utils.validate_float(self.inflection_mindelta, field="inflection_mindelta", allow_none = True)
    def set_inflection_mindelta(self, value: float):
        self.inflection_mindelta = utils.validate_float(value, field="inflection_mindelta", allow_none = False)

    def get_inflection_maxmindelta(self) -> float:
        return utils.validate_float(self.inflection_maxmindelta, field="inflection_maxmindelta", allow_none = True)
    def set_inflection_maxmindelta(self, value: float):
        self.inflection_maxmindelta = utils.validate_float(value, field="inflection_maxmindelta", allow_none = False)

    def get_inflection_mediandelta(self) -> float:
        return utils.validate_float(self.inflection_mediandelta, field="inflection_mediandelta", allow_none = True)
    def set_inflection_mediandelta(self, value: float):
        self.inflection_mediandelta = utils.validate_float(value, field="inflection_mediandelta", allow_none = False)

    def get_inflection_meandelta(self) -> float:
        return utils.validate_float(self.inflection_meandelta, field="inflection_meandelta", allow_none = True)
    def set_inflection_meandelta(self, value: float):
        self.inflection_meandelta = utils.validate_float(value, field="inflection_meandelta", allow_none = False)

    def get_inflection_standarddeviationdelta(self) -> float:
        return utils.validate_float(self.inflection_standarddeviationdelta, field="inflection_standarddeviationdelta", allow_none = True)
    def set_inflection_standarddeviationdelta(self, value: float):
        self.inflection_standarddeviationdelta = utils.validate_float(value, field="inflection_standarddeviationdelta", allow_none = False)

    def get_inflection_duration(self) -> float:
        return utils.validate_float(self.inflection_duration, field="inflection_duration", allow_none = True)
    def set_inflection_duration(self, value: float):
        self.inflection_duration = utils.validate_float(value, field="inflection_duration", allow_none = False)

    def get_step_duration(self) -> float:
        return utils.validate_float(self.step_duration, field="step_duration", allow_none = True)
    def set_step_duration(self, value: float):
        self.step_duration = utils.validate_float(value, field="step_duration", allow_none = False)

    def get_freq_stepup(self) -> int:
        return utils.validate_int(self.freq_stepup, field="freq_stepup", allow_none = True)
    def set_freq_stepup(self, value: int):
        self.freq_stepup = utils.validate_int(value, field="freq_stepup", allow_none = False)

    def get_freq_stepdown(self) -> int:
        return utils.validate_int(self.freq_stepdown, field="freq_stepdown", allow_none = True)
    def set_freq_stepdown(self, value: int):
        self.freq_stepdown = utils.validate_int(value, field="freq_stepdown", allow_none = False)

    def get_freq_numsteps(self) -> int:
        return utils.validate_int(self.freq_numsteps, field="freq_numsteps", allow_none = True)
    def set_freq_numsteps(self, value: int):
        self.freq_numsteps = utils.validate_int(value, field="freq_numsteps", allow_none = False)

    def get_freq_begsweep(self) -> int:
        return utils.validate_int(self.freq_begsweep, field="freq_begsweep", allow_none = True)
    def set_freq_begsweep(self, value: int):
        self.freq_begsweep = utils.validate_int(value, field="freq_begsweep", allow_none = False)

    def get_freq_begup(self) -> int:
        return utils.validate_int(self.freq_begup, field="freq_begup", allow_none = True)
    def set_freq_begup(self, value: int):
        self.freq_begup = utils.validate_int(value, field="freq_begup", allow_none = False)

    def get_freq_begdown(self) -> int:
        return utils.validate_int(self.freq_begdown, field="freq_begdown", allow_none = True)
    def set_freq_begdown(self, value: int):
        self.freq_begdown = utils.validate_int(value, field="freq_begdown", allow_none = False)

    def get_freq_endsweep(self) -> int:
        return utils.validate_int(self.freq_endsweep, field="freq_endsweep", allow_none = True)
    def set_freq_endsweep(self, value: int):
        self.freq_endsweep = utils.validate_int(value, field="freq_endsweep", allow_none = False)

    def get_freq_endup(self) -> int:
        return utils.validate_int(self.freq_endup, field="freq_endup", allow_none = True)
    def set_freq_endup(self, value: int):
        self.freq_endup = utils.validate_int(value, field="freq_endup", allow_none = False)

    def get_freq_enddown(self) -> int:
        return utils.validate_int(self.freq_enddown, field="freq_enddown", allow_none = True)
    def set_freq_enddown(self, value: int):
        self.freq_enddown = utils.validate_int(value, field="freq_enddown", allow_none = False)

    def get_num_sweepsupdown(self) -> int:
        return utils.validate_int(self.num_sweepsupdown, field="num_sweepsupdown", allow_none = True)
    def set_num_sweepsupdown(self, value: int):
        self.num_sweepsupdown = utils.validate_int(value, field="num_sweepsupdown", allow_none = False)

    def get_num_sweepsdownup(self) -> int:
        return utils.validate_int(self.num_sweepsdownup, field="num_sweepsdownup", allow_none = True)
    def set_num_sweepsdownup(self, value: int):
        self.num_sweepsdownup = utils.validate_int(value, field="num_sweepsdownup", allow_none = False)

    def get_num_sweepsupflat(self) -> int:
        return utils.validate_int(self.num_sweepsupflat, field="num_sweepsupflat", allow_none = True)
    def set_num_sweepsupflat(self, value: int):
        self.num_sweepsupflat = utils.validate_int(value, field="num_sweepsupflat", allow_none = False)

    def get_num_sweepsdownflat(self) -> int:
        return utils.validate_int(self.num_sweepsdownflat, field="num_sweepsdownflat", allow_none = True)
    def set_num_sweepsdownflat(self, value: int):
        self.num_sweepsdownflat = utils.validate_int(value, field="num_sweepsdownflat", allow_none = False)

    def get_num_sweepsflatup(self) -> int:
        return utils.validate_int(self.num_sweepsflatup, field="num_sweepsflatup", allow_none = True)
    def set_num_sweepsflatup(self, value: int):
        self.num_sweepsflatup = utils.validate_int(value, field="test_get_num_sweepsflatup", allow_none = False)

    def get_num_sweepsflatdown(self) -> int:
        return utils.validate_int(self.num_sweepsflatdown, field="num_sweepsflatdown", allow_none = True)
    def set_num_sweepsflatdown(self, value: int):
        self.num_sweepsflatdown = utils.validate_int(value, field="num_sweepsflatdown", allow_none = False)

    def get_num_inflections(self) -> int:
        return utils.validate_int(self.num_inflections, field="num_inflections", allow_none = True)
    def set_num_inflections(self, value: int):
        self.num_inflections = utils.validate_int(value, field="num_inflections", allow_none = False)


    def get_rounded_value(self, value:int|float, decimal_places:int=3) -> int|float:
        """
        Round a number value to a number of decimal_places. If value is an integer the integer
        is simply returned with no rounding.
        """
        return round(value, decimal_places) if value is not None and type(value) is float else value

    def recalculate_contour_statistics(self, session):
        """
        Recalculate contour statistics for the given selection.

        :param session: The current sqlalchemy session
        :type session: sqlalchemy.orm.session.Session
        :param selection: The selection object to recalculate the contour statistics for
        :type selection: Selection
        """
        self.reset_contour_stats()
        if self.contour_file is not None:
            try:
                contour_file_obj = contour_statistics.ContourFile(self.contour_file.get_full_absolute_path(),self.selection_number)
                contour_rows = contour_file_obj.calculate_statistics(session, self)
                self.generate_ctr_file(session, contour_rows)
            except ValueError as e:
                raise exception_handler.WarningException(f"Error processing contour {self.selection_number}: " + str(e))

    def get_unique_name(self, delimiter: str = "-"):
        """Generate a unique name for the encounter based on its recording and the selection number.
        The format of the unique name is `<RECORDING>: Selection <SELECTION_NUMBER>`
        See `recording.get_unique_name()` for for more information on `<RECORDING>`.

        Args:
            delimiter (str, optional): the delimiter splits values. Defaults to "-".

        Raises:
            ValueError: if there is no recording associated with this recording

        Returns:
            str: the unique name (see above for formatting)
        """
        if self.recording == None: raise ValueError("Unable to generate unique name as the encounter does not have a recording.")
        return f"{self.recording.get_unique_name(delimiter)}: Selection {self.selection_number}"



    def calculate_sampling_rate(self):
        if self.selection_file:
            import wave
            with wave.open(self.selection_file.get_full_absolute_path(), "rb") as wave_file:
                self.sampling_rate = wave_file.getframerate()

    def deactivate(self):
        self.traced = None
        self.deactivated = True

    def reactivate(self):
        self.traced = None
        self.deactivated = False

    def reset_selection_table_values(self):
        self.view = None
        self.channel = None
        self.begin_time = None
        self.end_time = None
        self.low_frequency = None
        self.high_frequency = None
        self.delta_time = None
        self.delta_frequency = None
        self.average_power = None
        self.annotation = None

    def update_traced_status(self):
        if self.contour_file and (self.annotation == "Y" or self.annotation == "M"):
            self.traced = True
        elif not self.contour_file and (self.annotation == "N"):
            self.traced = False
        else:
            self.traced = None
            
    def set_selection_file(self, selection_file: File):
        if selection_file.extension != 'wav':
            raise exception_handler.WarningException(f"Selection {self.selection_number} needs to be of type 'wav' but is '{selection_file.extension}'")
        self.calculate_sampling_rate()
        self.selection_file = selection_file

    def create_temp_plot(self, session, temp_dir, fft_size=None, hop_size=None, update_permissions=False):
        from .contour_statistics import ContourFile
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
            contour_file_obj = ContourFile(self.contour_file.get_full_absolute_path(), self.selection_number)
            contour_rows = contour_file_obj.contour_rows
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
        plot_path = os.path.join(temp_dir, self.generate_plot_file_name() + ".png")
        plt.savefig(plot_path, bbox_inches='tight')

        plt.close('all')

        return plot_path

    def generate_ctr_file(self, session, contour_rows):
        import matplotlib.pyplot as plt


        def find_most_common_difference(arr):
            differences = []
            for i in range(len(arr) - 1):
                differences.append(arr[i + 1] - arr[i])
            most_common_difference = max(set(differences), key=differences.count)
            return most_common_difference


        
        if self.ctr_file:
            self.ctr_file.move_to_trash()
            self.ctr_file = None
            
        temp_res = find_most_common_difference([unit.time_milliseconds for unit in contour_rows])/1000
        ctr_length = temp_res*len(contour_rows)
        # Create a dictionary to store the data in the .ctr format
        mat_data = {'tempRes':temp_res,'freqContour': np.array([unit.peak_frequency for unit in contour_rows]),'ctrLength':ctr_length}
        # Save the data to a MATLAB file
        scipy.io.savemat(os.path.join(database_handler.get_file_space_path(), os.path.join(self.generate_relative_path(), self.generate_ctr_file_name())) + ".ctr", mat_data)
        
        file_obj = File()
        file_obj.insert_path_and_filename_file_already_in_place(session, self.generate_relative_path(),self.generate_ctr_file_name().split(".")[0], "ctr")
        session.add(file_obj)
        self.ctr_file = file_obj

        session.commit()



    def reset_contour_stats(self):
        self.freq_max = None
        self.freq_min = None
        self.duration = None
        self.freq_begin = None
        self.freq_end = None
        self.freq_range = None
        self.dc_mean = None
        self.dc_standarddeviation = None
        self.freq_mean = None
        self.freq_standarddeviation = None
        self.freq_median = None
        self.freq_center = None
        self.freq_relbw = None
        self.freq_maxminratio = None
        self.freq_begendratio = None
        self.freq_quarter1 = None
        self.freq_quarter2 = None
        self.freq_quarter3 = None
        self.freq_spread = None
        self.dc_quarter1mean = None
        self.dc_quarter2mean = None
        self.dc_quarter3mean = None
        self.dc_quarter4mean = None
        self.freq_cofm = None
        self.freq_stepup = None
        self.freq_stepdown = None
        self.freq_numsteps = None
        self.freq_slopemean = None
        self.freq_absslopemean = None
        self.freq_posslopemean = None
        self.freq_negslopemean = None
        self.freq_sloperatio = None
        self.freq_begsweep = None
        self.freq_begup = None
        self.freq_begdown = None
        self.freq_endsweep = None
        self.freq_endup = None
        self.freq_enddown = None
        self.num_sweepsupdown = None
        self.num_sweepsdownup = None
        self.num_sweepsupflat = None
        self.num_sweepsdownflat = None
        self.num_sweepsflatup = None
        self.num_sweepsflatdown = None
        self.freq_sweepuppercent = None
        self.freq_sweepdownpercent = None
        self.freq_sweepflatpercent = None
        self.num_inflections = None
        self.inflection_maxdelta = None
        self.inflection_mindelta = None
        self.inflection_maxmindelta = None
        self.inflection_mediandelta = None
        self.inflection_meandelta = None
        self.inflection_standarddeviationdelta = None
        self.inflection_duration = None
        self.step_duration = None

    def generate_contour_stats_array(self):
        return [self.recording.encounter.encounter_name, self.recording.encounter.location, self.recording.encounter.project, self.recording.get_start_time_string(), self.recording.encounter.species.species_name, self.sampling_rate,  self.selection_number, self.freq_max, self.freq_min, self.duration, self.freq_begin, self.freq_end, self.freq_range, self.dc_mean, self.dc_standarddeviation, self.freq_mean, self.freq_standarddeviation, self.freq_median, self.freq_center, self.freq_relbw, self.freq_maxminratio, self.freq_begendratio, self.freq_quarter1, self.freq_quarter2, self.freq_quarter3, self.freq_spread, self.dc_quarter1mean, self.dc_quarter2mean, self.dc_quarter3mean, self.dc_quarter4mean, self.freq_cofm, self.freq_stepup, self.freq_stepdown, self.freq_numsteps, self.freq_slopemean, self.freq_absslopemean, self.freq_posslopemean, self.freq_negslopemean, self.freq_sloperatio, self.freq_begsweep, self.freq_begup, self.freq_begdown, self.freq_endsweep, self.freq_endup, self.freq_enddown, self.num_sweepsupdown, self.num_sweepsdownup, self.num_sweepsupflat, self.num_sweepsdownflat, self.num_sweepsflatup, self.num_sweepsflatdown, self.freq_sweepuppercent, self.freq_sweepdownpercent, self.freq_sweepflatpercent, self.num_inflections, self.inflection_maxdelta, self.inflection_mindelta, self.inflection_maxmindelta, self.inflection_meandelta, self.inflection_standarddeviationdelta, self.inflection_mediandelta, self.inflection_duration, self.step_duration]

    def generate_contour_stats_dict(self):
        headers = ['Encounter', 'Location', 'Project', 'Recording', 'Species', 'SamplingRate', 'SELECTIONNUMBER', 'FREQMAX', 'FREQMIN', 'DURATION', 'FREQBEG', 'FREQEND', 'FREQRANGE', 'DCMEAN', 'DCSTDDEV', 'FREQMEAN', 'FREQSTDDEV', 'FREQMEDIAN', 'FREQCENTER', 'FREQRELBW', 'FREQMAXMINRATIO', 'FREQBEGENDRATIO', 'FREQQUARTER1', 'FREQQUARTER2', 'FREQQUARTER3', 'FREQSPREAD', 'DCQUARTER1MEAN', 'DCQUARTER2MEAN', 'DCQUARTER3MEAN', 'DCQUARTER4MEAN', 'FREQCOFM', 'FREQSTEPUP', 'FREQSTEPDOWN', 'FREQNUMSTEPS', 'FREQSLOPEMEAN', 'FREQABSSLOPEMEAN', 'FREQPOSSLOPEMEAN', 'FREQNEGSLOPEMEAN', 'FREQSLOPERATIO', 'FREQBEGSWEEP', 'FREQBEGUP', 'FREQBEGDWN', 'FREQENDSWEEP', 'FREQENDUP', 'FREQENDDWN', 'NUMSWEEPSUPDWN', 'NUMSWEEPSDWNUP', 'NUMSWEEPSUPFLAT', 'NUMSWEEPSDWNFLAT', 'NUMSWEEPSFLATUP', 'NUMSWEEPSFLATDWN', 'FREQSWEEPUPPERCENT', 'FREQSWEEPDWNPERCENT', 'FREQSWEEPFLATPERCENT', 'NUMINFLECTIONS', 'INFLMAXDELTA', 'INFLMINDELTA', 'INFLMAXMINDELTA', 'INFLMEANDELTA', 'INFLSTDDEVDELTA', 'INFLMEDIANDELTA', 'INFLDUR', 'STEPDUR']
        values = [self.recording.encounter.encounter_name, self.recording.encounter.location, self.recording.encounter.project, self.recording.get_start_time_string(), self.recording.encounter.species.species_name, self.sampling_rate, self.selection_number, self.freq_max, self.freq_min, self.duration, self.freq_begin, self.freq_end, self.freq_range, self.dc_mean, self.dc_standarddeviation, self.freq_mean, self.freq_standarddeviation, self.freq_median, self.freq_center, self.freq_relbw, self.freq_maxminratio, self.freq_begendratio, self.freq_quarter1, self.freq_quarter2, self.freq_quarter3, self.freq_spread, self.dc_quarter1mean, self.dc_quarter2mean, self.dc_quarter3mean, self.dc_quarter4mean, self.freq_cofm, self.freq_stepup, self.freq_stepdown, self.freq_numsteps, self.freq_slopemean, self.freq_absslopemean, self.freq_posslopemean, self.freq_negslopemean, self.freq_sloperatio, self.freq_begsweep, self.freq_begup, self.freq_begdown, self.freq_endsweep, self.freq_endup, self.freq_enddown, self.num_sweepsupdown, self.num_sweepsdownup, self.num_sweepsupflat, self.num_sweepsdownflat, self.num_sweepsflatup, self.num_sweepsflatdown, self.freq_sweepuppercent, self.freq_sweepdownpercent, self.freq_sweepflatpercent, self.num_inflections, self.inflection_maxdelta, self.inflection_mindelta, self.inflection_maxmindelta, self.inflection_meandelta, self.inflection_standarddeviationdelta, self.inflection_mediandelta, self.inflection_duration, self.step_duration]
        return dict(zip(headers, values))

    def upload_selection_table_data(self, st_df):
        missing_columns = []

        for required_column in ('Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Annotation'):
            if required_column not in st_df.columns:
                missing_columns.append(required_column)
        missing_columns = []

        for required_column in ('Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Annotation'):
            if required_column not in st_df.columns:
                missing_columns.append(required_column)
        
        if len(missing_columns) > 0:
            raise exception_handler.WarningException(f"Missing required columns: {', '.join(missing_columns)}")

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
        self.view = st_df.iloc[0, st_df.columns.get_loc('View')]
        self.channel = st_df.iloc[0, st_df.columns.get_loc('Channel')]
        self.begin_time = st_df.iloc[0, st_df.columns.get_loc('Begin Time (s)')]
        self.end_time = st_df.iloc[0, st_df.columns.get_loc('End Time (s)')]
        self.low_frequency = st_df.iloc[0, st_df.columns.get_loc('Low Freq (Hz)')]
        self.high_frequency = st_df.iloc[0, st_df.columns.get_loc('High Freq (Hz)')]
        self.delta_time = st_df.iloc[0, st_df.columns.get_loc('Delta Time (s)')] if 'Delta Time (s)' in st_df.columns else None
        self.delta_frequency = st_df.iloc[0, st_df.columns.get_loc('Delta Freq (Hz)')] if 'Delta Freq (Hz)' in st_df.columns else None
        self.average_power = st_df.iloc[0, st_df.columns.get_loc('Avg Power Density (dB FS/Hz)')] if 'Avg Power Density (dB FS/Hz)' in st_df.columns else None

        if not self.delta_time: self.delta_time = self.end_time - self.begin_time
        if not self.delta_frequency: self.delta_frequency = self.high_frequency - self.low_frequency
        self.view = st_df.iloc[0, st_df.columns.get_loc('View')]
        self.channel = st_df.iloc[0, st_df.columns.get_loc('Channel')]
        self.begin_time = st_df.iloc[0, st_df.columns.get_loc('Begin Time (s)')]
        self.end_time = st_df.iloc[0, st_df.columns.get_loc('End Time (s)')]
        self.low_frequency = st_df.iloc[0, st_df.columns.get_loc('Low Freq (Hz)')]
        self.high_frequency = st_df.iloc[0, st_df.columns.get_loc('High Freq (Hz)')]
        self.delta_time = st_df.iloc[0, st_df.columns.get_loc('Delta Time (s)')] if 'Delta Time (s)' in st_df.columns else None
        self.delta_frequency = st_df.iloc[0, st_df.columns.get_loc('Delta Freq (Hz)')] if 'Delta Freq (Hz)' in st_df.columns else None
        self.average_power = st_df.iloc[0, st_df.columns.get_loc('Avg Power Density (dB FS/Hz)')] if 'Avg Power Density (dB FS/Hz)' in st_df.columns else None

        if not self.delta_time: self.delta_time = self.end_time - self.begin_time
        if not self.delta_frequency: self.delta_frequency = self.high_frequency - self.low_frequency

    def update_call(self):
        self.move_file()

    def move_file(self):
        if self.selection_file is not None:
            with database_handler.get_session() as session:
                selection_file = session.query(File).with_for_update().get(self.selection_file_id)
                selection_file.move_file(self.generate_relative_path(),self.generate_selection_file_name())
                session.commit()
        if self.contour_file is not None:
            with database_handler.get_session() as session:
                contour_file = session.query(File).with_for_update().get(self.contour_file_id)
                contour_file.move_file(self.generate_relative_path(),self.generate_contour_file_name())
                session.commit()
        if self.ctr_file is not None:
            with database_handler.get_session() as session:
                ctr_file = session.query(File).with_for_update().get(self.ctr_file_id)
                ctr_file.move_file(self.generate_relative_path(),self.generate_ctr_file_name())
                session.commit()

    def delete_children(self,keep_file_reference=True):        
        if self.selection_file_id is not None:
            with database_handler.get_session() as session:
                selection_file = session.query(File).with_for_update().get(self.selection_file_id)
                selection_file.delete()
                if not keep_file_reference: self.selection_file = None  # Remove the reference to the recording file
                session.commit()
        self.delete_contour_file(keep_file_reference=keep_file_reference)

    def delete_contour_file(self, keep_file_reference=True):
        if self.contour_file_id is not None:
            with database_handler.get_session() as session:
                contour_file = session.query(File).with_for_update().get(self.contour_file_id)
                contour_file.delete()
                if not keep_file_reference: self.contour_file = None
                session.commit()
        if self.ctr_file_id is not None:
            with database_handler.get_session() as session:
                ctr_file = session.query(File).with_for_update().get(self.ctr_file_id)
                ctr_file.delete()
                if not keep_file_reference: self.ctr_file = None
                session.commit()
    
    def generate_plot_file_name(self):
        from . import filespace_handler
        if not self.recording: raise ValueError("Encounter not linked to recording. Call session.flush() before calling this method.")
        return filespace_handler.validate(f"Plot-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.get_start_time())}")

    def generate_selection_file_name(self):
        from . import filespace_handler
        if not self.recording: raise ValueError("Encounter not linked to recording. Call session.flush() before calling this method.")
        return filespace_handler.validate(f"Selection-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.get_start_time())}")

    def generate_contour_file_name(self):
        from . import filespace_handler
        if not self.recording: raise ValueError("Encounter not linked to recording. Call session.flush() before calling this method.")
        return filespace_handler.validate(f"Contour-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.get_start_time())}")
    
    def generate_ctr_file_name(self):
        from . import filespace_handler
        if not self.recording: raise ValueError("Encounter not linked to recording. Call session.flush() before calling this method.")
        return filespace_handler.validate(f"CTR-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.get_start_time())}")
    
    def generate_relative_path(self):
        return os.path.join(self.recording.generate_relative_path_for_selections())

    def generate_full_relative_path(self):
        return os.path.join(self.generate_relative_path(), self.generate_filename())
    
    def set_selection_number(self, value):
        if value is not None and not (isinstance(value, int) or str(value).isdigit()):
            raise ValueError("Selection must be an integer or a string that can be converted to an integer")
        self.selection_number = value
    
    def set_updated_by_id(self, user_id: str):
        """Set the user ID of the user who is updating the recording.

        Args:
            user_id (str): The user ID who is updating the recording.
        """
        self.updated_by_id = user_id




class User(database_handler.db.Model, UserMixin):
    id = database_handler.db.Column(database_handler.db.String(36), primary_key=True, default=uuid.uuid4)
    login_id = database_handler.db.Column(database_handler.db.String(100), unique=True)
    password = database_handler.db.Column(database_handler.db.String(100))
    name = database_handler.db.Column(database_handler.db.String(1000))
    role_id = database_handler.db.Column(database_handler.db.Integer, database_handler.db.ForeignKey('role.id'))
    is_active = database_handler.db.Column(database_handler.db.Boolean, default=True)
    is_temporary = database_handler.db.Column(database_handler.db.Boolean, default=False)
    expiry = database_handler.db.Column(database_handler.db.DateTime(timezone=True))
    
    role=database_handler.db.relationship('Role', backref='users', lazy=True)

    def set_login_id(self, value):
        self.login_id = value
    
    def set_role_id(self, value):
        self.role_id = value
    
    def set_expiry(self, value):
        self.expiry = value
    
    def set_name(self, value):
        
        self.name = value
    
    def get_login_id(self):
        return '' if self.login_id is None else self.login_id

    def activate(self):
        """
        Activate user (by setting is_active to true)
        """
        self.is_active = True
    
    def deactivate(self):
        """
        Deactivate user (by setting is_active to false)
        """
        self.is_active = False




class Assignment(database_handler.db.Model):
    __tablename__ = 'assignment'
    
    user_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recording_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('recording.id'), primary_key=True, nullable=False)
    row_start = database_handler.db.Column(database_handler.db.DateTime(timezone=True), server_default=func.current_timestamp())
    user = database_handler.db.relationship("User", foreign_keys=[user_id])
    recording = database_handler.db.relationship("Recording", foreign_keys=[recording_id])
    created_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    completed_flag = database_handler.db.Column(database_handler.db.Boolean, default=False)

    def set_user_id(self, user_id: str):
        self.user_id = user_id
    
    def set_recording_id(self, recording_id: str):
        self.recording_id = recording_id

    def set_user_id(self, user_id: str):
        self.user_id = user_id
    
    def set_recording_id(self, recording_id: str):
        self.recording_id = recording_id

    def is_complete(self):
        return "Yes" if self.completed_flag else "No"
    

