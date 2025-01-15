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
from sqlalchemy import Column, Integer, String, Boolean, DateTime
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
    file_timezone = Column(database_handler.db.Integer)
    local_timezone = Column(database_handler.db.Integer)
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
    notes = Column(database_handler.db.Text)
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
        return utils.validate_enum(value=value, field=key, enum=['Unassigned','In Progress','Awaiting Review','Reviewed','On Hold'])

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
        pass

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the user."""
        pass

class IDataSource(AbstractModelBase, Serialisable, TableOperations):
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
    id = database_handler.db.Column(database_handler.db.Integer, primary_key=True)
    # Metadata
    name = database_handler.db.Column(database_handler.db.String(100))
    
    @validates("id")
    def _validate_id(self, key, value):
        return utils.validate_int(value=value, field=key, allow_none=False)
    
    @validates("name")
    def _validate_str(self, key, value):
        return utils.validate_string(value=value, field=key, allow_none=False)

class IAssignment(AbstractModelBase, Serialisable, TableOperations):
    __tablename__ = 'assignment'
    
    user_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('user.id'), primary_key=True, nullable=False)
    recording_id = database_handler.db.Column(database_handler.db.String(36), database_handler.db.ForeignKey('recording.id'), primary_key=True, nullable=False)
    row_start = Column(DateTime(timezone=True), server_default="current_timestamp()")
    user = database_handler.db.relationship("User", foreign_keys=[user_id])
    recording = database_handler.db.relationship("Recording", foreign_keys=[recording_id])
    created_datetime = database_handler.db.Column(database_handler.db.DateTime(timezone=True), nullable=False, server_default="NOW()")
    completed_flag = database_handler.db.Column(database_handler.db.Boolean, default=False)

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