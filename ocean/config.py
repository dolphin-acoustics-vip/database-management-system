import os
import tempfile
import secrets

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('DEV_STADOLPHINACOUSTICS_USER')}:{os.environ.get('DEV_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('DEV_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('DEV_STADOLPHINACOUSTICS_DATABASE')}"
    DEBUG = True
    secret_key = "not_so_secret_key"
    SECRET_KEY = os.environ.get('SECRET_KEY', secret_key)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('TESTING_STADOLPHINACOUSTICS_USER')}:{os.environ.get('TESTING_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('TESTING_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('TESTING_STADOLPHINACOUSTICS_DATABASE')}"
    WTF_CSRF_ENABLED = False # Disable CSRF (ignore potential CSRF attacks when testing)
    secret_key = "not_so_secret_key"
    SECRET_KEY = os.environ.get('SECRET_KEY', secret_key)

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('PROD_STADOLPHINACOUSTICS_USER')}:{os.environ.get('PROD_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('PROD_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('PROD_STADOLPHINACOUSTICS_DATABASE')}"
    DEBUG = False
    secret_key = secrets.token_urlsafe(32)
    SECRET_KEY = os.environ.get('SECRET_KEY', secret_key)
    SESSION_COOKIE_SECURE = True
