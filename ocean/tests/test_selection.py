import datetime
import os
import pytest
from . import factories
from ..app import models
from ..app import exception_handler
from ..app import utils
from . import common
import uuid

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def selection():
    return factories.SelectionFactory.create()

def populate_selection_table(selection):
    for attr, (dtype, _, _) in common.SELECTION_TABLE.items():
        setattr(selection, attr, dtype(1))

def populate_contour_statistics(selection):
    for attr, (dtype, _, _) in common.CONTOUR_STATISTICS.items():
        setattr(selection, attr, dtype(1))

@pytest.mark.parametrize("attr, value, expected", [
    ("selection_number", "1", 1),
    ("selection_number", "-100", -100),
    ("selection_number", 1, 1),
    ("selection_number", -100, -100),
    ("selection_file", None, None),
    ("selection_file_id", None, None),
    ("contour_file", None, None),
    ("contour_file_id", None, None),
    ("ctr_file", None, None),
    ("ctr_file_id", None, None),
    ("sampling_rate", 50000, 50000),
    ("sampling_rate", "50000", 50000),
    ("sampling_rate", 50000.0, 50000),
    ("sampling_rate", " 50000.0 ", 50000),
    ("sampling_rate", 0, 0),
    ("sampling_rate", "0", 0),
    ("sampling_rate", None, None),
    ("sampling_rate", "", None),
    ("sampling_rate", " ", None),
    ("traced", True, True),
    ("traced", "True", True),
    ("traced", "true", True),
    ("traced", False, False),
    ("traced", "False", False),
    ("traced", "false", False),
    ("traced", None, None),
    ("traced", "",  None),
    ("traced", " ", None),
    ("deactivated", True, True),
    ("deactivated", "True", True),
    ("deactivated", "true", True),
    ("deactivated", False, False),
    ("deactivated", "False", False),
    ("deactivated", "false", False),
    ("default_fft_size", 1, 1),
    ("default_fft_size", "1", 1),
    ("default_fft_size", 0, 0),
    ("default_fft_size", "0", 0),
    ("default_fft_size", 2048.5, 2048),
    ("default_fft_size", "2048.5", 2048),
    ("default_fft_size", None, None),
    ("default_fft_size", "", None),
    ("default_hop_size", 1, 1),
    ("default_hop_size", "1", 1),
    ("default_hop_size", 0, 0),
    ("default_hop_size", "0", 0),
    ("default_hop_size", 512.5, 512),
    ("default_hop_size", "512.5", 512),
    ("default_hop_size", None, None),
    ("default_hop_size", "", None),
])
def test_set_attribute(selection: models.Selection, attr: str, value, expected):
    setattr(selection, attr, value)
    assert getattr(selection, attr) == expected


@pytest.mark.parametrize("attr, value", [
    ("selection_number", None),
    ("selection_number", ""),
    ("selection_number", " "),
    ("selection_number", "this-is-not-an-integer"),
    ("deactivated", None),
    ("deactivated", ""),
    ("deactivated", " "),
    ("deactivated", "this-is-not-a-boolean"),
    ("traced", "this-is-not-a-boolean")
])
def test_set_attribute_validation_error(selection: models.Selection, attr: str, value):
    common.test_set_attribute_validation_error(selection, attr, value)


@pytest.mark.parametrize("attr, nullable", [
    ("recording_id", False),
    ("selection_file_id", True),
    ("contour_file_id", True),
    ("ctr_file_id", True),
    ("updated_by_id", True)
])
def test_uuid(selection: models.Selection, attr: str, nullable: bool):
    common.validate_uuid(selection, attr, str(uuid.uuid4()), nullable)

@pytest.mark.parametrize("attr, value, expected, nullable, dtype", [
    (attr, value, expected, nullable, dtype)
    for attr, (dtype, _, nullable) in {**common.CONTOUR_STATISTICS, **common.SELECTION_TABLE}.items()
    for value, expected in [
        (0, dtype(0)),
        (dtype(0), dtype(0)),
        (str(dtype(0)), dtype(0)),
        (1, dtype(1)),
        (dtype(1.5), dtype(1.5)),
        (dtype(-1.5), dtype(-1.5)),
        (str(dtype(1.5)), dtype(1.5)),
        (str(dtype(-1.5)), dtype(-1.5)),
        (" " + str(dtype(1.5)) + " ", dtype(1.5)),
        (" " + str(dtype(1.5)) + "\n", dtype(1.5)),
        ("", None),
        (" ", None),
        (" \n ", None),
        (" \t ", None),
        (None, None)
    ]
])
def test_set_contour_statistics_and_selection_table(selection: models.Selection, attr: str, value, expected, nullable: bool, dtype):
    if dtype == str and value is not None: value = str(value)
    if not nullable and expected is None: assert attr == None
    setattr(selection, attr, value)
    assert getattr(selection, attr) == expected
    if type(expected) != str and expected is not None:
        with pytest.raises(exception_handler.ValidationError):
            setattr(selection, attr, "this-is-not-a-" + str(dtype))

