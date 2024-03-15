import mysql.connector
import os

# Set the connection parameters
MYSQL_HOST = os.environ['STADOLPHINACOUSTICS_HOST']
MYSQL_USER = os.environ['STADOLPHINACOUSTICS_USER']
MYSQL_PASSWORD = os.environ['STADOLPHINACOUSTICS_PASSWORD']
MYSQL_DB = os.environ['STADOLPHINACOUSTICS_DATABASE']

try:
    # Connect to the database
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database="test_database"
    )
    print("Database connection successful.")


    print(MYSQL_HOST,MYSQL_USER,MYSQL_PASSWORD,MYSQL_DB)
    # Create a cursor object
    cursor = conn.cursor()

    # Read the SQL script from the file
    with open('generate_tables.sql', 'r') as file:
        sql_script = file.read()
    print("Executing the following SQL script:")

    # Execute the SQL script
    cursor.execute(sql_script,multi=True)
    print("SQL script executed successfully.")

    # Commit the changes
    conn.commit()

    # Close the cursor and connection
    cursor.close()
    conn.close()
except mysql.connector.Error as err:
    print("ERROR")
    print(err)