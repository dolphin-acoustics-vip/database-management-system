from flask_restx import Resource, reqparse, marshal_with, fields, Namespace
from flask import Response, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from ... import utils, exception_handler, models

api = Namespace('filespace', 'All endpoints that serve files from OCEAN to the user' )

SECURITY_KEY = "jsonWebToken"

responses = {
    200: 'Success',
    400: 'Bad Request',
    401: 'Unauthorized',
    404: 'Not Found',
    500: 'Internal Server Error'
}

file_resource_parser = reqparse.RequestParser()
file_resource_parser.add_argument('id', type=str, required=True, location='args')
@api.route('/file/')
class FileResource(Resource):
    method_decorators = [jwt_required()]

    @api.expect(file_resource_parser)
    @api.doc(security=SECURITY_KEY)
    def get(self):
        args = file_resource_parser.parse_args()
        file_id = args.get('id')
        file = models.File.query.filter_by(id=file_id).first()
        return utils.download_file(file, mimetype='audio/wav')


spectrogram_resource_parser = reqparse.RequestParser()
spectrogram_resource_parser.add_argument('selection_id', type=str, required=True, location='args')
@api.route('/spectrogram/')
class SpectrogramResource(Resource):
    method_decorators = [jwt_required()]
    @api.expect(spectrogram_resource_parser)
    @api.doc(responses=responses, security=SECURITY_KEY)
    def get(self):
        args = spectrogram_resource_parser.parse_args()
        selection = models.Selection.query.filter_by(id = args.get('selection_id')).first()
        if not selection: raise exception_handler.DoesNotExistError("Selection")
        plot_bytestream = selection.create_temp_plot()
        r = Response(plot_bytestream, mimetype='image/png')
        r.headers['Content-Disposition'] = f'attachment; filename="{selection.plot_file_name}.png"'
        return r
