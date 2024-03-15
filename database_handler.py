import MySQLdb
from flask_mysqldb import MySQL

class DatabaseHandler:
    def __init__(self, flask_app, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB):
        mysql = MySQL(flask_app)
        self.conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

    )