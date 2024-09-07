# Standard library imports
import os, uuid
from datetime import datetime, timedelta
import scipy.io
import numpy as np
import pandas as pd

# Third-party imports
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy import event

# Local application imports
import database_handler, exception_handler, utils
from database_handler import db, get_file_space_path, get_trash_path
from logger import logger



### UNUSED ###
SYSTEM_GMT_OFFSET = 0
def convert_to_gmt_time(system_time: datetime) -> datetime:
    """
    Converts a system time to GMT time by adding the system GMT offset.
    
    Parameters:
        system_time (datetime): The system time to be converted.
    
    Returns:
        datetime: The GMT time equivalent to the provided system time.
    """
    gmt_offset = timedelta(hours=SYSTEM_GMT_OFFSET)
    gmt_time = system_time + gmt_offset
    return gmt_time

def convert_from_gmt(gmt_time: datetime) -> datetime:
    """
    Converts a GMT time to a system time by subtracting the system GMT offset.
    
    Parameters:
        gmt_time (datetime): The GMT time to be converted.
    
    Returns:
        datetime: The system time equivalent to the provided GMT time.
    """
    gmt_offset = timedelta(hours=SYSTEM_GMT_OFFSET)
    system_time = gmt_time - gmt_offset
    return system_time

def parse_string_notempty(string:str, field:str) -> str:
    """
    Remove whitespace from a string, or raise exception_handler.WarningException()
    if the string is none or blank (stripped). This method should only be used on
    data fields which are mandatory, and thus must not be left blank.

    :param string: the string being parsed
    :type string: str

    :param field: the name of the field of the string being parsed (is used in the
    event of a raised exception)
    :type field: str

    :return: the parsed string stripped of its whitespace
    """
    if type(string) != str:
        raise exception_handler.WarningException(f'{field} must be a string.')
    if string == None or string.strip() == "":
        raise exception_handler.WarningException(f'{field} cannot be blank.')
    else:
        return string.strip()


class DataSource(db.Model):
    __tablename__ = 'data_source'

    id = db.Column(db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = db.Column(db.String(255))
    phone_number1 = db.Column(db.String(20), unique=True)
    phone_number2 = db.Column(db.String(20), unique=True)
    email1 = db.Column(db.String(255), nullable=False, unique=True)
    email2 = db.Column(db.String(255), unique=True)
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    type = db.Column(db.Enum('person', 'organisation'))

    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<DataSource %r>' % self.name
    


class Encounter(db.Model):
    __tablename__ = 'encounter'
    id = db.Column(db.String(36), primary_key=True, default=uuid.uuid4)
    encounter_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    species_id = db.Column(db.String(36), db.ForeignKey('species.id'), nullable=False)
    project = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Double)
    longitude = db.Column(db.Double)
    data_source_id = db.Column(db.String(36), db.ForeignKey('data_source.id'), nullable=False)
    recording_platform_id = db.Column(db.String(36), db.ForeignKey('recording_platform.id'), nullable=False)
    notes = db.Column(db.String(1000))
    file_timezone = db.Column(db.Integer)
    local_timezone = db.Column(db.Integer)
    
    species = db.relationship("Species")
    data_source = db.relationship("DataSource")
    recording_platform = db.relationship("RecordingPlatform")

    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    __table_args__ = (
        db.UniqueConstraint('encounter_name', 'location', 'project'),
    )
    
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
        num_recordings = db.session.query(Recording).filter_by(encounter_id=self.id).count()
        return num_recordings

    def generate_relative_path(self):
        """
        Generate a relative path for files stored in the file space based on the species, location, and encounter name.
        This relative path can be used by Recording and Selection to generate their own sub-directories within this path.
        """
        species_name = self.species.species_name  # Assuming the relationship is named 'species' and the species name field is 'name'
        return f"Species-{species_name.replace(' ', '_')}/Location-{self.location.replace(' ', '_')}/Encounter-{self.encounter_name.replace(' ', '_')}"
    
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

    def get_latitude(self):
        return '' if self.latitude is None else self.latitude

    def set_latitude(self, value):
        self.latitude = utils.validate_latitude(value)
    
    def set_longitude(self, value):
        self.longitude = utils.validate_longitude(value)

    def get_longitude(self, value):
        return '' if self.longitude is None else self.longitude
    
    def get_encounter_name(self):
        return '' if self.encounter_name is None else self.encounter_name

    def set_encounter_name(self, value):
        self.encounter_name = parse_string_notempty(value, 'Encounter name')

    def get_location(self):
        return '' if self.location is None else self.location

    def set_location(self, value):
        self.location = parse_string_notempty(value, 'Location')

    def get_project(self):
        return '' if self.project is None else self.project

    def set_project(self, value):
        self.project = parse_string_notempty(value, 'Project')

    def get_notes(self):
        return '' if self.notes is None else self.notes

    def set_notes(self, value):
        self.notes = value.strip()

    def set_species_id(self, species_id: str):
        self.species_id = utils.validate_id(species_id)
    
    def set_data_source_id(self, session, data_source_id):
        data_source_id = utils.validate_id(data_source_id)
        self.data_source_id = data_source_id

    def set_recording_platform_id(self, session, recording_platform_id):
        recording_platform_id = utils.validate_id(recording_platform_id)
        self.recording_platform_id = recording_platform_id

    def set_file_timezone(self, value):
        self.file_timezone = utils.validate_timezone(value)
    
    def get_file_timezone(self):
        return self.file_timezone
    
    def set_local_timezone(self, value):
        self.local_timezone = utils.validate_timezone(value)
    
    def get_local_timezone(self):
        return self.local_timezone



