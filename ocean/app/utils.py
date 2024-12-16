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
import uuid, datetime, tempfile

# Third-party imports
import shutil, zipfile, flask

# Local application imports
from . import exception_handler
from . import database_handler

def zip_and_download_files(file_paths, zip_filename):
    """
    Creates a zip file from the given list of file paths and returns
    the file as a response object.

    :param file_paths: A list of file paths to add to the zip file.
    :type file_paths: list
    :param zip_filename: The name of the zip file to create.
    :type zip_filename: str
    :return: A response object containing the zip file.
    :rtype: flask.Response
    """
    with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
        with zipfile.ZipFile(os.path.join(temp_dir, zip_filename), 'w') as zipf:
            for file_path in file_paths:
                zipf.write(file_path, os.path.basename(file_path))
        return flask.send_file(os.path.join(temp_dir, zip_filename), as_attachment=True)

def download_files(file_paths, file_names, zip_filename):
    """
    Creates a zip file from the given list of file paths and returns
    the file as a response object.

    :param file_paths: A list of file paths to add to the zip file.
    :type file_paths: list
    :param file_names: A list of names to use for the files in the zip file.
    :type file_names: list
    :param zip_filename: The name of the zip file to create.
    :type zip_filename: str
    :return: A response object containing the zip file.
    :rtype: flask.Response
    """
    with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
        new_file_paths = []
        for file_path, file_name in zip(file_paths, file_names):
            if not file_name.endswith("."):
                file_extension = os.path.splitext(file_path)[1]
                new_file_name = f"{file_name}{file_extension}"
            else:
                new_file_name = file_name
            new_file_path = os.path.join(temp_dir, new_file_name)
            shutil.copy(file_path, new_file_path)
            new_file_paths.append(new_file_path)
            
        return zip_and_download_files(new_file_paths, zip_filename)
    
def download_file(file_obj, file_name_generator=None):
    """
    Takes a file object and sends the file to the user. Before doing so,
    uses the file_name_generator() method passed to rename the file during
    export.
    """
    with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
        file_path = os.path.join(temp_dir, file_name_generator() if file_name_generator else file_obj.filename)
        if not file_path.endswith(file_obj.extension): file_path = f"{file_path}.{file_obj.extension}"
        shutil.copy(file_obj.get_full_absolute_path(), file_path)
        return flask.send_file(file_path, as_attachment=True)


def validate_datetime(value: datetime.datetime | str, field: str, allow_none: bool = False, tzinfo: datetime.tzinfo = datetime.timezone.utc) -> datetime.datetime:
    """
    Parse a datetime (or convertable string) value, returning the parsed datetime
    object. A convertable string is one in the following format
    - '%Y-%m-%dT%H:%M:%S'
    - '%Y-%m-%dT%H:%M'

    :param value: The datetime value to validate (or convertable string).
    :return: the parsed datetime object.
    """
    if not allow_none and value is None: raise exception_handler.WarningException(f"Field '{field}' cannot be None.")
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    
    if type(tzinfo) != datetime.timezone:
        raise ValueError(f"Field '{field}' requires tzinfo to be datetime.tzinfo or a subclass thereof (currently {type(tzinfo)}).")

    if type(value) == str:
        try:
            value_naive = datetime.datetime.fromisoformat(value)
            value_aware = datetime.datetime(value_naive.year, value_naive.month, value_naive.day, value_naive.hour, value_naive.minute, value_naive.second, tzinfo=tzinfo)
        except ValueError:
            raise exception_handler.WarningException(f"Field '{field}' when given value as a string must be in standard ISO format.")
        except OverflowError:
            raise exception_handler.WarningException(f"Field '{field}' out of range.")
    elif type(value) != datetime.datetime:
        raise exception_handler.WarningException(f"Field '{field}' must be of type aware datetime.datetime or str")
    elif value.tzinfo is None:
        value_naive = value
        value_aware = datetime.datetime(value_naive.year, value_naive.month, value_naive.day, value_naive.hour, value_naive.minute, value_naive.second, tzinfo=tzinfo)
    else:
        value_aware = value

    return value_aware

