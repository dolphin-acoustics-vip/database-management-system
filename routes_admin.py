import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import Session
import database
from models import *

routes_admin = Blueprint('admin', __name__)


@routes_admin.route('/admin')
def admin():
    """
    A route decorator that redirects to the admin dashboard page.
    """
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/dashboard')
def admin_dashboard():
    """
    A route decorator for the admin dashboard page. Retrieves data from the database tables DataSource and RecordingPlatform using the session object. Renders the admin dashboard template with the retrieved data lists.
    """
    with Session() as session:
        data_source_list = session.query(DataSource).all()
        recording_platform_list = session.query(RecordingPlatform).all()
        species_list = session.query(Species).all()

        return render_template('admin/admin-dashboard.html', data_source_list=data_source_list, recording_platform_list=recording_platform_list, species_list=species_list)

@routes_admin.route('/admin/data-source/<uuid:data_source_id>/view', methods=['GET'])
def admin_data_source_view(data_source_id):
    """
    Renders the edit data source page for the given data source ID.

    Parameters:
        data_source_id (UUID): The ID of the data source.

    Returns:
        flask.Response: The rendered edit data source page.
    """
    with Session() as session:
        try:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()  
            return render_template('admin/admin-data-source-view.html', data_source=data_source, data_source_type_values  = DataSource.type.type.enums)
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('admin.admin_dashboard'))
        
