import logging
from logging.handlers import RotatingFileHandler
import pytz
from datetime import datetime
from flask_login import login_user,login_required, current_user, login_manager

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define the timezone
tz = pytz.timezone('UTC')

class TimezoneFormatter(logging.Formatter):

    def format(self, record):
        print(current_user)
        if current_user and current_user.is_authenticated and not hasattr(record, 'user_id'):
            record.user_id = '- (user: ' + current_user.id + ')'
        elif not current_user and not hasattr(record, 'user_id'):
            record.user_id = ' (logged out)'
        
        return super().format(record)

    def formatTime(self, record, datefmt):
        dt = datetime.fromtimestamp(record.created, tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

# Create a file handler
file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024*100, backupCount=20)
file_handler.setLevel(logging.DEBUG)

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
