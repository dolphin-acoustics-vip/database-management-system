import datetime
import pytest
from . import factories
from ..app import models
from ..app import exception_handler
from . import common
import uuid

EMPTY_CHARACTERS = common.EMPTY_CHARACTERS

@pytest.fixture
def selection():
    return factories.SelectionFactory.create()

def test_hasattr_updated_by_id(selection: models.Selection):
    """Test if the Encounter object has the updated_by_id attribute"""
    assert hasattr(selection, "set_updated_by_id") == True
    
def test_hasattr_update_call(selection: models.Selection):
    assert hasattr(selection, "update_call") == True

def test_hasattr_delete_children(selection: models.Selection):
    assert hasattr(selection, "delete_children") == True    

def test_hasattr_row_start(selection: models.Selection):
    assert hasattr(selection, "row_start")
    assert hasattr(selection, "get_row_start")
    assert hasattr(selection, "get_row_start_pretty")

def test_hasattr_created_datetime(selection: models.Selection):
    assert hasattr(selection, "created_datetime")
    assert hasattr(selection, "get_created_datetime")
    assert hasattr(selection, "get_created_datetime_pretty")

def test_hasattr_other_methods(selection: models.Selection):
    assert hasattr(selection, "recalculate_contour_statistics")
    assert hasattr(selection, "calculate_sampling_rate")
    assert hasattr(selection, "set_selection_file")
    assert hasattr(selection, "create_temp_plot")
    assert hasattr(selection, "generate_ctr_file")
    assert hasattr(selection, "delete_contour_file")
    
def test_hasattr_getters(selection: models.Selection):
    assert hasattr(selection, "get_selection_number")
    assert hasattr(selection, "get_selection_file_id")
    assert hasattr(selection, "get_selection_file")
    assert hasattr(selection, "get_ctr_file_id")
    assert hasattr(selection, "get_ctr_file")
    assert hasattr(selection, "get_contour_file_id")
    assert hasattr(selection, "get_contour_file")
    assert hasattr(selection, "get_sampling_rate")
    assert hasattr(selection, "get_deactivated")
    assert hasattr(selection, "get_traced")
    assert hasattr(selection, "get_default_fft_size")
    assert hasattr(selection, "get_default_hop_size")
    assert hasattr(selection, "get_recording_id")
    assert hasattr(selection, "get_recording")
    
def test_hasattr_setters(selection: models.Selection):
    assert hasattr(selection, "set_selection_number")
    assert hasattr(selection, "set_selection_file_id")
    assert hasattr(selection, "set_selection_file")
    assert hasattr(selection, "set_ctr_file_id")
    assert hasattr(selection, "set_ctr_file")
    assert hasattr(selection, "set_contour_file_id")
    assert hasattr(selection, "set_contour_file")
    assert hasattr(selection, "set_sampling_rate")
    assert hasattr(selection, "set_default_fft_size")
    assert hasattr(selection, "set_default_hop_size")
    assert hasattr(selection, "set_recording_id")
    assert hasattr(selection, "set_recording")
    
@pytest.mark.parametrize("value", [True, False, None])
def test_get_traced(selection: models.Selection, value: bool):
    selection.traced = value
    assert selection.get_traced() == value
    
@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0)])
def test_get_sampling_rate(selection: models.Selection, value, expected):
    selection.sampling_rate = value
    assert selection.get_sampling_rate() == expected
    
@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0), (" ", None), (None, None)])
def test_set_sampling_rate(selection: models.Selection, value, expected):
    selection.set_sampling_rate(value)
    assert selection.sampling_rate == expected

