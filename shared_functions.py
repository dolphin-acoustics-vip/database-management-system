from datetime import datetime
import uuid
from flask import session as client_session
from flask import redirect, url_for, render_template, request
from database_handler import db
import exception_handler
from flask_login import login_user,login_required, current_user, login_manager



    

def parse_snapshot_date(date_string):
    formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]
    for date_format in formats:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            pass
    raise ValueError("Invalid date format")



def parse_date(date_string: str) -> datetime:
    """
    This function takes a string and attempts to parse it as a date.
    The date can be in two formats:
    - yyyymmdd_HHMMSS
    - yymmdd-HHMMSS
    
    :param date_string: The string to parse as a date
    :type date_string: str
    :return: The parsed date
    """
    import re
    match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', date_string)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        hour = match.group(4)
        minute = match.group(5)
        second = match.group(6)
        date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
        date = datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
    if not match:
        match = re.search(r'(\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', date_string)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            hour = match.group(4)
            minute = match.group(5)
            second = match.group(6)
            date_string = f"{day}/{month}/{year} {hour}:{minute}:{second}"
            date = datetime.strptime(date_string, '%d/%m/%y %H:%M:%S')

    return date