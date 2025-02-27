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
import hashlib
import io
import uuid, datetime, tempfile
from werkzeug.utils import secure_filename
from flask import send_file

# Third-party imports
import shutil, zipfile, flask

# Local application imports
from . import exception_handler
from . import database_handler


def parse_filename(filename: str):
    """
    Parse a filename into a tuple of (name, extension). If no extension is
    found, the extension will be of type None.
    """
    name, extension = os.path.splitext(filename)
    return name, extension

def stream_zip_file(generator, zip_filename):
    """
    Streams a zip file as a Flask response from a generator of file-like objects and file names.

    :param generator: A generator of tuples of (file_like_object, file_name) to be added to the zip file
    :param zip_filename: The name of the zip file that will be sent
    :return: A Flask Response object containing the zip file
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for file_stream, file_name in generator():
            zip_file.writestr(file_name, file_stream.read())
    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name=zip_filename)
    

def download_files(file_objects, file_names, zip_filename):
    """
    Creates and streams a zip file from the given list of file paths.

    :param file_paths: A list of file paths to add to the zip file.
    :type file_paths: list
    :param zip_filename: The name of the zip file to create.
    :type zip_filename: str
    :return: A response object containing the zip file.
    :rtype: flask.Response
    """
    def generate():
        """
        A generator function that streams the zip file contents.
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_object, file_name in zip(file_objects, file_names):
                # If the file does not exist, create a text entry explaining it
                if not os.path.exists(file_object._path_with_root):
                    error_message = f"The file {file_name} was not found."
                    zipf.writestr(f"ERROR_{secure_filename(file_name)}.txt", error_message)
                    continue
                binary = file_object.get_binary()
                if not file_object.verify_hash():
                    # If the hash does not match, create a text entry explaining the mismatch
                    error_message = f"The hash for {file_name} does not match."
                    zipf.writestr(f"ERROR_{secure_filename(file_name)}.txt", error_message)
                    continue
                # Secure the filename for zip entry
                zipf.writestr(secure_filename(file_name + "." + file_object.extension), binary)
        
        # Move the cursor to the start of the BytesIO object to begin streaming
        zip_buffer.seek(0)

        while chunk := zip_buffer.read(1024 * 1024):  # Read in 1MB chunks
            yield chunk

    return flask.Response(generate(), 
                          mimetype='application/zip', 
                          headers={'Content-Disposition': f'attachment; filename={zip_filename}'})

# def zip_and_download_files(file_paths, zip_filename):
#     """
#     Creates a zip file from the given list of file paths and returns
#     the file as a response object.

#     :param file_paths: A list of file paths to add to the zip file.
#     :type file_paths: list
#     :param zip_filename: The name of the zip file to create.
#     :type zip_filename: str
#     :return: A response object containing the zip file.
#     :rtype: flask.Response
#     """
#     with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
#         with zipfile.ZipFile(os.path.join(temp_dir, zip_filename), 'w') as zipf:
#             for file_path in file_paths:
#                 zipf.write(file_path, os.path.basename(file_path))
#         return flask.send_file(os.path.join(temp_dir, zip_filename), as_attachment=True)

# def download_files(file_paths, file_names, zip_filename):
#     """
#     Creates a zip file from the given list of file paths and returns
#     the file as a response object.

#     :param file_paths: A list of file paths to add to the zip file.
#     :type file_paths: list
#     :param file_names: A list of names to use for the files in the zip file.
#     :type file_names: list
#     :param zip_filename: The name of the zip file to create.
#     :type zip_filename: str
#     :return: A response object containing the zip file.
#     :rtype: flask.Response
#     """
#     with tempfile.TemporaryDirectory(dir=database_handler.get_tempdir()) as temp_dir:
#         new_file_paths = []
#         for file_path, file_name in zip(file_paths, file_names):
#             if not file_name.endswith("."):
#                 file_extension = os.path.splitext(file_path)[1]
#                 new_file_name = f"{file_name}{file_extension}"
#             else:
#                 new_file_name = file_name
#             new_file_path = os.path.join(temp_dir, new_file_name)
#             shutil.copy(file_path, new_file_path)
#             new_file_paths.append(new_file_path)
            
