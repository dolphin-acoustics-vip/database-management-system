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

"""ROCCA whistle classification.

PAMGuard's ROCCA classifiers are Weka random forests saved as Java objects (`.model` files),
so they are run by a small Java helper (`ocean/java/RoccaClassify.java`) that needs Java
and the Weka jar (ocean/java/lib). OCEAN passes it the contour statistics it already
calculates and gets back the raw votes of every classifier stage. The threshold is then
applied here (`label_from_stages`), so changing a classifier's threshold never requires
running the model again.
"""

# Standard library imports
import csv
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile

# Third-party imports
import numpy as np

# Local application imports
from . import database_handler
from . import exception_handler
from . import models
from .logger import logger

JAVA_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "java")
JAVA_SOURCE = os.path.join(JAVA_DIRECTORY, "RoccaClassify.java")
# The Weka version PAMGuard uses, included in the repository (ocean/java/lib)
WEKA_JAR = os.environ.get("OCEAN_WEKA_JAR", os.path.join(JAVA_DIRECTORY, "lib", "weka-dev-3.7.7.jar"))
MODEL_DIRECTORY = "Classifiers"
AMBIG = "Ambig"  # same label PAMGuard uses (RoccaRFModel.AMBIG)
ERR = "Err"  # same label PAMGuard uses when classification fails

# Selection attribute name -> ROCCA parameter name (e.g. 'dc_mean' -> 'DCMEAN')
ROCCA_NAMES = {attr: header for attr, (_, header, _) in models.Selection.get_contour_statistics_attrs().items()}


### Running the Java helper ###

def _run(cmd, stdin=None):
    try:
        result = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise exception_handler.WarningException(f"Unable to run '{cmd[0]}'. Java must be installed to use ROCCA classifiers.")
    if result.returncode != 0:
        raise exception_handler.WarningException(f"ROCCA classifier failed: {result.stderr.strip()[-500:]}")
    return result.stdout

def _classpath():
    """Compile the Java helper (once per version of the source file) and return the classpath."""
    if not os.path.exists(WEKA_JAR):
        raise exception_handler.WarningException(f"Weka library not found at {WEKA_JAR}. Set OCEAN_WEKA_JAR to its location.")
    with open(JAVA_SOURCE, "rb") as f:
        version = hashlib.sha1(f.read()).hexdigest()[:12]
    build_dir = os.path.join(tempfile.gettempdir(), f"ocean-rocca-{version}")
    if not os.path.isdir(build_dir):
        # Compile into a fresh directory then rename, so concurrent requests never see a half-built helper
        tmp = tempfile.mkdtemp(prefix="ocean-rocca-build-")
        _run(["javac", "-cp", WEKA_JAR, "-d", tmp, JAVA_SOURCE])
        try: os.rename(tmp, build_dir)
        except OSError: shutil.rmtree(tmp, ignore_errors=True)  # another request built it first
    return WEKA_JAR + os.pathsep + build_dir

def _run_helper(mode, model_path, stdin=None):
    return _run(["java", "-cp", _classpath(), "rocca.RoccaClassify", mode, model_path], stdin=stdin)

def model_info(model_path):
    """Return a dict describing a model file (`stages`, `attributes`, `species`) and check that
    OCEAN calculates every contour statistic it needs."""
    info = json.loads(_run_helper("info", model_path))
    missing = [a for a in info["attributes"] if a not in ROCCA_NAMES.values()]
    if missing:
        raise exception_handler.WarningException(f"The classifier uses contour statistics that OCEAN does not calculate: {', '.join(missing)}")
    return info


### Contour statistics ###

def _format_value(value):
    """Format a statistic for the Java helper. Values may be Python or numpy numbers."""
    if value is None: return ""
    if isinstance(value, (bool, np.bool_, int, np.integer)): return str(int(value))
    value = float(value)
    return "" if math.isnan(value) else repr(value)

def stats_row(selection):
    """The selection's contour statistics as strings, in `ROCCA_NAMES` order."""
    return [_format_value(getattr(selection, attr)) for attr in ROCCA_NAMES]

def stats_hash(selection):
    """A hash of the contour statistics, used to spot results that are out of date."""
    return hashlib.sha1(",".join(stats_row(selection)).encode()).hexdigest()

def has_contour_statistics(selection):
    return bool(selection.contour_file_id) and not selection.deactivated and selection.freq_max is not None


### Classification ###

def label_from_stages(stages, threshold, strong_diff):
    """Apply the threshold to the raw votes, as PAMGuard's RoccaRFModel.classifyContour does.

    At each stage the contour is `Ambig` if the top vote (or, if `strong_diff`, the gap between
    the top two votes) is below `threshold` percent. Otherwise it moves on to the next stage,
    and the top species of the last stage is the result."""
    if not stages: return ERR
    # PAMGuard compares against a Java float: ((float) threshold) / 100
    cutoff = float(np.float32(threshold) / np.float32(100))
    for stage in stages:
        votes = stage["votes"]
        top = votes.index(max(votes))
        ranked = sorted(votes)
        score = ranked[-1] - ranked[-2] if strong_diff and len(ranked) > 1 else votes[top]
        if score < cutoff: return AMBIG
    return stages[-1]["classes"][top]

