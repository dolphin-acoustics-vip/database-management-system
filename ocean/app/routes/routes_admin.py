# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

# Standard library imports
from datetime import datetime, timedelta
import uuid

# Third-party imports
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

# Local application imports
from .. import database_handler
from .. import models
from .. import exception_handler
from .. import logger
from .. import response_handler

routes_admin = Blueprint('admin', __name__)

@routes_admin.route('/admin', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
def admin():
    """
    Route to redirect root to the admin_dashboard() page.
    PERMISSIONS: Role 1, Role 2.
    """
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/dashboard', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
def admin_dashboard():
    """
    Route for the admin dashboard page.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET
    """
    # TODO: split the data source, recording platform, and species editing, into different subpages
    with database_handler.get_session() as session:
        data_source_list = session.query(models.DataSource).all()
        recording_platform_list = session.query(models.RecordingPlatform).all()
        species_list = session.query(models.Species).all()
        return render_template('admin/admin-dashboard.html', data_source_list=data_source_list, recording_platform_list=recording_platform_list, species_list=species_list)

@routes_admin.route('/admin/logger', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.exclude_role_2
def admin_logger():
    log_string = logger.get_log(200)
    log_string_html = log_string.strip().replace('\n', '<br>')
    return render_template('admin/admin-logger.html', log_string=log_string_html)

@routes_admin.route('/admin/logger/download', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.exclude_role_2
def admin_logger_download_log():
    return logger.send_log_file()

@routes_admin.route('/admin/data-source/<data_source_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_view(data_source_id):
    """
    Route for viewing a specific data source in the admin panel.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET
    """
    with database_handler.get_session() as session:
        try:
            data_source = session.query(models.DataSource).filter_by(id=data_source_id).first()  
            return render_template('admin/admin-data-source-view.html', data_source=data_source, data_source_type_values  = models.DataSource.type.type.enums)
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('admin.admin_dashboard'))
        
@routes_admin.route('/admin/data-source/<data_source_id>/edit', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_edit(data_source_id):
    """
    Update the data for a data source in the admin panel.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            # Update a DataSource object with form data
            data_source = session.query(models.DataSource).filter_by(id=data_source_id).first()  
            data_source.set_name(request.form['name'])
            data_source.set_phone_number1(request.form['phone_number1'])
            data_source.set_phone_number2(request.form['phone_number2'])
            data_source.set_email1(request.form['email1'])
            data_source.set_email2(request.form['email2'])
            data_source.set_address(request.form['address'])
            data_source.set_notes(request.form['notes'])
            data_source.set_type(request.form['source-type'])
            session.commit()
            response.add_message('Data source updated: {}'.format(data_source.name))
        except SQLAlchemyError as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/data-source/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_new():
    """
    Route for the new data source page.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    return render_template('admin/admin-data-source-new.html', data_source_type_values = models.DataSource.type.type.enums)

@routes_admin.route('/admin/data-source/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_insert():
    """
    Route to insert a new data source into the database. 
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    
    Requires a form with the following input fields (text input unless otherwise stated):
    - name
    - phone_number1
    - phone_number2
    - email1
    - email2
    - address
    - notes
    - source-type (dropdown of enum('person','organisation')); NOT NULL
    """
    with database_handler.get_session() as session:
        try:
            # Create a new data source with form data
            new_data_source = models.DataSource(
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
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/data-source/<data_source_id>/delete', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_delete(data_source_id):
    """
    Route to delete a DataSource object given its ID. 
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        try:
            data_source = session.query(models.DataSource).filter_by(id=data_source_id).first()
            session.delete(data_source)
            session.commit()
            flash('Data source deleted: {}'.format(data_source.name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
            
    return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<recording_platform_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_view(recording_platform_id):
    """
    Route to view a RecordingPlatform object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        try:
            recording_platform = session.query(models.RecordingPlatform).filter_by(id=recording_platform_id).first()  
            return render_template('admin/admin-recording-platform-view.html', recording_platform=recording_platform)
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('admin.admin_dashboard'))
        
@routes_admin.route('/admin/recording-platform/<recording_platform_id>/edit', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_edit(recording_platform_id):
    """
    Route to update a RecordingPlatform object, given its ID and an HTTP form request with the following fields:
    - name (text) NOT NULL
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST
    """
    with database_handler.get_session() as session:
        try:
            recording_platform = session.query(models.RecordingPlatform).filter_by(id=recording_platform_id).first()
            recording_platform.name = request.form['name']
            session.commit()
            flash('Recording platform updated: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_new():
    """
    Route for viewing the page to create a new RecordingPlatform object.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET
    """
    return render_template('admin/admin-recording-platform-new.html')

@routes_admin.route('/admin/recording-platform/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_insert():
    """
    Route to create a new RecordingPlatform object, given an HTTP form request with the following fields:
    - name (text) NOT NULL
    PERMISSIONS: Role 1, Role 2.
    METHODS: POST.
    """
    with database_handler.get_session() as session:
        try:
            new_recording_platform = models.RecordingPlatform(
                name=request.form['name']
            )
            session.add(new_recording_platform)
            session.commit()
            flash('Recording platform created: {}'.format(new_recording_platform.name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/recording-platform/<recording_platform_id>/delete', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_delete(recording_platform_id):
    """
    Route to delete a RecordingPlatform object from the database, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        try:
            recording_platform = session.query(models.RecordingPlatform).filter_by(id=recording_platform_id).first()
            session.delete(recording_platform)
            session.commit()
            flash('Recording platform deleted: {}'.format(recording_platform.name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

@routes_admin.route('/admin/species/<species_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_view(species_id):
    """
    Route to open the edit page for a Species object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        try:
            session = database_handler.get_session()
            species_data = session.query(models.Species).filter_by(id=species_id).first()
            return render_template('admin/admin-species-view.html', species=species_data)
        except Exception as e:
            exception_handler.handle_exception(exception=e, session=session)
            return redirect(url_for('admin.admin_dashboard'))
    
@routes_admin.route('/admin/species/<species_id>/edit', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_edit(species_id):
    """
    Route to update a Species object with new values, given a form with the following fields:
    - species_name (text) NOT NULL
    - genus_name (text)
    - common_name (text)
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with database_handler.get_session() as session:
        #session.execute(sqlalchemy.text("LOCK TABLE species WRITE"))
        species_data = session.query(models.Species).with_for_update().filter_by(id=species_id).first()
        if species_data:
            try:
                species_name = request.form['species_name']
                genus_name = request.form['genus_name']
                common_name = request.form['common_name']
                species_data.set_species_name(species_name)
                species_data.set_genus_name(genus_name)
                species_data.set_common_name(common_name)
                session.commit()
                species_data.update_call()
                flash('Species updated: {}'.format(species_name), 'success')
            except (SQLAlchemyError,Exception) as e:
                exception_handler.handle_exception(exception=e, session=session)
        else:
            flash('Species with ID {} not found'.format(species_id), 'error')
            session.rollback()

    return redirect(url_for('admin.admin_dashboard'))


@routes_admin.route('/admin/species/<species_id>/delete', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_delete(species_id):
    """
    Route to delete a Species object, give its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    with database_handler.get_session() as session:
        try:
            species = session.query(models.Species).filter_by(id=species_id).first()
            species_name = species.get_species_name()
            session.delete(species)
            session.commit()
            flash('Species deleted: {}'.format(species_name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
        finally:
            return redirect(url_for('admin.admin_dashboard'))

    
@routes_admin.route('/admin/species/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_new():
    """
    Route to render the new Species template.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    return render_template('admin/admin-species-new.html')

@routes_admin.route('/admin/species/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_insert():
    """
    Route to create a new Species object, given an HTTP form request with:
    - species_name (text) NOT NULL
    - genus_name (text)
    - common_name (text)
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST
    """
    with database_handler.get_session() as session:
        species_name = request.form['species_name']
        genus_name = request.form['genus_name']
        common_name = request.form['common_name']
        try:
            new_species = models.Species(species_name=species_name, genus_name=genus_name, common_name=common_name)
            session.add(new_species)
            session.commit()
            flash('Species added: {}.'.format(species_name), 'success')
        except SQLAlchemyError as e:
            exception_handler.handle_exception(exception=e, session=session)
    return redirect(url_for('admin.admin_dashboard'))



@routes_admin.route('/admin/user', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_user():
    """
    Route to render the template to view all users.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        users = session.query(models.User).order_by(models.User.is_active.desc()).all()
        return render_template('admin/admin-user.html', users=users)
    
    
@routes_admin.route('/admin/user/<user_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_user_view(user_id):
    """
    Route to view info on a particular User object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        user = session.query(models.User).filter_by(id=user_id).first()
        roles = session.query(models.Role).all()
        return render_template('admin/admin-user-view.html', user=user, roles=roles,datetime=datetime)
    

def update_or_insert_user(user, request):
    """ Update or insert a User object. `request.form` must contain the following information:
    - name (text) NOT NULL
    - role (int) NOT NULL
    - expiry (date)

    Args:
        session (_type_): the database session
        user (_type_): the User object (can be a newly created user if inserting)
        request (_type_): the HTTP request (must have form data)

    Returns:
        _type_: _description_
    """
    if user:
        if 'login_id' in request.form:
            user.set_login_id(request.form['login_id'])

        user.set_name(request.form['name'])

        if current_user == user and current_user.role_id == 1:
            if request.form['role'] != '1':
                raise exception_handler.WarningException('Role cannot be changed for the current logged in user.')
        user.set_role_id(request.form['role'])

        if 'expiry' in request.form:
            if user == current_user and datetime.strptime(request.form['expiry'], '%Y-%m-%d') < datetime.now():
                raise exception_handler.WarningException('Expiry date cannot be in the past for the current logged in user.')
            else:
                user.set_expiry(request.form['expiry'])

        is_active = False
        # This logic is required because is_active is a checkbox
        # so if it is not checked it will not appear in the HTTP request.
        if 'is_active' in request.form:
            is_active = True
        if 'is_active' not in request.form and user == current_user:
            is_active = True
            raise exception_handler.WarningException('User cannot be deactivated for the current logged in user.')
        
        user.activate() if is_active else user.deactivate()
    else:
        raise exception_handler.WarningException('Unexpected error')
    
@routes_admin.route('/admin/user/<user_id>/update', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_user_update(user_id):
    """
    Route to complete an UPDATE operation on a User object, given its ID.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    response = response_handler.JSONResponse()
    try:
        with database_handler.get_session() as session:
            user = session.query(models.User).filter_by(id=user_id).first()
            update_or_insert_user(user, request)
            session.commit()
            response.set_redirect(url_for('admin.admin_user'))
            flash('User updated: {}'.format(user.name), 'success')
    except Exception as e:
        response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

    
@routes_admin.route('/admin/user/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_user_new():
    """
    Route to show the page where the admin can add a new user.
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: GET.
    """
    with database_handler.get_session() as session:
        roles=session.query(models.Role).all()
        default_date = datetime.now() + timedelta(days=365)

    return render_template('admin/admin-user-new.html',roles=roles,default_date=default_date)    

@routes_admin.route('/admin/user/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_user_insert():
    """
    Route to insert a new user into the database through the User class.
    The data for the user should be given in a request. See update_or_insert_user()
    PERMISSIONS: Role 1, Role 2.
    RESTRICTIONS: Live session.
    METHODS: POST.
    """
    response = response_handler.JSONResponse()
    try:
        with database_handler.get_session() as session:
            user = models.User()
            session.add(user)
            update_or_insert_user(user, request)
            session.commit()
            response.set_redirect(url_for('admin.admin_user'))
            flash('User inserted: {}'.format(user.name), 'success')
    except Exception as e:
        response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()