def test_set_sampling_rate_wrong_format(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_sampling_rate('not-a-number')


def test_set_selection_file_id(selection: models.Selection):
    selection_file_id = uuid.uuid4()
    selection.set_selection_file_id(selection_file_id)
    assert selection.selection_file_id == selection_file_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_selection_file_id_none(selection: models.Selection, c: str):
    with pytest.raises(exception_handler.WarningException):
        selection.set_selection_file_id(c)

def test_set_selection_file_id_wrong_type(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_selection_file_id("this-is-not-a-uuid")

def test_set_selection_file_id_already_exists(selection: models.Selection):
    selection.set_selection_file_id(uuid.uuid4())
    with pytest.raises(ValueError):
        selection.set_selection_file_id(uuid.uuid4())

def test_set_selection_file(selection: models.Selection):
    selection_file = factories.FileFactory.create()
    selection_file.extension = "wav"
    selection.set_selection_file(selection_file)
    assert selection.selection_file == selection_file

def test_set_selection_file_none(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_selection_file(None)

def test_set_selection_file_wrong_type(selection: models.Selection):
    with pytest.raises(ValueError):
        selection_file = factories.FileFactory.create()
        selection_file.extension = "wav"
        selection.set_selection_file(factories.SpeciesFactory.create())

def test_set_selection_file_already_exists(selection: models.Selection):
    selection_file = factories.FileFactory.create()
    selection_file.extension = "wav"
    selection.set_selection_file(selection_file)
    with pytest.raises(ValueError):
        selection_file = factories.FileFactory.create()
        selection_file.extension = "wav"
        selection.set_selection_file(selection_file)

def test_set_selection_file_wrong_type(selection: models.Selection):
    selection_file = factories.FileFactory.create()
    selection_file.extension = "txt"
    with pytest.raises(exception_handler.WarningException):
        selection.set_selection_file(selection_file)



def test_set_contour_file_id(selection: models.Selection):
    contour_file_id = uuid.uuid4()
    selection.set_contour_file_id(contour_file_id)
    assert selection.contour_file_id == contour_file_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_contour_file_id_none(selection: models.Selection, c: str):
    with pytest.raises(exception_handler.WarningException):
        selection.set_contour_file_id(c)

def test_set_contour_file_id_wrong_type(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_contour_file_id("this-is-not-a-uuid")

def test_set_contour_file_id_already_exists(selection: models.Selection):
    selection.set_contour_file_id(uuid.uuid4())
    with pytest.raises(ValueError):
        selection.set_contour_file_id(uuid.uuid4())

def test_set_contour_file(selection: models.Selection):
    contour_file = factories.FileFactory.create()
    contour_file.extension = "csv"
    selection.set_contour_file(contour_file)
    assert selection.contour_file == contour_file

def test_set_contour_file_none(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_contour_file(None)

def test_set_contour_file_wrong_type(selection: models.Selection):
    with pytest.raises(ValueError):
        contour_file = factories.FileFactory.create()
        contour_file.extension = "csv"
        selection.set_contour_file(factories.SpeciesFactory.create())

def test_set_contour_file_already_exists(selection: models.Selection):
    contour_file = factories.FileFactory.create()
    contour_file.extension = "csv"
    selection.set_contour_file(contour_file)
    with pytest.raises(ValueError):
        contour_file = factories.FileFactory.create()
        contour_file.extension = "csv"
        selection.set_contour_file(contour_file)

def test_set_contour_file_wrong_type(selection: models.Selection):
    contour_file = factories.FileFactory.create()
    contour_file.extension = "txt"
    with pytest.raises(exception_handler.WarningException):
        selection.set_contour_file(contour_file)




def test_set_ctr_file_id(selection: models.Selection):
    ctr_file_id = uuid.uuid4()
    selection.set_ctr_file_id(ctr_file_id)
    assert selection.ctr_file_id == ctr_file_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_ctr_file_id_none(selection: models.Selection, c: str):
    with pytest.raises(exception_handler.WarningException):
        selection.set_ctr_file_id(c)

def test_set_ctr_file_id_wrong_type(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_ctr_file_id("this-is-not-a-uuid")

def test_set_ctr_file_id_already_exists(selection: models.Selection):
    selection.set_ctr_file_id(uuid.uuid4())
    with pytest.raises(ValueError):
        selection.set_ctr_file_id(uuid.uuid4())

def test_set_ctr_file(selection: models.Selection):
    ctr_file = factories.FileFactory.create()
    ctr_file.extension = "ctr"
    selection.set_ctr_file(ctr_file)
    assert selection.ctr_file == ctr_file

def test_set_ctr_file_none(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_ctr_file(None)

def test_set_ctr_file_wrong_type(selection: models.Selection):
    with pytest.raises(ValueError):
        ctr_file = factories.FileFactory.create()
        ctr_file.extension = "ctr"
        selection.set_ctr_file(factories.SpeciesFactory.create())

def test_set_ctr_file_already_exists(selection: models.Selection):
    ctr_file = factories.FileFactory.create()
    ctr_file.extension = "ctr"
    selection.set_ctr_file(ctr_file)
    with pytest.raises(ValueError):
        ctr_file = factories.FileFactory.create()
        ctr_file.extension = "ctr"
        selection.set_ctr_file(ctr_file)

def test_set_ctr_file_wrong_type(selection: models.Selection):
    ctr_file = factories.FileFactory.create()
    ctr_file.extension = "txt"
    with pytest.raises(exception_handler.WarningException):
        selection.set_ctr_file(ctr_file)





def test_set_recording_id(selection: models.Selection):
    recording_id = uuid.uuid4()
    selection.set_recording_id(recording_id)
    assert selection.recording_id == recording_id
    
@pytest.mark.parametrize("c", EMPTY_CHARACTERS)
def test_set_recording_id_none(selection: models.Selection, c: str):
    with pytest.raises(exception_handler.WarningException):
        selection.set_recording_id(c)

def test_set_recording_id_wrong_type(selection: models.Selection):
    
    with pytest.raises(exception_handler.WarningException):
        selection.set_recording_id("this-is-not-a-uuid")

def test_set_recording(selection: models.Selection):
    recording = factories.RecordingFactory.create()
    selection.set_recording(recording)
    assert selection.recording == recording

def test_set_recording_none(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_recording(None)

def test_set_recording_wrong_type(selection: models.Selection):
    with pytest.raises(ValueError):
        selection.set_recording(factories.SpeciesFactory.create())



@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0)])
def test_get_default_fft_size(selection: models.Selection, value, expected):
    selection.default_fft_size = value
    assert selection.get_default_fft_size() == expected
    
@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0), (" ", None), (None, None)])
def test_set_default_fft_size(selection: models.Selection, value, expected):
    selection.set_default_fft_size(value)
    assert selection.default_fft_size == expected

def test_set_default_fft_size_wrong_format(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_default_fft_size('not-a-number')


@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0)])
def test_get_default_hop_size(selection: models.Selection, value, expected):
    selection.default_hop_size = value
    assert selection.get_default_hop_size() == expected
    
