from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
from flask import send_from_directory

from ... import database_handler
from . import resources

def register(api, prefix):
    prefix = str(prefix)
    if str(prefix).endswith('/'):
        prefix = str(prefix)[:-1]
    if not str(prefix).endswith('api'):
        prefix = prefix + "/" + 'api'
    api.add_resource(resources.Selections, prefix + '/selections/')