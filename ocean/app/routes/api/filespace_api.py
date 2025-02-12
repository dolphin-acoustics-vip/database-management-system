from flask_restx import Resource, reqparse, marshal_with, fields, Namespace
from ... import models
from ... import utils

api = Namespace('filespace', 'All endpoints that serve files from OCEAN to the user' )

file_resource_parser = reqparse.RequestParser()
file_resource_parser.add_argument('id', type=str, required=True, location='args')
@api.route('/file/')
class FileResource(Resource):
    @api.expect(file_resource_parser)
    def get(self):
        args = file_resource_parser.parse_args()
        file_id = args.get('id')
        file = models.File.query.filter_by(id=file_id).first()
        return utils.download_file(file, mimetype='audio/wav')
