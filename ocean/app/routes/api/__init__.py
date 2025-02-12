from flask_restx import Api
from flask import Blueprint
from .metadata_api import api as ns1
from .filespace_api import api as ns2
from ... import exception_handler

# api = Api(
#     title='OCEAN API',
#     version='1.0',
#     description='An API to access data from OCEAN',
# )

blueprint = Blueprint('api', __name__)
api = Api(blueprint)


api.add_namespace(ns1)
api.add_namespace(ns2)

@api.errorhandler(exception_handler.DoesNotExistError)
def handle_dne_exception(error):
    return {'message': 'Requested resource does not exist with the defined paramters.'}, 404

@api.errorhandler(exception_handler.WarningException)
def handle_warning_exception(error):
    return {'message': error.message}, 400

@api.errorhandler(Exception)
def handle_root_exception(error):
    return {'message': 'Server error'}, 500