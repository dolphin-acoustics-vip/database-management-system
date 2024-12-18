import datetime

# Values that signify an "empty string"
EMPTY_CHARACTERS = ["", " ", "\n", "\t"]

DATE_FORMAT = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y%m%d', '%Y%m%dT%H:%M:%S', '%Y%m%dT%H:%M']

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