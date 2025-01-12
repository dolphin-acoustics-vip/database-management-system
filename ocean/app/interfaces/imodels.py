# INTERFACES FOR MODELS

from abc import ABC, ABCMeta, abstractmethod
from typing import Protocol
from uuid import UUID
from sqlalchemy.ext.declarative import declared_attr
from flask_login import UserMixin
from .. import database_handler
from sqlalchemy.orm import validates
from .. import utils
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
import typing

# Combine ABCMeta and SQLAlchemy's DeclarativeMeta
class CombinedMeta(ABCMeta, type(database_handler.db.Model)):
    pass


class IRecordingPlatform(database_handler.db.Model, metaclass=CombinedMeta):
    __abstract__ = True
    __table_args__ = (database_handler.db.PrimaryKeyConstraint('id'),)

    id = database_handler.db.Column('id',database_handler.db.String(36), primary_key=True, nullable=False, server_default="UUID()")
    name = database_handler.db.Column('name',database_handler.db.String(100), unique=True, nullable=False)
    updated_by_id = database_handler.db.Column('updated_by_id',database_handler.db.String(36), database_handler.db.ForeignKey('user.id'))

    @declared_attr
    def updated_by(cls):
        return database_handler.db.relationship("User", foreign_keys=[cls.updated_by_id])

    @validates("id", "updated_by_id")
    def validate_id(self, key, value):
        """`id` and `updated_by_id` must be a valid UUID"""
        return utils.validate_id(value=value, field="ID", allow_none=False)

    @validates("name")
    def validate_name(self, key, value):
        """`name` must be a non-empty string"""
        return utils.validate_string(value=value, field="Name", allow_none=False)

    @abstractmethod
    def to_dict(self) ->typing.Dict[str, typing.Any]:
        pass