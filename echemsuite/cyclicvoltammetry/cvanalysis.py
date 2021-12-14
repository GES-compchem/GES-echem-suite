#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 15 11:51:31 2021
@author: mattia
"""
from dataclasses import dataclass, field
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import curve_fit
from scipy import integrate
import sys
import traceback

from utils import find_maximas, grouping
from graphical_tools import MaxMinFinder, LineFit

# from sys import exit

# %% CVData
@dataclass
class CVData:
    ip_ratio: float
    charge_ratio: float
    charge_difference: float


# %%
@dataclass
class ElectrodeData:
    """
    Contains data about the electrode
    Attributes
    ----------
    ip : float
        Value of peak current minus the capacitive baseline
    mode : str
        Can either be anode or cathode
    """

    ip: float = None
    work_mode: str = None
    fit_mode: str = None
    auto_success: bool = False
    error: BaseException = None
    peak_base: float = None
    current_max: float = None
    peak_volt: float = None
    peak_index: int = None
    charge: float = None
    capacitive_fit: np.ndarray = None
    fit_data_bool: np.ndarray = None


# %%
class SCVAnalysis:
    """
    Single voltammetry analysis. Takes Cyclic voltammetry obj as inpyut.
    Paramters
    ---------
    source : CyclicVoltammetry
        Source object containing cyclic voltammetry data
    cycle : int
        Number of the cycle to be analyzed
    Attributes
    ----------
    voltage : numpy array
        Voltage [V] values for the selected cycle
    current : numpy array
        Current [mA] values for the selected cycle
    times : numpy array
        Time [s] values for the selected cycle
    ox_voltage : numpy array
        Voltage [V] values for the anode (oxidation)
    ox_current : numpy array
        Current [mA] values for the anode (oxidation)
    red_voltage : numpy array
        Voltage [V] values for the cathode (reduction)
    ox_current : numpy array
        Current [mA] values for the cathode (reduction)
    cv_data : cvanalysis.CVData
        Contains values about the CV (ip ratio, charge ratio, etc)
    anode_data : cvanalysis.ElectrodeData
        Contains values specific to the anode
    cathode_data : cvanalysis.ElectrodeData
        contains values specific to the cathode
    """

    def __init__(self, source, cycle):
        self._cv_obj = source  # CyclicVoltammetry object
        self.voltage = source[cycle]["Vf"].to_numpy()
        self.current = source[cycle]["Im"].to_numpy()
        self.times = source[cycle]["T"].to_numpy()

        # These will be initialized with self._split
        self.ox_voltage = None
        self.ox_current = None
        self.red_voltage = None
        self.red_current = None

        self.cv_data = CVData  # dataclass
        self.anode_data = None  # to be initialized later
        self.cathode_data = None

        self._split()

    def compute_ip(self, work_mode="both", automatic=True):
        if automatic:
            self._auto_ip(work_mode)
            # print(
            #     type(self.anode_data.error),
            #     self.anode_data.error,
            #     self._cv_obj.filepath,
            # )
            # print(sys.exc_info()[2])

        if not automatic:
            self._graphic_ip(work_mode)

        # Charge, ip(c,a) ratio, etc

        # self._charge()

        # self.plot(self.anode_data)
        # self.plot(self.cathode_data)
        # self.ip_ratio()

    def _auto_ip(self, work_mode="both"):
        if work_mode in ("anode", "both"):
            try:
                self.anode_data = self.automatic_ip(
                    self.ox_voltage, self.ox_current, "anode", "weighted-pos reverse"
                )
            except Exception as ex:
                tb_text = traceback.format_exc()
                self.anode_data = ElectrodeData(error=tb_text)
        if work_mode in ("cathode", "both"):
            try:
                self.cathode_data = self.automatic_ip(
                    self.red_voltage, self.red_current, "cathode", "weighted-pos"
                )
            except Exception as ex:
                tb_text = traceback.format_exc()
                self.cathode_data = ElectrodeData(error=tb_text)

    def _graphic_ip(self, work_mode="both"):
        if work_mode in ("anode", "both"):
            print(work_mode)
            peak_finder = MaxMinFinder(self.ox_voltage, self.ox_current, "max")
            max_coord, max_idx = peak_finder.run()
            cap_fit = LineFit(self.ox_voltage, self.ox_current, max_coord)
            fit_mask, ip_base, fit_params = cap_fit.run()
            self.anode_data = ElectrodeData(
                ip=max_coord[1] - ip_base,
                work_mode=work_mode,
                fit_mode="graphic",
                peak_base=ip_base,
                current_max=max_coord[1],
                peak_volt=max_coord[0],
                peak_index=max_idx,
                capacitive_fit=fit_params,
                fit_data_bool=fit_mask,
            )

        if work_mode in ("cathode", "both"):
            print(work_mode)
            peak_finder = MaxMinFinder(self.red_voltage, self.red_current, "min")
            max_coord, max_idx = peak_finder.run()
            cap_fit = LineFit(self.red_voltage, self.red_current, max_coord)
            fit_mask, ip_base, fit_params = cap_fit.run()
            self.cathode_data = ElectrodeData(
                ip=max_coord[1] - ip_base,
                work_mode=work_mode,
                fit_mode="graphic",
                peak_base=ip_base,
                current_max=max_coord[1],
                peak_volt=max_coord[0],
                peak_index=max_idx,
                capacitive_fit=fit_params,
                fit_data_bool=fit_mask,
            )

    def _split(self):
        # find maxima in voltage and split voltage and current in two arrays
        # at that point
        settings = self._cv_obj.settings
        voltage_diff = settings["final voltage"] - settings["initial voltage"]

        print(self._cv_obj.settings["filename"])
        print(voltage_diff)

        voltage = self.voltage
        current = self.current
        times = self.times

        if voltage_diff < 0:
            split = np.argmin(self.voltage) + 1
            voltage = np.flip(voltage)
            current = np.flip(current)
            times = np.flip(times)

        else:
            split = np.argmax(self.voltage) + 1

        print(split)
        # print(voltage)

        self.ox_voltage = voltage[:split]
        self.ox_current = current[:split]
        self.ox_times = times[:split]

        self.red_voltage = voltage[split:]
        self.red_current = current[split:]
        self.red_times = times[split:]

    def ip_ratio(self):
        # computes ipc/ipa ratio
        ip_a = self.anode_data.ip
        ip_c = abs(self.cathode_data.ip)

        self.cv_data.ip_ratio = ip_c / ip_a

        return ip_c / ip_a

    def _charge(self):
        # integrate area within i vs time to get the charge
        self.anode_data.charge = charge_a = integrate.trapezoid(
            self.ox_current, x=self.ox_times
        )

        self.cathode_data.charge = charge_c = integrate.trapezoid(
            self.red_current, x=-self.red_times
        )

        self.cv_data.charge_ratio = charge_c / charge_a
        self.cv_data.charge_difference = charge_a - charge_c

    def plot(self, work_mode):
        if work_mode == "anode":
            data = self.anode_data
        else:
            data = self.cathode_data

        mode = data.work_mode
        peak = data.current_max
        fit = data.capacitive_fit
        peak_pos = data.peak_volt

        plt.rcParams.update({"font.size": 12})
        plt.rc("legend", fontsize=9)
        plt.xlabel("V vs ref [V]")
        plt.ylabel("i [mA]")

        n_points = len(self.ox_voltage)
        rounded = n_points - (n_points % 5)

        if mode == "anode":
            volt = self.ox_voltage[:rounded]
            curr = self.ox_current[:rounded]
        else:
            volt = self.red_voltage[:rounded]
            curr = self.red_current[:rounded]

        plt.plot(volt, curr, label=mode)

        # ranges for capacitive fit line
        if mode == "anode":
            volt_min = np.amin(volt)
        else:
            volt_min = np.amax(volt)
        volt_max = peak_pos

        # build line
        def line(x_var, a_const, b_const):
            return a_const * x_var + b_const

        x_var = np.linspace(volt_min, volt_max, 2)
        y_var = line(x_var, fit[0], fit[1])

        y_vert = volt_max * fit[0] + fit[1]

        plt.plot(x_var, y_var, color="green", label="capacitive " + mode)
        plt.plot(
            [volt_max, volt_max],
            [y_vert, peak],
            color="orange",
            label=r"$i_{p,c}$ " + mode,
        )

        plt.legend()
        plt.show()

    def automatic_ip(self, in_volt, in_curr, mode, fit_type, average=10, d2_limit=5):

        # shorten array lenght to divisible by average for block average
        n_points = len(in_volt)
        trim = n_points - (n_points % average)

        volt = in_volt[0:trim]
        curr = in_curr[0:trim]

        # block average on source
        volt = np.mean(volt.reshape(-1, average), axis=1)
        curr = np.mean(curr.reshape(-1, average), axis=1)

        curr = gaussian_filter1d(curr, 1)  # smoothing

        # find peaks and consider just the first one (find_maximas from utils)
        # index is relative to the original, non averaged array
        if mode == "anode":
            peaks = find_maximas(in_curr, 5, 1)  # 5, 1 were found empirically
            try:
                peak_idx = peaks[0]
            except IndexError as error:
                raise IndexError(
                    f"No peaks found in {mode} CV of file {self._cv_obj.filepath}"
                ) from error
            peak_xpos = in_volt[peak_idx]
        else:
            peaks = find_maximas(-in_curr, 5, 1)  # 5, 1 were found empirically
            try:
                peak_idx = peaks[-1]
            except IndexError as error:
                raise IndexError(
                    f"No peaks found in {mode} CV of file {self._cv_obj.filepath}"
                ) from error
            peak_xpos = in_volt[peak_idx]  # position of the first peak on x axis

        # Compute derivatives
        curr_d1 = np.gradient(curr, volt)  # first derivative
        curr_d1 = gaussian_filter1d(curr_d1, 3)
        curr_d2 = np.gradient(curr_d1, volt)  # second derivative

        # filter values outside of the vertical range & following the 1st peak
        curr_d2_max = np.amax(curr_d2)
        curr_d2_min = np.amin(curr_d2)
        max_thr = curr_d2_max / d2_limit
        min_thr = curr_d2_min / d2_limit

        y_mask = np.logical_and(curr_d2 < max_thr, curr_d2 > min_thr)
        if mode == "anode":
            x_mask = volt < peak_xpos  # before first peak!
        else:
            x_mask = volt > peak_xpos  # before first peak!

        mask = np.logical_and(y_mask, x_mask)  # indicates elements within thrs

        # Masked array with only points within thresolds
        volt_base = volt[mask]
        curr_d2_base = curr_d2[mask]

        # thresholds for grouping (on second derivative!)
        volt_thr = 3 * (np.amax(volt) - np.amin(volt)) / n_points * average
        curr_thr = (np.amax(curr_d2) - np.amin(curr_d2)) / 10.0

        edges = np.amin(volt), np.amax(volt)
        # Find clusters of data where each point is within volt/curr threshold
        # grouping function from utils

        clusters = grouping(
            volt_base, curr_d2_base, volt_thr, curr_thr, order=fit_type, edges=edges
        )

        cap_idx = clusters[0]

        if len(cap_idx) <= 2:
            raise ValueError(
                f"Could not fit capacitive current for {mode} "
                f"in {self._cv_obj.filepath}"
            )

        # return indices of data to fit (on original, non averaged input)
        ci_min = cap_idx[0]
        ci_max = cap_idx[-1]

        if mode == "anode":
            orig_idx = np.logical_and(
                in_volt < volt_base[ci_max], in_volt > volt_base[ci_min]
            )
        else:
            orig_idx = np.logical_and(
                in_volt > volt_base[ci_max], in_volt < volt_base[ci_min]
            )

        # fit!
        def line(x_var, a_const, b_const):
            return a_const * x_var + b_const

        params, _ = curve_fit(line, in_volt[orig_idx], in_curr[orig_idx])

        # Intersection between capacitive fit and peak position
        ip_base = peak_xpos * params[0] + params[1]

        curr_max = in_curr[peaks[0]]

        ip = curr_max - ip_base

        return ElectrodeData(
            ip=ip,
            work_mode=mode,
            fit_mode="automatic",
            auto_success=True,
            peak_base=ip_base,
            current_max=curr_max,
            peak_volt=peak_xpos,
            peak_index=peak_idx,
            capacitive_fit=params,
            fit_data_bool=orig_idx,
        )


# %%
class CCVAnalysis:
    """
    Collective CV Analysis - analysis of multiple cyclic voltammetries. Take
    voltammetry reading and index of the required voltammetry.
    """

    def __init__(self, cv_obj, index_list):
        self.cv_objs = cv_obj  # CyclicVoltammetry objects
        self.index_list = index_list
        self.n_cv = len(self.cv_objs)

        self.SCVA_list = self._analyze()

        # for elem in self.SCVA_list:
        # print(elem.anode_data['peak current'])

        self.randles_sevcik(2, 3, 1)

    def _analyze(self):
        SCVA_list = []

        for i in range(self.n_cv):
            obj = self.cv_objs[i]
            curve = self.index_list[i]
            SCVA_list.append(SCVAnalysis(obj, curve))

        return SCVA_list

    def randles_sevcik(self, n_elec, area, conc, T=25, plot=False):
        # constants
        R = 8.31446261815324  # J K-1 mol-1
        F = 96485.3321233  # C mol-1
        T = T + 273.15
        K = 0.4463 * F ** 1.5 * (1 / (R * T)) ** 0.5

        denom = K * n_elec ** 1.5 * area * conc

        # computes diffusion for each cyclic voltammetry
        for analysis in self.SCVA_list:
            ips = analysis.anode_data["peak current"]
            v_rate = analysis._cv_obj.settings["scan rate"]
            diff = ips / (denom * v_rate ** 0.5)
            print(diff)

        if plot:
            pass