#         return zip_and_download_files(new_file_paths, zip_filename)

def download_file_from_path(path, deleted):
    root = database_handler.get_deleted_space() if deleted else database_handler.get_data_space()
    full_path = os.path.join(root, path)
    if os.path.exists(full_path):
        binary_content = open(full_path, 'rb').read()
        # Create an in-memory binary stream
        file_stream = io.BytesIO(binary_content)

        # Send the file stream as an attachment
        response = flask.send_file(
            file_stream,
            as_attachment=True,
            download_name=secure_filename(os.path.basename(full_path)),  # Custom download filename
        )

        return response
    else:
        raise exception_handler.WarningException("File not found.")

def download_BytesIO(file_stream, filename=None, mimetype='application/octet-stream'):
    file_stream.seek(0)
    return send_file(file_stream, as_attachment=True, download_name=secure_filename(filename) + ".ctr", mimetype=mimetype)

def download_file(file_obj, filename=None, mimetype='application/octet-stream'):
    """
    Takes a file object and sends the file to the user. If the file is to be downloaded
    with a custom name, set `filename`. If the file is to be downloaded with the same
    name as the original, set `filename` to None (default).
    """
    # Generate a custom filename for the download
    custom_filename = filename if filename else file_obj.filename
    if not custom_filename.endswith(file_obj.extension):
        custom_filename = f"{custom_filename}.{file_obj.extension}"

    # Calculate the SHA-256 hash of the file content
    # Compare it to the hash stored in the database
    if not file_obj.verify_hash(): raise exception_handler.WarningException("File hash mismatch. Unable to download file.")

    # Send the file as an attachment and stream it
    return send_file(
        os.path.abspath(file_obj._path_with_root),  # File path
        as_attachment=True,
        download_name=secure_filename(custom_filename),  # Safe filename
        mimetype=mimetype,  # MIME type for binary files
        conditional=True,
    )

def validate_boolean(value: bool | str, field: str, allow_none: bool = False):
    """
    Parse a value to a boolean. Accepted values include "1", "0", 1, 0, "True", "true", "False",
    "false", True and False. If `allow_none` is indicated `True` whitespace values are also
    accepted and return `None`.
    """
    err = exception_handler.ValidationError(field=field, required="Boolean", value=str(value))
    if not allow_none and (value is None or str(value).strip() == ""): raise err
    if allow_none and (value is None or str(value).strip() == ""): return None
    if type(value) != bool:
        if str(value) == "false" or str(value) == "False" or str(value) == "0": return False
        elif str(value) == "true" or str(value) == "True" or str(value) == "1": return True
        else: raise err
    return value

def validate_datetime(value: datetime.datetime | str, field: str, allow_none: bool = False, tzinfo: datetime.tzinfo = datetime.timezone.utc) -> datetime.datetime:
    """
    Parse a datetime (or convertable string) value, returning the parsed datetime
    object. A convertable string is one in the following format
    - '%Y-%m-%dT%H:%M:%S'
    - '%Y-%m-%dT%H:%M'

    :param value: The datetime value to validate (or convertable string).
    :return: the parsed datetime object.
    """
    err = exception_handler.ValidationError(field=field, required="Datetime", value=str(value))
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
    """Parse any float, integer or string representation of a latitude (between -90 and 90 inclusive)."""
    err = exception_handler.ValidationError(field=field, required="Float between -90 and 90 inclusive", value=str(value))
    if not allow_none and value is None: raise err
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    value = validate_float(value, field=field, allow_none=allow_none)
    if value is not None:
        if value < -90 or value > 90:
            raise err
    return value


def validate_longitude(value: float | str | int, field: str, allow_none: bool = False) -> float:
    """Parse any float, integer or string representation of a longitude (between -180 and 180 inclusive)."""
    err = exception_handler.ValidationError(field=field, required="Float between -180 and 180 inclusive", value=str(value))
    if not allow_none and value is None: raise err
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    value = validate_float(value, field=field, allow_none=allow_none)
    if value is not None:
        if value < -180 or value > 180:
            raise err
    return value

