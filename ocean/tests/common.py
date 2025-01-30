import datetime
from ..app import exception_handler
import pytest

# Values that signify an "empty string"
EMPTY_CHARACTERS = ["", " ", "\n", "\t", None, " \n\t "]
INVALID_CHARACTERS = ["/","\\","*","?","\"","<",">","|"," ", ":"]

DATE_FORMAT = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y%m%d', '%Y%m%dT%H:%M:%S', '%Y%m%dT%H:%M']


SELECTION_TABLE = {
    "view": (str, "View", True),
    "channel": (int, "Channel", True),
    "begin_time": (float, "Begin Time (s)", True),
    "end_time": (float, "End Time (s)", True),
    "low_frequency": (float, "Low Freq (Hz)", True),
    "high_frequency": (float, "High Freq (Hz)", True),
    "delta_time": (float, "Delta Time (s)", True),
    "delta_frequency": (float, "Delta Freq (Hz)", True),
    "average_power": (float, "Avg Power Density (dB FS/Hz)", True)
}

CONTOUR_STATISTICS = {
    "freq_max": (float, "FREQMAX", True),
    "freq_min": (float, "FREQMIN", True),
    "duration": (float, "DURATION", True),
    "freq_begin": (float, "FREQBEG", True),
    "freq_end": (float, "FREQEND", True),
    "freq_range": (float, "FREQRANGE", True),
    "dc_mean": (float, "DCMEAN", True),
    "dc_standarddeviation": (float, "DCSTDDEV", True),
    "freq_mean": (float, "FREQMEAN", True),
    "freq_standarddeviation": (float, "FREQSTDDEV", True),
    "freq_median": (float, "FREQMEDIAN", True),
    "freq_center": (float, "FREQCENTER", True),
    "freq_relbw": (float, "FREQRELBW", True),
    "freq_maxminratio": (float, "FREQMAXMINRATIO", True),
    "freq_begendratio": (float, "FREQBEGENDRATIO", True),
    "freq_quarter1": (float, "FREQQUARTER1", True),
    "freq_quarter2": (float, "FREQQUARTER2", True),
    "freq_quarter3": (float, "FREQQUARTER3", True),
    "freq_spread": (float, "FREQSPREAD", True),
    "dc_quarter1mean": (float, "DCQUARTER1MEAN", True),
    "dc_quarter2mean": (float, "DCQUARTER2MEAN", True),
    "dc_quarter3mean": (float, "DCQUARTER3MEAN", True),
    "dc_quarter4mean": (float, "DCQUARTER4MEAN", True),
    "freq_cofm": (float, "FREQCOFM", True),
    "freq_stepup": (int, "FREQSTEPUP", True),
    "freq_stepdown": (int, "FREQSTEPDOWN", True),
    "freq_numsteps": (int, "FREQNUMSTEPS", True),
    "freq_slopemean": (float, "FREQSLOPEMEAN", True),
    "freq_absslopemean": (float, "FREQABSSLOPEMEAN", True),
    "freq_posslopemean": (float, "FREQPOSSLOPEMEAN", True),
    "freq_negslopemean": (float, "FREQNEGSLOPEMEAN", True),
    "freq_sloperatio": (float, "FREQSLOPERATIO", True),
    "freq_begsweep": (int, "FREQBEGSWEEP", True),
    "freq_begup": (int, "FREQBEGUP", True),
    "freq_begdown": (int, "FREQBEGDWN", True),
    "freq_endsweep": (int, "FREQENDSWEEP", True),
    "freq_endup": (int, "FREQENDUP", True),
    "freq_enddown": (int, "FREQENDDWN", True),
    "num_sweepsupdown": (int, "NUMSWEEPSUPDWN", True),
    "num_sweepsdownup": (int, "NUMSWEEPSDWNUP", True),
    "num_sweepsupflat": (int, "NUMSWEEPSUPFLAT", True),
    "num_sweepsdownflat": (int, "NUMSWEEPSDWNFLAT", True),
    "num_sweepsflatup": (int, "NUMSWEEPSFLATUP", True),
    "num_sweepsflatdown": (int, "NUMSWEEPSFLATDWN", True),
    "freq_sweepuppercent": (float, "FREQSWEEPUPPERCENT", True),
    "freq_sweepdownpercent": (float, "FREQSWEEPDWNPERCENT", True),
    "freq_sweepflatpercent": (float, "FREQSWEEPFLATPERCENT", True),
    "num_inflections": (int, "NUMINFLECTIONS", True),
    "inflection_maxdelta": (float, "INFLMAXDELTA", True),
    "inflection_mindelta": (float, "INFLMINDELTA", True),
    "inflection_maxmindelta": (float, "INFLMAXMINDELTA", True),
    "inflection_mediandelta": (float, "INFLMEDIANDELTA", True),
    "inflection_meandelta": (float, "INFLMEANDELTA", True),
    "inflection_standarddeviationdelta": (float, "INFLSTDDEVDELTA", True),
    "inflection_duration": (float, "INFLDUR", True),
    "step_duration": (float, "STEPDUR", True),
}

CONTOUR_FILE = {
    'time_milliseconds': (int, 'Time [ms]', False),
    'peak_frequency': (float, 'Peak Frequency [Hz]', False),
    'duty_cycle': (float, 'Duty Cycle', False),
    'energy': (float, 'Energy', False),
    'window_RMS': (float, 'WindowRMS', False)
}

def equate_timestamps(ts1, ts2):
    return ts1.year == ts2.year and ts1.month == ts2.month and ts1.day == ts2.day and ts1.hour == ts2.hour and ts1.minute == ts2.minute and ts1.second == ts2.second

def parse_timestamp(timestamp: datetime.datetime, format: str) -> tuple[str, datetime.datetime]:
    """Convert timestamp into a format, returning both the
    string-formatted timestamp and a new copy of the timestamp
    with only the information included in the formatted string.

    Args:
        timestamp (datetime.datetime): the timestamp to be formatted
        format (str): the format to use for the formatting
        
    Returns:
        tuple[str, datetime.datetime]: a tuple with the string-formatted timestamp and a new copy of the timestamp with only information included in the formatted string
    """
    time_string = timestamp.strftime(format)
    timestamp = datetime.datetime.strptime(time_string, format)
    return time_string, timestamp

def create_assertion(new, old, exp=None):
    """Create an assertion for the insert and update methods.
    
    `new` is the value of the attribute after calling the method.
    `old` is the value of the attribute before calling the method.
    `exp` is the expected value of the attribute (if `None` the assertion is `old == new`).
    """
    if exp != None and new != None:
        return new == exp
    elif exp == None and not new == None:
        return old == new
    else:
        return new == old

def test_set_attribute(model, attr, value, expected):
    setattr(model, attr, value)
    assert getattr(model, attr) == expected


def test_set_attribute_validation_error(model, attr, value):
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, value)

def validate_uuid(model, attr, uuid, nullable=False):
    import uuid
    
    test_uuid = uuid.uuid4()
    setattr(model, attr, test_uuid)
    assert getattr(model, attr) == test_uuid
    test_uuid = uuid.uuid4()
    setattr(model, attr, str(test_uuid))
    assert getattr(model, attr) == test_uuid
    
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, "this-is-not-a-uuid")
    with pytest.raises(exception_handler.ValidationError):
        setattr(model, attr, 1)
    if nullable:
        setattr(model, attr, None)
        assert getattr(model, attr) == None
    else:
        with pytest.raises(exception_handler.ValidationError):
            setattr(model, attr, None)
