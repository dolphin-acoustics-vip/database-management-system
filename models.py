# Standard library imports
import os, uuid
from datetime import datetime
import shared_functions



# Third-party imports
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy import event


# Local application imports
from db import db, FILE_SPACE_PATH




def process_id(value):
    if type(value)==str:
        try:
            return uuid.UUID(value.strip())
        except ValueError:
            value = None
    elif value is None or value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
        return None
    elif isinstance(value, uuid.UUID):
        return value
    else:
        return None

def clean_directory(root_directory):
    """
    Walk through a given directory and remove any empty directories
    """
    # Get the root directory of the project
    for root, dirs, files in os.walk(root_directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)


class User(db.Model, UserMixin):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    login_id = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_temporary = db.Column(db.Boolean, default=False)
    expiry = db.Column(db.DateTime)
    
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
    
    def set_is_active(self, value):
        self.is_active = value

    def get_id(self):
        return str(self.id)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class Species(db.Model):
    __tablename__ = 'species'
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # TODO rename to scientific_name (refactor with actual database)
    species_name = db.Column(db.String(100), nullable=False, unique=True)
    genus_name = db.Column(db.String(100))
    common_name = db.Column(db.String(100))
    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    def update_call(self,session):
        encounters = session.query(Encounter).filter_by(species=self).all()
        for encounter in encounters:
            encounter.update_call(session)

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

class Encounter(db.Model):
    __tablename__ = 'encounter'
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    species_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('species.id'), nullable=False)
    origin = db.Column(db.String(100))
    latitude = db.Column(db.String(20))
    longitude = db.Column(db.String(20))
    data_source_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('data_source.id'), nullable=False)
    recording_platform_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('recording_platform.id'), nullable=False)
    notes = db.Column(db.String(1000))
    
    species = db.relationship("Species")
    data_source = db.relationship("DataSource")
    recording_platform = db.relationship("RecordingPlatform")

    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    __table_args__ = (
        db.UniqueConstraint('encounter_name', 'location'),
    )
    
    def get_number_of_recordings(self):
        """
        Calculate the number of recordings associated with the encounter and return
        """
        num_recordings = db.session.query(Recording).filter_by(encounter_id=self.id).count()
        return num_recordings

    def generate_relative_path(self):
        """
        Generate a relative path for files stored in the file space based on the species, location, and encounter name.
        """
        species_name = self.species.species_name  # Assuming the relationship is named 'species' and the species name field is 'name'
        return f"Species-{species_name.replace(' ', '_')}/Location-{self.location.replace(' ', '_')}/Encounter-{self.encounter_name.replace(' ', '_')}"
    
    def update_call(self,session):
        recordings = session.query(Recording).filter_by(encounter_id=self.id).all()
        for recording in recordings:
            recording.update_call(session)

    def delete(self,session):
        recordings = session.query(Recording).filter_by(encounter_id=self.id).all()
        for recording in recordings:
            recording.delete(session)
        session.delete(self)

    def get_latitude(self):
        return '' if self.latitude is None else self.latitude

    def set_latitude(self, value):
        self.latitude = None if value.strip() == '' else value.strip()
    
    def get_longitude(self):
        return '' if self.longitude is None else self.longitude

    def set_longitude(self, value):
        self.longitude = None if value.strip() == '' else value.strip()
    
    def set_species_id(self, value):
        self.species_id = process_id(value)

    def set_data_source_id(self, value):
        self.data_source_id = process_id(value)
    
    def set_recording_platform_id(self,value):
        self.recording_platform_id = process_id(value)
    
    def get_encounter_name(self):
        return '' if self.encounter_name is None else self.encounter_name

    def set_encounter_name(self, value):
        self.encounter_name = None if value.strip() == '' else value.strip()

    def get_location(self):
        return '' if self.location is None else self.location

    def set_location(self, value):
        self.location = None if value.strip() == '' else value.strip()

    def get_origin(self):
        return '' if self.origin is None else self.origin

    def set_origin(self, value):
        self.origin = None if value.strip() == '' else value.strip()

    def get_notes(self):
        return '' if self.notes is None else self.notes

    def set_notes(self, value):
        self.notes = None if value.strip() == '' else value.strip()


