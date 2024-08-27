import pytest
import pandas as pd
from calculations.rocca import contour

# Sample contour file path
CONTOUR_FILE_PATH = 'testing/sel_03_20021009_081417_ROCCA.csv'

# Sample contour stats file path
CONTOUR_STATS_FILE_PATH = 'testing/RoccaContourStats.xlsx'

def test_contour_calculations():
    # Load the sample contour stats file
    contour_stats_df = pd.read_excel(CONTOUR_STATS_FILE_PATH)

    # Select a row from the contour stats file
    row = contour_stats_df.iloc[0]

    # Load the contour file
    contour_file = contour.ContourFile(CONTOUR_FILE_PATH)

    # Calculate the contour statistics
    contour_file.calculate_statistics()

    # Check if the calculated statistics match the expected values
    assert contour_file.selection.duration == row['duration']
    assert contour_file.selection.freq_max == row['freq_max']
    assert contour_file.selection.freq_min == row['freq_min']
    # Add more assertions for other calculated statistics as needed

    # Clean up
    contour_file = None