def run_classifier(classifier, selections):
    """Run the classifier on the selections. Returns {selection_id: (stages, error)}."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["id"] + list(ROCCA_NAMES.values()))
    for selection in selections:
        writer.writerow([selection.id] + stats_row(selection))
    results = {}
    for line in _run_helper("classify", classifier.model_file._path_with_root, stdin=output.getvalue()).splitlines():
        result = json.loads(line)
        results[result["id"]] = (result.get("stages"), result.get("error"))
    return results

def classify_selections(session, classifier, selections):
    """Classify the selections and store the results (replacing any previous results from this
    classifier). Selections without contour statistics are skipped. Returns the number of
    errors. The caller must commit the session."""
    selections = [s for s in selections if has_contour_statistics(s)]
    if not selections: return 0
    results = run_classifier(classifier, selections)
    existing = {c.selection_id: c for c in session.query(models.SelectionClassification).filter(
        models.SelectionClassification.classifier_id == classifier.id,
        models.SelectionClassification.selection_id.in_([s.id for s in selections]))}
    errors = 0
    for selection in selections:
        stages, error = results.get(selection.id, (None, "No result returned by classifier"))
        result = existing.get(selection.id)
        if not result:
            result = models.SelectionClassification(selection_id=selection.id, classifier_id=classifier.id)
            session.add(result)
        result.stage_votes = json.dumps(stages) if stages else None
        result.error = error[:255] if error else None
        result.classified_as = ERR if error else label_from_stages(stages, classifier.threshold, classifier.strong_diff)
        result.stats_hash = stats_hash(selection)
        if error: errors += 1
    return errors

def relabel(session, classifier):
    """Re-apply the classifier's threshold to its stored votes (no Java needed)."""
    for result in session.query(models.SelectionClassification).filter_by(classifier_id=classifier.id):
        if result.stage_votes:
            result.classified_as = label_from_stages(result.stages, classifier.threshold, classifier.strong_diff)

def get_results(session, selection_ids):
    """Return {selection_id: SelectionClassification} with each selection's result from its
    encounter's classifier. Selections whose encounter has no classifier are left out."""
    if not selection_ids: return {}
    rows = session.query(models.SelectionClassification) \
        .join(models.Selection, models.Selection.id == models.SelectionClassification.selection_id) \
        .join(models.Recording, models.Recording.id == models.Selection.recording_id) \
        .join(models.Encounter, models.Encounter.id == models.Recording.encounter_id) \
        .filter(models.SelectionClassification.classifier_id == models.Encounter.classifier_id,
                models.SelectionClassification.selection_id.in_(selection_ids))
    return {c.selection_id: c for c in rows}

def api_dict(result, selection):
    """A classification result as returned by the API, or None if there is no result."""
    if result is None: return None
    classifier = result.classifier
    return {
        "classifier": {"id": classifier.id, "name": classifier.name,
                       "threshold": classifier.threshold, "strong_diff": classifier.strong_diff},
        "classified_as": result.classified_as,
        # One {species: vote} dict per classifier stage (most classifiers have a single stage)
        "stages": [dict(zip(stage["classes"], stage["votes"])) for stage in result.stages],
        "up_to_date": result.stats_hash == stats_hash(selection),
        "error": result.error,
    }

def classify_with_encounter_classifiers(session, selections):
    """Classify each selection with its encounter's classifier (selections whose encounter has
    no classifier are skipped). Returns (number classified, number of errors). The caller must
    commit the session."""
    by_classifier = {}
    for selection in selections:
        classifier = selection.recording.encounter.classifier
        if classifier and has_contour_statistics(selection):
            by_classifier.setdefault(classifier.id, (classifier, []))[1].append(selection)
    classified, errors = 0, 0
    for classifier, batch in by_classifier.values():
        errors += classify_selections(session, classifier, batch)
        classified += len(batch)
    return classified, errors

def classify_after_commit(selection_ids):
    """Classify selections (with their encounter's classifier) in a new session. Used after
    contours are uploaded or their statistics recalculated, and after an encounter's classifier is
    changed. Never raises: a failure here should not undo the change that triggered it, and the
    selections can be re-classified later. Returns a warning message if classification failed."""
    if not selection_ids: return None
    try:
        with database_handler.get_session() as session:
            selections = session.query(models.Selection).filter(models.Selection.id.in_(selection_ids)).all()
            classify_with_encounter_classifiers(session, selections)
            session.commit()
    except Exception as e:
        logger.error(f"ROCCA classification failed for selections {selection_ids}: {e}")
        return f"ROCCA classification failed: {e}"
    return None

def encounter_selection_ids(session, encounter_id):
    return [selection_id for (selection_id,) in session.query(models.Selection.id)
            .join(models.Recording, models.Recording.id == models.Selection.recording_id)
            .filter(models.Recording.encounter_id == encounter_id)]
