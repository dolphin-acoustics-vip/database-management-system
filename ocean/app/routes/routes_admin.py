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
from .. import transaction_handler

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
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            # Update a DataSource object with form data
            data_source = session.query(models.DataSource).filter_by(id=data_source_id).first()  
            data_source.update(request.form)
            session.commit()
            response.add_message('Data source updated: {}'.format(data_source.name))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/data-source/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_new():
    return render_template('admin/admin-data-source-new.html', data_source_type_values = models.DataSource.type.type.enums)

@routes_admin.route('/admin/data-source/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_insert():
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            data_source = models.DataSource()
            data_source.insert(request.form)
            session.add(data_source)
            session.commit()
            flash('Data source created: {}'.format(data_source.name), 'success')
            response.set_redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
        return response.to_json()

@routes_admin.route('/admin/data-source/<data_source_id>/delete', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_data_source_delete(data_source_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            data_source = session.query(models.DataSource).filter_by(id=data_source_id).first()
            session.delete(data_source)
            session.commit()
            flash('Data source deleted: {}'.format(data_source.name), 'success')
            response.set_redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/recording-platform/<recording_platform_id>/view', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_recording_platform_view(recording_platform_id):
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
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            recording_platform = session.query(models.RecordingPlatform).filter_by(id=recording_platform_id).first()
            recording_platform.update(request.form)
            session.commit()
            response.add_message('Recording platform updated: {}'.format(recording_platform.name))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

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
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            new_recording_platform = models.RecordingPlatform()
            session.add(new_recording_platform)
            new_recording_platform.insert(request.form)
            session.commit()
            flash(f'Recording platform created: {new_recording_platform.name}', 'success')
            response.set_redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

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
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            species = session.query(models.Species).with_for_update().filter_by(id=species_id).first()
            if not species: raise exception_handler.CriticalException('Unexpected error')
            species.update(request.form)
            session.commit()
            species.apply_updates()
            
            response.add_message(f"Species updated: {species.scientific_name}")
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/species/<species_id>/delete', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_delete(species_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            species = session.query(models.Species).filter_by(id=species_id).first()
            if not species: raise exception_handler.CriticalException('Unexpected error')
            scientific_name = species.scientific_name
            species.prepare_for_delete()
            session.delete(species)
            session.commit()
            flash('Species deleted: {}'.format(scientific_name), 'success')
            response.set_redirect(request.referrer)
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/species/new', methods=['GET'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_new():
    return render_template('admin/admin-species-new.html')

@routes_admin.route('/admin/species/insert', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.require_live_session
def admin_species_insert():
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        try:
            species = models.Species()
            species.insert(request.form)
            session.add(species)
            session.commit()
            flash(f'Species inserted: {species.scientific_name}', 'success')
            response.set_redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

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

            user.update(request.form, current_user)
            # update_or_insert_user(user, request)
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
            user.insert(request.form)
            # update_or_insert_user(user, request)
            session.commit()
            response.set_redirect(url_for('admin.admin_user'))
            flash('User inserted: {}'.format(user.name), 'success')
    except Exception as e:
        response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_admin.route('/admin/user/<user_id>/set-api-password', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.exclude_role_2
@database_handler.require_live_session
def admin_user_set_api_password(user_id):
    password = request.form.get('password')
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            user = session.query(models.User).filter_by(id=user_id).first()
            user.set_api_password(password)
        response.set_redirect(request.referrer)
    return response.to_json()

@routes_admin.route('/admin/user/<user_id>/revoke-api', methods=['POST'])
@database_handler.exclude_role_4
@database_handler.exclude_role_3
@database_handler.exclude_role_2
@database_handler.require_live_session
def admin_user_revoke_api(user_id):
    with response_handler.json_response_context() as response:
        with transaction_handler.atomic() as session:
            user = session.query(models.User).filter_by(id=user_id).first()
            user.revoke_api()
        response.set_redirect(request.referrer)
    return response.to_json()

# @routes_admin.route('/admin/user/<user_id>/add-api-key', methods=['POST'])
# @database_handler.exclude_role_4
# @database_handler.exclude_role_3
# @database_handler.exclude_role_2
# @database_handler.require_live_session
# def admin_user_add_api_key(user_id):
#     with response_handler.json_response_context() as response:
#         with transaction_handler.atomic() as session:
#             user = session.query(models.User).filter_by(id=user_id).first()
#             api_key = models.ApiKey()
#             api_key.insert({'user_id': user.id})
#             session.add(api_key)
#             session.commit()
#         response.set_redirect(request.referrer)
#     return response.to_json()

# @routes_admin.route('/admin/user/<api_key_id>/remove-api-key', methods=['POST'])
# @database_handler.exclude_role_4
# @database_handler.exclude_role_3
# @database_handler.exclude_role_2
# @database_handler.require_live_session
# def admin_user_remove_api_key(api_key_id):
#     password = request.form.get('password')
#     with response_handler.json_response_context() as response:
#         with transaction_handler.atomic() as session:
#             api_key = session.query(models.ApiKey).filter_by(id=api_key_id).first()
#             session.delete(api_key)
#             session.commit()
#         response.set_redirect(request.referrer)
#     return response.to_json()