from flask_restx import Api
from flask import Blueprint
from .metadata_api import api as ns1
from .filespace_api import api as ns2

# api = Api(
#     title='OCEAN API',
#     version='1.0',
#     description='An API to access data from OCEAN',
# )

blueprint = Blueprint('api', __name__)
api = Api(blueprint)

api.add_namespace(ns1)
api.add_namespace(ns2)