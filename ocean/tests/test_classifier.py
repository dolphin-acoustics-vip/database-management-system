import glob
import os
import re
import shutil
from types import SimpleNamespace

import pytest

from ..app import classifier, contour_statistics, utils

STAGE = {"classes": ["Pc", "Sb", "Tt"], "votes": [0.2, 0.5, 0.3]}


### Threshold logic (no Java needed) ###

def test_label_above_threshold():
    assert classifier.label_from_stages([STAGE], threshold=40, strong_diff=False) == "Sb"

def test_label_below_threshold_is_ambig():
    assert classifier.label_from_stages([STAGE], threshold=60, strong_diff=False) == classifier.AMBIG

def test_label_strong_diff_uses_gap_between_top_two():
    # gap between 0.5 and 0.3 is (just under) 0.2
    assert classifier.label_from_stages([STAGE], threshold=19, strong_diff=True) == "Sb"
    assert classifier.label_from_stages([STAGE], threshold=21, strong_diff=True) == classifier.AMBIG

def test_label_matches_pamguard_float_threshold():
    # PAMGuard compares votes with ((float) 40) / 100 = 0.4000000059604645, so a vote of
    # exactly 0.4 is Ambig in PAMGuard even though 0.4 >= 0.4 in Python.
    stage = {"classes": ["Pc", "Sb"], "votes": [0.6, 0.4]}
    assert classifier.label_from_stages([stage], threshold=60, strong_diff=False) == classifier.AMBIG

def test_label_multi_stage_uses_last_stage():
    stage2 = {"classes": ["Sb1", "Sb2"], "votes": [0.1, 0.9]}
    assert classifier.label_from_stages([STAGE, stage2], threshold=40, strong_diff=False) == "Sb2"

def test_label_multi_stage_ambig_at_second_stage():
    stage2 = {"classes": ["Sb1", "Sb2"], "votes": [0.45, 0.55]}
    assert classifier.label_from_stages([STAGE, stage2], threshold=60, strong_diff=False) == classifier.AMBIG

def test_label_no_stages_is_error():
    assert classifier.label_from_stages([], threshold=40, strong_diff=False) == classifier.ERR


### Contour statistics passed to the classifier ###

def _selection(**stats):
    selection = SimpleNamespace(id="sel-1", contour_file_id="file-1", deactivated=False)
    for attr in classifier.ROCCA_NAMES: setattr(selection, attr, None)
    for attr, value in stats.items(): setattr(selection, attr, value)
    return selection

def test_stats_row_formatting():
    row = dict(zip(classifier.ROCCA_NAMES.values(), classifier.stats_row(_selection(freq_max=12000.5, freq_begup=True, freq_numsteps=3))))
    assert row["FREQMAX"] == "12000.5"
    assert row["FREQBEGUP"] == "1"
    assert row["FREQNUMSTEPS"] == "3"
    assert row["FREQMIN"] == ""  # missing

def test_stats_row_accepts_numpy_values():
    import numpy as np
    row = dict(zip(classifier.ROCCA_NAMES.values(), classifier.stats_row(_selection(freq_max=np.float64(0.25), freq_numsteps=np.int64(2), freq_min=np.float64("nan")))))
    assert (row["FREQMAX"], row["FREQNUMSTEPS"], row["FREQMIN"]) == ("0.25", "2", "")

def test_stats_hash_changes_with_stats():
    assert classifier.stats_hash(_selection(freq_max=1.0)) == classifier.stats_hash(_selection(freq_max=1.0))
    assert classifier.stats_hash(_selection(freq_max=1.0)) != classifier.stats_hash(_selection(freq_max=2.0))

def test_has_contour_statistics():
    assert classifier.has_contour_statistics(_selection(freq_max=1.0))
    assert not classifier.has_contour_statistics(_selection())
    assert not classifier.has_contour_statistics(_selection(freq_max=1.0, deactivated=True))


### API output ###

def test_api_dict():
    selection = _selection(freq_max=1.0)
    result = SimpleNamespace(
        classifier=SimpleNamespace(id="c-1", name="RF8sp53att", threshold=40, strong_diff=False),
        classified_as="Sb", stages=[STAGE], stats_hash=classifier.stats_hash(selection), error=None)
    assert classifier.api_dict(result, selection) == {
        "classifier": {"id": "c-1", "name": "RF8sp53att", "threshold": 40, "strong_diff": False},
        "classified_as": "Sb",
        "stages": [{"Pc": 0.2, "Sb": 0.5, "Tt": 0.3}],
        "up_to_date": True,
        "error": None,
    }
    selection.freq_max = 2.0
    assert classifier.api_dict(result, selection)["up_to_date"] is False

def test_api_dict_without_result():
    assert classifier.api_dict(None, _selection()) is None


### End to end against PAMGuard (needs Java, the Weka jar and a model file) ###
# The RoccaContourStats.xlsx files in tests 4-9 were produced by PAMGuard with the TropPac
# classifier, which gives the same votes as RF8sp53att.model. Set OCEAN_TEST_ROCCA_MODEL to
# the path of that model file to run this test.

MODEL = os.environ.get("OCEAN_TEST_ROCCA_MODEL")
CONTOUR_STATS_DIR = "ocean/tests/resources/contour-stats"

@pytest.mark.skipif(not MODEL or not os.path.exists(MODEL) or not shutil.which("java") or not os.path.exists(classifier.WEKA_JAR),
                    reason="Requires OCEAN_TEST_ROCCA_MODEL, Java and the Weka jar")
def test_classification_matches_pamguard():
    selections, expected = [], {}
    for folder in sorted(glob.glob(os.path.join(CONTOUR_STATS_DIR, "test*"))):
        pamguard = utils.extract_to_dataframe(os.path.join(folder, "RoccaContourStats.xlsx"))
        if "ClassifiedSpecies" not in pamguard.columns: continue
        for file in sorted(glob.glob(os.path.join(folder, "*.csv"))):
            selection_number = int(re.search(r'sel_(\d+)', file).group(1))
            row = pamguard.loc[pamguard['SelectionNumber'] == selection_number]
            # OCEAN calculates the contour statistics itself, from the contour file
            selection = _selection()
            selection.id = f"{os.path.basename(folder)}-{selection_number}"
            handler = contour_statistics.ContourFileHandler()
            handler.insert_dataframe(utils.extract_to_dataframe(file))
            handler.calculate_statistics(selection)
            selections.append(selection)
            expected[selection.id] = (row['ClassifiedSpecies'].values[0], [row[f'Species{i}'].values[0] for i in range(1, 9)])
    assert selections, "No PAMGuard classification results found in the test resources"

    results = classifier.run_classifier(SimpleNamespace(model_file=SimpleNamespace(_path_with_root=MODEL)), selections)
    for selection_id, (species, votes) in expected.items():
        stages, error = results[selection_id]
        assert error is None, f"{selection_id}: {error}"
        # PAMGuard ran without an Ambig threshold, so compare with a threshold of 0
        assert classifier.label_from_stages(stages, threshold=0, strong_diff=False) == species, selection_id
        assert stages[0]["votes"] == pytest.approx(votes, abs=0.01), selection_id
