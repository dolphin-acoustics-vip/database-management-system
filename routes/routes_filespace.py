# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from flask_login import login_required

# Local application imports
from database_handler import get_session, exclude_role_1, exclude_role_2, exclude_role_3, exclude_role_4, get_file_space, get_file_space_path, get_trash_path
import models
import os
from exception_handler import *
import check_filespace
import shutil

routes_filespace = Blueprint('filespace', __name__)

@routes_filespace.route('/filespace/download-orphan-file', methods=['GET'])
def download_orphan_file():
    file_path = request.args.get('path')
    with get_session() as session:
        return send_file(file_path, as_attachment=True)

@routes_filespace.route('/filespace/delete-orphan-file', methods=['GET'])
def delete_orphan_file():
    file_path = request.args.get('path')
    deleted = request.args.get('deleted')
    with get_session() as session:
        check_filespace.delete_orphan_file(file_path,deleted)
    return redirect(url_for('filespace.filespace_view'))



@routes_filespace.route('/filespace/delete-file/<string:file_id>', methods=['GET'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
def filespace_delete_file(file_id):
    with get_session() as session:
        check_filespace.delete_file_object(file_id)
    return redirect(url_for('filespace.filespace_view'))



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


@routes_filespace.route('/filespace', methods=['GET'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
def filespace_view():
    with get_session() as session:
        invalid_links = check_filespace.query_file_class(session, False)
        invalid_deleted_links = check_filespace.query_file_class(session, True)

        orphaned_files = check_filespace.get_orphaned_files(session, False)
        orphaned_deleted_files = check_filespace.get_orphaned_files(session, True)
    

        def format_disk_usage(disk_usage):
            total, used, free = disk_usage

            total_formatted = format_bytes(total)
            used_formatted = format_bytes(used)
            free_formatted = format_bytes(free)

            return f"Total: {total_formatted}, Used: {used_formatted}, Free: {free_formatted}"

        storage = format_disk_usage(shutil.disk_usage(get_file_space_path()))
    
    file_space_dir = get_file_space()
    file_space_size = get_directory_size(file_space_dir)
    formatted_file_space_size = format_bytes(file_space_size)

    trash_dir = get_trash_path()
    trash_dir_size = get_directory_size(trash_dir)
    formatted_trash_dir_size = format_bytes(trash_dir_size)

    return render_template('filespace/filespace.html', invalid_links=invalid_links, invalid_deleted_links=invalid_deleted_links, orphaned_files=orphaned_files, orphaned_deleted_files=orphaned_deleted_files, storage=storage, file_space_size=formatted_file_space_size, trash_dir_size=formatted_trash_dir_size)


def trash_delete_file_helper(file_id):
    """
    A helper function to delete a file from the trash.

    :param file_id: the ID of the file to delete
    :type file_id: str
    """
    with get_session() as session:
        try:
            file = session.query(models.File).filter(models.File.id == file_id).first()
            if file:
                file.delete_file()
                session.delete(file)
            session.commit()
        except (Exception, SQLAlchemyError) as e:
            handle_exception(session, e)

@routes_filespace.route('/filespace/trash/delete/files', methods=['POST'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
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
@exclude_role_2
@exclude_role_3
@exclude_role_4
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
@exclude_role_2
@exclude_role_3
@exclude_role_4
def trash_send_file(file_id):
    with get_session() as session:
        file = session.query(models.File).filter(models.File.id == file_id).first()
        return send_file(file.get_full_absolute_path(), as_attachment=True)

@routes_filespace.route('/filespace/trash', methods=['GET'])
def trash_view():
    with get_session() as session:
        trash_files = session.query(models.File).filter(models.File.deleted == True).all()

    trash_dir = get_trash_path()
    trash_dir_size = get_directory_size(trash_dir)
    formatted_trash_dir_size = format_bytes(trash_dir_size)
    if len(trash_files) == 0 and trash_dir_size != 0: formatted_trash_dir_size += " (Expected the trash directory to be empty! The trash directory probably has orphaned files which are not shown in the table below. Consult the manual on how to fix this."
    return render_template('filespace/trash.html', trash_files=trash_files, trash_dir_size=formatted_trash_dir_size)