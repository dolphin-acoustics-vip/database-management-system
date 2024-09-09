import uuid
import exception_handler
import datetime

def validate_datetime(value: datetime.datetime | str, field=None, allow_empty=False) -> datetime.datetime:
    """
    Parse a datetime (or convertable string) value, returning the parsed datetime
    object. A convertable string is one in the following format
    - '%Y-%m-%dT%H:%M:%S'
    - '%Y-%m-%dT%H:%M'

    :param value: The datetime value to validate (or convertable string).
    :return: the parsed datetime object.
    """

    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None

    msg_sfx = "." if type(value) == str else ""

    if type(value) == str:
        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')  # Modify the format to include milliseconds
        except ValueError:
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')  # Try without seconds
            except ValueError:
                raise exception_handler.WarningException(f"Invalid date format{msg_sfx}")
    elif type(value) != datetime.datetime:
        raise exception_handler.WarningException(f"Invalid date format{msg_sfx}")
    return value

def validate_latitude(value: float | str, field=None, allow_empty=False) -> float:
    """
    Parse a float (or convertable string) value and validate it is between -90 and 90.

    :param value: The float value to validate.

    :return: the parsed float value.

    :raise exception_handler.WarningException: If value is not a float (or convertable string) or value is not between -90 and 90.
    """
    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None

    msg_sfx="." if field is None else f" in {field}"

    value = validate_float(value, field=field, allow_empty=allow_empty)
    if value is not None:
        if value < -90 or value > 90:
            raise exception_handler.WarningException(f"Latitude must be between -90 and 90{msg_sfx}")
    return value


def validate_longitude(value: float | str, field=None, allow_empty=False) -> float:
    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None

    msg_sfx = "." if field is None else f" in {field}"

    value = validate_float(value, field=field, allow_empty=allow_empty)
    if value is not None:
        if value < -180 or value > 180:
            raise exception_handler.WarningException(f"Longitude must be between -180 and 180{msg_sfx}")
        return value
    else: 
        return None

def validate_float(value: float | str, field=None, allow_empty=False) -> float:
    """
    Parse a float value and validate it is a float.

    :param value: The float value to validate.

    :return: the parsed float value.

    :raise exception_handler.WarningException: If the float value cannot be converted to a float.
    """


    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None
    
    msg_sfx = "." if field is None else f" in {field}"
    if value is not None:
        try:
            value = float(value)
        except ValueError:
            raise exception_handler.WarningException(f"Invalid float format{msg_sfx}")
    return value

def validate_id(value: str | uuid.UUID, field=None, allow_empty=False) -> str:
    """
    Parse an ID value and validate it is a valid UUID.

    :param value: The ID value to validate.
    
    :return: the parsed ID value as a string.

    :raise exception_handler.WarningException: If the ID value cannot be converted to a UUID.
    """
    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None

    msg_sfx = "." if field is None else f" in {field}"

    if value is not None:
        try:
            uuid.UUID(str(value))
        except ValueError:
            raise exception_handler.WarningException(f"Invalid ID format{msg_sfx}")
    return str(value)


def validate_timezone(value: int | str, field=None, allow_empty=False) -> int:
    """
    Parse a timezone value and validate it is between GMT-12 and GMT+14 (inclusive). 
    
    :raise exception_handler.WarningException: If the timezone value is not an 
    integer or a string that can be converted to an integer.

    :param value: The timezone value to validate (if passed as string must be convertable to an integer).

    :return: the parsed timezone value.
    """

    if allow_empty and ((type(value) == str and value.strip() == "") or value is None):
        return None
    
    msg_sfx = "." if field is None else f" in {field}"

    if value is not None:
        try:
            value = int(value)
        except ValueError:
            raise exception_handler.WarningException(f"Timezone must be an integer{msg_sfx}")
    if value is not None and (value < -720 or value > 840):
        raise exception_handler.WarningException(f"Timezone must be between GMT-12 and GMT+14 (inclusive){msg_sfx}")
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