def validate_latitude(value: float | str | int, field: str, allow_none: bool = False) -> float:
    """ Validate a given value as a latitude. This involves checking whether
    the provided float (if given a a string, converted to a float) fits within
    the bounds defining latitude (-90 to 90 inclusive). 

    Args:
        value (float | str | int): the latitude to be validated (if a string, it must be in a convertable format for float)
        field (str): the name of the field being validated (used in exception messages)
        allow_none (bool, optional): whether the value can be None. Defaults to False.

    Raises:
        ValueError: if the value is not a valid float nor latitude
        ValueError: if the value is None when `allow_none` is False

    Returns:
        float: the validated latitude in float format
    """
    if not allow_none and value is None: raise exception_handler.WarningException(f"Field '{field}' cannot be None.")
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    value = validate_float(value, field=field, allow_none=allow_none)
    if value is not None:
        if value < -90 or value > 90:
            raise exception_handler.WarningException(f"Field '{field}' must be between -90 and 90.")
    return value


def validate_longitude(value: float | str | int, field: str, allow_none: bool = False) -> float:
    """ Validate a given value as a longitude. This involves checking whether
    the provided float (if given a a string, converted to a float) fits within
    the bounds defining longitude (-180 to 180 inclusive).

    Args:
        value (float | str): the longitude to be validated
        field (str): the name of the field being validated
        allow_none (bool, optional): whether `value` can be `None`. Defaults to False.

    Raises:
        ValueError: if `value` is not a valid float nor longitude
        ValueError: if `value` is `None` when `allow_none` is False

    Returns:
        float: the validated longitude in float format
    """
    if not allow_none and value is None: raise exception_handler.WarningException(f"Field '{field}' cannot be None.")
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    value = validate_float(value, field=field, allow_none=allow_none)
    if value is not None:
        if value < -180 or value > 180:
            raise exception_handler.WarningException(f"Field '{field}' must be between -90 and 90.")
    return value


def validate_float(value: float | str, field=None, allow_none=False) -> float:
    """
    Parse a float value and validate it is a float.

    :param value: The float value to validate.

    :return: the parsed float value.

    :raise exception_handler.WarningException: If the float value cannot be converted to a float.
    """
    if not allow_none and value is None: raise exception_handler.WarningException(f"Field '{field}' cannot be None.")
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    try:
        value = float(value)
    except ValueError:
        raise exception_handler.WarningException(f"Field '{field}' must be of type float.")
    return float(value)

def validate_id(value: str | uuid.UUID, field: str, allow_none: bool=False) -> str:
    """Validate a value is a valid UUID

    Args:
        value (str | uuid.UUID): the value to be validated
        field (str, optional): the name of the field being validated.
        allow_none (bool, optional): whether `value` can be `None `or empty. Defaults to False.

    Raises:
        ValueError: if the value is not a valid UUID
        ValueError: if the value is `None` and `allow_none` is False

    Returns:
        str: the validated UUID in str format
    """
    if not allow_none and ((type(value) == str and value.strip() == "") or value is None):
        raise exception_handler.WarningException(f"Field '{field}' cannot be none or empty.")
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None):
        return None
    try:
        uuid.UUID(str(value))
    except ValueError:
        raise exception_handler.WarningException(f"Field '{field}' must be a valid UUID.")
    return uuid.UUID(str(value))

def validate_type(value, target_type, field, allow_none=False):
    """Validate the type of a value

    Args:
        value (Any): the value to validate
        target_type (Any): a type to match with the value (e.g. str, int, Object)
        field (str): the name of the field being validated (to be used in exception messages)
        allow_none (bool, optional): whether an exception should be thrown if the value is None. Defaults to False.

    Raises:
        ValueError: if the value is not of the target type
        WarningException: if the value is `None` or empty and `allow_none` is False

    Returns:
        target_type: the validated value
    """
    if not allow_none and not value: raise exception_handler.WarningException(f"{field} cannot be empty")
    if allow_none and not value: return None
    if not isinstance(value, target_type): raise ValueError(f"{field} must be of type {target_type}")
    return value
        

