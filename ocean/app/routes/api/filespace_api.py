from flask_restx import Resource, reqparse, marshal_with, fields, Namespace
from flask import Response, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from ... import utils, exception_handler, models
import json
import io

api = Namespace('filespace', 'All endpoints that serve files between OCEAN and the user' )

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


def extract_id_from_csv(file_object):
    #reading the first line of a contour csv to extract the id - assuming that id is the first line of each ref csv
    #expects the format "reference_contour_id:550e8400-e29b-41d4-a716
    first_line = file_object.readline().decode('utf-8').strip()
    file_object.seek(0)  #rewind file (?) to original
    if first_line.startswith('# contour_id:'):
        return first_line.split(':')[1].strip()
    return None


@api.route('/upload-ARTwarp-job/')
class ARTwarpJobUploadResource(Resource):
    method_decorators = [jwt_required()]


    #making assumptions that: script provides a json of job info, parameters file,
    # .csv files for each reference contour (category), json "category map" of which whistles
    # (selection_ids) correspond to which ref_ids
    # could/should also upload full original .mat file ?? - binary ?

    @api.doc(security=SECURITY_KEY)
    def post(self):
        #parse job info
        job_date = request.form.get('job_date')
        job_time = request.form.get('job_time')
        job_user = request.form.get('job_user')

        if not all([job_date, job_time, job_user]):
            return {"message": "Missing run info (date, time, or user)"}, 400

        #parse category map
        category_map = request.form.get('category_map')
        if not category_map:
            return {"message": "No category map provided"}, 400
        try:
            category_map = json.loads(category_map)
        except json.JSONDecodeError:
            return {"message": "category_map is not valid JSON"}, 400

        #get ARTwarp parameters file
        params_file = request.files.get('params_file')
        if not params_file:
            return {"message": "No parameters file provided"}, 400

        #get reference contour .csv files, here contour_file = reference-contour.csv
        ref_contour_files = request.files.getlist('contour_files')
        if not ref_contour_files:
            return {"message": "No contour files provided"}, 400

        ref_contours = []  #will hold (ref_contour_file, ref_contour_id) pairs

        for ref_contour_file in ref_contour_files:
            ref_contour_id = extract_id_from_csv(ref_contour_file)

            # need to define this extract_id_from_csv to extract ref_contour_id from ref_contour_file without
            # altering the csv itself
            # this is based on the assumption that ref.csvs 

            if not contour_id:
                #if any file is missing an id, reject entire upload
                return {
                    "message": f"Could not extract contour ID from file: {contour_file.filename}"
                }, 400
            contours.append((contour_file, contour_id))

        # need a way to validate that original whistle contour_ids in category map exist in OCEAN
        #or that they themself are ref contours (for multi-layered Jobs)
        # so we dont end up with orphaned categories (ref contours) without associated whistles (contours)

        if invalid_ids:
            return {
                "message": "Invalid data ids",
                "invalid_ids": invalid_ids
            }, 400

        #Save files to storage, if storage fails nothing gets written into database
        #is this necessary? checks could instead be performed by script somehow?
        params_path = save_file_to_storage(params_file, params_file.filename)

        saved_contours = []  # will hold (ref_contour_id, filename, storage_path) 
        for contour_file, contour_id in contours:
            path = save_file_to_storage(contour_file, contour_file.filename)
            saved_contours.append((contour_id, contour_file.filename, path))

        #
        # write to database - need classes defined first
        # 

        # success message (?)
        return {
            "message": "Run uploaded successfully",
            "refcontours_received": len(saved_contours),
            "sorted_whistles": len(category_map)
        }, 201