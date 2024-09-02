import os
import tempfile

# config.py

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_default_secret_key')
    # Add other general configurations

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ['TESTING_STADOLPHINACOUSTICS_USER']}:{os.environ['TESTING_STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['TESTING_STADOLPHINACOUSTICS_HOST']}/{os.environ['TESTING_STADOLPHINACOUSTICS_HOST']}"
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier testing

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"
    DEBUG = False