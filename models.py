from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session
import database
from db import db
import uuid
from datetime import datetime
import os

ROOT_PATH="uploads"

class Species(db.Model):
    __tablename__ = 'species'
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    species_name = db.Column(db.String(100), nullable=False, unique=True)
    genus_name = db.Column(db.String(100))
    common_name = db.Column(db.String(100))

    def get_species_name(self):
        print("get species name ", self.species_name,'' if self.species_name is None else self.species_name)
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
    notes = db.Column(db.String(1000))

    species = db.relationship("Species")

    __table_args__ = (
        db.UniqueConstraint('encounter_name', 'location'),
    )

    def generate_relative_path(self):
        species_name = self.species.species_name  # Assuming the relationship is named 'species' and the species name field is 'name'
        return f"Species-{species_name.replace(' ', '_')}/Location-{self.location.replace(' ', '_')}/Encounter-{self.encounter_name.replace(' ', '_')}/"
    

    
    def set_species_id(self, value):
        if type(value)==str:
            try:
                value = uuid.UUID(value)
            except ValueError:
                value = None
        if value is None or value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
            value = None
        
        self.species_id = value

    

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


def encounter_updated(session, encounter_id):
    try:
        recordings = session.query(Recording).filter_by(encounter_id=encounter_id).all()
        for recording in recordings:
            recording.move_file(session,ROOT_PATH)
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

    # TODO
    # add metadata such as
    # - duration
    # - size
    # - format

    def get_filename(self):
        return self.filename
    
    def get_path(self):
        return self.path
    
    def get_full_relative_path(self):
        return os.path.join(self.path, f"{self.filename}.{self.extension}")
    
    def insert_path_and_filename(self, file, new_path, new_filename, root_path):
        #file_location = os.path.join(root_path, path)
        #if not os.path.exists(file_location):
        #    raise ValueError("File path does not exist")
        #if not os.path.exists(os.path.join(file_location, filename)):
        #    raise ValueError("File does not exist")
        
        self.path = new_path
        self.filename = new_filename  # filename without extension

        self.extension = file.filename.split('.')[-1]
        print("INSERT INTO ",os.path.join(root_path, self.get_full_relative_path()))
        if not os.path.exists(os.path.join(root_path, self.get_full_relative_path())):
            os.makedirs(os.path.join(root_path, self.get_path()), exist_ok=True)
            file.save(os.path.join(root_path, self.get_full_relative_path()))
        else:
            raise ValueError("File already exists")

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
        trash_folder = 'trash'
        unique_name = str(uuid.uuid4())

        os.makedirs(trash_folder, exist_ok=True)

        file_path = os.path.join(ROOT_PATH, self.get_full_relative_path())
        file_name = self.filename
        file_name_with_unique = file_name + "-" + unique_name

        trash_file_path = os.path.join(trash_folder, file_name_with_unique)
        os.rename(file_path, trash_file_path)

    def move_file(self, session, new_relative_file_path, root_path):
        new_relative_file_path_with_root = os.path.join(root_path, new_relative_file_path) # add the root path to the relative path
        current_relative_file_path = os.path.join(root_path, self.get_full_relative_path())

        # make the directory of the new_relative_file_path_with_root
        print("MAKE DIRECTORY ",os.path.dirname(new_relative_file_path_with_root))
        print(os.path.exists(os.path.dirname(new_relative_file_path_with_root)))
        if not os.path.exists(os.path.dirname(new_relative_file_path_with_root)):
            os.makedirs(os.path.dirname(new_relative_file_path_with_root))
        
        # if the new and current file paths are not the same
        print(new_relative_file_path_with_root)
        print(current_relative_file_path)
        if new_relative_file_path_with_root != current_relative_file_path:
        
            print("UPDATING")
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
            
            # Check if the old directory is empty and delete it if so
            #if not os.listdir(parent_dir):
            #    os.rmdir(parent_dir)
            
            # Step down into parent folders to check if they are empty

            if os.path.exists(parent_dir):

                while parent_dir != root_path and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    parent_dir = os.path.dirname(parent_dir)
                print("APPLYING CHANGES")
            # Update self.path and self.filename
            
        else:
            if not os.path.samefile(new_relative_file_path, current_relative_file_path):
                raise ValueError(f"Attempted to populate a file that already exists: {new_relative_file_path}")
            return False
        
        

class Recording(db.Model):
    __tablename__ = 'recording'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    start_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)
    recording_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    selection_file_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('file.id'))
    encounter_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('encounter.id'), nullable=False)

    recording_file = db.relationship("File", foreign_keys=[recording_file_id])
    selection_file = db.relationship("File", foreign_keys=[selection_file_id])
    encounter = db.relationship("Encounter", foreign_keys=[encounter_id])

    __table_args__ = (
        db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )



    def move_file(self, session, root_path):
        if self.recording_file is not None:
            self.recording_file.move_file(session,self.generate_full_relative_path(extension="." + self.recording_file.extension),root_path)
        if self.selection_file is not None:
            self.selection_file.move_file(session,self.generate_full_relative_path(extension="." +self.selection_file.extension),root_path)


    def generate_relative_path(self):
        folder_name = self.start_time.strftime("Recording-%Y%m%d%H%M%S")  # Format the start time to include year, month, day, hour, minute, second, and millisecond
        return os.path.join(self.encounter.generate_relative_path(), folder_name)

    def generate_recording_filename(self,extension=""):
        return f"Rec-{self.encounter.species.species_name}-{self.encounter.location}-{self.encounter.encounter_name}-{self.start_time.strftime('%Y%m%d%H%M%S')}{extension}"
    
    def generate_full_relative_path(self,extension=""):
        return os.path.join(self.generate_relative_path(), self.generate_recording_filename(extension=extension))

    def generate_selection_filename(self,extension=""):
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
        if type(value)==str:
            try:
                value = uuid.UUID(value)
            except ValueError:
                value = None
        if value is None or value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
            value = None
        
        self.recording_file_id = value
    

    def set_selection_file_id(self, value):
        if type(value)==str:
            try:
                value = uuid.UUID(value)
            except ValueError:
                value = None
        if value is None or value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
            value = None
        
        self.selection_file_id = value

    def set_encounter_id(self, value):
        if type(value)==str:
            try:
                value = uuid.UUID(value)
            except ValueError:
                value = None
        if value is None or value == uuid.UUID('00000000-0000-0000-0000-000000000000'):
            value = None
        
        self.encounter_id = value

    def set_duration(self,value):
        if value is not None and not isinstance(value, int):
            raise ValueError("Duration must be an integer")
        self.duration = value