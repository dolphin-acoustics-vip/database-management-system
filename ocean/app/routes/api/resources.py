from flask_restful import Resource, reqparse, marshal_with, fields
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