import pytest
from . import factories



def test_hasattr_updated_by_id():
    """Test if the Species object has the updated_by_id attribute"""
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "set_updated_by_id") == True

def test_updated_by_id():
    """Test that the """
    selection = factories.SpeciesFactory()
    assert selection.updated_by_id == None
    selection.set_updated_by_id("1")
    assert selection.updated_by_id == "1"
    selection.set_updated_by_id("15")
    assert selection.updated_by_id == "15"

def test_hasattr_update_call():
    selection = factories.SpeciesFactory()
    assert hasattr(selection, "update_call") == True


# def test_contour_stats():
#     root_path = "ocean/tests/resources/contour-stats/test1"

#     for folder in os.listdir(root_path):
#         if "test" in folder:
#             path = os.path.join(root_path, folder)
#             _test_folder(path, db_session, selection_object)


# def _test_folder(path, db_session, selection_object):
#     if "RoccaContourStats.xlsx" not in os.listdir(path):
#         pytest.fail(f"The following folder does not contain RoccaContourStats.xlsx: {path}")

#     contour_stats_df = utils.extract_to_dataframe(os.path.join(path, "RoccaContourStats.xlsx"))
#     for file in os.listdir(path):
#         if file.endswith(".csv"):
#             _test_file(path, file, contour_stats_df, db_session, selection_object)


# def _test_file(path, file, contour_stats_df, db_session, selection_object):
#     match = re.search(r'sel_(\d+)', file)
#     if not match:
#         pytest.fail(f"The following file name does not contain 'sel_##': {file} in {path}")
#     sel_number = int(match.group(1))


#     contour_file_obj = contour_statistics.ContourFile(os.path.join(path, file),sel_number)
#     contour_file_obj.calculate_statistics(db_session, selection_object)

    
#     db_session.flush()

#     row = contour_stats_df.loc[contour_stats_df['SelectionNumber'] == sel_number]
#     if len(row) == 0:
#         pytest.fail(f"Could not find contour stats for selection {sel_number} in {path}")
    
#     calculated_contour_stats = selection_object.generate_contour_stats_dict()

#     _assert_contour_stats(path, row, calculated_contour_stats, sel_number)

# import pytest

# def _assert_contour_stats(path, row, calculated_contour_stats, sel_number):
#     for contour_stat in calculated_contour_stats:
#         if contour_stat == "SelectionNumber" or contour_stat == "SELECTIONNUMBER" or contour_stat == "Encounter" or contour_stat == "Recording" or contour_stat == "Location" or contour_stat == "Project" or contour_stat == "Species" or contour_stat == "SamplingRate": 
#             continue
#         if contour_stat not in row.columns:
#             pytest.fail(f"Header '{contour_stat}' not found in contour stats test: {path}")
        
#         import numpy

#         calculated_value = calculated_contour_stats[contour_stat]
#         if type(calculated_value) == float or type(calculated_value) == numpy.float64:
#             calculated_value = round(calculated_value, 6)
        
#         expected_value = row[contour_stat].values[0]
#         if type(expected_value) == float or type(expected_value) == numpy.float64:
#             expected_value = round(expected_value, 6)

#         assert calculated_value == pytest.approx(expected_value), f"Calculated contour stat '{contour_stat}' for test '{path}' and selection number '{sel_number}' does not match expected value: {row[contour_stat].values[0]} but got {calculated_contour_stats[contour_stat]}"
