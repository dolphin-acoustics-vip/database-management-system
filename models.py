# Standard library imports
import os, uuid
from datetime import datetime

# Third-party imports
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for

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

class Species(db.Model):
    __tablename__ = 'species'
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # TODO rename to scientific_name (refactor with actual database)
    species_name = db.Column(db.String(100), nullable=False, unique=True)
    genus_name = db.Column(db.String(100))
    common_name = db.Column(db.String(100))

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
            print("delete recording",recording.id)
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
    uploaded_by = db.Column(db.String(100))
    extension = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer)

    def delete(self, session):
        self.move_to_trash()
        session.delete(self)
    
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

    def move_to_trash(self):
        """
        Moves the file to the trash folder.

        This function moves the file to the trash folder by renaming the file and adding a unique identifier to its name.
        TODO: keep a record of deleted file metadata
        """
        trash_folder = 'trash'
        unique_name = str(uuid.uuid4())
        os.makedirs(trash_folder, exist_ok=True)
        file_path = os.path.join(FILE_SPACE_PATH, self.get_full_relative_path())
        file_name = self.filename
        file_name_with_unique = file_name + "-" + unique_name
        trash_file_path = os.path.join(trash_folder, file_name_with_unique) + "." + self.extension
        if os.path.exists(trash_folder) and os.path.exists(file_path):
            os.rename(file_path, trash_file_path)

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
        
        

class Recording(db.Model):
    __tablename__ = 'recording'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    start_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)
    recording_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    selection_table_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    encounter_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('encounter.id'), nullable=False)
    ignore_selection_table_warnings = db.Column(db.Boolean, default=False)

    recording_file = db.relationship("File", foreign_keys=[recording_file_id])
    selection_table_file = db.relationship("File", foreign_keys=[selection_table_file_id])
    encounter = db.relationship("Encounter", foreign_keys=[encounter_id])
    
    

    __table_args__ = (
        db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )

    def get_number_of_unresolved_warnings(self):
        counter = 0
        selections = db.session.query(Selection).filter_by(recording_id=self.id).all()
        for selection in selections:
            if selection.ignore_warnings == False and len(selection.getWarnings())>0:
                counter += 1
                
        missing_selections, error_msg = self.validate_selection_table(db.session)
        if not self.ignore_selection_table_warnings:
            for selection in missing_selections:
                counter += 1
        print("Unresolved",counter)
        return counter

    def get_number_of_selections(self):
        selections = db.session.query(Selection).filter_by(recording_id=self.id).all()
        return len(selections)

    def get_number_of_contours(self):
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
                'Contoured': object
            }

            # Check that the columns match the expected names and types
            for column, dtype in expected_columns.items():
                if column not in df.columns:
                    raise ValueError(f"Missing column: {column}")
                if df[column].dtype != dtype:
                    raise ValueError(f"Incorrect data type for column {column}: expected {dtype}, got {df[column].dtype}")

            # Check that the values in the 'Annotation' column are either 'Y' or 'M' or 'N'
            if not df['Annotation'].isin(['Y', 'M', 'N']).all():
                raise ValueError("Invalid values in 'Contoured' column: expected 'Y' or 'N'")

            return df

        return pd.DataFrame()

    def get_selection_table_row(self, selection_number):
        st_df = self.load_selection_table_data()
        return st_df.loc[st_df['Selection'] == selection_number]

    def reset_all_selections_unresolved_warnings(self,session):
        print("reset_all_selections_unresolved_warnings")
        selections = session.query(Selection).filter_by(recording_id=self.id).all()
        for selection in selections:
            selection.ignore_warnings = False

    def selection_exists_in_selection_table(self, selection_number):
        
        st_df = self.load_selection_table_data()
        if not st_df.empty:
            return selection_number in st_df.Selection.to_list()

    def validate_selection_table(self, session, custom_file=None):
        try:  
            st_df = self.load_selection_table_data(custom_file=custom_file)
            if st_df.empty:
                self.set_all_cross_referenced(session)
                return [], "The selection table does not exist"
            self.cross_reference_selections(session, st_df)
            missing_selections = self.find_missing_selections(session, st_df)
            session.commit()
            return missing_selections, ""
        except Exception as e:
            self.set_all_cross_referenced(session)
            return [], "The selection table provided is invalid: " + str(e)
            
        return [], "The selection table does not exist"

        
    def set_all_cross_referenced(self, session):
        selections = session.query(Selection).filter_by(recording_id=self.id).order_by(Selection.selection_number).all()
        for selection in selections:
            selection.setCrossReferencedFalse(session)
        
        
    def cross_reference_selections(self,session,st_df):
        selections = session.query(Selection).filter_by(recording_id=self.id).order_by(Selection.selection_number).all()
        selection_table_selection_numbers = st_df.Selection.to_list()
        for selection in selections:
            if selection.selection_number not in selection_table_selection_numbers:
                selection.setCrossReferencedFalse(session)  
            elif selection.selection_number in selection_table_selection_numbers:
                selection.setCrossReferencedTrue(session, st_df.loc[st_df['Selection'] == selection.selection_number, 'Contoured'].values[0])


    def find_missing_selections(self, session, st_df):
        selections = session.query(Selection).filter_by(recording_id=self.id).order_by(Selection.selection_number).all()
        missing_selections = []
        selection_numbers = [selection.selection_number for selection in selections]
        if self.selection_table_file != None:
            # Validate files exist for all selections within the selection table
            selections_array = sorted(st_df['Selection'].to_list())
            print(selections_array)
            for selection_num in selections_array:
                if selection_num not in selection_numbers:
                    missing_selections.append({"selection_number":selection_num})
        return missing_selections

        

    def delete(self, session):        
        if self.recording_file_id is not None:
            self.recording_file.delete(session)
            self.recording_file = None  # Remove the reference to the recording file
        
        if self.selection_table_file_id is not None:
            self.selection_table_file.delete(session)
            self.selection_table_file = None  # Remove the reference to the selection file
        

        selections = session.query(Selection).filter_by(recording_id=self.id).all()
        for selection in selections:
            selection.delete(session)


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
    

