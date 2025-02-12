from flask_restful import Resource, reqparse, marshal_with, fields
from flask import Response
from ... import models

selection_resource_fields = {
    'recording_id': fields.String,
    'selection_number': fields.Integer
}

parser = reqparse.RequestParser()
parser.add_argument('recording_id', type=str, help='Filter selections by recording_id', required=False, location='args')
parser.add_argument('selection_number', type=int, help='Filter selections by selection_number', required=False, location='args')

def create_filter_kwargs(**kwargs):
    filter_kwargs = {}
    for key, value in kwargs.items():
        if value is not None:
            filter_kwargs[key] = value
    return filter_kwargs

class SelectionResource(Resource):
    def get(self, **kwargs):
        args = parser.parse_args()
        filters = create_filter_kwargs(selection_number=args.get('selection_number'), recording_id=args.get('recording_id'))
        selections = models.Selection.query.filter_by(**filters).all()
        return [selection.to_dict() for selection in selections]
    
file_resource_parser = reqparse.RequestParser()
file_resource_parser.add_argument('id', type=str, required=True, location='args')

spectrogram_resource_parser = reqparse.RequestParser()
spectrogram_resource_parser.add_argument('selection_id', type=str, required=True, location='args')

class SpectrogramResource(Resource):
    def get(self):
        args = spectrogram_resource_parser.parse_args()
        selection = models.Selection.query.filter_by(id = args.get('selection_id')).first()
        plot_bytestream = selection.create_temp_plot()
        r = Response(plot_bytestream, mimetype='image/png')
        r.headers['Content-Disposition'] = f'attachment; filename="{selection.plot_file_name}.png"'
        return r

class FileResource(Resource):
    def get(self):
        args = file_resource_parser.parse_args()
        file_id = args.get('id')
        file = models.File.query.filter_by(id=file_id).first()
        from ... import utils
        return utils.download_file(file, mimetype='audio/wav')
