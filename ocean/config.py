import os
import tempfile
import secrets

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,  # Recycle connections after 5 minutes
        'pool_pre_ping': True,  # Enable the connection pool "pre-ping" feature
        'pool_size': 5,  # Number of connections to keep open in the pool
        'max_overflow': 10,  # Number of connections to allow in connection pool overflow
        'pool_timeout': 30,  # Seconds to wait before giving up on getting a connection
    }

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('DEV_STADOLPHINACOUSTICS_USER')}:{os.environ.get('DEV_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('DEV_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('DEV_STADOLPHINACOUSTICS_DATABASE')}"
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    SESSION_COOKIE_SECURE = True
    JWT_SECRET_KEY = SECRET_KEY
    URL_PREFIX='/ocean'
    
    # secret_key = secrets.token_urlsafe(32)
    # SECRET_KEY = os.environ.get('SECRET_KEY', secret_key)
    # SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    # JWT_SECRET_KEY = secrets.token_urlsafe(32)
    # URL_PREFIX='/ocean'

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('TESTING_STADOLPHINACOUSTICS_USER')}:{os.environ.get('TESTING_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('TESTING_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('TESTING_STADOLPHINACOUSTICS_DATABASE')}"
    WTF_CSRF_ENABLED = False # Disable CSRF (ignore potential CSRF attacks when testing)
    secret_key = "not_so_secret_key"
    SECRET_KEY = os.environ.get('SECRET_KEY', secret_key)

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{os.environ.get('PROD_STADOLPHINACOUSTICS_USER')}:{os.environ.get('PROD_STADOLPHINACOUSTICS_PASSWORD')}@{os.environ.get('PROD_STADOLPHINACOUSTICS_HOST')}/{os.environ.get('PROD_STADOLPHINACOUSTICS_DATABASE')}"
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    SECRET_KEY = "not_a_secret_key"
    SESSION_COOKIE_SECURE = True
    JWT_SECRET_KEY = SECRET_KEY
    URL_PREFIX='/ocean'
