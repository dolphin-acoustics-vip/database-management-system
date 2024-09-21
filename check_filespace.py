import database_handler
import models
import os

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
            if not models.File.has_record(session, path, deleted, file_path):
                orphaned_files.append(file_path)

    return orphaned_files

def get_missing_files(session, deleted):
    offset = 0
    orphaned_files = []
    while True:
        files = session.query(models.File).filter(models.File.deleted == deleted).offset(offset).limit(100).all()
        offset += 100
        if not files:
            break
        for file in files:
            absolute_path = file.get_full_absolute_path()
            if not os.path.exists(absolute_path):
                orphaned_files.append(absolute_path)
    return orphaned_files

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