@pytest.mark.parametrize("value, expected", [(15000,15000.0), (0,0.0), (-20.1345,-20.1345), ("15000", 15000.0), (" ", None), (None, None)])
def test_set_default_hop_size(selection: models.Selection, value, expected):
    selection.set_default_hop_size(value)
    assert selection.default_hop_size == expected

def test_set_default_hop_size_wrong_format(selection: models.Selection):
    with pytest.raises(exception_handler.WarningException):
        selection.set_default_hop_size('not-a-number')

    
    
def test_get_selection_number(selection: models.Selection):
    selection.selection_number = 1
    assert selection.get_selection_number() == 1
    selection.selection_number = 0
    assert selection.get_selection_number() == 0
    selection.selection_number = "0"
    assert selection.get_selection_number() == 0

def test_get_selection_number_invalid(selection: models.Selection):
    selection.selection_number = "24gs"
    with pytest.raises(exception_handler.WarningException):
        selection.get_selection_number()


def test_get_selection_file_id(selection: models.Selection):
    selection_file_id = uuid.uuid4()
    selection.selection_file_id = selection_file_id
    assert selection.get_selection_file_id() == selection_file_id
    selection_file_id = uuid.uuid4()
    selection.selection_file_id = selection_file_id.hex
    assert selection.get_selection_file_id() == selection_file_id
    selection.selection_file_id = None
    assert selection.get_selection_file_id() == None
    selection.selection_file_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        selection.get_selection_file_id()

def test_get_selection_file(selection: models.Selection):
    selection_file = factories.FileFactory.create()
    selection.selection_file = selection_file
    assert selection.get_selection_file() == selection_file
    selection.selection_file = None
    assert selection.get_selection_file() == None
    selection.selection_file = factories.SpeciesFactory.create()
    with pytest.raises(ValueError):
        selection.get_selection_file()

def test_get_contour_file_id(selection: models.Selection):
    contour_file_id = uuid.uuid4()
    selection.contour_file_id = contour_file_id
    assert selection.get_contour_file_id() == contour_file_id
    contour_file_id = uuid.uuid4()
    selection.contour_file_id = contour_file_id.hex
    assert selection.get_contour_file_id() == contour_file_id
    selection.contour_file_id = None
    assert selection.get_contour_file_id() == None
    selection.contour_file_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        selection.get_contour_file_id()

def test_get_contour_file(selection: models.Selection):
    contour_file = factories.FileFactory.create()
    selection.contour_file = contour_file
    assert selection.get_contour_file() == contour_file
    selection.contour_file = None
    assert selection.get_contour_file() == None
    selection.contour_file = factories.SpeciesFactory.create()
    with pytest.raises(ValueError):
        selection.get_contour_file()

def test_get_ctr_file_id(selection: models.Selection):
    ctr_file_id = uuid.uuid4()
    selection.ctr_file_id = ctr_file_id
    assert selection.get_ctr_file_id() == ctr_file_id
    ctr_file_id = uuid.uuid4()
    selection.ctr_file_id = ctr_file_id.hex
    assert selection.get_ctr_file_id() == ctr_file_id
    selection.ctr_file_id = None
    assert selection.get_ctr_file_id() == None
    selection.ctr_file_id = "not-a-uuid"
    with pytest.raises(exception_handler.WarningException):
        selection.get_ctr_file_id()

def test_get_ctr_file(selection: models.Selection):
    ctr_file = factories.FileFactory.create()
    selection.ctr_file = ctr_file
    assert selection.get_ctr_file() == ctr_file
    selection.ctr_file = None
    assert selection.get_ctr_file() == None
    selection.ctr_file = factories.SpeciesFactory.create()
    with pytest.raises(ValueError):
        selection.get_ctr_file()


def test_get_unique_name(selection: models.Selection):
    selection.recording.encounter.species.species_name = f"TestSpecies"
    selection.recording.encounter.encounter_name = f"TestEncounter"
    selection.recording.encounter.location = f"TestLocation"
    selection.recording.encounter.project = "TestProject"
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    selection.selection_number = 1
    assert selection.get_unique_name() == f"TestEncounter-TestLocation-TestProject-Recording-2020-08-21T02:54: Selection 1"

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

