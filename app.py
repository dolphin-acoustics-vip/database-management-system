import uuid
import MySQLdb
from flask import Flask, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for
from flask_mysqldb import MySQL
from flask import send_from_directory
import pprint
#import mysql.connector

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
app.config['UPLOAD_FOLDER'] = ''

# Initialize the MySQL extension
mysql = MySQL(app)

@app.route('/')
def hello_world():
    return "Root Page"
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/submit', methods=['POST'])
def submit():
    '''
    username = request.form['username']
    age = int(request.form['age'])
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO Person (Name,Age) VALUES (%s,%s)", (username,age))
    mysql.connection.commit()
    cur.close()

    #file = request.files['test_file']
    #file.save(os.path.join('uploads', file.filename))
    return f'You submitted the username: {username} with age {age}. <a href="/">Go back to home</a>'
    '''
    return


@app.route('/species')
def view_species():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, classification, name FROM species")
    species_data = cur.fetchall()
    cur.close()
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
    cur = mysql.connection.cursor()
    cur.execute("SELECT classification, name FROM species WHERE id = %s", (species_id,))
    species_data = cur.fetchone()
    cur.close()
    
    if request.method == 'POST':
        new_name = request.form['name']
        new_classification = request.form['classification']
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE species SET name = %s, classification = %s WHERE id = %s", (new_name, new_classification, species_id))
        mysql.connection.commit()
        cur.close()
        flash('Successfully updated the element with ID {}'.format(species_id), 'success')
        return redirect('/species')
    
    return render_template('edit_species.html', species=species_data)

# Define a route to clear flashed messages
@app.route('/clear_flashed_messages', methods=['POST'])
def clear_flashed_messages():
    flashed_messages = get_flashed_messages(with_categories=True)  # Retrieve flashed messages
    print("IGOTHERE")
    print(flashed_messages)
    for category, message in flashed_messages:
        print(message)
        session['_flashes'].remove((category, message))  # Remove specific flashed message from the session
        
    return jsonify({'message': 'Flashed messages cleared'})

@app.route('/species/delete/<uuid:species_id>', methods=['POST', 'DELETE'])
def delete_species(species_id):
    if request.method == 'POST' or request.method == 'DELETE':
        try:
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM species WHERE id = %s", (species_id,))
            mysql.connection.commit()
            cur.close()
            flash('Successfully deleted species {}'.format(species_id), 'success')
            return redirect('/species')
        except MySQLdb.IntegrityError as e:
            cur.close()
            flash('Failed to delete the species {}\nError code: {}\nError message: {}'.format(species_id, e.args[0], e.args[1]), 'error')
            return redirect('/species')

    else:
        flash('Failed to delete species {}'.format(species_id), 'error')
        return redirect('/species')
    
@app.route('/species/add', methods=['GET', 'POST'])
def add_species():
    if request.method == 'POST':
        name = request.form['name']
        classification = request.form['classification']
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO species (name, classification) VALUES (%s, %s)", (name, classification))
            mysql.connection.commit()
            flash('Successfully added the species {}!'.format(classification), 'success')
            cur.close()
            return redirect('/species')

        except MySQLdb.IntegrityError as e:
            flash( 'Error: {} {}'.format(e.args[0], e.args[1]), 'error')
            cur.close()
            return redirect('/species')
    return render_template('add_species.html')

       

    


@app.route('/add_encounter', methods=['GET', 'POST'])
def add_encounter():
    if request.method == 'POST':
        location = request.form['location']
        species_id = request.form['species']
        notes = request.form['notes']

        # Insert the encounter data into the database
        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO test_database.encounter (location, notes, species_id) VALUES (%s, %s, %s)",
                        (location, notes, species_id))
            mysql.connection.commit()
            cur.close()
            flash('Encounter added successfully!', 'success')
            return redirect('/encounter')
        except MySQLdb.IntegrityError as e:
            cur.close()
            flash('Error: {} {}'.format(e.args[0], e.args[1]), 'error')
            return redirect('/encounter')

    else:
        # Fetch species data from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, classification, name FROM test_database.species")
        species_list = cur.fetchall()
        cur.close()

        return render_template('add_encounter.html', species_list=species_list)

@app.route('/encounter', methods=['GET'])
def encounter_details():
    # Fetch encounter details from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT e.id, e.location, e.notes, s.classification as species_name FROM test_database.encounter e JOIN test_database.species s ON e.species_id = s.id")
    encounter_list = cur.fetchall()

    if len(encounter_list) < 1:
        cur.execute("SELECT id, classification, name FROM species")
        species_data = cur.fetchall()
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
    cur = mysql.connection.cursor()
    cur.execute("SELECT encounter.id, encounter.location, encounter.notes, encounter.species_id FROM encounter JOIN species ON encounter.species_id = species.id WHERE encounter.id = %s", (encounter_id,))
    encounter_data = cur.fetchone()
    cur.close()
    
    if request.method == 'POST':
        location = request.form['location']
        species_id = request.form['species']
        notes = request.form['notes']

        cur = mysql.connection.cursor()
        cur.execute("UPDATE encounter SET location = %s, species_id = %s, notes = %s WHERE id = %s", (location, species_id, notes, encounter_id))
        mysql.connection.commit()
        cur.close()
        

        cur = mysql.connection.cursor()
        cur.execute("SELECT encounter.id, encounter.location, encounter.notes, species.classification FROM encounter JOIN species ON encounter.species_id = species.id WHERE encounter.id = %s", (encounter_id,))
        encounter_data = cur.fetchone()
        cur.close()
        flash('Successfully updated the element with ID {}'.format(encounter_id), 'success')

        return redirect('/encounter')

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, classification, name FROM test_database.species")
    species_list = cur.fetchall()

    cur.execute("SELECT id,time_start,time_end,recording_file,selection_file,encounter_id FROM test_database.recording WHERE encounter_id = %s", (encounter_id,))
    recordings = cur.fetchall()
    cur.close()


    return render_template('edit_encounter.html', encounter=encounter_data, species_list=species_list,recordings=recordings)


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