"""TODO remove"""
@DeprecationWarning
def encounter_updated(session, encounter_id):
    try:
        recordings = session.query(Recording).filter_by(encounter_id=encounter_id).all()
        for recording in recordings:
            recording.move_file(session,FILE_SPACE_PATH)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e


class File(db.Model):
    __tablename__ = 'file'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    path = db.Column(db.String, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_date = db.Column(db.DateTime)
    extension = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer)

    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    def delete(self, session):
        self.move_to_trash(session)
        #session.delete(self)
    
    def update_call(self,session):
        pass

    def get_filename(self):
        return self.filename
    
    def get_path(self):
        return self.path
    
    def get_full_relative_path(self):
        return os.path.join(self.path, f"{self.filename}.{self.extension}")
    
    def get_full_absolute_path(self):
        return os.path.join(FILE_SPACE_PATH, self.get_full_relative_path())
    
    def insert_path_and_filename(self, file, new_path, new_filename, root_path):
        self.path = new_path
        self.filename = new_filename  # filename without extension

        self.extension = file.filename.split('.')[-1]
        if not os.path.exists(os.path.join(root_path, self.get_full_relative_path())):
            os.makedirs(os.path.join(root_path, self.get_path()), exist_ok=True)
            file.save(os.path.join(root_path, self.get_full_relative_path()))
        else:
            raise IOError(f"File already exists in location {os.path.join(root_path, self.get_full_relative_path())}. Cannot overwrite.")
            
    def update_path_and_filename(self, new_path, new_filename,root_path):

        self.path = new_path
        self.filename = new_filename

    def get_uploaded_date(self):
        return self.uploaded_date


    def set_uploaded_date(self, value):
        if value is not None and not isinstance(value, datetime):
            raise ValueError("Uploaded date must be a valid datetime")
        self.uploaded_date = value
    
    def set_uploaded_by(self, value):
        self.uploaded_by = value

    def move_to_trash(self,session):
        """
        Moves the file to the trash folder.

        This function moves the file to the trash folder by renaming the file and adding a unique identifier to its name.
        TODO: keep a record of deleted file metadata
        """
        
        trash_folder = 'trash'
        unique_name = str(uuid.uuid4())
        os.makedirs(trash_folder, exist_ok=True)
        file_name = self.filename
        trash_file_path = os.path.join(trash_folder,os.path.join(self.get_path(),unique_name + '_' + file_name + '.' + self.extension))
        
        self.move_file(session, trash_file_path, FILE_SPACE_PATH)


    def move_file(self, session, new_relative_file_path, root_path):
        """
        Move a file to a new location with the provided session.

        Parameters:
        - session: The session object to use for the database transaction
        - new_relative_file_path: The new relative file path to move the file to
        - root_path: The root path where the file is currently located
        - return: False if the file already exists at the new location, None otherwise
        """
        new_relative_file_path_with_root = os.path.join(root_path, new_relative_file_path) # add the root path to the relative path
        current_relative_file_path = os.path.join(root_path, self.get_full_relative_path())

        # make the directory of the new_relative_file_path_with_root
        if not os.path.exists(os.path.dirname(new_relative_file_path_with_root)):
            os.makedirs(os.path.dirname(new_relative_file_path_with_root))
        
        # if the new and current file paths are not the same
        if new_relative_file_path_with_root != current_relative_file_path:
        
            self.path = os.path.dirname(new_relative_file_path)
            self.filename = os.path.basename(new_relative_file_path).split(".")[0]
            self.extension = os.path.basename(new_relative_file_path).split(".")[-1]
            if os.path.exists(current_relative_file_path):
                os.rename(current_relative_file_path, new_relative_file_path_with_root)
            try:
                session.commit()
            except Exception as e:
                try:
                    os.rename(new_relative_file_path_with_root,current_relative_file_path)
                except Exception:
                    pass
            
            parent_dir = os.path.dirname(current_relative_file_path)

            if os.path.exists(parent_dir):
                while parent_dir != root_path and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    parent_dir = os.path.dirname(parent_dir)
            
        else:
            if not os.path.samefile(new_relative_file_path_with_root, current_relative_file_path):
                raise IOError(f"Attempted to populate a file that already exists: {new_relative_file_path_with_root}")
            return False

