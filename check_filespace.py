import database_handler
import models
import os
from flask import url_for
from sqlalchemy.exc import SQLAlchemyError


def check_file_orphaned(session, file_path, deleted):
    if deleted:
        rel_path = database_handler.get_trash_path()
    else:
        rel_path = database_handler.get_file_space_path()
    return not models.File.has_record(session, rel_path, file_path)
        

def get_orphaned_files(session, deleted):
    orphaned_files = []
    
    if deleted:
        path = database_handler.get_trash_path()
    else:
        path = database_handler.get_file_space_path()

    # In your code
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if check_file_orphaned(session, file_path, deleted):
                orphaned_files.append({'path': file_path, 'link': url_for('filespace.delete_orphan_file', path=file_path, deleted=deleted), 'download': url_for('filespace.download_orphan_file', path=file_path) , 'deleted': deleted})

    return orphaned_files


import os 

def delete_orphan_file(path, deleted):
    with database_handler.get_session() as session:
        if check_file_orphaned(session, path, deleted):
            if os.path.exists(path):
                os.remove(path)

def query_file_class(session, deleted):
    """
    Query all files in the database and check whether all links to the filespace are valid.
    
    An invalid link is one where a path is defined in the database, but it does not point to a file 
    in the filespace.

    :param session: the SQLAlchemy session
    :param deleted: whether to query deleted files
    :return: a dictionary of invalid files where the key is the file ID and the value is the file object
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

def check_file_exists_in_filespace(file):
    absolute_path = file.get_full_absolute_path()
    if not os.path.exists(absolute_path):
        return False
    else:
        return True

import exception_handler

def delete_file_object(file_id):
    with database_handler.get_session() as session:
        try:
            file = session.query(models.File).filter(models.File.id == file_id).first()
            if check_file_exists_in_filespace(file):
                raise exception_handler.WarningException("Cannot delete file record as this would orphan its file in the filespace.")
            else:
                session.delete(file)
                session.commit()
        except (Exception, SQLAlchemyError) as e:
            exception_handler.handle_exception(session, e)


def get_invalid_links(session, deleted):
    """
    Search through all files in the database and check whether all links to the filespace are valid.

    An invalid link is one where a path is defined in the database, but it does not point to a file 
    in the filespace.
    """

    offset = 0
    orphaned_files = []
    while True:
        files, offset = query_file_class(session, offset, deleted)
        if not files: break
        for file in files:
            if not check_file_exists_in_filespace(file):
                orphaned_files.append(file)
    return orphaned_files


"""

def check_filespace():
    with database_handler.get_session() as session:
        string = ""
        
        orphaned_files = get_orphaned_files(session, deleted = False)
        if orphaned_files:
            string += f"<h1>{len(orphaned_files)} Orphaned files (those which do not have representation in the metadata database).</h1>"

            string += "<ul>"
            for file in orphaned_files:
                string += f"<li>{file}</li>"
            string += "</ul>"
        else:
            string += "<h1>No orphaned files found.</h1>"


        missing_files = get_missing_files(session, False)
        if missing_files:
            string += "<h1>Files missing in the filespace.</h1>"
            string += "<ul>"
            for file in missing_files:
                string += f"<li>{file}</li>"
            string += "</ul>"
        else:
            string += "<h1>No missing files found.</h1>"
        


        deleted_orphaned_files = get_orphaned_files(session, deleted = True)
        if deleted_orphaned_files:
            string += f"<h1>{len(deleted_orphaned_files)} Orphaned deleted files (those which do not have representation in the metadata database).</h1>"

            string += "<ul>"
            for file in deleted_orphaned_files:
                string += f"<li>{file}</li>"
            string += "</ul>"
        else:
            string += "<h1>No orphaned deleted files found.</h1>"

        missing_deleted_files = get_missing_files(session, True)
        if missing_deleted_files:
            string += "<h1>Deleted files missing in the filespace.</h1>"
            string += "<ul>"
            for file in missing_deleted_files:
                string += f"<li>{file}</li>"
            string += "</ul>"
        else:
            string += "<h1>No missing deleted files found.</h1>"
        return string
"""