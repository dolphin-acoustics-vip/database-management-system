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

# third party libraries
from flask import url_for
from sqlalchemy.exc import SQLAlchemyError
import os, datetime

# Local application imports
import database_handler
import models
import exception_handler

def clean_directory(directory: str) -> None:
    """Walk through all folders in a directory and remove any which are empty.
    Note that this method has the potential to destroy metadata stored in
    folder names, however will never delete any files.

    :param root_directory: The root directory to start cleaning
    """
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass

def clean_filespace_temp() -> None:
    """Clean up the temporary filespace by completing three operations.
    The temporary filespace is a location where files are staged during
    the upload process. Sometimes files become orphaned in the event of
    an error and need to be cleaned up.
    1. Remove any temporary files (in models.File) older than 1 day
    2. Remove any orphaned files in the temporary filespace
    3. Remove any empty directories in the temporary filespace
    """

    with database_handler.get_session() as session:
        # Retrieve all temporary files and check that they are less than a day old
        # If they are, delete them
        temp_files = session.query(models.File).filter(models.File.temp == True).all()
        for temp_file in temp_files:
            if temp_file.upload_datetime < (datetime.datetime.now() - datetime.timedelta(days=1)):
                temp_file.delete_file()
                session.delete(temp_file)
                try:
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
        
        # Walk through the temporary filespace and remove any orphaned files
        for root, dirs, files in os.walk(database_handler.get_tempdir(), topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                if check_file_orphaned(session, file_path, False, True):
                    delete_orphan_file(file_path, False, True)
        
        # Remove any empty directories
        clean_directory(database_handler.get_tempdir())

# Legacy
cleanup_temp_filespace = clean_filespace_temp

def check_file_orphaned(session, path: str, deleted: bool, temp: bool) -> None:
    """Check whether a file (identified by the path) is an orphaned file or not. The location of a file depends on
    whether they are in the deleted, temporary, or data filespace. The variables deleted and temp determine this.
    An orphaned file is a file which exists in the filespace but is not referenced by any File object.

    If deleted and temp are false, this function will check if the file exists in the data filespace.
    If deleted and temp are false, this function will check if the file exists in the deleted filespace.
    If temp is true, this function will check if the file exists in the temporary filespace.

    :param session: the SQLAlchemy session
    :param path: the path of the file to check (note that this path is relative (and should not include any context about the trash, temp, or data filespace))
    :param deleted: whether to check in the deleted filespace or not
    :param temp: whether to check in the temporary filespace or not
    :return: True if the file is an orphaned file, False otherwise
    """
    
    return not models.File.has_record(session, path, deleted=deleted, temp=temp)

def get_orphaned_files(session, deleted: bool, temp: bool) -> list:
    """Search through all files in the database and check whether all links to the filespace are valid.
    An invalid link is one where a path is defined in the database, but it does not point to a file 
    in the filespace. The function will only check all files in the database pertaining to one of the
    following categories:
    - If deleted and temp are false, this function will check if the file exists in the data filespace.
    - If deleted and temp are false, this function will check if the file exists in the deleted filespace.
    - If temp is true, this function will check if the file exists in the temporary filespace.

    :param session: the SQLAlchemy session
    :param deleted: whether to query deleted files
    :param temp: whether to query temporary files
    :return: a list of dictionaries of orphaned files where the key is the models.File.id and the value is the models.File object
    """

    orphaned_files = []
    root_path = database_handler.get_root_directory(deleted, temp)
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = os.path.join(root, file)
            if check_file_orphaned(session, file_path, deleted, temp):
                orphaned_files.append({'path': file_path, 'link': url_for('filespace.delete_orphan_file', path=file_path, deleted=deleted), 'download': url_for('filespace.download_orphan_file', path=file_path) , 'deleted': deleted})

    return orphaned_files

def delete_orphan_file(path: str, deleted: bool, temp: bool):
    """Delete an orphaned file in the data, delted, or temp space of the file space. 
    If the file does not exist, do nothing.

    :param path: the path of the file to delete (this will be automatically joined together with the file space root and the sub folder defined by deleted and temp)
    :param deleted: whether to delete in the deleted filespace or not
    :param temp: whether to delete in the temporary filespace or not
    """
    with database_handler.get_session() as session:
        if check_file_orphaned(session, path, deleted, temp):
            if os.path.exists(path):
                os.remove(path)

def query_file_class(session, deleted: bool) -> dict:
    """Query all files in the database and check whether all links to the filespace are valid.
    
    An invalid link is one where a path is defined in the database, but it does not point to a file 
    in the filespace.

    :param session: the SQLAlchemy session
    :param deleted: whether to query deleted files (True) or not (False)
    :return: a dictionary of invalid files where the key is the models.File.id and the value is the models.File object
    """

    invalid_links = {}
    offset = 0
    while True:
        files = session.query(models.File).filter(models.File.deleted == deleted).offset(offset).limit(100).all()
        offset += 100
        if not files:
            break
        for file in files:
            absolute_path = file.get_full_absolute_path()
            if not os.path.exists(absolute_path):
                invalid_links[file.id] = file
                parent = None
                link = None
                delete_link = None

                # Check if the file is referenced by a Recording                
                if session.query(models.Recording).filter(models.Recording.recording_file_id == file.id).first():
                    parent = session.query(models.Recording).filter(models.Recording.recording_file_id == file.id).first()
                    link = url_for('recording.recording_view', recording_id=parent.id)
                # Check if the file is referenced by a Selection
                elif session.query(models.Selection).filter(models.Selection.selection_file_id == file.id).first():
                    parent = session.query(models.Selection).filter(models.Selection.selection_file_id == file.id).first()
                    link = url_for('selection.selection_view', selection_id=parent.id)
                elif session.query(models.Selection).filter(models.Selection.contour_file_id == file.id).first():
                    parent = session.query(models.Selection).filter(models.Selection.contour_file_id == file.id).first()
                    link = url_for('selection.selection_view', selection_id=parent.id)
                elif session.query(models.Selection).filter(models.Selection.ctr_file_id == file.id).first():
                    parent = session.query(models.Selection).filter(models.Selection.ctr_file_id == file.id).first()
                    link = url_for('selection.selection_view', selection_id=parent.id)
                elif session.query(models.Recording).filter(models.Recording.selection_table_file_id == file.id).first():
                    parent = session.query(models.Recording).filter(models.Recording.selection_table_file_id == file.id).first()
                    link = url_for('recording.recording_view', recording_id=parent.id)
                else:
                    delete_link = url_for('filespace.filespace_delete_file', file_id=file.id)

                invalid_links[file.id] = {"file": file, "parent": parent, "link": link, "delete": delete_link}

    return invalid_links

def check_file_exists_in_filespace(file: models.File) -> bool:
    """Checks whether a file object exists in the filespace.

    :param file: The models.File object
    :return: True if the file exists in the filespace, False otherwise
    """

    absolute_path = file.get_full_absolute_path()
    return os.path.exists(absolute_path)


# def get_invalid_links(session, deleted):
#     """
#     Search through all files in the database and check whether all links to the filespace are valid.

#     An invalid link is one where a path is defined in the database, but it does not point to a file 
#     in the filespace.
#     """

#     offset = 0
#     orphaned_files = []
#     while True:
#         files, offset = query_file_class(session, offset, deleted)
#         if not files: break
#         for file in files:
#             if not check_file_exists_in_filespace(file):
#                 orphaned_files.append(file)
#     return orphaned_files