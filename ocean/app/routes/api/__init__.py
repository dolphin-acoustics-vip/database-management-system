from flask_restx import Api, apidoc
from flask import Blueprint, request, jsonify
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import InvalidSignatureError, ExpiredSignatureError
from .metadata_api import api as ns1
from .filespace_api import api as ns2
from .auth_api import api as ns3
from ... import exception_handler, models
from ...logger import logger
from ...main import CONFIG

# api = Api(
#     title='OCEAN API',
#     version='1.0',
#     description='An API to access data from OCEAN',
# )

authorizations = {
    "jsonWebToken": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Provide a valid Web Token using the /auth/login/ endpoint with your Username (usually email) and API Password (provided by administrators). A token is valid for only 15 minutes. Enter in the format 'Bearer <token>'."
    }
}

apidoc.apidoc.url_prefix = CONFIG.URL_PREFIX

blueprint = Blueprint('api', __name__)
api = Api(
    blueprint,
    version="1.0",
    title="OCEAN API",
    description="Welcome to the OCEAN API documentation site!",
    authorizations=authorizations
)

api.add_namespace(ns1)
api.add_namespace(ns2)
api.add_namespace(ns3)

@api.errorhandler(NoAuthorizationError)
def handle_no_authorization_error(error):
    return {'message': 'Missing Authorization Header'}, 401

@api.errorhandler(InvalidSignatureError)
def handle_invalid_signature_error(error):
    logger.error(error)
    return {'message': 'Invalid Signature in Authorization Header'}, 401

@api.errorhandler(ExpiredSignatureError)
def handle_expired_signature_error(error):
    logger.error(error)
    return {'message': 'Expired Signature in Authorization Header'}, 401

@api.errorhandler(exception_handler.DoesNotExistError)
def handle_dne_exception(error):
    logger.error(error)
    return {'message': 'Requested resource does not exist with the defined paramters.'}, 404

@api.errorhandler(exception_handler.WarningException)
def handle_warning_exception(error):
    return {'message': str(error)}, 400

@api.errorhandler(Exception)
def handle_root_exception(error):
    logger.error(error)
    return {'message': 'Server error'}, 500