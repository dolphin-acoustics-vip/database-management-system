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
import pandas as pd
import os
from selection_test import Selection


class ContourDataUnit:
    time_milliseconds: int
    peak_frequency: float
    duty_cycle: float
    energy: float
    window_RMS: float
    
    def __init__(self, time_milliseconds, peak_frequency, duty_cycle, energy, window_RMS):
        self.time_milliseconds = time_milliseconds
        self.peak_frequency = peak_frequency
        self.duty_cycle = duty_cycle
        self.energy = energy
        self.window_RMS = window_RMS


class ContourFile:
    contour_rows = []
    
    def __init__(self, file=None):
        if file: self.insert_from_file(file)

    def insert_from_file(self, file):        
        extension = os.path.splitext(file.name)[1].lower()
        if extension == '.csv':
            df = pd.read_csv(file)
        elif extension == '.xlsx':
            df = pd.read_excel(file)
        else:
            raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")
        
        # check columns and datatypes
        expected_columns = {
            'Time [ms]': int,
            'Peak Frequency [Hz]': float,
            'Duty Cycle': float,
            'Energy': float,
            'WindowRMS': float
        }
        
        # remove whitespace from headers        
        df = df.rename(columns=lambda x: x.strip())
        
        for column, dtype in expected_columns.items():
            if column not in df.columns:
                raise ValueError(f"Missing column in '{file.name}': {column}")
            if df[column].dtype != dtype:
                raise ValueError(f"Incorrect data type for column '{column}' in '{file.name}': expected {dtype}, got {df[column].dtype}")
        
        for index, row in df.iterrows():
            self.contour_rows.append(ContourDataUnit(row['Time [ms]'], row['Peak Frequency [Hz]'], row['Duty Cycle'], row['Energy'], row['WindowRMS']))

    def calculate_statistics(self, selection: Selection):
        """
        Calculate contour statistics using the data in contour_rows. The contour stats
        are stored in the selection object (in the Database).
        
        Args:
            selection (Selection): The selection object to store the contour statistics in.
        """
        
        selection.freq_max = max(self.contour_rows, key=lambda x: x.peak_frequency).peak_frequency
        selection.freq_min = min(self.contour_rows, key=lambda x: x.peak_frequency).peak_frequency
        

        
        
        
        
        
        
