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
        if (not file):
            raise exception_handler.DoesNotExistError("File")

        return utils.download_file(file, mimetype='audio/wav')

contour_csv_file_resource_parser = reqparse.RequestParser()
contour_csv_file_resource_parser.add_argument('selection_id', type=str, required=True, location='args')
@api.route('/file/contour/csv/')
class ContourCSVFileResource(Resource):
    method_decorators = [jwt_required()]

    @api.expect(contour_csv_file_resource_parser)
    @api.doc(security=SECURITY_KEY)
    def get(self):
        args = contour_csv_file_resource_parser.parse_args()
        selection_id = args.get('selection_id')
        selection = models.Selection.query.filter_by(id = selection_id).first()
        if (not selection):
            raise exception_handler.DoesNotExistError("Selection")

        if (not selection.contour_file):
            raise exception_handler.DoesNotExistError("Contour CSV File")

        return utils.download_file(selection.contour_file, selection.contour_file_name, mimetype='text/csv')

contour_ctr_file_resource_parser = reqparse.RequestParser()
contour_ctr_file_resource_parser.add_argument('selection_id', type=str, required=True, location='args')
@api.route('/file/contour/ctr/')
class ContourCTRFileResource(Resource):
    method_decorators = [jwt_required()]

    @api.expect(contour_ctr_file_resource_parser)
    @api.doc(security=SECURITY_KEY)
    def get(self):
        args = contour_ctr_file_resource_parser.parse_args()
        selection_id = args.get('selection_id')
        selection = models.Selection.query.filter_by(id = selection_id).first()
        if (not selection):
            raise exception_handler.DoesNotExistError("Selection")

        if (not selection.ctr_file):
            raise exception_handler.DoesNotExistError("Contour CTR File")

        return utils.download_file(selection.ctr_file, selection.ctr_file_name, mimetype='text/x-ctr')

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
