from contour import ContourFile
import sys

file_path = sys.argv[1]

with open(file_path, "r") as f:
    contour_file = ContourFile(file=f)
    print(contour_file.data_units)
    for data_unit in contour_file.data_units:
        print(data_unit)
    