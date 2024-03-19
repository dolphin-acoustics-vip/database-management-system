import re, uuid, zipfile, os
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.orm import joinedload,sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from db import Session
import database
from models import *

routes_admin = Blueprint('admin', __name__)


@routes_admin.route('/admin/dashboard')
def admin_dashboard():
    """
    A route decorator for the admin dashboard page. Retrieves data from the database tables DataSource and RecordingPlatform using the session object. Renders the admin dashboard template with the retrieved data lists.
    """
    with Session() as session:
        data_source_list = session.query(DataSource).all()
        recording_platform_list = session.query(RecordingPlatform).all()
        return render_template('admin/admin-dashboard.html', data_source_list=data_source_list, recording_platform_list=recording_platform_list)

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
    with Session() as session:
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

