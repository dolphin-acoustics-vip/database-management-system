from flask_restx import Resource, reqparse, marshal_with, fields, Namespace
from flask import Response
from ... import models

api = Namespace('metadata', 'All endpoints that serve data from OCEAN to the user' )

def create_filter_kwargs(**kwargs):
    filter_kwargs = {}
    for key, value in kwargs.items():
        if value is not None:
            filter_kwargs[key] = value
    return filter_kwargs

selection_parser = reqparse.RequestParser()
selection_parser.add_argument('recording_id', type=str, help='Filter selections by recording_id', required=False, location='args')
selection_parser.add_argument('selection_number', type=int, help='Filter selections by selection_number', required=False, location='args')
@api.route('/selections/')
class SelectionResource(Resource):
    @api.expect(selection_parser)
    def get(self):
        args = selection_parser.parse_args()
        filters = create_filter_kwargs(selection_number=args.get('selection_number'), recording_id=args.get('recording_id'))
        selections = models.Selection.query.filter_by(**filters).all()
        return [selection.to_dict() for selection in selections]

spectrogram_resource_parser = reqparse.RequestParser()
spectrogram_resource_parser.add_argument('selection_id', type=str, required=True, location='args')
@api.route('/spectrogram/')
class SpectrogramResource(Resource):
    @api.expect(spectrogram_resource_parser)
    def get(self):
        args = spectrogram_resource_parser.parse_args()
        selection = models.Selection.query.filter_by(id = args.get('selection_id')).first()
        plot_bytestream = selection.create_temp_plot()
        r = Response(plot_bytestream, mimetype='image/png')
        r.headers['Content-Disposition'] = f'attachment; filename="{selection.plot_file_name}.png"'
        return r