def validate_timezone(value: int | str, field: str, allow_none=False) -> float:
    """Parse a timezone value and validate it is between GMT-12 and GMT+14 (inclusive). 
    The timezone is given in minutes before (negative) or after (positive) GMT+0. For
    example, GMT-2 is -120, GMT+1 is +60 and GMT+0 or GMT-0 is 0.
    
    WARNING: do not validate timezones greater than -720 (GMT-12) or less than 840 (GMT+14)
    
    Args:
        value (int | str): the timezone to be validated (if passed as a string it must be in an integer format, if passed as a string or string any decimal points are truncated)
        field (str): the name of the field being validated
        allow_none (bool, optional): whether `value` can be `None`. Defaults to False.

    Raises:
        ValueError: if the value is not a valid integer or is not between -720 and +840
        ValueError: if the value is `None` and `allow_none` is False

    Returns:
        int: the validated timezone
    
    """

    if not allow_none and not value: raise exception_handler.WarningException(f"{field} cannot be empty")
    elif type(value) == int and value == 0: return 0
    elif allow_none and not value or str(value).strip() == "": return None
    try:
        value = int(float(value))
    except Exception:
        raise exception_handler.WarningException(f"Field '{field}' must be a valid timezone in integer minutes.")
    if value is not None and (value < -720 or value > 840):
        raise exception_handler.WarningException(f"Field '{field}' must be a timezone between -720 and +840 (inclusive).")
    return value



def get_form_data(request, schema):
    """
    Retrieves form data from the current request and validates it against the provided schema.

    :param schema: The schema to validate the form data against.
    :type schema: dict {form data key: form data type}

    :return data: The form data as a dictionary.

    :raises ValueError: If any required keys are missing or if the data type of any key does not match the schema.
    """
    data = request.form.to_dict()
    errors = []

    for key, value in schema.items():
        if key not in data:
            errors.append(f"Missing key: {key}")
        else:
            try:
                data[key] = value(data[key])
            except ValueError:
                errors.append(f"Invalid data type for key: {key}. Expected {value.__name__}")

    if errors:
        raise ValueError("\n".join(errors))

    return data


import pandas as pd, os

def extract_to_dataframe(path:str) -> pd.DataFrame:
    """
    Produce a Pandas dataframe from a CSV, TSV or Excel file.

    :raises FileNotFoundError: if the given path does not have a file to be parsed.
    :raises ValueError: if the given file is invalid.

    :param path: the path to the file to be parsed
    """
    if type(path) != str:
        raise FileNotFoundError("Path is not a string")
    
    if path is None or path == "":
        raise ValueError("File is invalid")

    if not os.path.exists(path):
        raise FileNotFoundError("File does not exist")
    
    # Read the file into a pandas DataFrame
    file_extension = os.path.splitext(path)[1].lower()

    if file_extension == '.csv':
        # Read the CSV file into a pandas DataFrame
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError as e:
            raise ValueError("File is empty")
    elif file_extension == '.txt':
        # Read the text file into a pandas DataFrame
        try:
            df = pd.read_csv(path, sep='\t')
        except pd.errors.EmptyDataError as e:
            raise ValueError("File is empty")
    elif file_extension == '.xlsx' or file_extension == '.xls':
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(path)
        if len(df) == 0:
            raise ValueError("File is empty")
    else:
        raise ValueError("Unsupported file format. Please provide a .csv, .txt or .xlsx file")

    return df

def extract_args(arg, datatype=str, allow_empty=False):
    value = flask.request.args.get(arg)
    if value is None and not allow_empty:
        raise ValueError(f"Missing argument: {arg}")
    else:
        try:
            return datatype(value)
        except ValueError:
            raise ValueError(f"Invalid value for argument: {arg}")
        
        
def parse_string_notempty(value:str, field:str) -> str:
    """Parse a value and validate that it is neither None nor
    an empty string. Empty strings include all "" and those which
    have whitespace such as " " or "\t" or "\n". If the value is
    valid then it is converted to a string and stripped of whitespace.

    Args:
        value (str): the value to be parsed
        field (str): the name of the field being parsed

    Raises:
        ValueError: value is None
        ValueError: value is an empty string

    Returns:
        str: the value as a string with no whitespace
    """
    if value is None:
        raise exception_handler.WarningException(f"Field '{field}' cannot be null.")
    if str(value).strip() == "":
        raise exception_handler.WarningException(f" Field '{field}' cannot be empty.")
    else:
        return str(value).strip()


DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M'

def pretty_date(d: datetime.datetime | None, format=DEFAULT_DATE_FORMAT):
    if not d: return None
    if type(d) != datetime.datetime: raise ValueError("Attempting to parse datetime object but not in datetime.datetime format.")
    return d.strftime(format)
