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
    
    # calculated values
    sweep = 0                          # upsweep=1, downsweep=-1, horiz=0
    step = 0                           # step up=1, step down=2, no step=0
    slope = 0.0                        # slope of current unit, compared to prev
    
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
        
        num_points = len(self.contour_rows)
        print(num_points)
        
        ### frequency statistics ###
        
        # maximum frequency is the maximum peak_frequency in the contour_rows
        selection.freq_max = max(self.contour_rows, key=lambda x: x.peak_frequency).peak_frequency
        # minimum frequency is the minimum peak_frequency in the contour_rows
        selection.freq_min = min(self.contour_rows, key=lambda x: x.peak_frequency).peak_frequency
        # frequency range is the difference between the maximum and minimum frequencies
        selection.freq_range = selection.freq_max - selection.freq_min
        # median frequency is the median peak_frequency in the contour_rows
        selection.freq_median = pd.Series([row.peak_frequency for row in self.contour_rows]).median()
        # frequency center is the average of the maximum and minimum frequencies
        selection.freq_center = (selection.freq_max + selection.freq_min) / 2
        # frequency relative bandwidth is the frequency range divided by the frequency center
        selection.freq_relbw = selection.freq_range / selection.freq_center
        # maximum-minimum ratio is the maximum frequency divided by the minimum frequency
        selection.freq_maxminratio = selection.freq_max / selection.freq_min
        # beginning frequency is the first peak_frequency in the contour_rows
        selection.freq_begin = self.contour_rows[0].peak_frequency
        # ending frequency is the last peak_frequency in the contour_rows
        selection.freq_end = self.contour_rows[-1].peak_frequency
        # beginning-end ratio is the beginning frequency divided by the ending frequency
        selection.freq_begendratio = selection.freq_end / selection.freq_begin
        # frequency mean is the average of all peak_frequencies in the contour_rows
        selection.freq_mean = pd.Series([row.peak_frequency for row in self.contour_rows]).mean()
        # frequency standard deviation is the standard deviation of all peak_frequencies in the contour_rows
        selection.freq_standarddeviation = pd.Series([row.peak_frequency for row in self.contour_rows]).std()
        # frequency quarter 1 is the peak_frequency at one quarter of the duration
        selection.freq_quarter1 = self.contour_rows[int(num_points/4)].peak_frequency
        # frequency quarter 2 is the peak_frequency at two quarters of the duration
        selection.freq_quarter2 = self.contour_rows[int(num_points/2)].peak_frequency
        # frequency quarter 3 is the peak_frequency at three quarters of the duration
        selection.freq_quarter3 = self.contour_rows[3*int(num_points/4)].peak_frequency
        ## UNUSED - calculating percentiles for the frequency
        freq_quartile1 = pd.Series([row.peak_frequency for row in self.contour_rows]).quantile(0.25)
        freq_quartile2 = pd.Series([row.peak_frequency for row in self.contour_rows]).quantile(0.5)
        freq_quartile3 = pd.Series([row.peak_frequency for row in self.contour_rows]).quantile(0.75)
        # frequency spread is the difference between the third and first quartiles
        selection.freq_spread = freq_quartile3 - freq_quartile1
        
        frequencies = [row.peak_frequency for row in self.contour_rows]
        
        selection.freq_stepup = sum(frequencies[i] < frequencies[i+1] for i in range(len(frequencies)-1))
        selection.freq_stepdown = sum(frequencies[i] > frequencies[i+1] for i in range(len(frequencies)-1))
        selection.freq_numsteps = selection.freq_stepup + selection.freq_stepdown
       
       
        

        
        print("Frequency statistics calculated.")
        print("Frequency max:", selection.freq_max)
        print("Frequency min:", selection.freq_min)
        print("Frequency range:", selection.freq_range)
        print("Frequency median:", selection.freq_median)
        print("Frequency center:", selection.freq_center)
        print("Frequency relative bandwidth:", selection.freq_relbw)
        print("Frequency max-min ratio:", selection.freq_maxminratio)
        print("Frequency beginning:", selection.freq_begin)
        print("Frequency ending:", selection.freq_end)
        print("Frequency beginning/ending ratio:", selection.freq_begendratio)
        print("Frequency mean:", selection.freq_mean)
        print("Frequency standard deviation:", selection.freq_standarddeviation)
        print("Frequency quartiles:", selection.freq_quarter1, selection.freq_quarter2, selection.freq_quarter3)
        print("Frequency spread:", selection.freq_spread)
        print("Frequency step up:", selection.freq_stepup)
        print("Frequency step down:", selection.freq_stepdown)
        
        
        
        
        
