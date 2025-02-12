from flask_restx import Resource, reqparse, marshal_with, fields, Namespace, inputs
from flask import Response
from datetime import datetime
from ... import models
from ... import exception_handler

api = Namespace('metadata', 'All endpoints that serve data from OCEAN to the user' )

responses = {
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found',
    500: 'Internal Server Error'
}

PER_PAGE_DEFAULT = 50
PAGE_DEFAULT = 1

def create_filter_kwargs(**kwargs):
    filter_kwargs = {}
    for key, value in kwargs.items():
        if value is not None:
            filter_kwargs[key] = value
    return filter_kwargs

encounter_resource_parser = reqparse.RequestParser()
encounter_resource_parser.add_argument('encounter_name', type=str, help='Filter encounters by encounter_name', required=False, location='args')
encounter_resource_parser.add_argument('location', type=str, help='Filter encounters by location', required=False, location='args')
encounter_resource_parser.add_argument('project', type=str, help='Filter encounters by project', required=False, location='args')
encounter_resource_parser.add_argument('species_id', type=str, help='Filter encounters by species_id', required=False, location='args')
encounter_resource_parser.add_argument('per_page', type=int, help=f'Default {PER_PAGE_DEFAULT}', required=False, location='args')
encounter_resource_parser.add_argument('page', type=int, help=f'Default {PAGE_DEFAULT}', required=False, location='args')
encounter_resource_parser.add_argument('id', type=str, help='Filter encounters by id', required=False, location='args')
@api.route('/encounters/')
class EncounterResource(Resource):
    @api.expect(encounter_resource_parser)
    @api.doc(responses=responses)
    def get(self):
        args = encounter_resource_parser.parse_args()
        filters = create_filter_kwargs(id=args.get('id'), encounter_name=args.get('encounter_name'), location=args.get('location'), project=args.get('project'), species_id=args.get('species_id'))
        page = args.get('page', 1)
        per_page = args.get('per_page', 50)
        encounters = models.Encounter.query.filter_by(**filters).paginate(page=page, per_page=per_page)
        return [encounter.to_dict() for encounter in encounters]


selection_parser = reqparse.RequestParser()
selection_parser.add_argument('recording_id', type=str, help='Filter selections by recording_id', required=False, location='args')
selection_parser.add_argument('selection_number', type=int, help='Filter selections by selection_number', required=False, location='args')
selection_parser.add_argument('per_page', type=int, help=f'Default {PER_PAGE_DEFAULT}', required=False, location='args')
selection_parser.add_argument('page', type=int, help=f'Default {PAGE_DEFAULT}', required=False, location='args')
selection_parser.add_argument('id', type=str, help='Filter encounters by id', required=False, location='args')
@api.route('/selections/')
class SelectionResource(Resource):
    @api.expect(selection_parser)
    @api.doc(responses=responses)
    def get(self):
        args = selection_parser.parse_args()
        filters = create_filter_kwargs(id=args.get('id'), selection_number=args.get('selection_number'), recording_id=args.get('recording_id'))
        page = args.get('page', 1)
        per_page = args.get('per_page', 50)
        selections = models.Selection.query.filter_by(**filters).paginate(page=page, per_page=per_page)
        return [selection.to_dict() for selection in selections]

recording_resource_parser = reqparse.RequestParser()
recording_resource_parser.add_argument('encounter_id', type=str, help='Filter recordings by encounter_id', required=False, location='args')
recording_resource_parser.add_argument('start_time', type=inputs.datetime_from_iso8601, help='Filter recordings by start time (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM)', required=False, location='args')
recording_resource_parser.add_argument('per_page', type=int, help=f'Default {PER_PAGE_DEFAULT}', required=False, location='args')
recording_resource_parser.add_argument('page', type=int, help=f'Default {PAGE_DEFAULT}', required=False, location='args')
recording_resource_parser.add_argument('id', type=str, help='Filter encounters by id', required=False, location='args')
@api.route('/recordings/')
class RecordingResource(Resource):
    @api.expect(recording_resource_parser)
    @api.doc(responses=responses)
    def get(self):
        args = recording_resource_parser.parse_args()
        filters = create_filter_kwargs(id=args.get('id'), encounter_id=args.get('encounter_id'), start_time=args.get('start_time'))
        page = args.get('page', 1)
        per_page = args.get('per_page', 50)
        recordings = models.Recording.query.filter_by(**filters).paginate(page=page, per_page=per_page)
        return [recording.to_dict() for recording in recordings]