@pytest.mark.parametrize("value, expected", [
    ("Y", "Y"),
    ("y", "Y"),
    ("M", "M"),
    ("m", "M"),
    ("N", "N"),
    ("n", "N"),
    (None, None),
    (" ", None),
    ("\n\t", None),
])
def test_annotation(selection: models.Selection, value, expected):
    selection.annotation = value
    assert selection.annotation == expected

@pytest.mark.parametrize("value", [
    "Y - not valid",
    "not-valid",
    "YY",
    "NN",
    "MM",
])
def test_annotation_invalid(selection: models.Selection, value):
    with pytest.raises(exception_handler.ValidationError):
        setattr(selection, "annotation", value)

def test_clear_contour_statistics_attrs(selection: models.Selection):
    populate_contour_statistics(selection)
    for attr, (dtype, _, _) in common.CONTOUR_STATISTICS.items():
        assert getattr(selection, attr) is not None
    selection.clear_contour_statistics_attrs()
    for attr, (dtype, _, _) in common.CONTOUR_STATISTICS.items():
        assert getattr(selection, attr) is None

def test_clear_slection_table_attrs(selection: models.Selection):
    populate_selection_table(selection)
    for attr, (dtype, _, _) in common.SELECTION_TABLE.items():
        assert getattr(selection, attr) is not None
    selection.clear_selection_table_attrs()
    for attr, (dtype, _, _) in common.SELECTION_TABLE.items():
        assert getattr(selection, attr) is None


def test_ctr_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.ctr_file_name == "CTR-1-20200821T025422"

def test_selection_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.selection_file_name == "Selection-1-20200821T025422"

def test_plot_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.plot_file_name == "Plot-1-20200821T025422"

def test_contour_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.contour_file_name == "Contour-1-20200821T025422"

def test_relative_directory(selection: models.Selection):
    for c in common.INVALID_CHARACTERS + ["_"]:
        selection.selection_number = 1
        selection.recording.encounter = factories.EncounterFactory.create()
        selection.recording.encounter.species.scientific_name = f"Test{c}Species"
        selection.recording.encounter.encounter_name = f"Test{c}Encounter"
        selection.recording.encounter.location = f"Test{c}Location"
        selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
        assert selection.relative_directory == os.path.join(f"Species-Test_Species", f"Location-Test_Location", f"Encounter-Test_Encounter",f"Recording-20200821T025422", f"Selections-20200821025422")

def test_deactivate(selection: models.Selection):
    selection.traced = True
    selection.deactivated = False
    selection.deactivate()
    assert selection.traced == None
    assert selection.deactivated == True

def test_reactivate(selection: models.Selection):
    selection.traced = True
    selection.deactivated = True
    selection.reactivate()
    assert selection.traced == None
    assert selection.deactivated == False

def test_update_traced_annotation_Y_contour(selection: models.Selection):
    selection.annotation = "Y"

    selection.contour_file = factories.FileFactory.create(extension = "csv")
    selection.contour_file
    selection.update_traced()
    assert selection.traced == True
    
def test_update_traced_annotation_Y_no_contour(selection: models.Selection):
    selection.annotation = "Y"
    selection.contour_file = None
    selection.update_traced()
    assert selection.traced == None
    
def test_update_traced_annotation_M_contour(selection: models.Selection):
    selection.annotation = "M"
    selection.contour_file = factories.FileFactory.create(extension = "csv")
    selection.update_traced()
    assert selection.traced == True

def test_update_traced_annotation_M_no_contour(selection: models.Selection):
    selection.annotation = "M"
    selection.contour_file = None
    selection.update_traced()
    assert selection.traced == None
    
def test_update_traced_annotation_N_contour(selection: models.Selection):
    selection.annotation = "N"
    selection.contour_file = factories.FileFactory.create(extension = "csv")
    selection.update_traced()
    assert selection.traced == True
    
def test_update_traced_annotation_N_no_contour(selection: models.Selection):
    selection.annotation = "N"
    selection.contour_file = None
    selection.update_traced()
    assert selection.traced == False

@pytest.mark.parametrize("attr", common.CONTOUR_STATISTICS.keys())
def test_get_contour_statistics_attrs(selection: models.Selection, attr):
    assert attr in selection.get_contour_statistics_attrs()

@pytest.mark.parametrize("attr", common.SELECTION_TABLE.keys())
def test_get_selection_table_attrs(selection: models.Selection, attr):
    assert attr in selection.selection_table_attrs

def test_get_contour_statistics_dict(selection: models.Selection):
    populate_contour_statistics(selection)
    for attr, value in selection.get_contour_statistics_dict().items():
        assert attr in common.CONTOUR_STATISTICS
        assert type(value) == common.CONTOUR_STATISTICS[attr][0]

def test_get_contour_statistics_dict_headers(selection: models.Selection):
    populate_contour_statistics(selection)
    for attr, (dtype, header, _) in common.CONTOUR_STATISTICS.items():
        assert header in selection.get_contour_statistics_dict(use_headers=True)
        assert type(selection.get_contour_statistics_dict(use_headers=True)[header]) == dtype

def test_unique_name(selection: models.Selection):
    recording = factories.RecordingFactory.create()
    selection.selection_number = 1
    selection.recording = recording
    assert selection.unique_name == f"{recording.unique_name}, Selection: 1"

# TODO: add test9s) for:
# get_contour_file_handler