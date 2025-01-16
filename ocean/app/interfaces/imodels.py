# INTERFACES FOR MODELS

from abc import ABC, ABCMeta, abstractmethod
import datetime
from typing import Protocol
from uuid import UUID
import uuid
from sqlalchemy.ext.declarative import declared_attr
from flask_login import UserMixin
from .. import database_handler
from sqlalchemy.orm import validates
from .. import utils
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
import typing
import warnings
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from .. import exception_handler

# Combine ABCMeta and SQLAlchemy's DeclarativeMeta
class CombinedMeta(ABCMeta, type(database_handler.db.Model)):
    pass

class AbstractModelBase(database_handler.db.Model, metaclass=CombinedMeta):
    __abstract__ = True

class Serialisable(ABC):
    """An abstract class for serialisable objects.
    
    All serialisable objects must implement the private `_to_dict()` method."""
    
    @abstractmethod
    def _to_dict(self) -> typing.Dict[str, typing.Any]:
        """Convert the object to a dictionary representation.
        
        This method should be implemented to return a dictionary containing
        all publicly accessible attributes of the object. This method is then
        accessed by the public `to_dict()` which is already implemented and
        will recursively convert any values that are themselves serialisable
        to dictionaries.
        """
        pass

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Convert the object to a dictionary representation.
        
        The dictionary contains all publicly accessible attributes of
        the object as if relations in the database were keys and their
        values, values. Where an attribute implements the `Serialisable`
        interface, its value is recursively converted to a dictionary.
        """
        d = self._to_dict()
        for k, v in d.items():
            if isinstance(v, Serialisable):
                d[k] = v.to_dict()
        return d

class TableOperations(ABC):
    
    @abstractmethod
    def _form_dict(self) -> typing.Dict[str, bool]:
        """Return a dictionary of all attributes that can be set (for example
        by a form). The keys are the names of the attributes and the values
        are booleans indicating whether the attributes are required."""
        pass

    @abstractmethod
    def _insert_or_update(self, form, new):
        """A method that inserts or updates data in the object
        based on form data. 
        
        Raises:
            AttributeError: if the form is missing data
            exception_handler.ValidationError: if the form data is invalid
        """
        pass

    def insert(self, form):
        """Insert form data into the database object."""
        self._insert_or_update(form=form, new=True)

    def update(self, form):
        """Update the database object with form data.
        
        Warning: if the class implements `Cascading` oftentimes updates
        will require a call to `apply_updates()` to ensure changes are
        cascaded to all children.
        """
        self._insert_or_update(form=form, new=False)

    @abstractmethod
    def delete(self):
        """Check if the object can be deleted. Raise an exception if it
        cannot be deleted.
        
        An exception is raised usually if the object has foreign key
        dependencies that are not allowed to be automatically resolved.
        This will cause an `exception_handler.WarningException` to be raised
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def unique_name(self):
        """The unique name of the object"""
        pass

    def _update_filespace(self):
        """Update all child objects that impact the filespace (objects of the
        `File` class).
        
        This method must not be called outside of `apply_updates()`.
        
        Each change to the filespace is made and committed in
        a unique session to ensure that failures are isolated. There is no
        action needed from the caller to ensure changes are committed.
        
        Go through all of this object's foreign key references to the `File`
        class and ensure that the correct directory and filenames are generated
        and stored in accordance with this object's metadata. This method is
        automatically called by `apply_updates` but its implementation is
        specified by each individual class.
        """
        return

    def apply_updates(self):
        with database_handler.get_session() as session:
            self._update_filespace()
            if issubclass(type(self), Cascading):
                for child in self._get_children(session):
                    if issubclass(type(child), TableOperations):
                        child.apply_updates()
            session.commit()

class Cascading(ABC):
    
    @abstractmethod
    def _get_children(self, session):
        """Return a list of child objects of this obejct (also known as foreign key
        dependencies). The exact datatype of child objects will vary by implementation
        of this method. All child objects will be bound to the session passed as a
        parameter.
        """
        raise NotImplementedError()

    @abstractmethod
    def apply_updates(self):
        """Apply changes to this object and invoke updates on related objects. 
        
        This method should be called whenever a piece of metadata changes (either in
        this object or one of its parents). This method should ensure that any data
        in this object that rely on its parents metadata are updated accordingly.
        """
        pass

    def _delete_children(self):
        """Cascade delete all children of this object. The children are defined by
        the `_get_children()` method.
        
        The implementation of cascading is dependent on the `delete` method of all
        child objects.
        """
        with database_handler.get_session() as session:
            for child in self._get_children(session):
                if issubclass(type(child), TableOperations):
                    child.delete()
                    session.delete(child)
                    session.commit()

