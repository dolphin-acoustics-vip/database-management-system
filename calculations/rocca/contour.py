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
from enum import Enum

class Slope(Enum):
    DOWN=-1
    FLAT=0
    UP=1
    
class Sweep(Enum):
    DOWN=-1
    FLAT=0
    UP=1
class ContourDataUnit:

    
    time_milliseconds: int
    peak_frequency: float
    duty_cycle: float
    energy: float
    window_RMS: float
    
    # calculated values
    sweep = None                      # upsweep=1, downsweep=-1, horiz=0
    step = 0                           # step up=1, step down=2, no step=0
    slope = None                      # slope of current unit, compared to prev
    
    def __init__(self, time_milliseconds, peak_frequency, duty_cycle, energy, window_RMS):
        self.time_milliseconds = time_milliseconds
        self.peak_frequency = peak_frequency
        self.duty_cycle = duty_cycle
        self.energy = energy
        self.window_RMS = window_RMS
    
    def time_seconds(self):
        return self.time_milliseconds / 1000

    def set_slope(self, value: Slope):
        self.slope = value
    
    def set_sweep(self, value: Sweep):
        self.sweep = value

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
        from decimal import Decimal

        import numpy as np
        
        num_points = len(self.contour_rows)
              
                
        # create arrays of all times and frequencies as well as their differences
        times = [row.time_seconds() for row in self.contour_rows]
        frequencies = [row.peak_frequency for row in self.contour_rows]

        slope_sum = 0
        slope_abs_sum = 0
        slope_pos_counter = 0
        slope_pos_sum = 0
        slope_neg_counter = 0
        slope_neg_sum = 0
        num_sweeps_up = 0
        num_sweeps_up_flat = 0
        num_sweeps_up_down = 0
        num_sweeps_down = 0
        num_sweeps_down_flat = 0
        num_sweeps_down_up = 0
        num_sweeps_flat = 0
        num_sweeps_flat_down = 0
        num_sweeps_flat_up = 0
        sweep_up_count = 0
        sweep_down_count = 0
        sweep_flat_count = 0
        for i, contour in enumerate(self.contour_rows):
            slope = 0
            if i > 0:
                time_diff = contour.time_milliseconds - self.contour_rows[i-1].time_milliseconds
                freq_diff = contour.peak_frequency - self.contour_rows[i-1].peak_frequency
                
                # Evaluate sweep (pass the first two rows as sweep depends on a 2-unit moving average)
                # UP-UP, UP-FLAT, FLAT-UP, FLAT-FLAT -> sweep is UP
                # DOWN-DOWN, DOWN-FLAT, FLAT-DOWN, FLAT-FLAT -> sweep is DOWN
                # FLAT-FLAT -> sweep is FLAT
                # NOTE: this logic does not really seem to flow...
                if i > 1:
                    freq_diff_prev = self.contour_rows[i-1].peak_frequency - self.contour_rows[i-2].peak_frequency
                    contour.set_sweep(self.contour_rows[i-1].sweep)
                    if freq_diff >= 0 and freq_diff_prev >= 0:
                        sweep_up_count += 1
                        contour.set_sweep(Sweep.UP)
                    if freq_diff <= 0 and freq_diff_prev <= 0:
                        sweep_down_count += 1
                        contour.set_sweep(Sweep.DOWN)
                    if freq_diff == 0 and freq_diff_prev == 0:
                        sweep_flat_count += 1
                        contour.set_sweep(Sweep.FLAT)
                    
                    # calculate the number of sweeps in the contour
                    # Sweeps are viewed in pairs (UPUP, DOWNUP, UPDOWN etc.)
                    # over the last two units (rows)
                    prev_contour = self.contour_rows[i-1]
                    if contour.sweep == Sweep.UP and prev_contour.sweep == Sweep.UP:
                        num_sweeps_up += 1
                    elif contour.sweep == Sweep.FLAT and prev_contour.sweep == Sweep.UP:
                        num_sweeps_up_flat += 1
                    elif contour.sweep == Sweep.DOWN and prev_contour.sweep == Sweep.UP:
                        num_sweeps_up_down += 1
                    elif contour.sweep == Sweep.DOWN and prev_contour.sweep == Sweep.DOWN:
                        num_sweeps_down += 1
                    elif contour.sweep == Sweep.UP and prev_contour.sweep == Sweep.DOWN:
                        num_sweeps_down_up += 1
                    elif contour.sweep == Sweep.FLAT and prev_contour.sweep == Sweep.DOWN:
                        num_sweeps_down_flat += 1
                    elif contour.sweep == Sweep.FLAT and prev_contour.sweep == Sweep.FLAT:
                        num_sweeps_flat += 1
                    elif contour.sweep == Sweep.UP and prev_contour.sweep == Sweep.FLAT:
                        num_sweeps_flat_up += 1
                    elif contour.sweep == Sweep.DOWN and prev_contour.sweep == Sweep.FLAT:
                        num_sweeps_flat_down += 1                        
                        
                # calculate the slope of each row in the contour
                # Slopes differ from sweeps as they only take into account the
                # one-step frequency difference rather than two.
                if time_diff > 0:
                    slope = freq_diff / time_diff
                    slope_sum += slope
                    slope_abs_sum += abs(slope)
                    if slope > 0:
                        slope_pos_sum += slope
                        slope_pos_counter += 1
                    elif slope < 0:
                        slope_neg_sum += slope
                        slope_neg_counter += 1
                if freq_diff > 0:
                    contour.set_slope(Slope.UP)
                elif freq_diff < 0:
                    contour.set_slope(Slope.DOWN)
                else:
                    contour.set_slope(Slope.FLAT)
            contour.slope = slope
        
        # determine sweep up, down, and flat percentages
        sweep_count = sweep_up_count + sweep_down_count + sweep_flat_count
        selection.freq_sweepuppercent = sweep_up_count / sweep_count
        selection.freq_sweepdownpercent = sweep_down_count / sweep_count
        selection.freq_sweepflatpercent = sweep_flat_count / sweep_count
        
        # assign the two-unit sweep count values from above
        selection.num_sweepsdownflat = num_sweeps_down_flat
        selection.num_sweepsdownup = num_sweeps_down_up
        selection.num_sweepsflatdown = num_sweeps_flat_down
        selection.num_sweepsflatup = num_sweeps_flat_up
        selection.num_sweepsupdown = num_sweeps_up_down
        selection.num_sweepsupflat = num_sweeps_up_flat
        
        print("Down-Flat:",selection.num_sweepsdownflat)
        print("Down-Up:",selection.num_sweepsdownup)
        print("Flat-Down:",selection.num_sweepsflatdown)
        print("Flat-Up:",selection.num_sweepsflatup)
        print("Up-Down:",selection.num_sweepsupdown)
        print("Up-Flat:",selection.num_sweepsupflat)
        
        print("Sweep up percentage:",sweep_up_count,selection.freq_sweepuppercent)
        print("Sweep down percentage:",sweep_down_count,selection.freq_sweepdownpercent)
        print("Sweep flat percentage",sweep_flat_count,selection.freq_sweepflatpercent)
        
        if slope_pos_counter > 0:
            selection.freq_posslopemean = (slope_pos_sum / slope_pos_counter)*1000
        if slope_neg_counter > 0:
            selection.freq_negslopemean = (slope_neg_sum / slope_neg_counter)*1000
            selection.freq_sloperatio = selection.freq_posslopemean / selection.freq_negslopemean
        if num_points > 0:
            selection.freq_slopemean = (slope_sum / (num_points-1))*1000
            selection.freq_absslopemean = (slope_abs_sum / (num_points-1))*1000
        
        # calculate beginning slope as an average of the first three non-zero slopes,
        # skipping the first row as the slope will always be zero
        beg_slope_avg = (self.contour_rows[1].slope + self.contour_rows[2].slope + self.contour_rows[3].slope)/3
        if beg_slope_avg > 0:
            selection.freq_begsweep = Slope.UP
            selection.freq_begup = True
            selection.freq_begdown = False
        elif beg_slope_avg < 0:
            selection.freq_begsweep = Slope.DOWN
            selection.freq_begup = False
            selection.freq_begdown = True
        else:
            selection.freq_begsweep = Slope.FLAT
            selection.freq_begup = False
            selection.freq_begdown = False
        
        end_slope_avg = (self.contour_rows[-1].slope + self.contour_rows[-2].slope + self.contour_rows[-3].slope)/3
        if end_slope_avg > 0:
            selection.freq_endsweep = Slope.UP
            selection.freq_endup = True
            selection.freq_enddown = False
        elif end_slope_avg < 0:
            selection.freq_endsweep = Slope.DOWN
            selection.freq_endup = False
            selection.freq_enddown = True
        else:
            selection.freq_endsweep = Slope.FLAT
            selection.freq_endup = False
            selection.freq_enddown = False
        
        
        
        
        
        print("Begin sweep: ", selection.freq_begsweep)
        print("Begin up", selection.freq_begup)
        print("Begin down", selection.freq_begdown)
        
        print("End sweep:", selection.freq_endsweep)
        print("End up:", selection.freq_endup)
        print("End down", selection.freq_enddown)
        
        # duration is the difference between the first and last times
        selection.duration = times[-1] - times[0]

        
            
        print("Mean slope: ", selection.freq_slopemean)
        print("Mean absolute slope: ", selection.freq_absslopemean)
        print("Mean positive slope: ", selection.freq_posslopemean)
        print("Mean negative slope: ", selection.freq_negslopemean)
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
        
        
        
        
        