"""
class Audit(db.Model):
    __tablename__ = 'audit'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    created_at = db.Column(db.DateTime, nullable=False, server_default="current_timestamp()")
    updated_at = db.Column(db.DateTime, nullable=False, server_default="current_timestamp()", onupdate="current_timestamp()")
    action = db.Column(db.String(50), nullable=False)

"""
    
class Recording(db.Model):
    __tablename__ = 'recording'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    start_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)
    recording_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    selection_table_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    encounter_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('encounter.id'), nullable=False)
    ignore_selection_table_warnings = db.Column(db.Boolean, default=False)
    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))

    recording_file = db.relationship("File", foreign_keys=[recording_file_id])
    selection_table_file = db.relationship("File", foreign_keys=[selection_table_file_id])
    encounter = db.relationship("Encounter", foreign_keys=[encounter_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    row_start = db.Column(db.DateTime, server_default=func.current_timestamp())
    #row_end = db.Column(db.DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    #valid_to = Column(DateTime, server_default=func.inf())
    __table_args__ = (
        db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )

    def set_user_id(self, user_id):
        self.updated_by_id = user_id



    def get_number_of_selections(self):
        selections = shared_functions.create_system_time_request(db.session, Selection, {"recording_id":self.id}, order_by="selection_number")
        return len(selections)

    def get_number_of_contours(self):
        #selections = shared_functions.create_system_time_request(db.session, Selection, {"recording_id":self.id}, order_by="selection_number")

        contours = db.session.query(Selection).filter_by(recording_id=self.id).filter(Selection.contour_file != None).all()
        return len(contours)

    def update_call(self, session):
        self.move_file(session,FILE_SPACE_PATH)
        if self.recording_file is not None:
            self.recording_file.update_call(session)
        if self.selection_table_file is not None:
            self.selection_table_file.update_call(session)

        
        selections = session.query(Selection).filter_by(recording_id=self.id).all()
        for selection in selections:
            selection.update_call(session)
        
            

    def load_selection_table_data(self,custom_file=None):
        import pandas as pd
        
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
            elif file_extension == '.xlsx':
                # Read the Excel file into a pandas DataFrame
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")
            # Define the expected column names and data types
            '''
            expected_columns = {
                'Selection': int,
                'View': object,
                'Channel': int,
                'Begin Time (s)': float,
                'End Time (s)': float,
                'Low Freq (Hz)': float,
                'High Freq (Hz)': float,
                'Delta Time (s)': float,
                'Delta Freq (Hz)': float,
                'Avg Power Density (dB FS/Hz)': float,
                'Annotation': object,
                'annotation': object
            }

            # Check that the columns match the expected names and types
            for column, dtype in expected_columns.items():
                if column not in df.columns:
                    raise ValueError(f"Missing column: {column}")
                if df[column].dtype != dtype:
                    raise ValueError(f"Incorrect data type for column {column}: expected {dtype}, got {df[column].dtype}")
            '''
            # Check that the values in the 'Annotation' column are either 'Y' or 'M' or 'N'
            if not df['Annotation'].isin(['Y', 'M', 'N']).all():
                raise ValueError("Invalid values in 'annotation' column: expected 'Y' or 'N'")

            return df

        return pd.DataFrame()

    def validate_selection_table(self, session, custom_file=None):
        try:
            st_df = self.load_selection_table_data(custom_file=custom_file)
            if st_df.empty:
                return [], "The Selection Table does not exist"
            self.upload_selection_table_rows(session, st_df)
            #missing_selections = self.find_missing_selections(session, st_df)
            session.commit()
            #return missing_selections, ""
            return ""
        except Exception as e:
            raise e
            return "The Selection Table provided is invalid: " + str(e)
            
        return "The Selection Table does not exist"

    def upload_selection_table_rows(self, session, st_df):
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
        selections = shared_functions.create_system_time_request(session, Selection, {"recording_id":self.id}, order_by="selection_number")
        missing_selections = []
        selection_numbers = [selection.selection_number for selection in selections]
        if self.selection_table_file != None:
            # Validate files exist for all selections within the Selection Table
            selections_array = sorted(st_df['Selection'].to_list())
            for selection_num in selections_array:
                if selection_num not in selection_numbers:
                    missing_selections.append({"selection_number":selection_num})
        return missing_selections

        

    def delete(self, session, keep_file_reference=False):        
        if self.recording_file_id is not None:
            self.recording_file.delete(session)
            if not keep_file_reference: self.recording_file = None  # Remove the reference to the recording file
        
        if self.selection_table_file_id is not None:
            self.selection_table_file.delete(session)
            if not keep_file_reference: self.selection_table_file = None  # Remove the reference to the selection file
        
        selections = session.query(Selection).filter_by(recording_id=self.id).all()
        for selection in selections:
            selection.delete(session, keep_file_reference=keep_file_reference)


        session.delete(self)


    def move_file(self, session, root_path):
        if self.recording_file is not None:
            self.recording_file.move_file(session,self.generate_full_relative_path(extension="." + self.recording_file.extension),root_path)
        if self.selection_table_file is not None:
            self.selection_table_file.move_file(session,self.generate_full_relative_path(extension="." +self.selection_table_file.extension),root_path)

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

    def generate_selection_table_filename(self,extension=""):
        return f"Sel-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{self.start_time.strftime('%Y%m%d%H%M%S')}{extension}"
    def get_start_time(self):
        return self.start_time
    
    def get_seconds(self):
        return self.start_time.second


    def set_start_time(self, datetime_object, seconds=0):
        if seconds is None or seconds == "":
            seconds = 0
        if isinstance(datetime_object, str):
            try:
                datetime_object = datetime.strptime(f"{datetime_object}:{seconds}", '%Y-%m-%dT%H:%M:%S')  # Modify the format to include milliseconds
            except ValueError:
                raise ValueError("Invalid datetime format")
        elif not isinstance(datetime_object, datetime):
            raise ValueError("Start time must be a valid datetime")
        self.start_time = datetime_object
    
    def match_start_time(self, match_datetime):
        return self.start_time == match_datetime

    def get_start_time_string(self, seconds=False):
        if seconds:
            return self.start_time.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            return self.start_time.strftime('%Y-%m-%dT%H:%M')

    def get_start_time(self):
        return self.start_time
    

    def get_duration(self):
        return self.duration

    
    def set_recording_file_id(self, value):
        self.recording_file_id = process_id(value)
    

    def set_selection_table_file_id(self, value):
        self.selection_table_file_id = process_id(value)

    def set_encounter_id(self, value):
        self.encounter_id = process_id(value)

    def set_duration(self,value):
        if value is not None and not isinstance(value, int):
            raise ValueError("Duration must be an integer")
        self.duration = value
    
"""

class RecordingAudit(Audit, Recording, db.Model):
    __tablename__ = 'recording_audit'

    record_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('recording.id'), nullable=False)
    record = db.relationship("Recording", foreign_keys=[record_id])
"""
class Selection(db.Model):
    __tablename__ = 'selection'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="UUID()")
    selection_number = db.Column(db.Integer, nullable=False)
    selection_file_id = db.Column(db.String, db.ForeignKey('file.id'), nullable=False)
    recording_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('recording.id'), nullable=False)
    contour_file_id = db.Column(db.String, db.ForeignKey('file.id'))
    annotation = db.Column(db.String, nullable=False)
    row_start = db.Column(db.DateTime, server_default=func.current_timestamp())

    ### Selection Table data ###
    view = db.Column(db.String)
    channel = db.Column(db.Integer)
    begin_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    low_frequency = db.Column(db.Float)
    high_frequency = db.Column(db.Float)
    delta_time = db.Column(db.Float)
    delta_frequency = db.Column(db.Float)
    average_power = db.Column(db.Float)

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
    inflection_meandelta = db.Column(db.Float, nullable=True, default=None)
    inflection_standarddeviationdelta = db.Column(db.Float, nullable=True, default=None)
    inflection_duration = db.Column(db.Float, nullable=True, default=None)
    step_duration = db.Column(db.Float, nullable=True, default=None)
    freq_peak = db.Column(db.Float, nullable=True, default=None)
    bw3db = db.Column(db.Float, nullable=True, default=None)
    bw3dblow = db.Column(db.Float, nullable=True, default=None)
    bw3dbhigh = db.Column(db.Float, nullable=True, default=None)
    bw10db = db.Column(db.Float, nullable=True, default=None)
    bw10dblow = db.Column(db.Float, nullable=True, default=None)
    bw10dbhigh = db.Column(db.Float, nullable=True, default=None)
    rms_signal = db.Column(db.Float, nullable=True, default=None)
    rms_noise = db.Column(db.Float, nullable=True, default=None)
    snr = db.Column(db.Float, nullable=True, default=None)
    num_crossings = db.Column(db.Integer, nullable=True, default=None)
    sweep_rate = db.Column(db.Float, nullable=True, default=None)
    mean_timezc = db.Column(db.Float, nullable=True, default=None)
    median_timezc = db.Column(db.Float, nullable=True, default=None)
    variance_timezc = db.Column(db.Float, nullable=True, default=None)
    whale_train = db.Column(db.Integer, nullable=True, default=None)

    contour_file = db.relationship("File", foreign_keys=[contour_file_id])
    selection_file = db.relationship("File", foreign_keys=[selection_file_id])
    recording = db.relationship("Recording", foreign_keys=[recording_id])
    
    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])


    __table_args__ = (
        db.UniqueConstraint('selection_number', 'recording_id', name='unique_selection_number_recording'),
        {"mysql_engine": "InnoDB", "mysql_charset": "latin1", "mysql_collate": "latin1_swedish_ci"}
    )


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


    def upload_selection_table_data(self, session, st_df):
        if st_df.iloc[0,0]==self.selection_number:
            self.view = st_df.iloc[0, 1]
            self.channel = st_df.iloc[0, 2]
            self.begin_time = st_df.iloc[0, 3]
            self.end_time = st_df.iloc[0, 4]
            self.low_frequency = st_df.iloc[0, 5]
            self.high_frequency = st_df.iloc[0, 6]
            self.delta_time = st_df.iloc[0, 7]
            self.delta_frequency = st_df.iloc[0, 8]
            self.average_power = st_df.iloc[0, 9]
            self.annotation = st_df.iloc[0, 10]
        session.commit()

    def update_call(self, session):
        self.move_file(session,FILE_SPACE_PATH)

    def move_file(self, session, root_path):
        if self.selection_file is not None:
            self.selection_file.move_file(session,self.generate_full_relative_path()+"." +self.selection_file.extension,root_path)
        if self.contour_file is not None:
            self.contour_file.move_file(session,self.generate_full_relative_path()+"." +self.contour_file.extension,root_path)

    def delete(self, session,keep_file_reference):        
        if self.selection_file_id is not None:
            self.selection_file.delete(session)
            if not keep_file_reference: self.selection_file = None  # Remove the reference to the recording file
        if self.contour_file_id is not None:
            self.contour_file.delete(session)
            if not keep_file_reference: self.contour_file = None
        session.delete(self)


    def delete_contour_file(self, session):
        if self.contour_file_id is not None:
            self.contour_file.delete(session)
            self.contour_file = None
        

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


class DataSource(db.Model):
    __tablename__ = 'data_source'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="UUID()")
    name = db.Column(db.String(255))
    phone_number1 = db.Column(db.String(20), unique=True)
    phone_number2 = db.Column(db.String(20), unique=True)
    email1 = db.Column(db.String(255), nullable=False, unique=True)
    email2 = db.Column(db.String(255), unique=True)
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    type = db.Column(db.Enum('person', 'organisation'))

    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<DataSource %r>' % self.name
    


class RecordingPlatform(db.Model):
    __tablename__ = 'recording_platform'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="UUID()")
    name = db.Column(db.String(100), unique=True, nullable=False)
    updated_by_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'))
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    def __repr__(self):
        return '<RecordingPlatform %r>' % self.name