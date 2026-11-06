# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

# Standard library imports
import csv
import json
from io import StringIO

# Third-party imports
from flask import Blueprint, Response, flash, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

# Local application imports
from .. import classifier as rocca
from .. import database_handler
from .. import exception_handler
from .. import models
from .. import response_handler
from .. import transaction_handler
from .. import utils

routes_classifier = Blueprint('classifier', __name__)


def _get_classifier(session, classifier_id) -> models.Classifier:
    classifier = session.query(models.Classifier).filter_by(id=classifier_id).first()
    if not classifier: raise exception_handler.DoesNotExistError("classifier")
    return classifier

def _encounters_using(session, classifier):
    return session.query(models.Encounter).filter(models.Encounter.classifier_id == classifier.id) \
        .order_by(models.Encounter.encounter_name).all()

def _parse_settings(form):
    """Parse the name and threshold settings shared by the insert and update forms."""
    name = utils.validate_string(form.get("name"), field="Name", allow_none=False)
    try:
        threshold = int(form.get("threshold", 40))
    except ValueError:
        raise exception_handler.WarningException("Threshold must be a whole number.")
    if not 0 <= threshold <= 100: raise exception_handler.WarningException("Threshold must be between 0 and 100.")
    return name, threshold, form.get("strong_diff") == "on"


### Admin pages ###

@routes_classifier.route('/admin/classifier', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
def classifier_list():
    with database_handler.get_session() as session:
        classifiers = session.query(models.Classifier).order_by(models.Classifier.created_datetime.desc()).all()
        counts = dict(session.query(models.SelectionClassification.classifier_id, func.count())
                      .group_by(models.SelectionClassification.classifier_id))
        encounter_counts = dict(session.query(models.Encounter.classifier_id, func.count())
                                .filter(models.Encounter.classifier_id != None).group_by(models.Encounter.classifier_id))
        return render_template('admin/admin-classifier.html', classifiers=classifiers, counts=counts, encounter_counts=encounter_counts)

@routes_classifier.route('/admin/classifier/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def classifier_insert():
    with response_handler.json_response_context() as response:
        name, threshold, strong_diff = _parse_settings(request.form)
        upload = request.files.get('file')
        if not upload or not upload.filename.lower().endswith('.model'):
            raise exception_handler.WarningException("Please choose a PAMGuard ROCCA classifier (.model) file.")
        with transaction_handler.atomic_with_filespace() as transaction:
            session = transaction.session
            if session.query(models.Classifier).filter_by(name=name).first():
                raise exception_handler.WarningException(f"A classifier called {name} already exists.")
            model_file = transaction.create_tracked_file()
            model_file.insert(upload, rocca.MODEL_DIRECTORY, utils.secure_fname(f"Classifier-{name}"))
            info = rocca.model_info(model_file._path_with_root)  # raises if the model can't be used
            classifier = models.Classifier(name=name, threshold=threshold, strong_diff=strong_diff,
                                           species_list=json.dumps(info["species"]), num_stages=info["stages"],
                                           updated_by_id=current_user.id)
            classifier.model_file = model_file
            session.add(classifier)
            session.flush()
            classifier_id = classifier.id
        flash(f"Classifier uploaded: {name}. Choose it on an encounter's edit page to classify that encounter's selections.", "success")
        response.set_redirect(url_for('classifier.classifier_view', classifier_id=classifier_id))
    return response.to_json()

@routes_classifier.route('/admin/classifier/<classifier_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
def classifier_view(classifier_id):
    with database_handler.get_session() as session:
        classifier = _get_classifier(session, classifier_id)
        label_counts = session.query(models.SelectionClassification.classified_as, func.count()) \
            .filter_by(classifier_id=classifier.id).group_by(models.SelectionClassification.classified_as) \
            .order_by(func.count().desc()).all()
        encounters = _encounters_using(session, classifier)
        return render_template('admin/admin-classifier-view.html', classifier=classifier, label_counts=label_counts, encounters=encounters)

@routes_classifier.route('/admin/classifier/<classifier_id>/update', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def classifier_update(classifier_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            classifier = _get_classifier(session, classifier_id)
            classifier.name, classifier.threshold, classifier.strong_diff = _parse_settings(request.form)
            classifier.updated_by_id = current_user.id
            rocca.relabel(session, classifier)
        flash("Classifier updated and existing results re-labelled with the new threshold.", "success")
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_classifier.route('/admin/classifier/<classifier_id>/delete', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def classifier_delete(classifier_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            classifier = _get_classifier(session, classifier_id)
            if _encounters_using(session, classifier):
                raise exception_handler.WarningException("This classifier is used by encounters. Choose a different classifier for them before deleting it.")
            name = classifier.name
            classifier.model_file.mark_for_deletion()
            session.delete(classifier)  # its results are removed by ON DELETE CASCADE
        flash(f"Classifier deleted: {name}", "success")
        response.set_redirect(url_for('classifier.classifier_list'))
    return response.to_json()

@routes_classifier.route('/admin/classifier/<classifier_id>/export', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
def classifier_export(classifier_id):
    with database_handler.get_session() as session:
        classifier = _get_classifier(session, classifier_id)
        rows = session.query(models.SelectionClassification, models.Selection) \
            .join(models.Selection, models.Selection.id == models.SelectionClassification.selection_id) \
            .filter(models.SelectionClassification.classifier_id == classifier.id).all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Encounter', 'Location', 'Project', 'Recording', 'Species', 'SELECTIONNUMBER',
                         'ClassifiedAs', 'Votes', 'UpToDate', 'Error'])
        for result, selection in rows:
            encounter = selection.recording.encounter
            writer.writerow([encounter.encounter_name, encounter.location, encounter.project, selection.recording.start_time,
                             encounter.species.scientific_name, selection.selection_number, result.classified_as,
                             result.votes_description, result.stats_hash == rocca.stats_hash(selection), result.error])
        output.seek(0)
        filename = utils.secure_fname(f"Classifications-{classifier.name}") + ".csv"
        return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})


### Re-classify buttons on the selection, recording and encounter pages ###

def _classify_now(session, selections, response):
    """Classify `selections` with their encounter's classifier and commit the results."""
    classified, errors = rocca.classify_with_encounter_classifiers(session, selections)
    session.commit()
    response.add_message(f"{classified} selection(s) classified" + (f" ({errors} failed)." if errors else "."))

@routes_classifier.route('/selection/<selection_id>/classify', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def selection_classify(selection_id):
    with response_handler.json_response_context() as response:
        with database_handler.get_session() as session:
            selection = session.query(models.Selection).filter_by(id=selection_id).first()
            if not selection: raise exception_handler.DoesNotExistError("selection")
            _classify_now(session, [selection], response)
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_classifier.route('/recording/<recording_id>/classify', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def recording_classify(recording_id):
    with response_handler.json_response_context() as response:
        with database_handler.get_session() as session:
            recording = session.query(models.Recording).filter_by(id=recording_id).first()
            if not recording: raise exception_handler.DoesNotExistError("recording")
            _classify_now(session, recording.selections, response)
    return response.to_json()

@routes_classifier.route('/encounter/<encounter_id>/classify', methods=['POST'])
@login_required
@database_handler.exclude_role_4
@database_handler.require_live_session
def encounter_classify(encounter_id):
    with response_handler.json_response_context() as response:
        with database_handler.get_session() as session:
            selections = session.query(models.Selection).join(models.Recording, models.Recording.id == models.Selection.recording_id) \
                .filter(models.Recording.encounter_id == encounter_id).all()
            _classify_now(session, selections, response)
    return response.to_json()
