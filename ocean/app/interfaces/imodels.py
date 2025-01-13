# INTERFACES FOR MODELS

from abc import ABC, ABCMeta, abstractmethod
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

    def prepare_for_delete(self):
        """Check if the object can be deleted. Raise an exception if it
        cannot be deleted.
        
        An exception is raised usually if the object has foreign key
        dependencies that are not allowed to be automatically resolved.
        This will cause an `exception_handler.WarningException` to be raised
        """
        pass

class Cascading(ABC):
    
    @abstractmethod
    def _get_children(self):
        """Return a list of child objects of this obejct (also known as foreign key
        dependencies). The exact datatype of child objects will vary by implementation
        of this method.
        """
        pass

    @abstractmethod
    def apply_updates(self):
        """Apply changes to this object and invoke updates on related objects. 
        
        This method should be called whenever a piece of metadata changes (either in
        this object or one of its parents). This method should ensure that any data
        in this object that rely on its parents metadata are updated accordingly.
        """
        pass

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