class Selection(db.Model):
    __tablename__ = 'selection'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="UUID()")
    selection_number = db.Column(db.Integer, nullable=False)
    selection_file_id = db.Column(db.String, db.ForeignKey('file.id'), nullable=False)
    recording_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('recording.id'), nullable=False)
    contour_file_id = db.Column(db.String, db.ForeignKey('file.id'))
    cross_referenced = db.Column(db.Boolean, nullable=False, default=False)
    contoured = db.Column(db.String, nullable=False)
    ignore_warnings = db.Column(db.Boolean, nullable=False, default=False)
    
    contour_file = db.relationship("File", foreign_keys=[contour_file_id])
    selection_file = db.relationship("File", foreign_keys=[selection_file_id])
    recording = db.relationship("Recording", foreign_keys=[recording_id])
    


    __table_args__ = (
        db.UniqueConstraint('selection_number', 'recording_id', name='unique_selection_number_recording'),
        {"mysql_engine": "InnoDB", "mysql_charset": "latin1", "mysql_collate": "latin1_swedish_ci"}
    )


    def getWarnings(self):
        warnings = []
        if self.contour_file and self.contoured=="N":
            warnings.append("Contour file exists but annotated 'N'.")
        elif not self.contour_file and self.contoured=="Y" or self.contoured=="M":
            warnings.append(f"Selection annotated '{self.contoured}' but no contour file.")
        elif not self.recording.selection_table_file:
            warnings.append("No selection table file.")
        return warnings

    def setCrossReferencedTrue(self, session, contoured):
        self.cross_referenced = True
        self.contoured = contoured
        session.commit()
        
    def setCrossReferencedFalse(self, session):
        self.cross_referenced = False
        self.contoured=None
        session.commit()

    def get_selection_table_row(self):
        #print(self.recording.get_selection_table_row(self.selection_number))
        row_dict = {}

        row = self.recording.get_selection_table_row(self.selection_number)
        print(row)
        if not row.empty:
            first_row = row.iloc[0]
            for column, value in first_row.items():
                row_dict[column] = value
        return row_dict


    def update_call(self, session):
        self.move_file(session,FILE_SPACE_PATH)

    def move_file(self, session, root_path):
        if self.selection_file is not None:
            self.selection_file.move_file(session,self.generate_full_relative_path()+"." +self.selection_file.extension,root_path)
        if self.contour_file is not None:
            self.contour_file.move_file(session,self.generate_full_relative_path()+"." +self.contour_file.extension,root_path)

    def delete(self, session):        
        if self.selection_file_id is not None:
            self.selection_file.delete(session)
            self.selection_file = None  # Remove the reference to the recording file
        if self.contour_file_id is not None:
            self.contour_file.delete(session)
            self.contour_file = None
        session.delete(self)


    def delete_contour_file(self, session):
        if self.contour_file_id is not None:
            self.contour_file.delete(session)
            self.contour_file = None
            self.ignore_warnings=False
        

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

    def __repr__(self):
        return '<DataSource %r>' % self.name
    


class RecordingPlatform(db.Model):
    __tablename__ = 'recording_platform'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="UUID()")
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return '<RecordingPlatform %r>' % self.name