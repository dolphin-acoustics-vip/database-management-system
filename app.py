import uuid
import MySQLdb
from flask import Flask, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for
from flask_mysqldb import MySQL
from flask import send_from_directory
import pprint
from database_handler import *
#import mysql.connector
MySQLdb.Error
import os

app = Flask(__name__)
app.secret_key = 'kdgnwinhuiohji3275y3hbhjex?1'
# NOTE: need to set environment variables
# https://www.hostinger.co.uk/tutorials/linux-environment-variables#:~:text=To%20list%20current%20environment%20variables,both%20environment%20and%20shell%20variables. 
# Configure the database connection
app.config['MYSQL_HOST'] = os.environ['STADOLPHINACOUSTICS_HOST'] 
app.config['MYSQL_USER'] = os.environ['STADOLPHINACOUSTICS_USER'] 
app.config['MYSQL_PASSWORD'] = os.environ['STADOLPHINACOUSTICS_PASSWORD'] 
app.config['MYSQL_DB'] = os.environ['STADOLPHINACOUSTICS_DATABASE'] 
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # return all queries as dict
app.config['MYSQL_SQL_MODE'] = 'STRICT_ALL_TABLES'
app.config['UPLOAD_FOLDER'] = ''

# Initialize the MySQL extension
mysql = MySQL(app)
# Set up the application context
with app.app_context():
    print("I GOT HERE")
    handler = DatabaseHandler(mysql)


@app.route('/')
def hello_world():

    with app.app_context():
        print(handler.query_species_table())
        print(handler.query_species_table_manual("SELECT * FROM species WHERE id=%s",['d246d579-e2b9-11ee-aa64-00155d9e7589']))

    return "Root Page"
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/species')
def view_species():
    species_data = handler.query_species_table(["id","species_name","genus_name","common_name"])
    return render_template('species.html', species_list=species_data)

    
# Route to serve the image file from the resources directory
@app.route('/resources/<path:filename>')
def download_file(filename):
    return send_from_directory('resources', filename)


# Add a route to serve the general-style.css file
@app.route('/static/css/general-style.css')
def serve_general_style():
    return send_from_directory('static/css', 'general-style.css')

# Add a route to serve the hero-section.css file
@app.route('/static/css/hero-section.css')
def serve_hero_section():
    return send_from_directory('static/css', 'hero-section.css')

@app.route('/species/edit/<uuid:species_id>', methods=['GET', 'POST'])
def edit_species(species_id):
    try:
        # Fetch species data from the database
        species_data = handler.query_species_table([],{"id":species_id},one_record=True)
        
        if request.method == 'POST':
            species_name = request.form['species_name']
            genus_name = request.form['genus_name']
            common_name = request.form['common_name']

            handler.update_species_table({"species_name": species_name, "genus_name": genus_name, "common_name": common_name}, species_id)
            flash('Successfully updated the element with ID {}'.format(species_id), 'success')
            return redirect('/species')
    except SQLError as e:
        flash(e.get_error_description(), 'error')
        return redirect('/species')
    return render_template('edit_species.html', species=species_data)

# Define a route to clear flashed messages
@app.route('/clear_flashed_messages', methods=['POST'])
def clear_flashed_messages():
    flashed_messages = get_flashed_messages(with_categories=True)  # Retrieve flashed messages
    for category, message in flashed_messages:
        print(message)
        session['_flashes'].remove((category, message))  # Remove specific flashed message from the session
        
    return jsonify({'message': 'Flashed messages cleared'})

@app.route('/species/delete/<uuid:species_id>', methods=['POST', 'DELETE'])
def delete_species(species_id):
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            species_name = handler.query_species_table(['species_name'],{"id":species_id},one_record=True)['species_name']
            handler.delete_species_table(species_id)
            flash('Successfully deleted species {}'.format(species_name), 'success')
            return redirect('/species')
        except SQLError as e:
            flash(e.get_error_description(), 'error')
            return redirect('/species')

    else:
        flash('Failed to delete species {}'.format(species_id), 'error')
        return redirect('/species')
    
