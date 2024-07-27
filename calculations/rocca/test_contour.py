from contour import ContourFile
import sys
from selection_test import Selection

file_path = sys.argv[1]

with open(file_path, "r") as f:
    contour_file = ContourFile(file=f)
    selection = Selection()
        
    contour_file.calculate_statistics(selection)
    print("Max", selection.freq_max)
    print("Min", selection.freq_min)    

    