def validate_string(value: str, field=None, allow_none = False):
    if not allow_none and (value is None or str(value).strip() == ""): raise exception_handler.ValidationError(field=field, required="String", value=str(value))
    if str(value).strip() == "" and allow_none: return None
    if value is None and allow_none: return None
    if type(value) != str: raise exception_handler.ValidationError(field=field, required="String", value=str(value))
    return str(value).strip()

def validate_float(value: float | str, field=None, allow_none=False) -> float:
    err = exception_handler.ValidationError(field=field, required="Float", value=str(value))
    if not allow_none and value is None: raise err
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    try:
        value = float(value)
    except ValueError:
        raise err
    return float(value)

def validate_int(value: int | str, field=None, allow_none=False) -> int:
    err = exception_handler.ValidationError(field=field, required="Integer", value=str(value))
    if not allow_none and value is None: raise err
    elif type(allow_none) == int and allow_none == 0: return 0
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None): return None
    try:
        value = int(float(value))
    except Exception:
        raise err
    return int(float(value))

def validate_id(value: str | uuid.UUID, field: str, allow_none: bool=False) -> str:
    err = exception_handler.ValidationError(field=field, required="UUID", value=str(value))
    if not allow_none and ((type(value) == str and value.strip() == "") or value is None):
        raise err
    elif allow_none and ((type(value) == str and value.strip() == "") or value is None):
        return None
    try:
        uuid.UUID(str(value))
    except ValueError:
        raise err
    return uuid.UUID(str(value))

def validate_type(value, target_type, field, allow_none=False):
    err = exception_handler.ValidationError(field=field, required=str(target_type), value=str(value))
    if not allow_none and not value: raise err
    if allow_none and not value: return None
    if not isinstance(value, target_type): raise err
    return value
        

def validate_timezone(value: int | str, field: str, allow_none=False) -> float:
    """Parse a timezone value and validate it is between GMT-12 and GMT+14 (inclusive). 
    The timezone is given in minutes before (negative) or after (positive) GMT+0. For
    example, GMT-2 is -120, GMT+1 is +60 and GMT+0 or GMT-0 is 0.
    
    WARNING: do not validate timezones greater than -720 (GMT-12) or less than 840 (GMT+14)
    """
    err = exception_handler.ValidationError(field=field, required="Integer in minutes between -720 and 840", value=str(value))
    if not allow_none and (value is None or str(value).strip() == ""): raise exception_handler.WarningException(f"{field} cannot be empty")
    elif type(value) == int and value == 0: return 0
    elif allow_none and not value or str(value).strip() == "": return None
    try:
        value = int(float(value))
    except Exception:
        raise err
    if value is not None and (value < -720 or value > 840):
        raise err
    return value

import typing

def parse_form(form: typing.Dict[str, typing.Any], schema: typing.Dict[str, bool]):
    data = {}
    missing = []
    for k in schema:
        if k not in form and schema[k] == True:
            missing.append(k)
        elif k in form:
            data[k] = form[k]
    if len(missing) > 0: raise AttributeError(f"The submitted form does not contain the required fields: {', '.join(missing)}")
    return data

# Characters which need to be replaced by an underscore in paths
INVALID_CHARACTERS = ["/","\\","*","?","\"","<",">","|"," ", ":"]

def secure_fname(s: str) -> str:
    if str(s).strip() == "" or s is None: raise exception_handler.CriticalException("File name cannot be secured as it is None.")
    else: 
        s = str(s).strip()
        for c in INVALID_CHARACTERS:
            s = s.replace(c,"_")
        # double check security using in-built Python library
        return secure_filename(s)