@app.route('/species/add', methods=['GET', 'POST'])
def add_species():
    if request.method == 'POST':
        species_name = request.form['species_name']
        genus_name = request.form['genus_name']
        common_name = request.form['common_name']
        
        try:
            handler.insert_species_table({"species_name": species_name, "genus_name": genus_name, "common_name": common_name})
            flash('Successfully added the species {}!'.format(species_name), 'success')
            return redirect('/species')

        except SQLError as e:
            flash(e.get_error_description(), 'error')
            return redirect('/species')
    return render_template('add_species.html')

       

    


@app.route('/encounter/add', methods=['GET', 'POST'])
def add_encounter():
    if request.method == 'POST':
        encounter_name = request.form['encounter_name']
        location = request.form['location']
        species_id = request.form['species']
        origin = request.form['origin']
        notes = request.form['notes']

        # Insert the encounter data into the database
        try:
            handler.insert_encounter_table({"encounter_name": encounter_name, "location": location, "species_id": species_id, "origin": origin, "notes": notes})
            flash('Encounter added.', 'success')
            return redirect('/encounter')
        except SQLError as e:
            flash(e.get_error_description(), 'error')
            return redirect('/encounter')

    else:

        return render_template('add_encounter.html', species_list=handler.query_species_table())

@app.route('/encounter', methods=['GET'])
def encounter_details():
    # Fetch encounter details from the database
    cur = mysql.connection.cursor()
    encounter_list = handler.query_encounter_table_manual(f"SELECT * FROM {ENCOUNTER} JOIN {SPECIES} ON {ENCOUNTER}.species_id = species.id", [])

    if len(encounter_list) < 1:
        species_data = handler.query_species_table(ALL)
        if len(species_data) < 1:
            return render_template('error.html', error_code=404, error_message='No encounter data found. You cannot add encounter data until there are species to add the encounter for.', goback_link='/home', goback_message="Home")

    return render_template('encounter.html', encounter_list=encounter_list)

@app.route('/encounter/delete/<uuid:encounter_id>', methods=['GET', 'POST','DELETE'])
def delete_encounter(encounter_id):
    if request.method == 'POST' or request.method == 'DELETE':
        print("DELETE ENCOUNTER")
        # Delete the encounter from the database
        try:
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM test_database.encounter WHERE id = %s", (encounter_id,))
            mysql.connection.commit()
            cur.close()
        
            flash(f'Encounter {encounter_id} deleted successfully.', 'success')
            return redirect('/encounter')        
        except MySQLdb.IntegrityError as e:
            cur.close()
            flash(f'Error in deleting encounter {encounter_id}: {e.args[0]} {e.args[1]}', 'error')
            return redirect('/species')
    else:
        # Fetch encounter details before deletion if needed
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM test_database.encounter WHERE id = %s", (encounter_id,))
        encounter = cur.fetchone()
        cur.close()
        return render_template('delete_encounter.html', encounter=encounter)


@app.route('/download_file/<path:filename>')
def download_file_from_uploads(filename):
    if filename!="":
        # Assuming the files are stored in a directory named 'uploads'
        # You may need to adjust the file path based on your actual file storage setup
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        return send_file(file_path, as_attachment=True) 

@app.route('/encounter/edit/<uuid:encounter_id>', methods=['GET','POST'])
def edit_encounter(encounter_id):
    try:
        encounter_data = handler.query_encounter_table(ALL,{"id":encounter_id},one_record=True)

        if request.method == 'POST':
            encounter_name = request.form['encounter_name']
            location = request.form['location']
            species_id = request.form['species']
            origin = request.form['origin']
            notes = request.form['notes']

            handler.update_encounter_table({"encounter_name": encounter_name, "location": location, "species_id": species_id, "origin": origin, "notes": notes}, encounter_id)

            flash('Updated {}'.format(encounter_name), 'success')

            return redirect('/encounter')


        species_list = handler.query_species_table(ALL)
    except SQLError as e:
        flash(e.get_error_description(), 'error')
        return redirect('/encounter')


    return render_template('edit_encounter.html', encounter=encounter_data, species_list=species_list)