class ISpecies(AbstractModelBase, Serialisable, TableOperations, Cascading):
    __tablename__ = 'species'
    __table_args__ = (database_handler.db.PrimaryKeyConstraint('id'),)

    id = Column(String(36), primary_key=True, nullable=False, server_default="UUID()")
    # TODO rename to scientific_name (refactor with actual database)
    species_name = Column(String(100), nullable=False, unique=True)
    genus_name = Column(String(100))
    common_name = Column(String(100))
    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    def _to_dict(self):
        return {
            'id': self.id,
            'species_name': self.species_name,
            'genus_name': self.genus_name,
            'common_name': self.common_name,
            'updated_by_id': self.updated_by_id,
        }
    
    def _form_dict(self):
        return {
            'species_name': True,
            'genus_name': True,
            'common_name': True
        }

    @validates("id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=False)
    
    @validates("updated_by_id")
    def _validate_id_nullable(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=True)

    @validates("genus_name", "common_name")
    def _validate_str_nullable(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)
    
    @validates("species_name")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)

    @property
    @abstractmethod
    def folder_name(self) -> str:
        """The folder name of the species in the filespace. Implementation must
        be secure (for example see `from werkzeug.utils import secure_filename`)"""
        pass

class IRecordingPlatform(AbstractModelBase, Serialisable, TableOperations):
    """Abstract class for the SQLAlchemy table recording_platform.
    
    Abstract class implementation is inforced using ABC. 
    Inherits from `Serialisable`.
    """

    __tablename__ = 'recording_platform'
    __table_args__ = (database_handler.db.PrimaryKeyConstraint('id'),)

    id = Column(String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = Column(String(100), unique=True, nullable=False)
    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    def _to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'updated_by_id': self.updated_by_id,
            'updated_by': self.updated_by
        }
    
    def _form_dict(self) -> dict:
        return {
            'name': True
        }

    @property
    def unique_name(self):
        """The recording platform name"""
        return self.name

    @validates("id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field="ID", allow_none=False)

    @validates("updated_by_id")
    def _validate_id_nullable(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=True)

    @validates("name")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field="Name", allow_none=False)
    
    @validates("updated_by")
    def _reject(self, key, value):
        raise ValueError(f"Unable to set {key} on recording_platform")

class IEncounter(AbstractModelBase, Serialisable, TableOperations, Cascading):
    __tablename__ = 'encounter'
    # __table_args__ = (database_handler.db.PrimaryKeyConstraint('id'),)

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    encounter_name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    species_id = Column(String(36), database_handler.db.ForeignKey('species.id'), nullable=False)
    project = Column(String(100), nullable=False)
    latitude = Column(database_handler.db.Double)
    longitude = Column(database_handler.db.Double)
    data_source_id = Column(String(36), database_handler.db.ForeignKey('data_source.id'), nullable=False)
    recording_platform_id = Column(String(36), database_handler.db.ForeignKey('recording_platform.id'), nullable=False)
    notes = Column(String(1000))
    file_timezone = Column(Integer)
    local_timezone = Column(Integer)
    species = database_handler.db.relationship("Species")
    data_source = database_handler.db.relationship("DataSource")
    recording_platform = database_handler.db.relationship("RecordingPlatform")
    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    __table_args__ = (
        database_handler.db.UniqueConstraint('encounter_name', 'location', 'project'),
    )

    def _to_dict(self):
        return {
            'id': self.id,
            'encounter_name': self.encounter_name,
            'location': self.location,
            'species_id': self.species_id,
            'project': self.project,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'data_source_id': self.data_source_id,
            'recording_platform_id': self.recording_platform_id,
            'notes': self.notes,
            'file_timezone': self.file_timezone,
            'local_timezone': self.local_timezone,
            'species': self.species,
            'data_source': self.data_source,
            'recording_platform': self.recording_platform,
            'updated_by_id': self.updated_by_id,
        }
    
    def _form_dict(self):
        return {
            'encounter_name': True,
            'location': True,
            'project': True,
            'species_id': True,
            'latitude': False,
            'longitude': False,
            'data_source_id': False,
            'recording_platform_id': False,
            'notes': False,
            'file_timezone': False,
            'local_timezone': False
        }
    
    @property
    def unique_name(self):
        """The encounter name"""
        return self.encounter_name

    @validates("id", "species_id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field="ID", allow_none=False)

    @validates("updated_by_id", "data_source_id", "recording_platform_id")
    def _validate_id_nullable(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=True)
    
    @validates("encounter_name", "location", "project")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)
    
    @validates("latitude", "longitude")
    def _validate_float(self, key, value):
        return utils.validate_float(value=value, field=key, allow_none=True)
    
    @validates("file_timezone", "local_timezone")
    def _validate_int(self, key, value):
        return utils.validate_int(value=value, field=key, allow_none=True)

    @validates("notes")
    def _validate_str_nullable(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)

    @property
    @abstractmethod
    def recording_count(self) -> int:
        """Returns the number of recordings in the encounter"""
        pass

    @property
    @abstractmethod
    def relative_directory(self) -> str:
        """Returns the relative directory to the encounter in the filespace. Implementation must
        be secure (for example see `from werkzeug.utils import secure_filename`)"""
        pass

    @property
    @abstractmethod
    def folder_name(self):
        """The folder name of the encounter in the filespace. Implementation must
        be secure (for example see `from werkzeug.utils import secure_filename`)"""
        pass

    @property
    @abstractmethod
    def location_folder_name(self):
        """The folder name of the location in the filespace. Implementation must
        be secure (for example see `from werkzeug.utils import secure_filename`)"""
        pass

