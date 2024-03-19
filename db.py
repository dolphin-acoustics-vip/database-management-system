from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy.orm import joinedload,sessionmaker
import os


db = SQLAlchemy(session_options={"autoflush": False})

app = Flask(__name__)
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'

# Configure the database connection using SQLAlchemy and MariaDB
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqldb://{os.environ['STADOLPHINACOUSTICS_USER']}:{os.environ['STADOLPHINACOUSTICS_PASSWORD']}@{os.environ['STADOLPHINACOUSTICS_HOST']}/{os.environ['STADOLPHINACOUSTICS_DATABASE']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'

db.init_app(app)

# Create the engine and session within a route or a view function
with app.app_context():
    engine = db.get_engine()
    Session = sessionmaker(bind=engine, autoflush=False)

