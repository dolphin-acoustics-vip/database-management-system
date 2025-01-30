import re
import numpy
import pytest
from . import factories
import os
import pandas as pd
from ..app import contour_statistics, utils

import pytest
from ..app import contour_statistics
from . import common

BASE_DIR = "ocean/tests/resources/contour-stats"

def _test_contour_stats():
    for folder in [
        os.path.join(BASE_DIR, "test1"),
        os.path.join(BASE_DIR, "test2"),
        os.path.join(BASE_DIR, "test3"),
        os.path.join(BASE_DIR, "test4"),
        os.path.join(BASE_DIR, "test5"),
        os.path.join(BASE_DIR, "test6"),
        os.path.join(BASE_DIR, "test7"),
        os.path.join(BASE_DIR, "test8"),
    ]:
        if "RoccaContourStats.xlsx" not in os.listdir(folder):
            pytest.fail(f"The following folder does not contain RoccaContourStats.xlsx: {folder}")

        contour_stats_df = utils.extract_to_dataframe(os.path.join(folder, "RoccaContourStats.xlsx"))
        for file in os.listdir(folder):
            if file.endswith(".csv"):
                match = re.search(r'sel_(\d+)', file)
                if not match:
                    pytest.fail(f"The following file name does not contain 'sel_##': {file} in {folder}")
                selection_number = int(match.group(1))
                file_dataframe = utils.extract_to_dataframe(os.path.join(folder, file))
                yield (folder, selection_number, file_dataframe, contour_stats_df)

def _test_file():
    for folder, selection_number, file_dataframe, contour_stats_df in _test_contour_stats():
        selection = factories.SelectionFactory.create()
        selection.selection_number = selection_number
        contour_file_obj = contour_statistics.ContourFileHandler()
        contour_file_obj.insert_dataframe(file_dataframe)
        contour_file_obj.calculate_statistics(selection)
        row = contour_stats_df.loc[contour_stats_df['SelectionNumber'] == selection_number]
        if len(row) == 0:
            pytest.fail(f"Could not find contour stats for selection {selection_number} in {folder}")
        for attr, (dtype, header, nullable) in common.CONTOUR_STATISTICS.items():
            yield (folder, row, selection, attr, header)

@pytest.mark.parametrize("folder, row, selection, attr, header", _test_file())
def test_assert_contour_stats(folder, row, selection, attr, header):
    if header not in row.columns:
        pytest.fail(f"Header '{header}' not found in contour stats test: {folder}")
    expected_value = row[header].values[0]
    if type(expected_value) == float or type(expected_value) == numpy.float64:
        expected_value = round(expected_value, 6)
    assert getattr(selection, attr) == pytest.approx(expected_value, abs=1e-4), f"Selection '{selection}' contour stat '{header}' does not match expected value: {row[header].values[0]} but got {getattr(selection, attr)}"

@pytest.fixture
def contour_file_handler():
    return factories.ContourFileHandlerFactory.create()

@pytest.mark.parametrize("attr", common.CONTOUR_FILE.keys())
def test_contour_file_attrs(contour_file_handler: contour_statistics.ContourFileHandler, attr):
    assert attr in contour_file_handler.contour_file_attrs()
    assert common.CONTOUR_FILE[attr][0] == contour_file_handler.contour_file_attrs()[attr][0]
    assert common.CONTOUR_FILE[attr][1] == contour_file_handler.contour_file_attrs()[attr][1]