def populate_selection_table_values(selection):
    selection.view = "TestView"
    selection.channel = "TestChannel"
    selection.begin_time = 1.5
    selection.end_time = 2.0
    selection.low_frequency = 1000.0
    selection.high_frequency = 2001.4
    selection.delta_time = 0.5
    selection.delta_frequence = 1001.4
    selection.average_power = 80
    selection.annoation = "Y"

def test_reset_selection_table_values(selection: models.Selection):
    populate_selection_table_values(selection)
    selection.reset_selection_table_values()
    assert selection.view == None
    assert selection.channel == None
    assert selection.begin_time == None
    assert selection.end_time == None
    assert selection.low_frequency == None
    assert selection.high_frequency == None
    assert selection.delta_time == None
    assert selection.delta_frequency == None
    assert selection.average_power == None
    assert selection.annotation == None

def test_update_traced_status_annotation_Y_contour(selection: models.Selection):
    selection.annotation = "Y"
    selection.contour_file = factories.FileFactory.create()
    selection.update_traced_status()
    assert selection.traced == True
    
def test_update_traced_status_annotation_Y_no_contour(selection: models.Selection):
    selection.annotation = "Y"
    selection.contour_file = None
    selection.update_traced_status()
    assert selection.traced == None
    
def test_update_traced_status_annotation_M_contour(selection: models.Selection):
    selection.annotation = "M"
    selection.contour_file = factories.FileFactory.create()
    selection.update_traced_status()
    assert selection.traced == True

def test_update_traced_status_annotation_M_no_contour(selection: models.Selection):
    selection.annotation = "M"
    selection.contour_file = None
    selection.update_traced_status()
    assert selection.traced == None
    
def test_update_traced_status_annotation_N_contour(selection: models.Selection):
    selection.annotation = "N"
    selection.contour_file = factories.FileFactory.create()
    selection.update_traced_status()
    assert selection.traced == None
    
def test_update_traced_status_annotation_N_no_contour(selection: models.Selection):
    selection.annotation = "N"
    selection.contour_file = None
    selection.update_traced_status()
    assert selection.traced == False

def test_generate_ctr_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.generate_ctr_file_name() == "CTR-1-20200821T025422"

def test_generate_selection_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.generate_selection_file_name() == "Selection-1-20200821T025422"

def test_generate_plot_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.generate_plot_file_name() == "Plot-1-20200821T025422"

def test_generate_contour_file_name(selection: models.Selection):
    selection.selection_number = 1
    selection.recording.start_time = datetime.datetime(2020,8,21,2,54,22)
    assert selection.generate_contour_file_name() == "Contour-1-20200821T025422"

def test_generate_ctr_file(selection: models.Selection):
    # Something to do with testing whether given a particular
    # contour file a proper CTR file is created
    pass

def test_reset_contour_stats(selection: models.Selection):
    pass

def test_generate_contour_stats_array(selection: models.Selection):
    pass

def test_generate_contour_stats_dict(selection: models.Selection):
    pass

def test_upload_selection_table_data(selection: models.Selection):
    pass


def test_generate_relative_directory(selection: models.Selection):
    pass

def test_set_selection_number(selection: models.Selection):
    pass

def test_set_selection_number_empty(selection: models.Selection):
    pass

def test_set_selection_number_wrong_type(selection: models.Selection):
    pass



CALCULATED_FIELDS = [
    (models.Selection.freq_max, models.Selection.get_freq_max),
    (models.Selection.freq_min, models.Selection.get_freq_min)
]


