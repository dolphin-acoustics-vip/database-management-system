import database_handler
from flask import Flask
import os

app = Flask(__name__)
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'


handler = database_handler.DatabaseHandler(
    app,
    os.environ['STADOLPHINACOUSTICS_HOST'],
    os.environ['STADOLPHINACOUSTICS_USER'],
    os.environ['STADOLPHINACOUSTICS_PASSWORD'],
    os.environ['STADOLPHINACOUSTICS_DATABASE']
)

print(handler.query_species_table())