import uuid
import exception_handler

def validate_latitude(value: float | str) -> float:
    """
    Parse a float (or convertable string) value and validate it is between -90 and 90.

    :param value: The float value to validate.

    :return: the parsed float value.

    :raise exception_handler.WarningException: If value is not a float (or convertable string) or value is not between -90 and 90.
    """
    value = validate_float(value)
    if value < -90 or value > 90:
        raise exception_handler.WarningException("Latitude must be between -90 and 90.")
    return value

def validate_longitude(value: float | str) -> float:
    value = validate_float(value)
    if value < -180 or value > 180:
        raise exception_handler.WarningException("Longitude must be between -180 and 180.")
    return value

def validate_float(value: float | str) -> float:
    """
    Parse a float value and validate it is a float.

    :param value: The float value to validate.

    :return: the parsed float value.

    :raise exception_handler.WarningException: If the float value cannot be converted to a float.
    """
    if value is not None:
        try:
            value = float(value)
        except ValueError:
            raise exception_handler.WarningException("Invalid float format.")
    return value

def validate_id(value: str | uuid.UUID) -> str:
    """
    Parse an ID value and validate it is a valid UUID.

    :param value: The ID value to validate.
    
    :return: the parsed ID value as a string.

    :raise exception_handler.WarningException: If the ID value cannot be converted to a UUID.
    """
    if value is not None:
        try:
            uuid.UUID(value)
        except ValueError:
            raise exception_handler.WarningException("Invalid ID format.")
    return str(value)


def validate_timezone(value: int | str) -> int:
    """
    Parse a timezone value and validate it is between GMT-12 and GMT+14 (inclusive). 
    
    :raise exception_handler.WarningException: If the timezone value is not an 
    integer or a string that can be converted to an integer.

    :param value: The timezone value to validate (if passed as string must be convertable to an integer).

    :return: the parsed timezone value.
    """
    if value is not None:
        try:
            value = int(value)
        except ValueError:
            raise exception_handler.WarningException("Timezone must be an integer.")
    if value is not None and (value < -720 or value > 840):
        raise exception_handler.WarningException("Timezone must be between GMT-12 and GMT+14 (inclusive).")
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