class IRecording(AbstractModelBase, Serialisable, TableOperations, Cascading):
    __tablename__ = 'recording'

    # identifiers
    id = Column(String(36), primary_key=True, nullable=False, server_default="uuid_generate_v4()")
    # parent
    encounter_id = Column(String(36), database_handler.db.ForeignKey('encounter.id'), nullable=False)
    encounter = database_handler.db.relationship("Encounter", foreign_keys=[encounter_id])
    # metadata
    start_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(database_handler.db.Enum('Unassigned','In Progress','Awaiting Review','Reviewed','On Hold'), nullable=False, default='Unassigned')
    status_change_datetime = Column(DateTime(timezone=True))
    notes = Column(Text)
    # children
    recording_file_id = Column(String(36), database_handler.db.ForeignKey('file.id'))
    recording_file = database_handler.db.relationship("File", foreign_keys=[recording_file_id])
    selection_table_file_id = Column(String(36), database_handler.db.ForeignKey('file.id'))
    selection_table_file = database_handler.db.relationship("File", foreign_keys=[selection_table_file_id])
    # automatic metadata
    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])
    row_start = Column(DateTime(timezone=True), server_default="current_timestamp()")
    created_datetime = Column(DateTime(timezone=True), nullable=False, server_default="current_timestamp()")

    __table_args__ = (
        database_handler.db.UniqueConstraint('start_time', 'encounter_id', name='unique_time_encounter_id'),
    )

    def _to_dict(self):
        return {
            'unique_name': self.unique_name,
            'id': self.id,
            'encounter_id': self.encounter_id,
            'encounter': self.encounter,
            'start_time': self.start_time,
            'status': self.status,
            'status_change_datetime': self.status_change_datetime,
            'notes': self.notes,
            'recording_file_id': self.recording_file_id,
            'recording_file': self.recording_file,
            'selection_table_file_id': self.selection_table_file_id,
            'selection_table_file': self.selection_table_file,
            'updated_by_id': self.updated_by_id,
            'row_start': self.row_start,
            'created_datetime': self.created_datetime
        }

    def _form_dict(self):
        return {
            'start_time': True,
            'status': False,
            'notes': False
        }

    @validates("id", "encounter_id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=False)
    
    @validates("recording_file_id", "selection_table_file_id", "updated_by_id")
    def _validate_id_nullable(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=True)

    @validates("start_time")
    def _validate_datetime(self, key, value):
        return utils.validate_datetime(value=value, field=key, allow_none=False)
    
    @validates("status_change_datetime")
    def _validate_datetime_nullable(self, key, value):
        return utils.validate_datetime(value=value, field=key, allow_none=True)

    @validates("notes")
    def _validate_str_nullable(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)

    @validates("status")
    def _validate_status(self, key, value):
        return utils.validate_enum(value=value, field=key, enum=['Unassigned','In Progress','Awaiting Review','Reviewed','On Hold'], allow_none = False)

    @validates("row_start", "created_datetime")
    def _reject_change(self, key, value):
        raise exception_handler.CriticalException(f"Cannot change {key}")
    
    @abstractmethod
    def selection_table_apply(self):
        """Applies the selection table to the recording. Before calling this method ensure
        that `selection_table_file` has been set. You can also set `selection_table_file_id`
        but that requires a flush to the session before continuing.
        """
        raise NotImplementedError()

    @abstractmethod
    def selection_table_data_delete(self):
        """Delete the data from the recording's selections that was provided by the selection table.
        Will not delete any selections themselves."""
        raise NotImplementedError()

    @abstractmethod
    def selection_table_export(self):
        """Export the selection table to a CSV or TSV file."""

    @property
    @abstractmethod
    def start_time_pretty(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def relative_directory(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def folder_name(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def recording_file_name(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def selection_table_file_name(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def selection_count(self):
        """Returns the number of selections in the recording."""
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def selection_file_count(self):
        """Returns the number of selection files in the recording."""
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def contour_file_count(self):
        """Returns the number of contour files in the recording."""
        raise NotImplementedError()
    
    @abstractmethod
    def is_reviewed(self):
        """Returns True if the recording has been reviewed, otherwise False."""
        raise NotImplementedError()

    @abstractmethod
    def is_on_hold(self):
        """Returns True if the recording has been on hold, otherwise False."""
        raise NotImplementedError()

    @abstractmethod
    def is_awaiting_review(self):
        """Returns True if the recording is awaiting review, otherwise False."""
        raise NotImplementedError()
    
    @abstractmethod
    def is_in_progress(self):
        """Returns True if the recording is in progress, otherwise False."""
        raise NotImplementedError()
    
    @abstractmethod
    def is_unassigned(self):
        """Returns True if the recording is unassigned, otherwise False."""
        raise NotImplementedError()
    
    def _update_status(self, assignments):
        """Helper method to `update_status`."""
        raise NotImplementedError()

    @abstractmethod
    def update_status(self) -> bool:
        """Update the `status` and `status_change_datetime` of the recording based on the recording's current assignments.
        Returns True if the status was changed, False otherwise.
        
        If the recording is has assignments that have not been completed the status will be set to `In Progress`.
        If the recording has no assignments the status will be set to `Unassigned`.
        If the recording has assignments that have all been completed the status will be set to `Awaiting Review`.
        Regardless of any of the above conditions if the status is on `On Hold` or `Reviewed` it will not change.
        """
        raise NotImplementedError()
    
    @abstractmethod
    def get_selections(self, session):
        """Returns an ordered list of `Selection` objects that are associated with the recording."""
        raise NotImplementedError()

    @abstractmethod
    def update_selection_traced_status(self, session):
        """Updates the `traced` status of the `Selection` objects that are associated with the recording. 
        Does not commit the session automatically. Does not make changes to the session."""
        raise NotImplementedError()

class ISelection(AbstractModelBase, Serialisable, TableOperations, Cascading):
    __tablename__ = 'selection'

    id = Column(String(36), primary_key=True, nullable=False, server_default="UUID()")
    selection_number = Column(Integer, nullable=False)
    selection_file_id = Column(String(36), database_handler.db.ForeignKey('file.id'), nullable=False)
    recording_id = Column(String(36), database_handler.db.ForeignKey('recording.id'), nullable=False)
    contour_file_id = Column(String(36), database_handler.db.ForeignKey('file.id'))
    ctr_file_id = Column(String(36), database_handler.db.ForeignKey('file.id'))
    sampling_rate = Column(Float)
    traced = Column(Boolean, nullable=True, default=None)
    deactivated = Column(Boolean, nullable=False, default=False)
    row_start = Column(DateTime(timezone=True), server_default="current_timestamp()")
    default_fft_size = Column(Integer)
    default_hop_size = Column(Integer)
    created_datetime = Column(DateTime(timezone=True), nullable=False, server_default="current_timestamp()")

    ### Selection Table data ###
    view = Column(Text)
    channel = Column(Integer)
    begin_time = Column(Float)
    end_time = Column(Float)
    low_frequency = Column(Float)
    high_frequency = Column(Float)
    delta_time = Column(Float)
    delta_frequency = Column(Float)
    average_power = Column(Float)
    annotation = Column(Text)

    ### Contour Statistics data ###
    freq_max = Column(Float, nullable=True, default=None)
    freq_min = Column(Float, nullable=True, default=None)
    duration = Column(Float, nullable=True, default=None)
    freq_begin = Column(Float, nullable=True, default=None)
    freq_end = Column(Float, nullable=True, default=None)
    freq_range = Column(Float, nullable=True, default=None)
    dc_mean = Column(Float, nullable=True, default=None)
    dc_standarddeviation = Column(Float, nullable=True, default=None)
    freq_mean = Column(Float, nullable=True, default=None)
    freq_standarddeviation = Column(Float, nullable=True, default=None)
    freq_median = Column(Float, nullable=True, default=None)
    freq_center = Column(Float, nullable=True, default=None)
    freq_relbw = Column(Float, nullable=True, default=None)
    freq_maxminratio = Column(Float, nullable=True, default=None)
    freq_begendratio = Column(Float, nullable=True, default=None)
    freq_quarter1 = Column(Float, nullable=True, default=None)
    freq_quarter2 = Column(Float, nullable=True, default=None)
    freq_quarter3 = Column(Float, nullable=True, default=None)
    freq_spread = Column(Float, nullable=True, default=None)
    dc_quarter1mean = Column(Float, nullable=True, default=None)
    dc_quarter2mean = Column(Float, nullable=True, default=None)
    dc_quarter3mean = Column(Float, nullable=True, default=None)
    dc_quarter4mean = Column(Float, nullable=True, default=None)
    freq_cofm = Column(Float, nullable=True, default=None)
    freq_stepup = Column(Integer, nullable=True, default=None)
    freq_stepdown = Column(Integer, nullable=True, default=None)
    freq_numsteps = Column(Integer, nullable=True, default=None)
    freq_slopemean = Column(Float, nullable=True, default=None)
    freq_absslopemean = Column(Float, nullable=True, default=None)
    freq_posslopemean = Column(Float, nullable=True, default=None)
    freq_negslopemean = Column(Float, nullable=True, default=None)
    freq_sloperatio = Column(Float, nullable=True, default=None)
    freq_begsweep = Column(Integer, nullable=True, default=None)
    freq_begup = Column(Integer, nullable=True, default=None)
    freq_begdown = Column(Integer, nullable=True, default=None)
    freq_endsweep = Column(Integer, nullable=True, default=None)
    freq_endup = Column(Integer, nullable=True, default=None)
    freq_enddown = Column(Integer, nullable=True, default=None)
    num_sweepsupdown = Column(Integer, nullable=True, default=None)
    num_sweepsdownup = Column(Integer, nullable=True, default=None)
    num_sweepsupflat = Column(Integer, nullable=True, default=None)
    num_sweepsdownflat = Column(Integer, nullable=True, default=None)
    num_sweepsflatup = Column(Integer, nullable=True, default=None)
    num_sweepsflatdown = Column(Integer, nullable=True, default=None)
    freq_sweepuppercent = Column(Float, nullable=True, default=None)
    freq_sweepdownpercent = Column(Float, nullable=True, default=None)
    freq_sweepflatpercent = Column(Float, nullable=True, default=None)
    num_inflections = Column(Integer, nullable=True, default=None)
    inflection_maxdelta = Column(Float, nullable=True, default=None)
    inflection_mindelta = Column(Float, nullable=True, default=None)
    inflection_maxmindelta = Column(Float, nullable=True, default=None)
    inflection_mediandelta = Column(Float, nullable=True, default=None)
    inflection_meandelta = Column(Float, nullable=True, default=None)
    inflection_standarddeviationdelta = Column(Float, nullable=True, default=None)
    inflection_duration = Column(Float, nullable=True, default=None)
    step_duration = Column(Float, nullable=True, default=None)
    
    contour_file = database_handler.db.relationship("File", foreign_keys=[contour_file_id])
    selection_file = database_handler.db.relationship("File", foreign_keys=[selection_file_id])
    recording = database_handler.db.relationship("Recording", foreign_keys=[recording_id])
    ctr_file = database_handler.db.relationship("File", foreign_keys=[ctr_file_id])
    
    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        database_handler.db.UniqueConstraint('selection_number', 'recording_id', name='unique_selection_number_recording'),
        {"mysql_engine": "InnoDB", "mysql_charset": "latin1", "mysql_collate": "latin1_swedish_ci"}
    )

    @validates('selection_number')
    def _validate_int(self, key, value):
        return utils.validate_int(value, field=key, allow_none=False)
    
    @validates(
        'default_fft_size',
        'default_hop_size',
        'channel',
        'freq_stepup',
        'freq_stepdown',
        'freq_numsteps',
        'freq_begsweep',
        'freq_begup',
        'freq_begdown',
        'freq_endsweep',
        'freq_endup',
        'freq_enddown',
        'num_sweepsupdown',
        'num_sweepsdownup',
        'num_sweepsupflat',
        'num_sweepsdownflat',
        'num_sweepsflatup',
        'num_sweepsflatdown',
        'num_inflections',
        )
    def _validate_int_nullable(self, key, value):
        return utils.validate_int(value, field=key, allow_none=True)

    @validates('recording_id')
    def _validate_uuid(self, key, value):
        return utils.validate_id(value, field=key, allow_none=False)

    @validates('selection_file_id', 'contour_file_id', 'ctr_file_id', 'updated_by_id')
    def _validate_uuid_nullable(self, key, value):
        return utils.validate_id(value, field=key, allow_none=True)

    @validates(
        'sampling_rate',
        'begin_time',
        'end_time',
        'low_frequency',
        'high_frequency',
        'delta_time',
        'delta_frequency',
        'average_power',
        'freq_max',
        'freq_min',
        'duration',
        'freq_begin',
        'freq_end',
        'freq_range',
        'dc_mean',
        'dc_standarddeviation',
        'freq_mean',
        'freq_standarddeviation',
        'freq_median',
        'freq_center',
        'freq_relbw',
        'freq_maxminratio',
        'freq_begendratio',
        'freq_quarter1',
        'freq_quarter2',
        'freq_quarter3',
        'freq_spread',
        'dc_quarter1mean',
        'dc_quarter2mean',
        'dc_quarter3mean',
        'dc_quarter4mean',
        'freq_cofm',
        'freq_slopemean',
        'freq_absslopemean',
        'freq_posslopemean',
        'freq_negslopemean',
        'freq_sloperatio',
        'freq_sweepuppercent',
        'freq_sweepdownpercent',
        'freq_sweepflatpercent',
        'inflection_maxdelta',
        'inflection_mindelta',
        'inflection_maxmindelta',
        'inflection_mediandelta',
        'inflection_meandelta',
        'inflection_standarddeviationdelta',
        'inflection_duration',
        'step_duration',
    )
    def _validate_float_nullable(self, key, value):
        return utils.validate_float(value=value, field=key, allow_none=True)

    @validates("view")
    def _validate_str_nullable(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)

    @validates("annotation")
    def _validate_annotation(self, key, value):
        def prepare(string):
            if string is None: return None
            return str(string).upper()
        return utils.validate_enum(value=value, field=key, enum=["Y","M","N"], prepare=prepare, allow_none=True)

    @validates('deactivated')
    def _validate_bool(self, key, value):
        return utils.validate_boolean(value=value, field=key, allow_none=False)
    
    @validates('traced')
    def _validate_bool_nullable(self, key, value):
        return utils.validate_boolean(value=value, field=key, allow_none=True)

    @property
    def row_start_pretty(self):
        return utils.pretty_date(self.row_start)

    @property
    def created_datetime_pretty(self):
        return utils.pretty_date(self.created_datetime)

    def _to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            'unique_name':self.unique_name,
            'selection_number':self.selection_number,
            'selection_file':self.selection_file,
            'selection_file_id':self.selection_file_id,
            'ctr_file':self.ctr_file,
            'ctr_file_id':self.ctr_file_id,
            'contour_file':self.contour_file,
            'contour_file_id':self.contour_file,
            'recording_id':self.recording_id,
            'created_datetime':self.created_datetime,
            'row_start':self.row_start
        }
    
    def _form_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            'selection_number':True,
        }

    @staticmethod
    def get_contour_statistics_attrs() -> typing.Dict[str,type]:
        """A dictionary of all the contour statistics attribute names (string) as the key and
        a tuple of the the attribute data type and the column name and a boolean as the value.
        The boolean is meant to indicate whether the attribute should be included on the selection
        table or not.
        """
        return {
            "freq_max": (float, "FREQMAX", True),
            "freq_min": (float, "FREQMIN", True),
            "duration": (float, "DURATION", True),
            "freq_begin": (float, "FREQBEG", True),
            "freq_end": (float, "FREQEND", True),
            "freq_range": (float, "FREQRANGE", True),
            "dc_mean": (float, "DCMEAN", True),
            "dc_standarddeviation": (float, "DCSTDDEV", True),
            "freq_mean": (float, "FREQMEAN", True),
            "freq_standarddeviation": (float, "FREQSTDDEV", True),
            "freq_median": (float, "FREQMEDIAN", True),
            "freq_center": (float, "FREQCENTER", True),
            "freq_relbw": (float, "FREQRELBW", True),
            "freq_maxminratio": (float, "FREQMAXMINRATIO", True),
            "freq_begendratio": (float, "FREQBEGENDRATIO", True),
            "freq_quarter1": (float, "FREQQUARTER1", True),
            "freq_quarter2": (float, "FREQQUARTER2", True),
            "freq_quarter3": (float, "FREQQUARTER3", True),
            "freq_spread": (float, "FREQSPREAD", True),
            "dc_quarter1mean": (float, "DCQUARTER1MEAN", True),
            "dc_quarter2mean": (float, "DCQUARTER2MEAN", True),
            "dc_quarter3mean": (float, "DCQUARTER3MEAN", True),
            "dc_quarter4mean": (float, "DCQUARTER4MEAN", True),
            "freq_cofm": (float, "FREQCOFM", True),
            "freq_stepup": (int, "FREQSTEPUP", True),
            "freq_stepdown": (int, "FREQSTEPDOWN", True),
            "freq_numsteps": (int, "FREQNUMSTEPS", True),
            "freq_slopemean": (float, "FREQSLOPEMEAN", True),
            "freq_absslopemean": (float, "FREQABSSLOPEMEAN", True),
            "freq_posslopemean": (float, "FREQPOSSLOPEMEAN", True),
            "freq_negslopemean": (float, "FREQNEGSLOPEMEAN", True),
            "freq_sloperatio": (float, "FREQSLOPERATIO", True),
            "freq_begsweep": (int, "FREQBEGSWEEP", True),
            "freq_begup": (int, "FREQBEGUP", True),
            "freq_begdown": (int, "FREQBEGDWN", True),
            "freq_endsweep": (int, "FREQENDSWEEP", True),
            "freq_endup": (int, "FREQENDUP", True),
            "freq_enddown": (int, "FREQENDDWN", True),
            "num_sweepsupdown": (int, "NUMSWEEPSUPDWN", True),
            "num_sweepsdownup": (int, "NUMSWEEPSDWNUP", True),
            "num_sweepsupflat": (int, "NUMSWEEPSUPFLAT", True),
            "num_sweepsdownflat": (int, "NUMSWEEPSDWNFLAT", True),
            "num_sweepsflatup": (int, "NUMSWEEPSFLATUP", True),
            "num_sweepsflatdown": (int, "NUMSWEEPSFLATDWN", True),
            "freq_sweepuppercent": (float, "FREQSWEEPUPPERCENT", True),
            "freq_sweepdownpercent": (float, "FREQSWEEPDWNPERCENT", True),
            "freq_sweepflatpercent": (float, "FREQSWEEPFLATPERCENT", True),
            "num_inflections": (int, "NUMINFLECTIONS", True),
            "inflection_maxdelta": (float, "INFLMAXDELTA", True),
            "inflection_mindelta": (float, "INFLMINDELTA", True),
            "inflection_maxmindelta": (float, "INFLMAXMINDELTA", True),
            "inflection_mediandelta": (float, "INFLMEDIANDELTA", True),
            "inflection_meandelta": (float, "INFLMEANDELTA", True),
            "inflection_standarddeviationdelta": (float, "INFLSTDDEVDELTA", True),
            "inflection_duration": (float, "INFLDUR", True),
            "step_duration": (float, "STEPDUR", True),
        }

    @abstractmethod
    def selection_file_delete(self):
        """Delete the selection file associated with the selection. The session used to call
        this method needs to be committed by the caller."""
        raise NotImplementedError

    @abstractmethod
    def selection_file_insert(self, session, stream):
        """Insert a file (given as a stream) into `selection_file`. If it is already populated
        raise `exception_handler.WarningException`. If not, insert it. Note that the session used
        to call this method needs to be committed by the caller. The new file will be automatically
        added to the provided session, but not comitted."""
        raise NotImplementedError

    @abstractmethod
    def contour_file_insert(self, session, stream):
        """Insert a file (given as a stream) into `contour_file`. If it is already populated
        raise `exception_handler.WarningException`. If not, insert it. Note that the session used
        to call this method needs to be committed by the caller. The new file will be automatically
        added to the provided session, but not comitted."""
        raise NotImplementedError
    
    @abstractmethod
    def ctr_file_delete(self):
        """Delete the CTR file associated with the selection. The session used to call
        this method needs to be committed by the caller."""
        raise NotImplementedError

    @abstractmethod
    def ctr_file_generate(self):
        """Generate a file made of the data in `contour_file`. If it is already populated
        raise `exception_handler.WarningException`. If not, generate it. Note that the session used
        to call this method needs to be committed by the caller. If a CTR file already exists, it
        is first deleted before being regenerated. The new file will be automatically
        added to the provided session, but not comitted."""
        raise NotImplementedError

    def get_contour_statistics_dict(self, use_headers=False) -> typing.Dict[str, typing.Any]:
        """A dictionary of all the contour statistics attribute names (string) as the key and the
        attribute data types as the value. This does not include `selection_number` as this
        attribute pertains to the entire `Selection` object. If `use_headers` is True, the
        attribute names will be the header names in the CSV file. If `use_headers` is False,
        the attribute names will be the attribute names of the object."""
        d = {}
        for k, v in ISelection.get_contour_statistics_attrs().items():
            if v[2] and not use_headers: d[k] = getattr(self, k)
            elif v[2] and use_headers: d[v[1]] = getattr(self, k)
        return d

    @property
    def selection_table_attrs(self) -> typing.Dict[str, type]:
        """A dictionary of all the selection table attribute names (string) as the key and the
        attribute data types as the value. This does not include `selection_number` as this
        attribute pertains to the entire `Selection` object."""
        return {
            "view": str,
            "channel": int,
            "begin_time": float,
            "end_time": float,
            "low_frequency": float,
            "high_frequency": float,
            "delta_time": float,
            "delta_frequency": float,
            "average_power": float,
            "annotation": str,
        }

    @staticmethod
    def contour_file_attrs():
        """A dictionary of all the contour file attribute names (string) as the key and the
        attribute data types as the value."""
        return {
            'time_milliseconds': (int, 'Time [ms]', False),
            'peak_frequency': (float, 'Peak Frequency [Hz]', False),
            'duty_cycle': (float, 'Duty Cycle', False),
            'energy': (float, 'Energy', False),
            'window_RMS': (float, 'WindowRMS', False)
        }

    @property
    @abstractmethod
    def unique_name(self):
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def relative_directory(self):
        raise NotImplementedError
    
    @property
    @abstractmethod
    def selection_file_name(self):
        raise NotImplementedError
    
    @property
    @abstractmethod
    def contour_file_name(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def ctr_file_name(self):
        raise NotImplementedError

    @property
    def plot_file_name(self):
        raise NotImplementedError

    @abstractmethod
    def contour_file_insert(self, session, file_stream):
        """Insert a file (given as a stream) into `contour_file`. If it is already populated
        raise `exception_handler.WarningException`. If not, insert it. The new file will already
        be added to the session, but not comitted. This method automatically generates the CTR
        file."""
        raise NotImplementedError

    @abstractmethod
    def contour_file_delete(self, session):
        """Delete the contour file associated with the selection. The session used to call
        this method needs to be committed by the caller. This will also remove any associated
        CTR file."""
        raise NotImplementedError

    @abstractmethod
    def contour_statistics_calculate(self):
        """Calculate contour statistics. Raises `ValueError` in the event of an error."""
        raise NotImplementedError()
    
    @abstractmethod
    def clear_contour_statistics_attrs(self):
        """Clear all the contour statistics (by setting them to None). Note that this does not
        impact the `contour_file` file itself."""
        raise NotImplementedError()
    
    @abstractmethod
    def _calculate_sampling_rate(self):
        """Calculate the sampling rate of the `selection_file` associated with the object.
        If there is no `selection_file` raise `exception_handler.WarningException`."""
        raise NotImplementedError()

    @abstractmethod
    def deactivate(self):
        """Deactivate the selection. This involves resetting the value of `traced` to `None`."""
        raise NotImplementedError()
    
    @abstractmethod
    def reactivate(self):
        """Reactivate the selection. This involves resetting the value of `traced` to `None`."""

    @abstractmethod
    def clear_selection_table_attrs(self) -> None:
        """Clear all the selection table attributes (by setting them to `None`). Note that this
        does not impact the `selection_table_file` file itself."""
        raise NotImplementedError()
    
    @abstractmethod
    def update_traced(self):
        """Determine and set the value of `traced` based on the `contour_file` and `annotation`.
        'traced' is an attribute that tracks whether the selection has DEFINITELY been traced
        (`traced = True`) or DEFINITELY NOT been traced (`traced = False`). If the traced status
        of the selection is UNDETERMINED then `traced = None`.


        - `True` if there is a `contour_file` and `annotation` is `Y` or `M`.
        - `False` if there is not a `contour_file` and `annotation` is `N`.
        - `None` otherwise or if `annotation` has no value.
        """
        raise NotImplementedError()

    # TODO: create interface for ContourFileHandler
    from ..contour_statistics import ContourFileHandler

    @abstractmethod
    def get_contour_file_handler(self) -> ContourFileHandler:
        """If the `contour_file` exists then read the contents into a `contour_statistics.ContourFileHandler` object.
        Data validation errors (such as formatting of the contour file) are raised as `exception_handler.WarningException`
        exceptions. If the contour file does not exist the the function returns `None`."""
        raise NotImplementedError()

    @abstractmethod
    def generate_contour_stats_dict(self):
        """Generate a dictionary of the object's contour statistics. Returns `None` if the contour
        file does not exist. The dictionary contains all the headers of `self.contour_statistics_attrs`
        as the header and values as the value."""
        raise NotImplementedError()

class IUser(AbstractModelBase, Serialisable, TableOperations, UserMixin):
    """Abstract class for the SQLAlchemy table user.
    
    Abstract class implementation is inforced using ABC. 
    Inherits from `Serialisable` and `UserMixin`.

    Implementation for the following is required:
    - `activate()`
    - `deactivate()`
    """
    
    __tablename__ = 'user'
    __table_args__ = (database_handler.db.PrimaryKeyConstraint('id'),)

    id = Column(String(36), primary_key=True, nullable=False, server_default="UUID()")
    login_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(1000), nullable=True)
    role_id = Column(Integer, database_handler.db.ForeignKey('role.id'), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expiry = Column(DateTime(timezone=True), nullable=False)
    role = database_handler.db.relationship('Role', backref='users', lazy=True)

    @property
    def unique_name(self):
        """The login ID"""
        return self.login_id

    def _to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'login_id': self.login_id,
            'role_id': self.role_id,
            'role': self.role
        }
    
    def _form_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            'name': True,
            'login_id': False,
            'role_id': True,
            'expiry': True,
            'is_active': False
        }

    @validates("id")
    def validate_id(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=False)

    @validates("login_id")
    def validate_login_id(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)

    @validates("name")
    def validate_name(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)
    
    @validates("is_active")
    def validate_is_active(self, key, value):
        return utils.validate_boolean(value=value, field=key, allow_none=False)

    @validates("expiry")
    def validate_expiry(self, key, value):
        return utils.validate_datetime(value=value, field=key, allow_none=False)

    @validates("role_id")
    def validate_role_id(self, key, value):
        return utils.validate_int(value=value, field=key, allow_none=False)
    
    @validates("role")
    def validate_role(self, key, value):
        # TODO: implement
        return value

    @property
    def pretty_expiry(self) -> str:
        """Get the expiry date in a human readable format."""
        return utils.pretty_date(self.expiry)

    @abstractmethod
    def activate(self) -> None:
        """Activate the user."""
        raise NotImplementedError()

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the user."""
        raise NotImplementedError()

class IDataSource(AbstractModelBase, Serialisable, TableOperations):
    __tablename__ = 'data_source'

    id = Column(String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = Column(String(255))
    phone_number1 = Column(String(20), unique=True)
    phone_number2 = Column(String(20), unique=True)
    email1 = Column(String(255), nullable=False, unique=True)
    email2 = Column(String(255), unique=True)
    address = Column(Text)
    notes = Column(Text)
    type = Column(database_handler.db.Enum('person', 'organisation'))

    updated_by_id = Column(String(36), database_handler.db.ForeignKey('user.id'))
    updated_by = database_handler.db.relationship("User", foreign_keys=[updated_by_id])

    def _form_dict(self):
        return {
            'name': False,
            'phone_number1': False,
            'phone_number2': False,
            'email1': True,
            'email2': False,
            'address': False,
            'notes': False,
            'type': False
        }
    
    def _to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone_number1': self.phone_number1,
            'phone_number2': self.phone_number2,
            'email1': self.email1,
            'email2': self.email2,
            'address': self.address,
            'notes': self.notes,
            'type': self.type,
            'updated_by_id': self.updated_by_id,
        }

    @validates("id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=False)
    
    @validates("updated_by_id")
    def _validate_id_nullable(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=True)

    @validates("email1")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)

    @validates("name", "phone_number1", "phone_number2", "email2", "address", "notes")
    def _validate_str_nullable(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=True)

    @validates("type")
    def _validate_type(self, key, value):
        return utils.validate_enum(value=value, field=key, enum=['person', 'organisation'])

class IRole(AbstractModelBase):
    __tablename__ = 'role'
    
    # Identifier
    id = Column(Integer, primary_key=True)
    # Metadata
    name = Column(String(100))
    
    @validates("id")
    def _validate_id(self, key, value):
        return utils.validate_int(value=value, field=key, allow_none=False)
    
    @validates("name")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)

class IAssignment(AbstractModelBase, Serialisable, TableOperations):
    __tablename__ = 'assignment'
    
    user_id = Column(String(36), database_handler.db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recording_id = Column(String(36), database_handler.db.ForeignKey('recording.id'), primary_key=True, nullable=False)
    row_start = Column(DateTime(timezone=True), server_default="current_timestamp()")
    user = database_handler.db.relationship("User", foreign_keys=[user_id])
    recording = database_handler.db.relationship("Recording", foreign_keys=[recording_id])
    created_datetime = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    completed_flag = Column(Boolean, default=False)

    @validates("user_id", "recording_id")
    def _validate_id(self, key, value):
        return utils.validate_id(value=value, field=key, allow_none=False)
    
    @validates("created_datetime", "row_start")
    def _validate_datetime(self, key, value):
        raise AttributeError(f"Unable to set {key}")
    
    @validates("completed_flag")
    def _validate_completed_flag(self, key, value):
        return utils.validate_boolean(value=value, field=key, allow_none=False)

    @property
    def row_start_pretty(self):
        return utils.pretty_date(self.row_start)

    @property
    def created_datetime_pretty(self):
        return utils.pretty_date(self.created_datetime)

    @staticmethod
    def _form_dict():
        return {
            'user_id': True,
            'recording_id': True,
        }

    def _to_dict(self):
        return {
            "user_id": self.user_id,
            "user": self.user,
            "recording_id": self.recording_id,
            "recording": self.recording,
            "row_start": self.row_start,
            "completed_flag": self.completed_flag,
            "created_datetime": self.created_datetime
        }

    @abstractmethod
    def complete(self):
        """Mark the assignment as completed."""
        raise NotImplementedError()

    @abstractmethod
    def incomplete(self):
        """Mark the assignment as incomplete."""
        raise NotImplementedError()