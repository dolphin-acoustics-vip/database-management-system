import logging
from logging.handlers import RotatingFileHandler
import pytz, os
from datetime import datetime
from flask import send_file
from flask_login import login_user,login_required, current_user, login_manager

log_dir = 'logs'


class CustomRotatingFileHandler(RotatingFileHandler):

    def getFiles():
        return os.listdir(log_dir)
    
    def get_log(self, num_lines=None):
        with open(self.baseFilename, 'r') as f:
            lines = f.readlines()
            if num_lines is not None:
                return ''.join(lines[-num_lines:])
            else:
                return ''.join(lines)

    def clear_logs(self):
        files = self.getFiles()
        for file in files:
            os.remove(file)

    


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)


# Define the timezone
tz = pytz.timezone('UTC')

class TimezoneFormatter(logging.Formatter):

    def format(self, record):
        if current_user and current_user.is_authenticated and not hasattr(record, 'user_id'):
            record.user_id = '- (user: ' + current_user.id + ')'
        elif not current_user and not hasattr(record, 'user_id'):
            record.user_id = ' (logged out)'
        
        return super().format(record)

    def formatTime(self, record, datefmt):
        dt = datetime.fromtimestamp(record.created, tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")



# Create a file handler
file_handler = CustomRotatingFileHandler(os.path.join(log_dir,'app.log'), mode='w')
file_handler.setLevel(logging.DEBUG)

def delete_files():
    file_handler.delete_files()

def get_log(num_lines=None):
    return file_handler.get_log(num_lines=num_lines)

def send_log_file():
    return send_file(file_handler.baseFilename)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)

# Create a formatter and set it for the handlers
formatter = TimezoneFormatter('%(asctime)s - %(name)s - %(levelname)s %(user_id)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)