class File(db.Model):
    __tablename__ = 'file'

    id = db.Column(db.String(36), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    path = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_date = db.Column(db.DateTime(timezone=True))
    extension = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer)
    original_filename = db.Column(db.String(255))

    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

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
        return self.uploaded_date

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
    
    def get_full_absolute_path(self):
        """
        :return: the full absolute path of the filespace joined with the directory, 
        filename and extension of the file represented by the object
        """
        return os.path.join(get_file_space_path(), self.get_full_relative_path())
    
    # def get_absolute_directory(self):
    #     return os.path.join(get_file_space_path(), self.path)

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
        loose_file_path = os.path.join(get_file_space_path(),loose_file_directory, loose_file_name + '.' + loose_file_extension)
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

    # TODO: find the datatype of file
    # TODO: remove root_path requirement as it is automatically generated in the method
    def insert_path_and_filename(self, session, file, new_directory:str, new_filename:str, root_path=None):
        """
        Insert a file into the filespace. Automatically save the file on the server and
        store (and commit) its directory, filename and extension in the database. If 
        successful write an informational message to the logger.

        :param session: the SQLAlchemy session
        :param file: TBD
        :param new_directory: the relative directory in which to store the file
        :param new_filename: the full filename (including extension) to rename the file to
        """

        root_path = get_file_space_path()
        
        self.path = new_directory
        self.filename = new_filename  # filename without extension
        self.original_filename = file.filename
        self.extension = file.filename.split('.')[-1]
        
        destination_path = os.path.join(root_path, self.get_full_relative_path())
        self.rename_loose_file(self.path, self.filename, self.extension)
        os.makedirs(os.path.join(root_path, self.path), exist_ok=True)
        file.save(destination_path)
        logger.info(f"Saved file to {destination_path}")

    
    # def update_path_and_filename(self, new_path, new_filename,root_path):

    #     self.path = new_path
    #     self.filename = new_filename

    # def get_uploaded_date(self):
    #     return self.uploaded_date


    # def set_uploaded_date(self, value):
    #     if value is not None and not isinstance(value, datetime):
    #         raise ValueError("Uploaded date must be a valid datetime")
    #     self.uploaded_date = value
    
    # def set_uploaded_by(self, value):
    #     self.uploaded_by = value

    def move_to_trash(self):
        """
        Moves the file to the trash folder.

        This function moves the file to the trash folder by renaming the file and adding a unique identifier to its name.
        TODO: keep a record of deleted file metadata
        """
        unique_name = str(uuid.uuid4())
        file_name = self.filename
        trash_file_path = os.path.join(self.get_directory(),file_name + '_' +  unique_name + '.' + self.extension)
        self.move_file(trash_file_path, move_to_trash=True)

    def delete_file(self, session):
        os.path.remove(self.get_full_absolute_path())

    def move_file(self, new_relative_file_path, move_to_trash=False):
        """
        Move a file to a new location with the provided session.

        Parameters:
        - session: The session object to use for the database transaction
        - new_relative_file_path: The new relative file path to move the file to
        - return: False if the file already exists at the new location, None otherwise
        """
        if move_to_trash: root_path = database_handler.get_trash_path()
        else: root_path = database_handler.get_file_space_path()

        new_relative_file_path_with_root = os.path.join(root_path, new_relative_file_path) # add the root path to the relative path
        current_relative_file_path = os.path.join(database_handler.get_file_space_path(), self.get_full_relative_path())
        
        # make the directory of the new_relative_file_path_with_root
        if not os.path.exists(os.path.dirname(new_relative_file_path_with_root)):
            os.makedirs(os.path.dirname(new_relative_file_path_with_root))
            logger.info(f"Created directory: {os.path.dirname(new_relative_file_path_with_root)}")

        # if the new and current file paths are not the same
        if new_relative_file_path_with_root != current_relative_file_path:
            self.path = os.path.dirname(new_relative_file_path)
            self.filename = os.path.basename(new_relative_file_path).split(".")[0]
            self.extension = os.path.basename(new_relative_file_path).split(".")[-1]
            self.rename_loose_file(self.path, self.filename, self.extension)
            if os.path.exists(current_relative_file_path):
                os.rename(current_relative_file_path, new_relative_file_path_with_root)
                logger.info(f"Moved file from {current_relative_file_path} to {new_relative_file_path_with_root}")
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




