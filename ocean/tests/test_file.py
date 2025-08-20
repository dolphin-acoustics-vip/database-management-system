import hashlib
from pytest import fixture
import pytest
import os, shutil
from os.path import join

from . import common
from . import factories
from ..app import models
from ..app import database_handler



FILESPACE = "ocean/tests/resources/filespace"
BASE_DIR = "ocean/tests/resources/files"

def trash_path(relative_directory = None, relative_filename = None):
    return os.path.join(FILESPACE, "trash", relative_directory, relative_filename)

def data_path(relative_directory = None, relative_filename = None):
    return os.path.join(FILESPACE, "data", relative_directory, relative_filename)


@fixture
def filespace():
    def handle_remove_readonly(func, path, exc_info):
        import stat
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                os.chmod(os.path.join(root, dir), stat.S_IWUSR)
            for file in files:
                os.chmod(os.path.join(root, file), stat.S_IWUSR)
        # Try the operation again
        func(path)

    if os.path.exists(FILESPACE):
        # Try to remove read-only files and handle permission errors
        shutil.rmtree(FILESPACE, onerror=handle_remove_readonly)

    os.makedirs(FILESPACE, exist_ok=True)
    database_handler.FILE_SPACE_PATH = FILESPACE
    yield FILESPACE

    # Cleanup after test
    if os.path.exists(FILESPACE):
        shutil.rmtree(FILESPACE, onerror=handle_remove_readonly)

@fixture
def text_file():
    with open(os.path.join(BASE_DIR, "test.txt"), "rb") as f:
        yield f

@fixture
def text_file_path():
    return os.path.join(BASE_DIR, "test.txt")
    
@fixture
def text_file_object(text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension="txt")
    return file

@fixture
def wav_file():
    with open(os.path.join(BASE_DIR, "test.wav"), "rb") as f:
        yield f

@fixture
def csv_file():
    with open(os.path.join(BASE_DIR, "test.csv"), "rb") as f:
        yield f

def test_file_insert(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension="txt")
    assert os.path.exists(data_path("dir1", "file1.txt"))
    assert file.filename_with_extension == "file1.txt"

def test_file_insert_no_extension(filespace, text_file_path):
    file = factories.FileFactory()
    file.insert(text_file_path, "dir1", "file1")
    assert os.path.exists(data_path("dir1", "file1.txt"))
    assert file.filename_with_extension == "file1.txt"

def test_path_with_root(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension = "txt")
    assert file.path == join("dir1", "file1.txt")
    assert file.filename_with_extension == "file1.txt"
    assert file._path_with_root == join(data_path("dir1", "file1.txt"))

def test_file_insert_duplicate(filespace, text_file):
    """Test that adding two files to the same location does not overwrite"""
    file1 = factories.FileFactory()
    file2 = factories.FileFactory()
    file1.insert(text_file, "dir1", "file1", extension= "txt")
    file2.insert(text_file, "dir1", "file1", extension= "txt")
    assert os.path.exists(data_path("dir1", "file1.txt"))
    assert os.path.exists(data_path("dir1", "file1-1.txt"))
    assert file1.filename_with_extension == "file1.txt"
    assert file1.path == join("dir1", "file1.txt")
    assert file2.filename_with_extension == "file1-1.txt"

def test_file_mark_for_deletion():
    file = factories.FileFactory()
    file.mark_for_deletion()
    assert file.to_be_deleted == True

def test_file_not_mark_for_deletion():
    file = factories.FileFactory()
    assert file.to_be_deleted == False or not file.to_be_deleted

@pytest.mark.parametrize("c", common.INVALID_CHARACTERS)
def test_file_insecure_filename(filespace, c: str, text_file):
    file = factories.FileFactory()
    file.insert(text_file, directory = f"dir{c}1", filename = f"file{c}1", extension = "txt")
    assert file.filename_with_extension == "file_1.txt"

def test_file_move(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension = "txt")
    src = data_path("dir1", "file1.txt")
    assert os.path.exists(src)
    file._move("dir2", "file2")
    dst = data_path("dir2", "file2.txt")
    assert not os.path.exists(src)
    assert os.path.exists(dst)

def test_file_move_already_exists(filespace, text_file):
    file1 = factories.FileFactory()
    file1.insert(text_file, "dir1", "file1", extension = "txt")
    file2 = factories.FileFactory()
    file2.insert(text_file, "dir1", "file2", extension = "txt")
    file1._move("dir1", "file2")
    assert os.path.exists(data_path("dir1", "file2.txt"))
    assert os.path.exists(data_path("dir1", "file2-1.txt"))
    assert not os.path.exists(data_path("dir1", "file1"))

def test_file_move_delete(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file2", extension = "txt")
    assert os.path.exists(data_path("dir1", "file2.txt"))
    file._move("dir1", "file2", delete = True)
    assert os.path.exists(trash_path("dir1", file.filename_with_extension))
    assert not os.path.exists(data_path("dir1", "file2.txt"))

def test_file_delete(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file2", extension = "txt")
    assert os.path.exists(data_path("dir1", "file2.txt"))
    file._delete()
    assert os.path.exists(trash_path("dir1", file.filename_with_extension))
    assert not os.path.exists(data_path("dir1", "file2.txt"))

def test_file_hash(filespace, text_file_path):
    file = factories.FileFactory()
    file.insert(text_file_path, "dir1", "file1", extension = "txt")
    with open(text_file_path, "rb") as f:
        assert hashlib.sha256(f.read()).digest() ==  file.calculate_hash() 

def test_verify_hash(filespace, text_file):
    exp = hashlib.sha256(text_file.read()).digest()
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension = "txt")
    assert file.verify_hash(fix = False) == True

def test_rollback(filespace, text_file):
    file = factories.FileFactory()
    file.insert(text_file, "dir1", "file1", extension = "txt")
    assert os.path.exists(data_path("dir1", "file1.txt"))
    file.rollback()
    assert not os.path.exists(data_path("dir1", "file2.txt"))
    assert not os.path.exists(trash_path("dir1", file.filename_with_extension))

