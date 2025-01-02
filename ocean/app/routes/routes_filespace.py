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
import os
import shutil

# Third-party imports
from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for, session as flask_session
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_required

# Local application imports
from .. import database_handler
from .. import exception_handler
from .. import models
from .. import filespace_handler
from .. import response_handler

routes_filespace = Blueprint('filespace', __name__)

def process_boolean_string(value):
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    else:
        return None

@routes_filespace.route('/filespace/download-orphan-file/', methods=['GET'])
def download_orphan_file():
    from .. import utils
    file_path = request.args.get('file_path')
    deleted = process_boolean_string(request.args.get('deleted'))
    return utils.download_file_from_path(file_path, deleted)

@routes_filespace.route('/filespace/delete-orphan-file/', methods=['DELETE'])
def delete_orphan_file():
    response = response_handler.JSONResponse()
    try:
        file_path = request.args.get('file_path')
        deleted = process_boolean_string(request.args.get('deleted'))
        filespace_handler.delete_orphan_file(file_path, deleted, False)
        response.add_message(f"Deleted orphan file {file_path}")
    except (Exception, SQLAlchemyError) as e:
        response.add_error(exception_handler.handle_exception(exception=e, show_flash=False))
    return response.to_json()

@routes_filespace.route('/filespace/delete-file/<string:file_id>', methods=['DELETE'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def filespace_delete_file(file_id):
    response = response_handler.JSONResponse()
    with database_handler.get_session() as session:
        file_name = None
        try:
            file = session.query(models.File).filter(models.File.id == file_id).first()
            if not file:
                raise exception_handler.WarningException(f"Unknown error ocurred.")
            file_name = file.filename
            file_id = file.id

            if filespace_handler.check_file_exists_in_filespace(file):
                raise exception_handler.WarningException("Cannot delete file record as this would orphan its file in the filespace.")
            else:
                session.delete(file)
                session.commit()
                response.add_message(f"Deleted {file_name}")
        except (Exception, SQLAlchemyError) as e:

            response.add_error(exception_handler.handle_exception(exception=e, prefix=f"Error deleting {file_name}", session=session, show_flash=False))
    return response.to_json()

def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def format_bytes(value):
    if value < 1024:
        return f"{value} bytes"
    elif value < 1024 ** 2:
        return f"{value / 1024:.2f} KB"
    elif value < 1024 ** 3:
        return f"{value / 1024 ** 2:.2f} MB"
    elif value < 1024 ** 4:
        return f"{value / 1024 ** 3:.2f} GB"
    else:
        return f"{value / 1024 ** 4:.2f} TB"


@routes_filespace.route('/filespace/get-broken-links', methods=['GET'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def get_broken_links():
    response = response_handler.JSONResponse()

    deleted = request.args.get('deleted')
    if deleted.lower() == 'true': deleted = True
    elif deleted.lower() == 'false': deleted = False
    else:
        response.add_error("Invalid value for 'deleted' parameter.")
        return response.to_json()

    with database_handler.get_session() as session:
        try:
            broken_links = filespace_handler.query_file_class(session, deleted)
            response.data['brokenLinks'] = broken_links
        except (Exception, SQLAlchemyError) as e:
            response.add_error(exception_handler.handle_exception(exception=e, session=session, show_flash=False))
    return response.to_json()

@routes_filespace.route('/filespace/get-orphaned-files', methods=['GET'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def get_orphaned_files():
    response = response_handler.JSONResponse()

    deleted = process_boolean_string(request.args.get('deleted'))
    if deleted is None: 
        response.add_error("Invalid value for 'deleted' parameter.")
    print(deleted)
    orphaned_files = filespace_handler.get_orphaned_files(deleted, False)
    response.data["orphanedFiles"] = orphaned_files
    print(deleted, response.data)
    return response.to_json()

@routes_filespace.route('/filespace', methods=['GET'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def filespace_view():
    with database_handler.get_session() as session:
        filespace_handler.cleanup_temp_filespace()

        def format_disk_usage(disk_usage):
            total, used, free = disk_usage

            total_formatted = format_bytes(total)
            used_formatted = format_bytes(used)
            free_formatted = format_bytes(free)

            return f"Total: {total_formatted}, Used: {used_formatted}, Free: {free_formatted}"

        storage = format_disk_usage(shutil.disk_usage(database_handler.get_file_space_path()))
    
    file_space_dir = database_handler.get_file_space()
    file_space_size = get_directory_size(file_space_dir)
    formatted_file_space_size = format_bytes(file_space_size)

    trash_dir = database_handler.get_trash_path()
    trash_dir_size = get_directory_size(trash_dir)
    formatted_trash_dir_size = format_bytes(trash_dir_size)

    return render_template('filespace/filespace.html', storage=storage, file_space_size=formatted_file_space_size, trash_dir_size=formatted_trash_dir_size)

def trash_delete_file_helper(file_id):
    """
    A helper function to delete a file from the trash.

    :param file_id: the ID of the file to delete
    :type file_id: str
    """
    with database_handler.get_session() as session:
        try:
            file = session.query(models.File).filter(models.File.id == file_id).first()
            if file:
                file.delete_file()
                session.delete(file)
            session.commit()
        except (Exception, SQLAlchemyError) as e:
            exception_handler.handle_exception(exception=e, session=session)

@routes_filespace.route('/filespace/trash/delete/files', methods=['POST'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def trash_delete_files():
    """
    A route to delete a given list of files from the trash.

    The route takes a list of file IDs from the request form and attempts to delete each of them from the trash.
    It then flashes a success message to the user and redirects them to the trash view.

    :param file_ids: A list of file IDs to delete (passed as an argument to the route)
    :return: A redirect to the trash view
    """
    file_ids=[]
    file_ids_string = request.form['file_ids[]']
    if file_ids_string != "":
        file_ids = file_ids_string.split(",")
    success_counter = 0
    for file_id in file_ids:
        trash_delete_file_helper(file_id)
        success_counter += 1
    flash(f"Deleted {success_counter} files permanently from the trash.", "success")
    return redirect(url_for('filespace.trash_view'))

@routes_filespace.route('/filespace/trash/delete', methods=['GET'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def trash_delete_file():
    """
    A route to delete a single file from the trash.

    The route takes a single file ID from the request arguments and attempts to delete it from the trash.
    It then redirects the user to the trash view.

    :param file_id: The ID of the file to delete from the trash (passed as an argument to the route)
    :return: A redirect to the trash view
    """
    file_id = request.args.get('file_id')
    trash_delete_file_helper(file_id)
    return redirect(url_for('filespace.trash_view'))

@routes_filespace.route('/filespace/trash/send/<string:file_id>', methods=['GET'])
@login_required
@database_handler.exclude_role_2
@database_handler.exclude_role_3
@database_handler.exclude_role_4
def trash_send_file(file_id):
    with database_handler.get_session() as session:
        file = session.query(models.File).filter(models.File.id == file_id).first()
        return send_file(file.get_full_absolute_path(), as_attachment=True)

@routes_filespace.route('/filespace/trash', methods=['GET'])
def trash_view():
    with database_handler.get_session() as session:
        trash_files = session.query(models.File).filter(models.File.deleted == True).all()

    trash_dir = database_handler.get_trash_path()
    trash_dir_size = get_directory_size(trash_dir)
    formatted_trash_dir_size = format_bytes(trash_dir_size)
    if len(trash_files) == 0 and trash_dir_size != 0: formatted_trash_dir_size += " (Expected the trash directory to be empty! The trash directory probably has orphaned files which are not shown in the table below. Consult the manual on how to fix this."
    return render_template('filespace/trash.html', trash_files=trash_files, trash_dir_size=formatted_trash_dir_size)