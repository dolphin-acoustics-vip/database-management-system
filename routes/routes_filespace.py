# Third-party imports
from flask import Blueprint, flash,get_flashed_messages, jsonify, redirect,render_template,request, send_file,session, url_for, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from flask_login import login_required

# Local application imports
from database_handler import Session, require_live_session,exclude_role_1,exclude_role_2,exclude_role_3,exclude_role_4
from models import *
from exception_handler import *
import check_filespace


routes_filespace = Blueprint('filespace', __name__)

@routes_filespace.route('/filespace/download-orphan-file', methods=['GET'])
def download_orphan_file():
    file_path = request.args.get('path')
    with database_handler.get_session() as session:
        return send_file(file_path, as_attachment=True)

@routes_filespace.route('/filespace/delete-orphan-file', methods=['GET'])
def delete_orphan_file():
    file_path = request.args.get('path')
    deleted = request.args.get('deleted')
    with database_handler.get_session() as session:
        check_filespace.delete_orphan_file(file_path,deleted)
    return redirect(url_for('filespace.filespace_view'))



@routes_filespace.route('/filespace/delete-file/<string:file_id>', methods=['GET'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
def filespace_delete_file(file_id):
    with database_handler.get_session() as session:
        check_filespace.delete_file_object(file_id)
    return redirect(url_for('filespace.filespace_view'))


@routes_filespace.route('/filespace', methods=['GET'])
@login_required
@exclude_role_2
@exclude_role_3
@exclude_role_4
def filespace_view():
    with database_handler.get_session() as session:
        invalid_links = check_filespace.query_file_class(session, False)
        invalid_deleted_links = check_filespace.query_file_class(session, True)

        orphaned_files = check_filespace.get_orphaned_files(session, False)
        orphaned_deleted_files = check_filespace.get_orphaned_files(session, True)
    
    return render_template('filespace/filespace.html', invalid_links=invalid_links, invalid_deleted_links=invalid_deleted_links, orphaned_files=orphaned_files, orphaned_deleted_files=orphaned_deleted_files, total_disk_space=total_disk_space, used_disk_space=used_disk_space, free_disk_space=free_disk_space)