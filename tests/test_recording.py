import pytest
import models, exception_handler, datetime, pandas as pd

invalid_datetime_error_message = "invalid date format"

def test_setter_start_time(recording_object: models.Recording):
    test_start_time = datetime.datetime.now()

    valid_str_1 = datetime.datetime.strftime(test_start_time, "%Y-%m-%dT%H:%M:%S")
    valid_str_2 = datetime.datetime.strftime(test_start_time, "%Y-%m-%dT%H:%M")

    invalid_str_1 = datetime.datetime.strftime(test_start_time, "%Y-%m-%dT%H:%M:%S.%f")
    invalid_str_2 = datetime.datetime.strftime(test_start_time, "%Y-%d-%mT%H:%M:%SZ")
    invalid_str_3 = datetime.datetime.strftime(test_start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    invalid_str_4 = "THIS IS NOT A DATE"
    
    with pytest.raises(exception_handler.WarningException) as exc: 
        recording_object.set_start_time(invalid_str_1)
    assert invalid_datetime_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        recording_object.set_start_time(invalid_str_2)
    assert invalid_datetime_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        recording_object.set_start_time(invalid_str_3)
    assert invalid_datetime_error_message in str(exc).lower()

    with pytest.raises(exception_handler.WarningException) as exc:
        recording_object.set_start_time(invalid_str_4)
    assert invalid_datetime_error_message in str(exc).lower()

    recording_object.set_start_time(valid_str_1)
    recording_object.set_start_time(valid_str_2)



def test_upload_selection_table_rows(recording_object, db_session):
    # Create a selection table DataFrame
    selection_table_df = pd.DataFrame({
        'Selection': ['1','2','3'],
        'View': ['Test View 1', 'Test View 2', 'Test View 3'],
        'Channel': [1,2,3],
        'Begin Time (s)': [0.1, 0.2, 0.3],
        'End Time (s)': [0.2, 0.3, 0.4],
        'Low Freq (Hz)': [0.1, 0.2, 0.3],
        'High Freq (Hz)': [0.2, 0.3, 0.4],
        'Annotation': ['Y', 'M', 'N']
    })

    # Call the upload_selection_table_rows method
    recording_object.unpack_selection_table(db_session, selection_table_df)
    db_session.flush()

    # Check that the selection table data was uploaded correctly
    selection_table_data = db_session.query(models.Selection).filter_by(recording_id=recording_object.id).all()
    assert len(selection_table_data) == len(selection_table_df)
    for i, selection in enumerate(selection_table_data):
        assert selection.selection_number == int(selection_table_df.iloc[i]['Selection'])
        assert selection.annotation == selection_table_df.iloc[i]['Annotation']

missing_annotation_warning = "Missing required columns: Annotation".lower()
missing_selection_warning = "Missing required columns: Selection".lower()

def test_upload_selection_table_no_selection(recording_object, db_session):
    selection_table_df = pd.DataFrame({
        'Annotation': ['Y', 'M', 'N'],
        'View': ['Test View 1', 'Test View 2', 'Test View 3'],
        'Channel': [1,2,3],
        'Begin Time (s)': [0.1, 0.2, 0.3],
        'End Time (s)': [0.2, 0.3, 0.4],
        'Low Freq (Hz)': [0.1, 0.2, 0.3],
        'High Freq (Hz)': [0.2, 0.3, 0.4]
    })

    with pytest.raises(exception_handler.WarningException) as exc:
        recording_object.unpack_selection_table(db_session, selection_table_df)
    assert missing_selection_warning in str(exc).lower()

def test_upload_selection_table_no_annotation(recording_object, db_session):
    selection_table_df = pd.DataFrame({
        'Selection': ['1', '2', '3'],
        'View': ['Test View 1', 'Test View 2', 'Test View 3'],
        'Channel': [1,2,3],
        'Begin Time (s)': [0.1, 0.2, 0.3],
        'End Time (s)': [0.2, 0.3, 0.4],
        'Low Freq (Hz)': [0.1, 0.2, 0.3],
        'High Freq (Hz)': [0.2, 0.3, 0.4]
    })

    with pytest.raises(exception_handler.WarningException) as exc:
        recording_object.unpack_selection_table(db_session, selection_table_df)
    assert missing_annotation_warning in str(exc).lower()

def test_upload_selection_table_annotation_invalid(recording_object, db_session):
    selection_table_df = pd.DataFrame({
        'Selection': ['1', '2', '3', '4', '5'],
        'View': ['Test View 1', 'Test View 2', 'Test View 3', 'Test View 4', 'Test View 5'],
        'Channel': [1,2,3,4,5],
        'Begin Time (s)': [0.1, 0.2, 0.3, 0.4, 0.5],
        'End Time (s)': [0.2, 0.3, 0.4, 0.5, 0.6],
        'Low Freq (Hz)': [0.1, 0.2, 0.3, 0.4, 0.5],
        'High Freq (Hz)': [0.2, 0.3, 0.4, 0.5, 0.6],
        'Annotation': ["Y - with a message", "M - with a message", "N - with a message", "2", "Oddball"]
    })

    expected = ["Y","M","N","M","M"]

    # Call the upload_selection_table_rows method
    recording_object.unpack_selection_table(db_session, selection_table_df)
    db_session.flush()

    selection_table_data = db_session.query(models.Selection).filter_by(recording_id=recording_object.id).all()
    assert len(selection_table_data) == len(selection_table_df)
    # When annotation is unknown we automtically insert M
    for i, selection in enumerate(selection_table_data):
        assert selection.annotation == expected[i]



# def test_upload_selection_table_rows_invalid_data(recording_object, db_session):
#     # Create a selection table DataFrame with invalid data
#     selection_table_df = pd.DataFrame({
#         'Selection': [1, 2, 3],
#         'Invalid Column': ['Test Annotation 1', 'Test Annotation 2', 'Test Annotation 3']
#     })

#     # Call the upload_selection_table_rows method
#     with pytest.raises(ValueError):
#         recording_object.upload_selection_table_rows(db_session, selection_table_df)

# def test_upload_selection_table_rows_empty_data(recording_object, db_session):
#     # Create an empty selection table DataFrame
#     selection_table_df = pd.DataFrame()

#     # Call the upload_selection_table_rows method
#     with pytest.raises(ValueError):
#         recording_object.upload_selection_table_rows(db_session, selection_table_df)