def secure_datename(d: datetime.datetime) -> str:
    if str(d).strip() == "" or d is None: raise exception_handler.CriticalException("Datetime is None or empty.")
    if not d or type(d) != datetime.datetime: raise exception_handler.CriticalException(f"Attempting to parse date but invalid format (got {type(d)}).")
    return secure_filename(d.strftime('%Y%m%dT%H%M%S'))

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
        raise exception_handler.WarningException("File is invalid")

    if not os.path.exists(path):
        raise FileNotFoundError("File does not exist")
    
    # Read the file into a pandas DataFrame
    file_extension = os.path.splitext(path)[1].lower()

    if file_extension == '.csv':
        # Read the CSV file into a pandas DataFrame
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError as e:
            raise exception_handler.WarningException("File is empty")
    elif file_extension == '.txt':
        # Read the text file into a pandas DataFrame
        try:
            df = pd.read_csv(path, sep='\t')
        except pd.errors.EmptyDataError as e:
            raise exception_handler.WarningException("File is empty")
    elif file_extension == '.xlsx' or file_extension == '.xls':
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(path)
        if len(df) == 0:
            raise exception_handler.WarningException("File is empty")
    else:
        raise exception_handler.WarningException("File must be a .csv, .txt or .xlsx file")

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


DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

def pretty_date(d: datetime.datetime | None, format=DEFAULT_DATE_FORMAT):
    if not d: return None
    if type(d) != datetime.datetime and type(d) != datetime.date: raise ValueError("Attempting to parse datetime object but not in datetime.datetime format.")
    if type(d) == datetime.date: return d.strftime("%Y-%m-%d")
    else: return d.strftime(format)


def parse_date(date_string: str) -> datetime.datetime:
    """
    This function takes a string and attempts to parse it as a date. This method is used 
    wherever it is necessary to read a date from a filename.
    The date can be in two formats:
    - yyyymmdd_HHMMSS
    - yymmdd-HHMMSS
    
    :param date_string: The string to parse as a date
    :type date_string: str
    :return: The parsed date
    """
    if type(date_string) != str or not date_string: return None
    import re
    date = None
    match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', date_string)
    if not match:
        match = re.search(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', date_string)
        if not match:
            match = re.search(r'(\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', date_string)
            if not match:
                match = re.search(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', date_string)
                if not match:
                    match = re.search(r'(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', date_string)
                    if not match:
                        match = re.search(r'(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', date_string)
                        if not match:
                            match = re.search(r'(\d{2})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})', date_string)
                            if not match:
                                return None
    if len(match.group(1)) == 2: year = int("20" + match.group(1))
    else: year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))
    second = int(match.group(6))
    date = datetime.datetime(year, month, day, hour, minute, second)
    return date


def serialise_object(attributes):
    """
    This function takes an object and a list of its attributes and
    creates a dictionary representation of the object. The dictionary
    will contain the attributes specified in the list as keys, and
    the values of those attributes as the corresponding values.

    If the attribute is a datetime object, it is first converted to
    ISO format before being added to the dictionary. If the attribute
    is a bytes object, it is first converted to a hexadecimal string
    before being added to the dictionary. If the attribute has a
    'to_dict' method, it is called and the result is added to the
    dictionary.

    If the object does not have an attribute with the given name, a
    ValueError is raised.

    :param obj: the object to be serialized
    :param attributes: a list of attributes to be included in the
        serialized representation
    :return: a dictionary containing the serialized object
    """
    def to_camel_case(snake_str):
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    result = {}
    for attr in attributes:
        getter = attributes[attr]
        value = getter()
        if hasattr(value, 'to_dict'):
            value = value.to_dict()
        elif isinstance(value, datetime.datetime):
            value = value.isoformat()
        elif isinstance(value, bytes):
            value = value.hex()

        result[to_camel_case(attr)] = value

    return result

def verify_subarray_of_dict(sub, arr):
    if sub is not None and arr is not None:
        for s in sub:
            if s not in arr:
                raise ValueError(f"Unknown attribute: {s}")
    raise ValueError("Subarray or dict is None")

def validate_enum(value, field, enum, prepare=None, allow_none=False):
    if allow_none and (value is None or str(value).strip() == ""): return None
    if prepare is not None: value = prepare(str(value))
    if value not in enum:
        raise exception_handler.ValidationError(field=field, required=",".join(enum), value=value)
    return value