def test_hasattr_calculated_fields(selection: models.Selection):
    assert hasattr(selection, "freq_max")
    assert hasattr(selection, "freq_min")
    assert hasattr(selection, "duration")
    assert hasattr(selection, "freq_begin")
    assert hasattr(selection, "freq_end")
    assert hasattr(selection, "freq_range")
    assert hasattr(selection, "dc_mean")
    assert hasattr(selection, "dc_standarddeviation")
    assert hasattr(selection, "freq_mean")
    assert hasattr(selection, "freq_standarddeviation")
    assert hasattr(selection, "freq_median")
    assert hasattr(selection, "freq_center")
    assert hasattr(selection, "freq_relbw")
    assert hasattr(selection, "freq_maxminratio")
    assert hasattr(selection, "freq_begendratio")
    assert hasattr(selection, "freq_quarter1")
    assert hasattr(selection, "freq_quarter2")
    assert hasattr(selection, "freq_quarter3")
    assert hasattr(selection, "freq_spread")
    assert hasattr(selection, "dc_quarter1mean")
    assert hasattr(selection, "dc_quarter2mean")
    assert hasattr(selection, "dc_quarter3mean")
    assert hasattr(selection, "dc_quarter4mean")
    assert hasattr(selection, "freq_cofm")
    assert hasattr(selection, "freq_stepup")
    assert hasattr(selection, "freq_stepdown")
    assert hasattr(selection, "freq_numsteps")
    assert hasattr(selection, "freq_slopemean")
    assert hasattr(selection, "freq_absslopemean")
    assert hasattr(selection, "freq_posslopemean")
    assert hasattr(selection, "freq_negslopemean")
    assert hasattr(selection, "freq_sloperatio")
    assert hasattr(selection, "freq_begsweep")
    assert hasattr(selection, "freq_begup")
    assert hasattr(selection, "freq_begdown")
    assert hasattr(selection, "freq_endsweep")
    assert hasattr(selection, "freq_endup")
    assert hasattr(selection, "freq_enddown")
    assert hasattr(selection, "num_sweepsupdown")
    assert hasattr(selection, "num_sweepsdownup")
    assert hasattr(selection, "num_sweepsupflat")
    assert hasattr(selection, "num_sweepsdownflat")
    assert hasattr(selection, "num_sweepsflatup")
    assert hasattr(selection, "num_sweepsflatdown")
    assert hasattr(selection, "freq_sweepuppercent")
    assert hasattr(selection, "freq_sweepdownpercent")
    assert hasattr(selection, "freq_sweepflatpercent")
    assert hasattr(selection, "num_inflections")
    assert hasattr(selection, "inflection_maxdelta")
    assert hasattr(selection, "inflection_mindelta")
    assert hasattr(selection, "inflection_maxmindelta")
    assert hasattr(selection, "inflection_mediandelta")
    assert hasattr(selection, "inflection_meandelta")
    assert hasattr(selection, "inflection_standarddeviationdelta")
    assert hasattr(selection, "inflection_duration")
    assert hasattr(selection, "step_duration")


FLOAT_TEST_VALUES = [
    (-1000, True, -1000.0),
    (0, True, 0.0),
    (100, True, 100.0),
    (100000, True, 100000.0),
    ("-1000", True, -1000.0),
    ("-1000.1351351", True, -1000.1351351),
    ("-1.00", True, -1.0),
    ("0", True, 0.0),
    ("100f", False, None),
    ("-13513ssd", False, None),
]