class Recording(db.Model):
    __tablename__ = 'recording'

    id = db.Column(db.String(36), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    duration = db.Column(db.Integer)
    recording_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    selection_table_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    encounter_id = db.Column(db.String(36), db.ForeignKey('encounter.id'), nullable=False)
    ignore_selection_table_warnings = db.Column(db.Boolean, default=False)
    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    created_datetime = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    recording_file = db.relationship("File", foreign_keys=[recording_file_id])
    selection_table_file = db.relationship("File", foreign_keys=[selection_table_file_id])
    encounter = db.relationship("Encounter", foreign_keys=[encounter_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    status = db.Column(db.Enum('Unassigned','In Progress','Awaiting Review','Reviewed','On Hold'), nullable=False, default='Unassigned')
    status_change_datetime = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)
    row_start = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    #row_end = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    #valid_to = Column(DateTime, server_default=func.inf())
    __table_args__ = (
        db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )

    def get_unique_name(self, delimiter="-"):
        return f"{self.encounter.get_unique_name(delimiter)}: recording {self.start_time}"

    def is_complete(self):
        return True if self.status == 'Reviewed' else False

    def is_on_hold(self):
        return True if self.status == 'On Hold' else False

    def set_user_id(self, user_id):
        self.updated_by_id = user_id

    def update_status_change_datetime(self):
        self.status_change_datetime = datetime.now()

    def set_status(self, status):
        if self.status != status:
            self.update_status_change_datetime()
        self.status = status


    def update_status_upon_assignment_flag_change(self, session):
        assignments = session.query(Assignment).filter_by(recording_id=self.id).all()
        old_status = self.status
        if self.status != 'On Hold' and self.status != 'Reviewed':

            # this will be run when a user selects complete
            self.status = 'Awaiting Review'
            for assignment in assignments:
                if assignment.completed_flag is False:
                    self.status = 'In Progress'
        
        if old_status != self.status:
            self.update_status_change_datetime()
    def update_status_upon_assignment_add_remove(self, session):

        assignments = session.query(Assignment).filter_by(recording_id=self.id).all()
        old_status = self.status
        if self.status != 'On Hold' and self.status != 'Reviewed' and self.status != 'Awaiting Review':
            if len(assignments) == 0:
                self.status = 'Unassigned'
            else:
                self.status = 'In Progress'
        if old_status != self.status:
            self.update_status_change_datetime()
        
    def get_number_of_selections(self):
        selections = database_handler.create_system_time_request(db.session, Selection, {"recording_id":self.id}, order_by="selection_number")
        return len(selections)

    def get_number_of_contours(self):
        #selections = database_handler.create_system_time_request(db.session, Selection, {"recording_id":self.id}, order_by="selection_number")

        contours = db.session.query(Selection).filter_by(recording_id=self.id).filter(Selection.contour_file != None).all()
        return len(contours)

    def update_call(self):
        if self.recording_file is not None:
            with database_handler.get_session() as session:
                recording_file = session.query(File).with_for_update().get(self.recording_file_id)
                recording_file.move_file(self.generate_full_relative_path(extension="." + self.recording_file.extension))
                session.commit()
        if self.selection_table_file is not None:
            with database_handler.get_session() as session:
                selection_table_file = session.query(File).with_for_update().get(self.selection_table_file_id)
                selection_table_file.move_file(self.generate_full_relative_path(extension="." +self.selection_table_file.extension))
                session.commit()
        
        with database_handler.get_session() as session:
            selections = session.query(Selection).with_for_update().filter_by(recording_id=self.id).all()
            for selection in selections:
                selection.update_call()
            session.commit()
        
    def load_selection_table_data(self,custom_file=None):
        
        if self.selection_table_file is not None or custom_file is not None:
            if custom_file:
                file_path=custom_file
            else:
                file_path = self.selection_table_file.get_full_absolute_path()
            if file_path is None or file_path == "":
                return pd.DataFrame()
            # Read the file into a pandas DataFrame
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == '.csv':
                # Read the CSV file into a pandas DataFrame
                df = pd.read_csv(file_path)
            elif file_extension == '.txt':
                # Read the text file into a pandas DataFrame
                df = pd.read_csv(file_path, sep='\t')
            elif file_extension == '.xlsx' or file_extension == '.xls':
                # Read the Excel file into a pandas DataFrame
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format. Please provide a .csv, .txt or .xlsx file.")


            return df

        return pd.DataFrame()

    def validate_selection_table(self, session, custom_file=None):
        try:
            st_df = self.load_selection_table_data(custom_file=custom_file)
            if st_df.empty:
                raise exception_handler.WarningException("The Selection Table provided is empty")
            self.upload_selection_table_rows(session, st_df)
        except Exception as e:
            raise exception_handler.WarningException("The Selection Table provided is invalid: " + str(e))

    def upload_selection_table_rows(self, session, st_df):

        if 'Selection' not in st_df.columns:
            raise ValueError("The Selection Table must contain a 'Selection' column")
        if 'Annotation' not in st_df.columns:
            raise ValueError("The Selection Table must contain an 'Annotation' column")
        selection_table_selection_numbers = st_df.Selection.to_list()

        for selection_number in selection_table_selection_numbers:
            selection = session.query(Selection).filter_by(recording_id=self.id, selection_number=selection_number).first()
            if selection is None:
                new_selection = Selection(recording_id=self.id, selection_number=selection_number)
                session.add(new_selection)
                new_selection.upload_selection_table_data(session, st_df.loc[st_df['Selection'] == selection_number, :])
            else:
                selection.upload_selection_table_data(session, st_df.loc[st_df['Selection'] == selection_number, :])
        session.commit()
    

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
                assignment.delete()
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


    def generate_relative_path_for_selections(self):
        folder_name = self.start_time.strftime("Selections-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.generate_relative_path(), folder_name)

    def generate_relative_path(self):
        folder_name = self.start_time.strftime("Recording-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.encounter.generate_relative_path(), folder_name)

    def generate_recording_filename(self,extension=""):
        return f"Rec-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{self.start_time.strftime('%Y%m%d%H%M%S')}{extension}"
    
    def generate_full_relative_path(self,extension=""):
        return os.path.join(self.generate_relative_path(), self.generate_recording_filename(extension=extension))

    def generate_selection_table_filename(self):
        return f"Sel-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{self.start_time.strftime('%Y%m%d%H%M%S')}"
    def get_start_time(self):
        return self.start_time
    
    def get_seconds(self):
        return self.start_time.second


    def set_start_time(self, datetime_object):
        try:
            datetime_object = datetime.strptime(datetime_object, '%Y-%m-%dT%H:%M:%S')  # Modify the format to include milliseconds
        except ValueError:
            try:
                datetime_object = datetime.strptime(datetime_object, '%Y-%m-%dT%H:%M')  # Try without milliseconds
            except ValueError:
                raise exception_handler.WarningException("Invalid datetime format. Start time must be of the format yyyy-mm-dd dd:mm:ss.")

        self.start_time = datetime_object
    
    def match_start_time(self, match_datetime):
        return self.start_time == match_datetime

    def get_start_time_string(self):
        return self.start_time.strftime('%Y-%m-%dT%H:%M:%S')

    def get_start_time(self):
        return self.start_time
    
    def set_encounter_id(self, session, encounter_id):
        encounter = session.query(Encounter).filter(Encounter.id == encounter_id).first()
        if encounter:
            self.encounter = encounter
        else:
            raise exception_handler.CriticalException('Unable to make link to encounter.')

    def get_duration(self):
        return self.duration



    def set_duration(self,value):
        if value is not None and not isinstance(value, int):
            raise ValueError("Duration must be an integer")
        self.duration = value
    
    def update_selection_traced_status(self,session):
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
        for selection in selections:
            selection.update_traced_status()
    
    def reset_selection_table_values(self,session):
        selections = database_handler.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
        for selection in selections:
            selection.reset_selection_table_values(session)



class RecordingPlatform(db.Model):
    __tablename__ = 'recording_platform'

    id = db.Column(db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = db.Column(db.String(100), unique=True, nullable=False)
    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<RecordingPlatform %r>' % self.name
    
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

"""

class RecordingAudit(Audit, Recording, db.Model):
    __tablename__ = 'recording_audit'

    record_id = db.Column(db.String(36), db.ForeignKey('recording.id'), nullable=False)
    record = db.relationship("Recording", foreign_keys=[record_id])
"""
class Selection(db.Model):
    __tablename__ = 'selection'

    id = db.Column(db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    selection_number = db.Column(db.Integer, nullable=False)
    selection_file_id = db.Column(db.String(36), db.ForeignKey('file.id'), nullable=False)
    recording_id = db.Column(db.String(36), db.ForeignKey('recording.id'), nullable=False)
    contour_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    ctr_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    spectogram_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    plot_file_id = db.Column(db.String(36), db.ForeignKey('file.id'))
    sampling_rate = db.Column(db.Float, nullable=False)
    traced = db.Column(db.Boolean, nullable=True, default=None)
    deactivated = db.Column(db.Boolean, nullable=True, default=False)
    row_start = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    default_fft_size = db.Column(db.Integer)
    default_hop_size = db.Column(db.Integer)

    ### Selection Table data ###
    view = db.Column(db.Text)
    channel = db.Column(db.Integer)
    begin_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    low_frequency = db.Column(db.Float)
    high_frequency = db.Column(db.Float)
    delta_time = db.Column(db.Float)
    delta_frequency = db.Column(db.Float)
    average_power = db.Column(db.Float)
    annotation = db.Column(db.Text, nullable=False)

    ### Contour Statistics data ###
    freq_max = db.Column(db.Float, nullable=True, default=None)
    freq_min = db.Column(db.Float, nullable=True, default=None)
    duration = db.Column(db.Float, nullable=True, default=None)
    freq_begin = db.Column(db.Float, nullable=True, default=None)
    freq_end = db.Column(db.Float, nullable=True, default=None)
    freq_range = db.Column(db.Float, nullable=True, default=None)
    dc_mean = db.Column(db.Float, nullable=True, default=None)
    dc_standarddeviation = db.Column(db.Float, nullable=True, default=None)
    freq_mean = db.Column(db.Float, nullable=True, default=None)
    freq_standarddeviation = db.Column(db.Float, nullable=True, default=None)
    freq_median = db.Column(db.Float, nullable=True, default=None)
    freq_center = db.Column(db.Float, nullable=True, default=None)
    freq_relbw = db.Column(db.Float, nullable=True, default=None)
    freq_maxminratio = db.Column(db.Float, nullable=True, default=None)
    freq_begendratio = db.Column(db.Float, nullable=True, default=None)
    freq_quarter1 = db.Column(db.Float, nullable=True, default=None)
    freq_quarter2 = db.Column(db.Float, nullable=True, default=None)
    freq_quarter3 = db.Column(db.Float, nullable=True, default=None)
    freq_spread = db.Column(db.Float, nullable=True, default=None)
    dc_quarter1mean = db.Column(db.Float, nullable=True, default=None)
    dc_quarter2mean = db.Column(db.Float, nullable=True, default=None)
    dc_quarter3mean = db.Column(db.Float, nullable=True, default=None)
    dc_quarter4mean = db.Column(db.Float, nullable=True, default=None)
    freq_cofm = db.Column(db.Float, nullable=True, default=None)
    freq_stepup = db.Column(db.Integer, nullable=True, default=None)
    freq_stepdown = db.Column(db.Integer, nullable=True, default=None)
    freq_numsteps = db.Column(db.Integer, nullable=True, default=None)
    freq_slopemean = db.Column(db.Float, nullable=True, default=None)
    freq_absslopemean = db.Column(db.Float, nullable=True, default=None)
    freq_posslopemean = db.Column(db.Float, nullable=True, default=None)
    freq_negslopemean = db.Column(db.Float, nullable=True, default=None)
    freq_sloperatio = db.Column(db.Float, nullable=True, default=None)
    freq_begsweep = db.Column(db.Integer, nullable=True, default=None)
    freq_begup = db.Column(db.Integer, nullable=True, default=None)
    freq_begdown = db.Column(db.Integer, nullable=True, default=None)
    freq_endsweep = db.Column(db.Integer, nullable=True, default=None)
    freq_endup = db.Column(db.Integer, nullable=True, default=None)
    freq_enddown = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsupdown = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsdownup = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsupflat = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsdownflat = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsflatup = db.Column(db.Integer, nullable=True, default=None)
    num_sweepsflatdown = db.Column(db.Integer, nullable=True, default=None)
    freq_sweepuppercent = db.Column(db.Float, nullable=True, default=None)
    freq_sweepdownpercent = db.Column(db.Float, nullable=True, default=None)
    freq_sweepflatpercent = db.Column(db.Float, nullable=True, default=None)
    num_inflections = db.Column(db.Integer, nullable=True, default=None)
    inflection_maxdelta = db.Column(db.Float, nullable=True, default=None)
    inflection_mindelta = db.Column(db.Float, nullable=True, default=None)
    inflection_maxmindelta = db.Column(db.Float, nullable=True, default=None)
    inflection_mediandelta = db.Column(db.Float, nullable=True, default=None)
    inflection_meandelta = db.Column(db.Float, nullable=True, default=None)
    inflection_standarddeviationdelta = db.Column(db.Float, nullable=True, default=None)
    inflection_duration = db.Column(db.Float, nullable=True, default=None)
    step_duration = db.Column(db.Float, nullable=True, default=None)
    
    contour_file = db.relationship("File", foreign_keys=[contour_file_id])
    selection_file = db.relationship("File", foreign_keys=[selection_file_id])
    recording = db.relationship("Recording", foreign_keys=[recording_id])
    ctr_file = db.relationship("File", foreign_keys=[ctr_file_id])
    spectogram_file = db.relationship("File", foreign_keys=[spectogram_file_id])
    plot_file = db.relationship("File", foreign_keys=[plot_file_id])
    
    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])


    __table_args__ = (
        db.UniqueConstraint('selection_number', 'recording_id', name='unique_selection_number_recording'),
        {"mysql_engine": "InnoDB", "mysql_charset": "latin1", "mysql_collate": "latin1_swedish_ci"}
    )

    def get_unique_name(self, delimiter="-"):
        return f"{self.recording.get_unique_name(delimiter)}: selection {self.selection_number}"

    def calculate_sampling_rate(self):
        if self.selection_file:
            import wave
            with wave.open(self.selection_file.get_full_absolute_path(), "rb") as wave_file:
                self.sampling_rate = wave_file.getframerate()

    def deactivate(self):
        self.traced = None
        self.deactivated = True

    def reactivate(self):
        self.traced = self.update_traced_status()
        self.deactivated = False

    def reset_selection_table_values(self, session):
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
        elif self.contour_file:
            self.traced = True
        else:
            self.traced = None

    def getWarnings(self):
        warnings = []
        if self.contour_file and self.annotation=="N":
            warnings.append("Contour file exists but annotated 'N'.")
        elif not self.contour_file and self.annotation=="Y" or self.annotation=="M":
            warnings.append(f"Selection annotated '{self.annotation}' but no contour file.")
        if not self.recording.selection_table_file:
            warnings.append("No Selection Table file.")
        ## ADD CHECK THAT SELECTION TABLE HAS BEEN UPLOADED
        return warnings

    def generate_ctr_file_name(self):
        return f"contour-{self.selection_number}-{self.recording.start_time.strftime('%Y%m%d%H%M%S')}"

    def set_selection_file(self, selection_file: File):
        if selection_file.extension != 'wav':
            raise exception_handler.WarningException(f"Selection {self.selection_number} needs to be of type 'wav' but is '{selection_file.extension}'")
        self.calculate_sampling_rate()
        self.selection_file = selection_file

    def create_temp_plot(self, session, temp_dir, fft_size=None, hop_size=None, update_permissions=False):
        import librosa
        import matplotlib.pyplot as plt
        import numpy as np
        import os
        from contour_statistics import ContourFile
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

        print("Contour file 2", self.contour_file, self.contour_file_id)

        # Plot the contour if it exists
        if self.contour_file_id:
            contour_file_obj = ContourFile(self.contour_file.get_full_absolute_path())
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
        plot_path = os.path.join(temp_dir, self.generate_plot_filename() + ".png")
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
        scipy.io.savemat(os.path.join(get_file_space_path(), os.path.join(self.generate_relative_path(), self.generate_ctr_file_name())) + ".ctr", mat_data)
        
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

    def upload_selection_table_data(self, session, st_df):
        try:
            # Find the index of the 'Selection' column
            selection_index = st_df.columns.get_loc('Selection')
        except ValueError:
            raise ValueError("Missing required column: 'Selection'")
        
        # Find the index of the 'Annotation' column
        annotation_index = st_df.columns.get_loc('Annotation')
        
        if pd.isna(selection_index) or pd.isna(annotation_index):
            raise ValueError("Missing required columns: 'Selection' or 'Annotation'")

        # Get the values for the 'Selection' and 'Annotation' columns
        selection_number = st_df.iloc[0, selection_index]
        annotation = st_df.iloc[0, annotation_index]
        if isinstance(annotation, str):
            if annotation.upper() == "Y" or annotation.upper() == "N" or annotation.upper() == "M":
                self.annotation = annotation.upper()
            else:
                self.annotation = "M"
        else:
            self.annotation = "M"

        # Check if the selection number matches the expected value
        if selection_number != self.selection_number:
            raise ValueError("Invalid selection number")

        # Set the other fields based on the available columns
        self.view = st_df.iloc[0, st_df.columns.get_loc('View')] if 'View' in st_df.columns else ""
        self.channel = st_df.iloc[0, st_df.columns.get_loc('Channel')] if 'Channel' in st_df.columns else ""
        self.begin_time = st_df.iloc[0, st_df.columns.get_loc('Begin Time (s)')] if 'Begin Time (s)' in st_df.columns else 0
        self.end_time = st_df.iloc[0, st_df.columns.get_loc('End Time (s)')] if 'End Time (s)' in st_df.columns else 0
        self.low_frequency = st_df.iloc[0, st_df.columns.get_loc('Low Freq (Hz)')] if 'Low Freq (Hz)' in st_df.columns else 0
        self.high_frequency = st_df.iloc[0, st_df.columns.get_loc('High Freq (Hz)')] if 'High Freq (Hz)' in st_df.columns else 0
        self.delta_time = st_df.iloc[0, st_df.columns.get_loc('Delta Time (s)')] if 'Delta Time (s)' in st_df.columns else 0
        self.delta_frequency = st_df.iloc[0, st_df.columns.get_loc('Delta Freq (Hz)')] if 'Delta Freq (Hz)' in st_df.columns else 0
        self.average_power = st_df.iloc[0, st_df.columns.get_loc('Avg Power Density (dB FS/Hz)')] if 'Avg Power Density (dB FS/Hz)' in st_df.columns else 0

            
        session.commit()

    def update_call(self):
        self.move_file()

    def move_file(self):
        if self.selection_file is not None:
            with database_handler.get_session() as session:
                selection_file = session.query(File).with_for_update().get(self.selection_file_id)
                selection_file.move_file(os.path.join(self.generate_relative_path(),self.generate_filename())+"." +selection_file.extension)
                session.commit()
        if self.contour_file is not None:
            with database_handler.get_session() as session:
                contour_file = session.query(File).with_for_update().get(self.contour_file_id)
                contour_file.move_file(os.path.join(self.generate_relative_path(),self.generate_contour_filename())+"." +contour_file.extension)
                session.commit()
        if self.ctr_file is not None:
            with database_handler.get_session() as session:
                ctr_file = session.query(File).with_for_update().get(self.ctr_file_id)
                ctr_file.move_file(os.path.join(self.generate_relative_path(),self.generate_ctr_file_name())+"." +ctr_file.extension)
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

            
    def generate_plot_filename(self):
        return f"Selectionplot-{str(self.selection_number)}-{self.recording.start_time.strftime('%Y%m%d%H%M%S')}_plot"

    def generate_spectogram_filename(self):
        return f"Selection-{str(self.selection_number)}-{self.recording.start_time.strftime('%Y%m%d%H%M%S')}_spectrogram"

    def generate_filename(self):
        return f"Selection-{str(self.selection_number)}-{self.recording.start_time.strftime('%Y%m%d%H%M%S')}"
    
    def generate_contour_filename(self):
        return f"Contour-{str(self.selection_number)}-{self.recording.start_time.strftime('%Y%m%d%H%M%S')}"
    
    def generate_relative_path(self):
        return os.path.join(self.recording.generate_relative_path_for_selections())

    def generate_full_relative_path(self):
        return os.path.join(self.generate_relative_path(), self.generate_filename())
    
    def set_selection_number(self, value):
        if value is not None and not (isinstance(value, int) or str(value).isdigit()):
            raise ValueError("Selection must be an integer or a string that can be converted to an integer")
        self.selection_number = value



class Species(db.Model):
    __tablename__ = 'species'
    id = db.Column(db.String(36), primary_key=True, default=uuid.uuid4)
    # TODO rename to scientific_name (refactor with actual database)
    species_name = db.Column(db.String(100), nullable=False, unique=True)
    genus_name = db.Column(db.String(100))
    common_name = db.Column(db.String(100))
    updated_by_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

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

    def get_species_name(self):
        return '' if self.species_name is None else self.species_name

    def set_species_name(self, value):
        self.species_name = None if value.strip() == '' else value.strip()
    
    def get_genus_name(self):
        return '' if self.genus_name is None else self.genus_name
    
    def set_genus_name(self, value):
        self.genus_name = None if value.strip() == '' else value.strip()

    def get_common_name(self):
        return '' if self.common_name is None else self.common_name
    
    def set_common_name(self, value):
        self.common_name = None if value.strip() == '' else value.strip()



class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=uuid.uuid4)
    login_id = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_temporary = db.Column(db.Boolean, default=False)
    expiry = db.Column(db.DateTime(timezone=True))
    
    role=db.relationship('Role', backref='users', lazy=True)

    def set_login_id(self, value):
        self.login_id = value
    
    def set_role_id(self, value):
        self.role_id = value
    
    def set_expiry(self, value):
        self.expiry = value
    
    def set_password(self, value):
        self.password = value
    
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




class Assignment(db.Model):
    __tablename__ = 'assignment'
    
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recording_id = db.Column(db.String(36), db.ForeignKey('recording.id'), primary_key=True, nullable=False)
    row_start = db.Column(db.DateTime(timezone=True), server_default=func.current_timestamp())
    user = db.relationship("User", foreign_keys=[user_id])
    recording = db.relationship("Recording", foreign_keys=[recording_id])
    created_datetime = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())
    completed_flag = db.Column(db.Boolean, default=False)


    def is_complete(self):
    
        return "Yes" if self.completed_flag else "No"
    

    def delete(self, session):

        session.delete(self)
        session.commit()