@routes_admin.route('/admin/data-source/<uuid:data_source_id>/edit', methods=['POST'])
def admin_data_source_edit(data_source_id):
    """
    Updates a data source in the database with the provided data. 

    Parameters:
    data_source_id (uuid): The unique identifier of the data source to be edited.

    Returns:
    Redirect: Redirects to the administration portal after updating the data source.
    """
    with Session() as session:
        try:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()  
            data_source.name = request.form['name']
            data_source.phone_number1 = request.form['phone_number1']
            data_source.phone_number2 = request.form['phone_number2']
            data_source.email1 = request.form['email1']
            data_source.email2 = request.form['email2']
            data_source.address = request.form['address']
            data_source.notes = request.form['notes']
            data_source.type = request.form['source-type']
            session.commit()
            flash('Data source updated: {}'.format(data_source.name), 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/data-source/new', methods=['GET'])
def admin_data_source_new():
    """
    A route decorator that handles GET requests for creating a new data source in the admin panel.
    """
    return render_template('admin/admin-data-source-new.html', data_source_type_values = DataSource.type.type.enums)

@routes_admin.route('/admin/data-source/insert', methods=['POST'])
def admin_data_source_insert():
    """
    A function to handle the insertion of a new data source using form data.
    """
    with Session() as session:
        try:
            # Create a new data source with form data
            new_data_source = DataSource(
                name=request.form['name'],
                phone_number1=request.form['phone_number1'],
                phone_number2=request.form['phone_number2'],
                email1=request.form['email1'],
                email2=request.form['email2'],
                address=request.form['address'],
                notes=request.form['notes'],
                type=request.form['source-type']
            )
            session.add(new_data_source)
            session.commit()
            flash('Data source created: {}'.format(new_data_source.name), 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/data-source/<uuid:data_source_id>/delete', methods=['GET'])
def admin_data_source_delete(data_source_id):
    """
    A function to delete a data source identified by the given data_source_id.
    It removes the data source from the database and redirects to the administration portal.
    
    Parameters:
    data_source_id (uuid): The unique identifier of the data source to be deleted.
    """
    with Session() as session:
        try:
            data_source = session.query(DataSource).filter_by(id=data_source_id).first()
            session.delete(data_source)
            session.commit()
            flash('Data source deleted: {}'.format(data_source.name), 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<uuid:recording_platform_id>/view', methods=['GET'])
def admin_recording_platform_view(recording_platform_id):
    """
    Renders the admin view for a specific recording platform.

    Parameters:
    recording_platform_id (uuid): The unique identifier of the recording platform.

    Returns:
    flask.Response: The rendered HTML template for the admin recording platform view.
    """
    with Session() as session:
        recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()
        return render_template('admin/admin-recording-platform-view.html', recording_platform=recording_platform)

@routes_admin.route('/admin/recording-platform/<uuid:recording_platform_id>/edit', methods=['POST'])
def admin_recording_platform_edit(recording_platform_id):
    """
    A function to edit a recording platform in the admin interface.
    
    Parameters:
    recording_platform_id (str): The UUID of the recording platform to edit.
    
    Returns:
    None
    """
    with Session() as session:
        try:
            recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()
            if request.method == 'POST':
                # Update recording platform with form data
                recording_platform.name = request.form['name']
                session.commit()
                flash('Recording platform updated: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
        return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/new', methods=['GET'])
def admin_recording_platform_new():
    """
    A route decorator for creating a new recording platform in the admin panel.
    """
    return render_template('admin/admin-recording-platform-new.html')

@routes_admin.route('/admin/recording-platform/insert', methods=['POST'])
def admin_recording_platform_insert():
    """
    Create a new recording platform with form data and insert it into the database.
    """
    with Session() as session:
        try:
            new_recording_platform = RecordingPlatform(
                name=request.form['name']
            )
            session.add(new_recording_platform)
            session.commit()
            flash('Recording platform created: {}'.format(new_recording_platform.name), 'success')
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
        return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<uuid:recording_platform_id>/delete', methods=['GET'])
def admin_recording_platform_delete(recording_platform_id):
    """
    A route to delete a recording platform in the admin panel. Takes the recording platform id as a parameter.
    """
    with Session() as session:
        try:
            recording_platform = session.query(RecordingPlatform).filter_by(id=recording_platform_id).first()
            session.delete(recording_platform)
            session.commit()
            flash('Recording platform deleted: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
        return redirect(url_for('admin.admin_dashboard'))


'''
@routes_admin.route('/species/dashboard', methods=['GET'])
def admin_species_dashboard():
    with Session() as session:
        try:
            species_data = session.query(Species).all()
            return render_template('species/species.html', species_list=species_data)
        except Exception as e:
            flash(str(e), 'error')
'''

@routes_admin.route('/admin/species/<uuid:species_id>/view', methods=['GET'])
def admin_species_view(species_id):
    """
    Edit and update species data based on the provided species ID.

    Parameters:
    - species_id: The UUID of the species to edit.

    Returns:
    - If the request method is POST and the species exists, updates the species data and redirects to '/species'.
    - If the species does not exist, flashes an error message and redirects to '/species'.
    - If the request method is not POST, renders the 'edit_species.html' template for editing.
    - In case of exceptions, rolls back the session, flashes an error message, and redirects to '/species'.
    """
    try:
        session = Session()
        species_data = session.query(Species).filter_by(id=species_id).first()
 
        return render_template('admin/admin-species-view.html', species=species_data)
    except Exception as e:
        session.rollback()
        flash(str(e), 'error')
        return redirect(url_for('admin.admin_dashboard'))
    finally:
        session.close()
    
    
@routes_admin.route('/admin/species/<uuid:species_id>/edit', methods=['POST'])
def admin_species_edit(species_id):
    with Session() as session:
        species_data = session.query(Species).filter_by(id=species_id).first()

        if species_data:
            species_name = request.form['species_name']
            genus_name = request.form['genus_name']
            common_name = request.form['common_name']
            species_data.set_species_name(species_name)
            species_data.set_genus_name(genus_name)
            species_data.set_common_name(common_name)
            species_data.update_call(session)
            session.commit()
            #clean_up_root_directory(UPLOAD_FOLDER)
            flash('Species updated: {}'.format(species_name), 'success')
        else:
            flash('Species with ID {} not found'.format(species_id), 'error')
            session.rollback()
        return redirect(url_for('admin.admin_dashboard'))

# Update the route handler to use SQLAlchemy for deleting a species from the table
@routes_admin.route('/admin/species/<uuid:species_id>/delete', methods=['POST'])
def admin_species_delete(species_id):
    try:
        with Session() as session:
            species = session.query(Species).filter_by(id=species_id).first()
            species_name = species.get_species_name()
            session.delete(species)
            session.commit()
            flash('Species deleted: {}'.format(species_name), 'success')
    except SQLAlchemyError as e:
        flash(str(e), 'error')
        session.rollback()
    return redirect(url_for('admin.admin_dashboard'))

    
@routes_admin.route('/admin/species/new', methods=['GET'])
def admin_species_new():
    return render_template('admin/admin-species-new.html')

@routes_admin.route('/admin/species/insert', methods=['POST'])
def admin_species_insert():
    with Session() as session:
        species_name = request.form['species_name']
        genus_name = request.form['genus_name']
        common_name = request.form['common_name']
        try:
            new_species = Species(species_name=species_name, genus_name=genus_name, common_name=common_name)
            session.add(new_species)
            session.commit()
            flash('Species added: {}.'.format(species_name), 'success')
        except SQLAlchemyError as e:
            flash(database.parse_alchemy_error(e), 'error')
            session.rollback()
    return redirect(url_for('admin.admin_dashboard'))