@app.route('/add_recording', methods=['POST'])
def add_recording():
    # Move the uploaded files to a relative path within the root folder of your program
    # Example: os.replace(recording_file_path, 'relative_path/' + recording_file.filename)
    cur = mysql.connection.cursor()
    encounter_id= request.form['encounter_id']

    time_start = request.form['time_start']
    # Check if the end time is provided
    if 'time_end' in request.form and request.form['time_end'] != '':
        time_end = request.form['time_end']
    else:
        time_end = None

    print(request.files)
    try:
        new_recording_id = uuid.uuid4().hex
        cur.execute("INSERT INTO test_database.recording (id, time_start, time_end, encounter_id) VALUES (%s, %s, %s, %s)", (str(new_recording_id),time_start, time_end, encounter_id))
        mysql.connection.commit()

        last_inserted_id = str(cur.lastrowid)
        print("LAST INSERTED",last_inserted_id)


        # Check if recording file is provided
        if 'recording_file' in request.files and request.files['recording_file'].filename != '':
            recording_file = request.files['recording_file']
            recording_file_path = 'uploads/'  + str(new_recording_id) + "_" + recording_file.filename
            recording_file.save(recording_file_path)
            cur.execute("UPDATE recording SET recording_file = %s WHERE id = %s", (recording_file_path, new_recording_id))
            mysql.connection.commit()
        else:
            recording_file_path = None

        # Check if selection file is provided
        if 'selection_file' in request.files and request.files['selection_file'].filename != '':
            selection_file = request.files['selection_file']
            selection_file_path = 'uploads/'  + str(new_recording_id) + "_" + selection_file.filename
            selection_file.save(selection_file_path)
            cur.execute("UPDATE recording SET selection_file = %s WHERE id = %s", (selection_file_path, new_recording_id))
            mysql.connection.commit()
        else:
            selection_file_path = None        


        cur.close()
        flash('Successfully added the recording', 'success')
        return redirect(url_for('edit_encounter', encounter_id=encounter_id))
    except MySQLdb.IntegrityError as e:
        flash('Error: {} {}'.format(e.args[0], e.args[1]), 'error')
        return redirect(url_for('edit_encounter', encounter_id=encounter_id))

@app.route('/update_recording/<uuid:encounter_id>/<uuid:recording_id>', methods=['POST'])
def update_recording(encounter_id,recording_id):
    if request.method == 'POST':
        new_start_time = request.form['time_start']
        # Check if the end time is provided
        if 'time_end' in request.form and request.form['time_end'] != '':
            time_end = request.form['time_end']
        else:
            time_end = None

        cur = mysql.connection.cursor()
        # Check if recording file is provided
        if 'recording_file' in request.files and request.files['recording_file'].filename != '':
            recording_file = request.files['recording_file']
            recording_file_path = 'uploads/' + str(recording_id) + "_" + recording_file.filename
            recording_file.save(recording_file_path)
            cur.execute("UPDATE recording SET recording_file = %s WHERE id = %s", (recording_file_path, recording_id))
        else:
            recording_file_path = None

        # Check if selection file is provided
        if 'selection_file' in request.files and request.files['selection_file'].filename != '':
            selection_file = request.files['selection_file']
            selection_file_path = 'uploads/' + str(recording_id) + "_" + selection_file.filename
            selection_file.save(selection_file_path)
            cur.execute("UPDATE recording SET selection_file = %s WHERE id = %s", (selection_file_path, recording_id))
            mysql.connection.commit()
        else:
            selection_file_path = None
        # Update the database with the new recording details (new_start_time, new_end_time, new_recording_file, new_selection_file)
        # You would need to implement the logic to update the database based on your database schema

        # Example of updating the start and end time in the database
        
        cur.execute("UPDATE recording SET time_start = %s, time_end = %s WHERE id = %s", (new_start_time, time_end, recording_id))
        mysql.connection.commit()


        cur.close()

        # Redirect to the edit_encounter page or any other appropriate page after the update
        flash('Successfully updated the recording with ID {}'.format(recording_id), 'success')
        return redirect(url_for('edit_encounter', encounter_id=encounter_id))
    else:
        # Handle the case where the request method is not POST
        # This can include error handling or redirection
        pass

if __name__ == '__main__':
    app.run(debug=True)