@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_max(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_max = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_max()
        selection.freq_max = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_max(val)
    else:
        assert (selection.get_freq_max() == exp) == valid
        selection.freq_max = None
        selection.set_freq_max(val)
        assert selection.freq_max == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_min(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_min = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_min()
        selection.freq_min = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_min(val)
    else:
        assert (selection.get_freq_min() == exp) == valid
        selection.freq_min = None
        selection.set_freq_min(val)
        assert selection.freq_min == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_duration(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.duration = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_duration()
        selection.duration = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_duration(val)
    else:
        assert (selection.get_duration() == exp) == valid
        selection.duration = None
        selection.set_duration(val)
        assert selection.duration == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_begin(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_begin = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_begin()
        selection.freq_begin = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_begin(val)
    else:
        assert (selection.get_freq_begin() == exp) == valid
        selection.freq_begin = None
        selection.set_freq_begin(val)
        assert selection.freq_begin == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_end(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_end = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_end()
        selection.freq_end = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_end(val)
    else:
        assert (selection.get_freq_end() == exp) == valid
        selection.freq_end = None
        selection.set_freq_end(val)
        assert selection.freq_end == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_range(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_range = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_range()
        selection.freq_range = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_range(val)
    else:
        assert (selection.get_freq_range() == exp) == valid
        selection.freq_range = None
        selection.set_freq_range(val)
        assert selection.freq_range == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_mean()
        selection.dc_mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_mean(val)
    else:
        assert (selection.get_dc_mean() == exp) == valid
        selection.dc_mean = None
        selection.set_dc_mean(val)
        assert selection.dc_mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_standarddeviation(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_standarddeviation = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_standarddeviation()
        selection.dc_standarddeviation = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_standarddeviation(val)
    else:
        assert (selection.get_dc_standarddeviation() == exp) == valid
        selection.dc_standarddeviation = None
        selection.set_dc_standarddeviation(val)
        assert selection.dc_standarddeviation == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_mean()
        selection.freq_mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_mean(val)
    else:
        assert (selection.get_freq_mean() == exp) == valid
        selection.freq_mean = None
        selection.set_freq_mean(val)
        assert selection.freq_mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_standarddeviation(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_standarddeviation = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_standarddeviation()
        selection.freq_standarddeviation = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_standarddeviation(val)
    else:
        assert (selection.get_freq_standarddeviation() == exp) == valid
        selection.freq_standarddeviation = None
        selection.set_freq_standarddeviation(val)
        assert selection.freq_standarddeviation == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_median(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_median = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_median()
        selection.freq_median = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_median(val)
    else:
        assert (selection.get_freq_median() == exp) == valid
        selection.freq_median = None
        selection.set_freq_median(val)
        assert selection.freq_median == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_center(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_center = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_center()
        selection.freq_center = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_center(val)
    else:
        assert (selection.get_freq_center() == exp) == valid
        selection.freq_center = None
        selection.set_freq_center(val)
        assert selection.freq_center == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_relbw(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_relbw = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_relbw()
        selection.freq_relbw = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_relbw(val)
    else:
        assert (selection.get_freq_relbw() == exp) == valid
        selection.freq_relbw = None
        selection.set_freq_relbw(val)
        assert selection.freq_relbw == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_maxminratio(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_maxminratio = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_maxminratio()
        selection.freq_maxminratio = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_maxminratio(val)
    else:
        assert (selection.get_freq_maxminratio() == exp) == valid
        selection.freq_maxminratio = None
        selection.set_freq_maxminratio(val)
        assert selection.freq_maxminratio == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_begendratio(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_begendratio = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_begendratio()
        selection.freq_begendratio = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_begendratio(val)
    else:
        assert (selection.get_freq_begendratio() == exp) == valid
        selection.freq_begendratio = None
        selection.set_freq_begendratio(val)
        assert selection.freq_begendratio == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_quarter1(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_quarter1 = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_quarter1()
        selection.freq_quarter1 = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_quarter1(val)
    else:
        assert (selection.get_freq_quarter1() == exp) == valid
        selection.freq_quarter1 = None
        selection.set_freq_quarter1(val)
        assert selection.freq_quarter1 == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_quarter2(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_quarter2 = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_quarter2()
        selection.freq_quarter2 = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_quarter2(val)
    else:
        assert (selection.get_freq_quarter2() == exp) == valid
        selection.freq_quarter2 = None
        selection.set_freq_quarter2(val)
        assert selection.freq_quarter2 == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_quarter3(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_quarter3 = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_quarter3()
        selection.freq_quarter3 = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_quarter3(val)
    else:
        assert (selection.get_freq_quarter3() == exp) == valid
        selection.freq_quarter3 = None
        selection.set_freq_quarter3(val)
        assert selection.freq_quarter3 == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_spread(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_spread = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_spread()
        selection.freq_spread = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_spread(val)
    else:
        assert (selection.get_freq_spread() == exp) == valid
        selection.freq_spread = None
        selection.set_freq_spread(val)
        assert selection.freq_spread == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_quarter1mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_quarter1mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_quarter1mean()
        selection.dc_quarter1mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_quarter1mean(val)
    else:
        assert (selection.get_dc_quarter1mean() == exp) == valid
        selection.dc_quarter1mean = None
        selection.set_dc_quarter1mean(val)
        assert selection.dc_quarter1mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_quarter2mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_quarter2mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_quarter2mean()
        selection.dc_quarter2mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_quarter2mean(val)
    else:
        assert (selection.get_dc_quarter2mean() == exp) == valid
        selection.dc_quarter2mean = None
        selection.set_dc_quarter2mean(val)
        assert selection.dc_quarter2mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_quarter3mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_quarter3mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_quarter3mean()
        selection.dc_quarter3mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_quarter3mean(val)
    else:
        assert (selection.get_dc_quarter3mean() == exp) == valid
        selection.dc_quarter3mean = None
        selection.set_dc_quarter3mean(val)
        assert selection.dc_quarter3mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_dc_quarter4mean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.dc_quarter4mean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_dc_quarter4mean()
        selection.dc_quarter4mean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_dc_quarter4mean(val)
    else:
        assert (selection.get_dc_quarter4mean() == exp) == valid
        selection.dc_quarter4mean = None
        selection.set_dc_quarter4mean(val)
        assert selection.dc_quarter4mean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_cofm(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_cofm = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_cofm()
        selection.freq_cofm = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_cofm(val)
    else:
        assert (selection.get_freq_cofm() == exp) == valid
        selection.freq_cofm = None
        selection.set_freq_cofm(val)
        assert selection.freq_cofm == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_slopemean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_slopemean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_slopemean()
        selection.freq_slopemean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_slopemean(val)
    else:
        assert (selection.get_freq_slopemean() == exp) == valid
        selection.freq_slopemean = None
        selection.set_freq_slopemean(val)
        assert selection.freq_slopemean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_absslopemean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_absslopemean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_absslopemean()
        selection.freq_absslopemean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_absslopemean(val)
    else:
        assert (selection.get_freq_absslopemean() == exp) == valid
        selection.freq_absslopemean = None
        selection.set_freq_absslopemean(val)
        assert selection.freq_absslopemean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_posslopemean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_posslopemean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_posslopemean()
        selection.freq_posslopemean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_posslopemean(val)
    else:
        assert (selection.get_freq_posslopemean() == exp) == valid
        selection.freq_posslopemean = None
        selection.set_freq_posslopemean(val)
        assert selection.freq_posslopemean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_negslopemean(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_negslopemean = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_negslopemean()
        selection.freq_negslopemean = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_negslopemean(val)
    else:
        assert (selection.get_freq_negslopemean() == exp) == valid
        selection.freq_negslopemean = None
        selection.set_freq_negslopemean(val)
        assert selection.freq_negslopemean == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_sloperatio(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_sloperatio = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_sloperatio()
        selection.freq_sloperatio = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_sloperatio(val)
    else:
        assert (selection.get_freq_sloperatio() == exp) == valid
        selection.freq_sloperatio = None
        selection.set_freq_sloperatio(val)
        assert selection.freq_sloperatio == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_sweepuppercent(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_sweepuppercent = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_sweepuppercent()
        selection.freq_sweepuppercent = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_sweepuppercent(val)
    else:
        assert (selection.get_freq_sweepuppercent() == exp) == valid
        selection.freq_sweepuppercent = None
        selection.set_freq_sweepuppercent(val)
        assert selection.freq_sweepuppercent == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_sweepdownpercent(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_sweepdownpercent = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_sweepdownpercent()
        selection.freq_sweepdownpercent = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_sweepdownpercent(val)
    else:
        assert (selection.get_freq_sweepdownpercent() == exp) == valid
        selection.freq_sweepdownpercent = None
        selection.set_freq_sweepdownpercent(val)
        assert selection.freq_sweepdownpercent == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_freq_sweepflatpercent(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_sweepflatpercent = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_sweepflatpercent()
        selection.freq_sweepflatpercent = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_sweepflatpercent(val)
    else:
        assert (selection.get_freq_sweepflatpercent() == exp) == valid
        selection.freq_sweepflatpercent = None
        selection.set_freq_sweepflatpercent(val)
        assert selection.freq_sweepflatpercent == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_maxdelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_maxdelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_maxdelta()
        selection.inflection_maxdelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_maxdelta(val)
    else:
        assert (selection.get_inflection_maxdelta() == exp) == valid
        selection.inflection_maxdelta = None
        selection.set_inflection_maxdelta(val)
        assert selection.inflection_maxdelta == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_mindelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_mindelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_mindelta()
        selection.inflection_mindelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_mindelta(val)
    else:
        assert (selection.get_inflection_mindelta() == exp) == valid
        selection.inflection_mindelta = None
        selection.set_inflection_mindelta(val)
        assert selection.inflection_mindelta == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_maxmindelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_maxmindelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_maxmindelta()
        selection.inflection_maxmindelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_maxmindelta(val)
    else:
        assert (selection.get_inflection_maxmindelta() == exp) == valid
        selection.inflection_maxmindelta = None
        selection.set_inflection_maxmindelta(val)
        assert selection.inflection_maxmindelta == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_mediandelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_mediandelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_mediandelta()
        selection.inflection_mediandelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_mediandelta(val)
    else:
        assert (selection.get_inflection_mediandelta() == exp) == valid
        selection.inflection_mediandelta = None
        selection.set_inflection_mediandelta(val)
        assert selection.inflection_mediandelta == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_meandelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_meandelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_meandelta()
        selection.inflection_meandelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_meandelta(val)
    else:
        assert (selection.get_inflection_meandelta() == exp) == valid
        selection.inflection_meandelta = None
        selection.set_inflection_meandelta(val)
        assert selection.inflection_meandelta == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_standarddeviationdelta(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_standarddeviationdelta = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_standarddeviationdelta()
        selection.inflection_standarddeviationdelta = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_standarddeviationdelta(val)
    else:
        assert (selection.get_inflection_standarddeviationdelta() == exp) == valid
        selection.inflection_standarddeviationdelta = None
        selection.set_inflection_standarddeviationdelta(val)
        assert selection.inflection_standarddeviationdelta == exp
        
@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_inflection_duration(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.inflection_duration = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_inflection_duration()
        selection.inflection_duration = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_inflection_duration(val)
    else:
        assert (selection.get_inflection_duration() == exp) == valid
        selection.inflection_duration = None
        selection.set_inflection_duration(val)
        assert selection.inflection_duration == exp

@pytest.mark.parametrize("val, valid, exp", FLOAT_TEST_VALUES)
def test_step_duration(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.step_duration = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_step_duration()
        selection.step_duration = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_step_duration(val)
    else:
        assert (selection.get_step_duration() == exp) == valid
        selection.step_duration = None
        selection.set_step_duration(val)
        assert selection.step_duration == exp




INT_TEST_VALUES = [
    (-1000, True, -1000),
    (0, True, 0),
    (100, True, 100),
    (100000, True, 100000),
    ("-1000", True, -1000),
    ("-1000.1351351", True, -1000),
    ("-1.00", True, -1),
    ("0", True, 0),
    ("100f", False, None),
    ("-13513ssd", False, None),
]

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_stepup(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_stepup = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_stepup()
        selection.freq_stepup = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_stepup(val)
    else:
        assert (selection.get_freq_stepup() == exp) == valid
        selection.freq_stepup = None
        selection.set_freq_stepup(val)
        assert selection.freq_stepup == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_stepdown(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_stepdown = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_stepdown()
        selection.freq_stepdown = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_stepdown(val)
    else:
        assert (selection.get_freq_stepdown() == exp) == valid
        selection.freq_stepdown = None
        selection.set_freq_stepdown(val)
        assert selection.freq_stepdown == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_numsteps(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_numsteps = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_numsteps()
        selection.freq_numsteps = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_numsteps(val)
    else:
        assert (selection.get_freq_numsteps() == exp) == valid
        selection.freq_numsteps = None
        selection.set_freq_numsteps(val)
        assert selection.freq_numsteps == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_begsweep(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_begsweep = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_begsweep()
        selection.freq_begsweep = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_begsweep(val)
    else:
        assert (selection.get_freq_begsweep() == exp) == valid
        selection.freq_begsweep = None
        selection.set_freq_begsweep(val)
        assert selection.freq_begsweep == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_begup(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_begup = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_begup()
        selection.freq_begup = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_begup(val)
    else:
        assert (selection.get_freq_begup() == exp) == valid
        selection.freq_begup = None
        selection.set_freq_begup(val)
        assert selection.freq_begup == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_begdown(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_begdown = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_begdown()
        selection.freq_begdown = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_begdown(val)
    else:
        assert (selection.get_freq_begdown() == exp) == valid
        selection.freq_begdown = None
        selection.set_freq_begdown(val)
        assert selection.freq_begdown == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_endsweep(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_endsweep = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_endsweep()
        selection.freq_endsweep = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_endsweep(val)
    else:
        assert (selection.get_freq_endsweep() == exp) == valid
        selection.freq_endsweep = None
        selection.set_freq_endsweep(val)
        assert selection.freq_endsweep == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_endup(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_endup = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_endup()
        selection.freq_endup = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_endup(val)
    else:
        assert (selection.get_freq_endup() == exp) == valid
        selection.freq_endup = None
        selection.set_freq_endup(val)
        assert selection.freq_endup == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_freq_enddown(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.freq_enddown = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_freq_enddown()
        selection.freq_enddown = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_freq_enddown(val)
    else:
        assert (selection.get_freq_enddown() == exp) == valid
        selection.freq_enddown = None
        selection.set_freq_enddown(val)
        assert selection.freq_enddown == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsupdown(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsupdown = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsupdown()
        selection.num_sweepsupdown = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsupdown(val)
    else:
        assert (selection.get_num_sweepsupdown() == exp) == valid
        selection.num_sweepsupdown = None
        selection.set_num_sweepsupdown(val)
        assert selection.num_sweepsupdown == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsdownup(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsdownup = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsdownup()
        selection.num_sweepsdownup = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsdownup(val)
    else:
        assert (selection.get_num_sweepsdownup() == exp) == valid
        selection.num_sweepsdownup = None
        selection.set_num_sweepsdownup(val)
        assert selection.num_sweepsdownup == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsupflat(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsupflat = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsupflat()
        selection.num_sweepsupflat = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsupflat(val)
    else:
        assert (selection.get_num_sweepsupflat() == exp) == valid
        selection.num_sweepsupflat = None
        selection.set_num_sweepsupflat(val)
        assert selection.num_sweepsupflat == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsdownflat(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsdownflat = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsdownflat()
        selection.num_sweepsdownflat = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsdownflat(val)
    else:
        assert (selection.get_num_sweepsdownflat() == exp) == valid
        selection.num_sweepsdownflat = None
        selection.set_num_sweepsdownflat(val)
        assert selection.num_sweepsdownflat == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsflatup(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsflatup = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsflatup()
        selection.num_sweepsflatup = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsflatup(val)
    else:
        assert (selection.get_num_sweepsflatup() == exp) == valid
        selection.num_sweepsflatup = None
        selection.set_num_sweepsflatup(val)
        assert selection.num_sweepsflatup == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_sweepsflatdown(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_sweepsflatdown = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_sweepsflatdown()
        selection.num_sweepsflatdown = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_sweepsflatdown(val)
    else:
        assert (selection.get_num_sweepsflatdown() == exp) == valid
        selection.num_sweepsflatdown = None
        selection.set_num_sweepsflatdown(val)
        assert selection.num_sweepsflatdown == exp

@pytest.mark.parametrize("val, valid, exp", INT_TEST_VALUES)
def test_num_inflections(val, valid, exp, selection):
    """Testing the setter and getter"""
    selection.num_inflections = val
    if valid == False:
        with pytest.raises(exception_handler.WarningException):
            selection.get_num_inflections()
        selection.num_inflections = None
        with pytest.raises(exception_handler.WarningException):
            selection.set_num_inflections(val)
    else:
        assert (selection.get_num_inflections() == exp) == valid
        selection.num_inflections = None
        selection.set_num_inflections(val)
        assert selection.num_inflections == exp