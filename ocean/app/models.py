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
import matplotlib.ticker as ticker

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
    encounters = database_handler.db.relationship("Encounter", primaryjoin="Encounter.species_id == Species.id", lazy="joined", back_populates="species")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        self.scientific_name = form['scientific_name']
        if 'genus_name' in form: self.genus_name = form['genus_name']
        if 'common_name' in form: self.common_name = form['common_name']

    def unique_name(self):
        return self.scientific_name
    
    def prepare_for_delete(self):
        if len(self.encounters) > 0:
            raise exception_handler.WarningException("Cannot delete species as it has dependencies.")

    @property
    def folder_name(self) -> str:
        return f"Species-{self.scientific_name}"

class RecordingPlatform(imodels.IRecordingPlatform):
    __tablename__ = 'recording_platform'
    
    def unique_name(self):
        return self.name

    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        self.name = form["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DataSource(imodels.IDataSource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def unique_name(self):
        return self.name
    
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

    recordings = database_handler.db.relationship("Recording", primaryjoin="Recording.encounter_id == IEncounter.id", lazy="joined", back_populates="encounter")


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _insert_or_update(self, form, new):
        form = utils.parse_form(form, self._form_dict())
        for key, value in form.items():
            setattr(self, key, value)

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


class File(imodels.IFile):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_abandoned_files(session):
        """TODO: Implement checking for this"""
        # raise NotImplementedError
        from sqlalchemy.orm import joinedload
        from sqlalchemy import not_, any_
        # assuming File is your SQLAlchemy model
        files = session.query(File)\
            .filter(~File.id.in_(
                session.query(Recording.recording_file_id)
                .union(session.query(Recording.selection_table_file_id))
                .union(session.query(Selection.selection_file_id))
                .union(session.query(Selection.contour_file_id))
                .union(session.query(Selection.ctr_file_id))
            ))\
            .all()  

    @property
    def filename_with_extension(self):
        if not self.extension: raise exception_handler.CriticalException("File has no extension")
        if not self.filename: raise exception_handler.CriticalException("File has no filename")
        return f"{self.filename}.{self.extension}"

    @property
    def path(self):
        return os.path.join(self.directory, self.filename_with_extension)
    
    @property
    def _path_with_root(self):
        """Return the full path of the file, including the filespace root directory"""
        if self.deleted: return os.path.join(database_handler.get_trash_path(), self.path)
        else: return os.path.join(database_handler.get_data_space(), self.path)

    @property
    def hash_hex(self):
        if self.hash: return self.hash.hex()

    def mark_for_deletion(self, permanent = False):
        self.to_be_deleted = True

    def __prepare_destination(self, directory: str = None, filename: str = None):
        """Prepare the destination path for moving the file. Will automatically update
        values of `self.directory` and `self.filename`. When using this function, you
        may assume that the value returned is the path of the file based on the arguments
        passed, and that the directory of this path exists (or has been created and is empty).
        
        This function will also validate the value of `self.extension`.
        """
        if not directory and not filename: raise exception_handler.CriticalException("No directory or filename provided.")
        self.directory = directory
        self.filename = utils.secure_fname(filename)
        # Validate extension
        self.extension = self.extension
        dst = self._path_with_root
        if not os.path.exists(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        i = 1
        basename = self.filename
        while os.path.exists(dst):
            self.filename = utils.secure_fname(f"{basename}-({i})")
            dst = self._path_with_root
            i += 1
        return dst

    def _move(self, directory: str = None, filename: str = None, delete: bool = False):
        """Move the file to the new directory and filename provided. Will automatically
        update values of `self.directory` and `self.filename`. The hash of the file will
        not change as the file is simply being moved. The argument `filename` MUST NOT
        contain an extension - if it does, there will be more than one extension.
        
        If `delete` is set to `True` the file will be moved from its current location to
        the trash folder (soft-delete). The `self.deleted` flag will be set to `True`.
        """
        src = self._path_with_root
        if delete:
            self.deleted = True
            filename = f"{self.filename}-{uuid.uuid4()}"
        dst = self.__prepare_destination(directory = directory, filename = filename)
        if src != dst:
            if os.path.exists(src):
                os.rename(src, dst)

    def insert(self, file, directory: str, filename: str, original_filename: str = None, extension: str = None):
        if isinstance(file, str):  # If `file` is a file path string
            if not os.path.exists(file): raise exception_handler.CriticalException("File with given path does not exist.")
            self.filename, self.extension = utils.parse_filename(os.path.basename(file))
            file_stream = open(file, 'rb')  # Open the file stream
        
        elif hasattr(file, 'stream'):
            file_stream = file.stream
            f, e = utils.parse_filename(file.filename)
            if not e and not extension: raise exception_handler.CriticalException("No extension provided.")
            elif not extension: self.extension = e
            elif not e: self.extension = extension
            if not f and not original_filename: self.original_filename = "Automatically generated"
            elif not f: self.original_filename = original_filename
            elif not original_filename: self.original_filename = f
        
        # If `file` is a stream, set the extension and original_filename from the method parameters
        elif hasattr(file, 'read'):
            file_stream = file
            if not extension: raise exception_handler.CriticalException("No extension provided.")
            else: self.extension = extension
            if not original_filename: self.original_filename = "Automatically generated"
            else: self.original_filename = original_filename
        else: raise exception_handler.CriticalException(f"File is not a file-like object (must contain `read()` or `stream`). Got {type(file)}.")

        if not directory: raise exception_handler.CriticalException("No directory provided.")
        if not filename: raise exception_handler.CriticalException("No filename provided.")
        self.directory = directory
        self.filename = filename

        dst = self.__prepare_destination(directory = self.directory, filename = self.filename)
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(dst, 'wb') as dest_file:
            while True:
                chunk = file_stream.read(chunk_size)
                if chunk:
                    dest_file.write(chunk)
                else:
                    break
        self.inserted = True
        self.hash = self.calculate_hash()

    def update(self, directory: str, filename: str):
        self._move(directory = directory, filename = filename)

    def _insert_or_update(self):
        raise NotImplementedError("Please use `insert()` or `update()` instead depending on your use case.")

    @classmethod
    def has_record(self, session, file_path, deleted = False, temp = False):
        comparison_path = file_path
        comparison_dir = os.path.dirname(comparison_path)
        comparison_file = os.path.splitext(os.path.basename(comparison_path))[0]
        comparison_ext = os.path.splitext(comparison_path)[1].replace('.', '')

        return session.query(self).filter(
            self.directory == comparison_dir,
            self.filename == comparison_file,
            self.extension == comparison_ext,
            self.deleted == deleted,
        ).first() is not None

    def calculate_hash(self):
        import hashlib
        if os.path.exists(self._path_with_root) == False:
            return None
        with open(self._path_with_root, 'rb') as file:
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
    
    def _delete_permanent(self):
        os.remove(self._path_with_root)

    def rollback(self, session = None):
        """
        If the current File object has not been committed to the database yet,
        remove the file from the file space. This enacts a hard delete as the
        assumption is that the file should not have been uploaded in the first
        place.

        Warning: this does not delete the File object from a future commit.

        :param session: the SQLAlchemy session
        """
        try:
            if self in session.new or (hasattr(self, 'just_inserted') and self.just_inserted == True):
                self._delete_permanent()
                session.delete(self)
        except Exception as e:
            pass

    def _delete(self) -> str:
        """Helper method for `delete()`."""
        if not self.deleted:
            self._move(self.directory, self.filename, delete=True)

    def delete(self, session):
        """Move the file represented by the object to the trash (soft-delete). This method will set
        the `deleted` to `True` to indicate its new location, if successful. To maintain atomicity
        the `session` provied will be comitted at the end of the successful operation. It is recommended
        that a fresh session is passed before this operation is called.
        
        You may assume that if
        """
        session.flush()
        self._delete()
        session.commit()

    def get_binary(self):
        """
        Reads and returns the binary content of the file represented by this object.

        :return: The binary content of the file.
        :raises FileNotFoundError: If the file does not exist.
        :raises IOError: If there is an issue reading the file.
        """
        absolute_path = self._path_with_root
        
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
    
    selections = database_handler.db.relationship("Selection", primaryjoin="Selection.recording_id == Recording.id", lazy="joined", back_populates="recording")
    assignments = database_handler.db.relationship("Assignment", primaryjoin="Assignment.recording_id == Recording.id", lazy="joined", back_populates="recording")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_filespace_children(self):
        return [self.recording_file, self.selection_table_file]
    
    def get_selections_count(self, traced = (None, True, False)):
        if traced is not None and None in traced and True in traced and False in traced: return len(self.selections)
        count = 0
        for selection in self.selections: count = count + 1 if selection.traced in traced else count
        return count

    def _insert_or_update(self, form, new):
        from .filespace_handler import get_complete_temporary_file
        attr_form = utils.parse_form(form, self._form_dict())
        for key, value in attr_form.items():
            setattr(self, key, value)

    def recording_file_delete(self):
        if self.recording_file: self.recording_file.mark_for_deletion()
        self.recording_file = None

    def selection_table_file_delete(self):
        if self.selection_table_file: self.selection_table_file.mark_for_deletion()
        self.selection_table_file = None
        self.selection_table_data_delete()

    def recording_file_insert(self, file):  
        if self.recording_file: raise exception_handler.CriticalException("Recording already has a recording file")
        
        self.recording_file = file

    def selection_table_file_insert(self, file):
        if self.selection_table_file: raise exception_handler.CriticalException("Recording already has a selection table file")
        self.selection_table_file = file
        new_selections = self.selection_table_apply()
        self.update_selection_traced_status()
        return new_selections

    @property
    def start_time_pretty(self):
        return utils.pretty_date(self.start_time)
            
    @property
    def folder_name(self):
        return utils.secure_fname(f"Recording-{utils.secure_datename(self.start_time)}")

    @property
    def recording_file_name(self):
        return utils.secure_fname(f"Rec-{self.encounter.species.scientific_name}-{self.encounter.location}-{self.encounter.encounter_name}-{utils.secure_datename(self.start_time)}")

    @property
    def selection_table_file_name(self):
        return utils.secure_fname(f"SelTable-{self.encounter.species.scientific_name}-{self.encounter.location}-{self.encounter.encounter_name}-{utils.secure_datename(self.start_time)}")

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

    @property
    def selections_count(self):
        return len(self.selections)

    @property
    def selection_file_count(self):
        return len([selection for selection in self.selections if selection.selection_file is not None])

    @property
    def contour_file_count(self):
        return len([selection for selection in self.selections if selection.contour_file is not None])
    
    def _update_filespace(self):
        if self.recording_file is not None:
            with database_handler.get_session() as recording_file_session:
                recording_file = recording_file_session.query(File).with_for_update().get(self.recording_file.id)
                recording_file.update(self.relative_directory, self.recording_file_name)
                recording_file_session.commit()
        if self.selection_table_file is not None:
            with database_handler.get_session() as selection_table_file_session:
                selection_table_file = selection_table_file_session.query(File).with_for_update().get(self.selection_table_file.id)
                selection_table_file.update(self.relative_directory, self.selection_table_file_name)
                selection_table_file_session.commit()

    def _selection_table_apply(self, dataframe):
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
        
        selection_ids_dict = {selection.selection_number: selection for selection in self.selections}

        for selection_number in selection_table_selection_numbers:
            if selection_number not in selection_ids_dict:
                new_selection = Selection(recording=self, selection_number=selection_number)
                new_selection.upload_selection_table_data(dataframe.loc[dataframe['Selection'] == selection_number, :])
                new_selections.append(new_selection)
            else:
                selection_ids_dict[selection_number].upload_selection_table_data(dataframe.loc[dataframe['Selection'] == selection_number, :])
        return new_selections

    def selection_table_apply(self):
        selection_table_df = utils.extract_to_dataframe(path=self.selection_table_file._path_with_root)
        return self._selection_table_apply(selection_table_df)
    
    def selection_table_data_delete(self):
        for selection in self.selections:
            selection.clear_selection_table_attrs()

    def generate_relative_path_for_selections(self):
        # TODO: REMOVE
        folder_name = self.start_time.strftime("Selections-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.relative_directory, folder_name)

    def update_selection_traced_status(self):
        for selection in self.selections:
            selection.update_traced()

    def selection_table_export(self, export_format):
        headers = ['Selection', 'View', 'Channel', 'Begin Time (s)', 'End Time (s)', 'Low Freq (Hz)', 'High Freq (Hz)', 'Delta Time (s)', 'Delta Freq (Hz)', 'Avg Power Density (dB FS/Hz)', 'Annotation']

        selections = self.selections
        encounter = self.encounter

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

    def _get_filespace_children(self):
        return [self.selection_file, self.contour_file, self.ctr_file]
    
    @property
    def unique_name(self):
        if self.recording == None: raise exception_handler.CriticalException("Selection is not linked to a recording.")
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

    def selection_file_insert(self, file):
        if self.selection_file: raise exception_handler.WarningException(f"Selection file for selection {self.selection_number} already exists.")
        self.selection_file = file
        self._calculate_sampling_rate()
    
    def contour_file_insert(self, contour_file, ctr_file):
        if self.contour_file or self.contour_file_id: raise exception_handler.WarningException(f"Contour file for selection {self.selection_number} already exists.")
        self.contour_file = contour_file
        self.ctr_file_generate(ctr_file = ctr_file)
        self.contour_statistics_calculate()
        self.update_traced()

    def contour_file_delete(self):
        self.ctr_file_delete()
        if self.contour_file: self.contour_file.mark_for_deletion()
        self.contour_file = None
        self.update_traced()
        self.clear_contour_statistics_attrs()

    def selection_file_delete(self):
        if self.selection_file: self.selection_file.mark_for_deletion()
        self.ctr_file = None

    def ctr_file_delete(self):
        if self.ctr_file: self.ctr_file.mark_for_deletion()
        self.ctr_file = None

    def ctr_file_generate(self, ctr_file: File):
        contour_file_handler = self.get_contour_file_handler()
        if contour_file_handler:
            mat_data = contour_file_handler.get_ctr_data()
            if mat_data:
                with io.BytesIO() as f:
                    scipy.io.savemat(f, mat_data)
                    f.seek(0)
                    ctr_file.insert(file = f, directory = self.relative_directory, filename = self.ctr_file_name, extension="ctr")
                self.ctr_file = ctr_file
        else:
            raise exception_handler.WarningException(f"Contour file for selection {self.selection_number} does not exist.")

    def clear_contour_statistics_attrs(self):
        for attr in imodels.ISelection.get_contour_statistics_attrs():
            setattr(self, attr, None)

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
                contour_statistics_obj = contour_statistics.ContourFile(self.contour_file._path_with_root, self.selection_number)
                contour_statistics_obj.calculate_statistics(self)
            except ValueError as e:
                raise exception_handler.WarningException(f"Error processing contour {self.selection_number}: " + str(e))
            except FileNotFoundError as e:
                raise exception_handler.WarningException(f"Error processing contour {self.selection_number} (file no longer exists)")

    def _calculate_sampling_rate(self):
        if self.selection_file:
            with wave.open(self.selection_file._path_with_root, "rb") as wave_file:
                self.sampling_rate = wave_file.getframerate()
        else: raise exception_handler.WarningException("Unable to calculate sampling rate as the selection file does not exist.")

    def deactivate(self):
        self.deactivated = True
        self.update_traced()

    def reactivate(self):
        self.deactivated = False
        self.update_traced()

    def clear_selection_table_attrs(self):
        for attr in self.selection_table_attrs:
            setattr(self, attr, None)

    def update_traced(self):
        if self.deactivated: self.traced = None
        if self.contour_file: self.traced = True
        elif not self.contour_file and (self.annotation == "N"): self.traced = False
        else: self.traced = None
            
    def create_temp_plot(self):
        # Sampling rate defaults to 44100 (otherwise use that from the selection file)
        sampling_rate = int(self.sampling_rate) if self.sampling_rate else 44100
        
        # Adjustable: 20–50 ms (time between frequency bins)
        bin_width = 25  
        window_size = 2 ** int(round(np.log2((bin_width / 1000) * sampling_rate)))
        hop_size = window_size // 4  # 75% overlap

        # Set x-axis labels in milliseconds
        def format_ms(x, pos):
            """Convert x axis labels from seconds to milliseconds"""
            return f"{x*1000:.0f}"

        with open(self.selection_file._path_with_root, 'rb') as selection_file:
            audio, sr = librosa.load(selection_file, sr=sampling_rate)
            audio_length = len(audio)/sampling_rate
        
        spectrogram = librosa.stft(audio, n_fft=window_size, hop_length=hop_size)

        # If there is no contour file, create just one subplot (spectrogram only)
        # If there is a contour file, create two subplots (spectrogram and contour)
        if self.contour_file: fig, axs = plt.subplots(1, 2, figsize=(30, 10))
        else: fig, axs = plt.subplots(1, 1, figsize=(30, 5))
        spectogram_axs = axs[0] if self.contour_file else axs
        contour_axs = axs[1] if self.contour_file else None

        # Plot the spectrogram
        librosa.display.specshow(librosa.amplitude_to_db(np.abs(spectrogram), ref=np.max), ax=spectogram_axs, sr=sampling_rate, hop_length=hop_size, cmap='inferno', x_axis='time', y_axis='hz')
        spectogram_axs.set_xlabel(f'Time (ms)', fontsize=20)
        spectogram_axs.set_ylabel('Frequency (Hz)', fontsize=20)
        spectogram_axs.tick_params(axis='both', labelsize=14)
        spectrogram_y_min = spectogram_axs.get_ylim()[0]
        sprectrogram_y_max = spectogram_axs.get_ylim()[1] if spectogram_axs.get_ylim()[1] < 20000 else 20000
        spectogram_axs.set_xlim(0)
        spectogram_axs.set_ylim(spectrogram_y_min, sprectrogram_y_max)
        spectogram_axs.xaxis.set_major_formatter(ticker.FuncFormatter(format_ms))
        spectrogram_x_min, spectrogram_x_max = [x * 1000 for x in spectogram_axs.get_xlim()]

        # Plot the contour if it exists
        if self.contour_file_id and contour_axs:
            contour_file_handler = self.get_contour_file_handler()
            contour_rows = contour_file_handler.contour_rows
            contour_domain = [(unit.time_milliseconds - contour_rows[0].time_milliseconds) for unit in contour_rows]
            contour_range = [unit.peak_frequency for unit in contour_rows]
            contour_axs.plot(contour_domain, contour_range)
            contour_axs.set_xlabel('Time (ms)', fontsize=20)
            contour_axs.set_ylabel('Frequency (Hz)', fontsize=20)
            contour_axs.tick_params(axis='both', labelsize=14)
            contour_axs.set_ylim(spectrogram_y_min, sprectrogram_y_max)
            contour_axs.set_xlim(spectrogram_x_min, spectrogram_x_max)
        
        fig.suptitle(f'{self.unique_name} spectrogram (Sampling Rate: {sampling_rate} Hz, Duration {audio_length:.2f} s, Window Size: {window_size}, Hop Size: {hop_size})', fontsize=26)
        
        # Layout so plots do not overlap
        fig.tight_layout()

        # Create a BytesIO object to store the plot
        buf = io.BytesIO()

        # Save the plot to the BytesIO object
        plt.savefig(buf, format='png', bbox_inches='tight')

        # Seek back to the beginning of the buffer
        buf.seek(0)

        # Return the bytestream of the plot
        return buf.getvalue()


    def __contour_file_load_dataframe(self) -> pd.DataFrame:
        """Read the `contour_file` into a pandas dataframe, validating columns and their types."""
        if self.contour_file:
            try:
                self.contour_file.get_binary()
                if self.contour_file.extension.lower() == "csv":
                    df = pd.read_csv(self.contour_file._path_with_root)
                elif self.contour_file.extension.lower() == "xlsx":
                    df = pd.read_excel(self.contour_file._path_with_root)
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
        if not df.empty:
            # Populate contour file handler with values from the dataframe
            handler = contour_statistics.ContourFileHandler()
            handler.insert_dataframe(df)
            return handler
        else:
            raise exception_handler.WarningException(f"Contour file {self.selection_number} unable to be parsed.")

    def generate_contour_stats_dict(self):
        if not self.contour_statistics_calculated: return None
        headers = ['Encounter', 'Location', 'Project', 'Recording', 'Species', 'SamplingRate', 'SELECTIONNUMBER']
        values = [self.recording.encounter.encounter_name, self.recording.encounter.location, self.recording.encounter.project, self.recording.start_time_pretty, self.recording.encounter.species.scientific_name, self.sampling_rate, self.selection_number]
        contour_statistics_attrs = imodels.ISelection.get_contour_statistics_attrs()
        for attr in contour_statistics_attrs:
            if contour_statistics_attrs[attr][2]:
                headers.append(attr)[1]
                values.append(getattr(self, attr))
        return dict(zip(headers, values))

    def contour_statistics_calculate(self):
        if self.contour_file:
            self._calculate_sampling_rate()
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
                selection_file.update(self.relative_directory,self.selection_file_name)
                session.commit()
        if self.contour_file is not None:
            with database_handler.get_session() as session:
                contour_file = session.query(File).with_for_update().get(self.contour_file_id)
                contour_file.update(self.relative_directory,self.contour_file_name)
                session.commit()
        if self.ctr_file is not None:
            with database_handler.get_session() as session:
                ctr_file = session.query(File).with_for_update().get(self.ctr_file_id)
                ctr_file.update(self.relative_directory,self.ctr_file_name)
                session.commit()

    @property
    def plot_file_name(self):
        from . import filespace_handler
        return f"Plot-{self.selection_number}-{filespace_handler.format_date_for_filespace(self.recording.start_time)}"

class User(imodels.IUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def activate(self):
        self.is_active = True
    
    def deactivate(self):
        self.is_active = False

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

    def complete(self):
        self.completed_flag = True

    def incomplete(self):
        self.completed_flag = False

    @property
    def unique_name(self):
        return f"{self.recording.unique_name}_{self.user.unique_name}"