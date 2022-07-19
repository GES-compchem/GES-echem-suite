from typing import List
import pandas as pd
import numpy as np
from scipy.stats import linregress
import sys
from os import path
from datetime import datetime


class CellCycling:
    """
    Contains all the cycles
    """

    def __init__(self, cycles: list):
        self._cycles = cycles
        self._number_of_cycles: int = None

        self._numbers: list = None  # initialized by get_numbers()

        self._capacity_retention: list = None  # initialized in capacity_retention() property
        self.reference: int = 0  # used for calculating retentions

        self._retention_fit_parameters = None  # initialized by fit_retention()
        self._capacity_fade = None  # initialized by fit_retention()

    def __getitem__(self, cycle_number):
        if self._cycles[cycle_number]._hidden is False:
            return self._cycles[cycle_number]
        else:
            print(f"ERROR: cycle {self._cycles[cycle_number].number} is currently hidden.")
            print("To reinstate it, use the unhide() function")
            return None

    def __iter__(self):
        for cycle in self._cycles:
            if cycle._hidden is False:
                yield cycle

    def get_numbers(self):
        self._numbers = [cycle.number for cycle in self]

    def hide(self, hide_indices: list):
        """Cycle masking/hiding feature. Prevents certain cycles from being
        used/shown in calculations.

        Parameters
        ----------
        hide_indices : list
            list of indices to mask/hide
        """
        for i in hide_indices:
            self._cycles[i]._hidden = True

        self.get_numbers()

    def unhide(self, unhide_indices: list):
        """Cycle unmasking/unhiding feature. Reinstate cycles from being
        used/shown in calculations.

        Parameters
        ----------
        unhide_indices : list
            list of indices to unmask/unhide
        """
        for i in unhide_indices:
            self._cycles[i]._hidden = False

        self.get_numbers()

    @property
    def capacity_retention(self):
        """
        List of capacity retentions calculated as the ratios between the discharge capacity at cycle
        n and the discharge capacity of the reference cycle (by default, first cycle). To change the
        reference cycle, set the "self.reference" property
        """
        initial_capacity = self._cycles[self.reference].discharge.capacity

        self._capacity_retention = []

        for cycle in self:
            if cycle.discharge:
                self._capacity_retention.append(
                    cycle.discharge.capacity / initial_capacity * 100
                )
            else:
                self._capacity_retention.append(None)

        return self._capacity_retention

    def fit_retention(self, start: int, end: int):
        """Fits the currently available retention data with a linear fit
        
        Parameters
        ----------
        start : int
            starting cycle number for the fitting procedure
        end : int
            ending cycle number for the fitting procedure

        Returns
        -------
        fit_parameters : LinregressResult instance
            Result is an LinregressResult object with the following attributes:
            slope
            intercept
            rvalue
            pvalue
            stderr
            intercept_stderr
        """

        retention_array = self.capacity_retention[start:end]

        print(f"INFO: fitting Capacity Retention data from cycle {start} to {end}")
        self._retention_fit_parameters = linregress(range(start, end), retention_array)

        print(
            f"INFO: fit equation: retention = {self._retention_fit_parameters.slope} * cycle_number + {self._retention_fit_parameters.intercept}"
        )
        print(f"INFO: R^2 = {self._retention_fit_parameters.rvalue**2}")

        # capacity fade calculated between consecutive cycles, taken as the slope of the linear fit

        self._capacity_fade = -(self._retention_fit_parameters.slope) * 100

    @property
    def fit_parameters(self):
        """Fitting parameters obtained from the linear fit of the capacity retention"""
        return self._retention_fit_parameters

    @property
    def capacity_fade(self):
        """% of capacity retention lost between two consecutive cycles (note: this is not the TOTAL
        capacity fade!)"""
        return self._capacity_fade

    def predict_retention(self, cycle_numbers: list):
        """Predicts the retention for a given number of cycles, given a series of fit parameters
        in the form of a LinregressResult object

        Parameters
        ----------
        cycle_numbers : list
            list containing the cycle numbers for which you want to predict the retention

        Returns
        -------
        predicted_retentions : list
            list containing the predicted retention values
        """

        predicted_retentions = []
        for cycle_number in cycle_numbers:
            retention = (
                self._retention_fit_parameters.slope * cycle_number
                + self._retention_fit_parameters.intercept
            )
            predicted_retentions.append(retention)

        return predicted_retentions

    def retention_threshold(self, thresholds: list):
        """Predicts the cycle numbers for which the capacity retention reaches a certain threshold

        Parameters
        ----------
        thresholds : list
            list containing the retention thresholds for which you want to predict the cycle number

        Returns
        -------
        predicted_thresholds : list
            list containing the predicted retention values
        """

        predicted_cycle_numbers = []
        for retention in thresholds:
            cycle_number = int(
                (
                    (retention - self._retention_fit_parameters.intercept)
                    / self._retention_fit_parameters.slope
                )
                // 1
            )
            predicted_cycle_numbers.append(cycle_number)

        return predicted_cycle_numbers

    @property
    def coulomb_efficiencies(self):
        """List of coulombic efficiencies"""
        return [cycle.coulomb_efficiency for cycle in self]

    @property
    def voltage_efficiencies(self):
        """List of voltaic efficiencies"""
        return [cycle.voltage_efficiency for cycle in self]

    @property
    def energy_efficiencies(self):
        """List of energy efficiencies"""
        return [cycle.energy_efficiency for cycle in self]

    @property
    def number_of_cycles(self):
        """Returns the total number of cycles"""
        return len([cycle for cycle in self])

    @property
    def numbers(self):
        """Returns a list of all the available cycle numbers"""
        self.get_numbers()
        return self._numbers


class Cycle:
    """
    Contains the charge and discharge half-cycles
    """

    def __init__(self, number: int, charge=None, discharge=None):

        self._number = number
        self._charge: HalfCycle = charge
        self._discharge: HalfCycle = discharge

        self._hidden: bool = False

        (
            self._coulomb_efficiency,
            self._energy_efficiency,
            self._voltage_efficiency,
        ) = self.calculate_efficiencies()

    # CYCLE NUMBER
    @property
    def number(self):
        """Cycle number"""
        return self._number

    # CHARGE / DISCHARGE
    @property
    def charge(self):
        """Charge half-cycle"""
        return self._charge

    @property
    def discharge(self):
        """Discharge half-cycle"""
        return self._discharge

    # TIME
    @property
    def time(self):
        """DataFrame containing the time data points (in s) for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.time, self.discharge.time])
        elif self.charge and not self.discharge:
            return self.charge.time
        elif self.discharge and not self.charge:
            return self.discharge.time

    # VOLTAGE
    @property
    def voltage(self):
        """DataFrame containing the voltage data (in V) points for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.voltage, self.discharge.voltage])
        elif self.charge and not self.discharge:
            return self.charge.voltage
        elif self.discharge and not self.charge:
            return self.discharge.voltage

    # CURRENT
    @property
    def current(self):
        """DataFrame containing the current data points (in A) for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.current, self.discharge.current])
        elif self.charge and not self.discharge:
            return self.charge.current
        elif self.discharge and not self.charge:
            return self.discharge.current

    # POWER
    @property
    def power(self):
        """DataFrame containing the instantaneous power data points (in W) for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.power, self.discharge.power])
        elif self.charge and not self.discharge:
            return self.charge.power
        elif self.discharge and not self.charge:
            return self.discharge.power

    # ENERGY
    @property
    def energy(self):
        """DataFrame containing the instantaneous energy data points (in mWh) for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.energy, self.discharge.energy])
        elif self.charge and not self.discharge:
            return self.charge.energy
        elif self.discharge and not self.charge:
            return self.discharge.energy

    # ACCUMULATED CHARGE
    @property
    def Q(self):
        """DataFrame containing the accumulated charge data points (in mAh) for the complete cycle"""
        if self.charge and self.discharge:
            return pd.concat([self.charge.Q, self.discharge.Q])
        elif self.charge and not self.discharge:
            return self.charge.Q
        elif self.discharge and not self.charge:
            return self.discharge.Q

    def calculate_efficiencies(self):
        """
        Computes the coulombic and energy efficiency of the cycle as the ratio 
        between the discharge and charge energies, provided they exist.
        """

        if self.charge and self.discharge:

            if self.charge.capacity <= 0 or self.charge.total_energy <= 0:
                # 101 is a sentinel value
                self._coulomb_efficiency = 101
                self._energy_efficiency = 101
                self._voltage_efficiency = 101
            else:
                self._coulomb_efficiency = (
                    self.discharge.capacity / self.charge.capacity * 100
                )
                self._energy_efficiency = (
                    self.discharge.total_energy / self.charge.total_energy * 100
                )
                self._voltage_efficiency = (
                    self._energy_efficiency / self._coulomb_efficiency * 100
                )

            return (
                self._coulomb_efficiency,
                self._energy_efficiency,
                self._voltage_efficiency,
            )

        else:
            return None, None, None

    # EFFICIENCIES
    @property
    def coulomb_efficiency(self):
        """Coulombic efficiency"""
        return self._coulomb_efficiency

    @property
    def energy_efficiency(self):
        """Energy efficiency"""
        return self._energy_efficiency

    @property
    def voltage_efficiency(self):
        """Voltaic efficiency"""
        return self._voltage_efficiency

    # LEGACY PROPERTIES

    @property
    def time_charge(self):
        print(
            "WARNING: the property 'time_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'time_charge' with 'charge.time'."
        )
        return self.charge.time

    @property
    def time_discharge(self):
        print(
            "WARNING: the property 'time_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'time_discharge' with 'discharge.time'."
        )
        return self.discharge.time

    @property
    def voltage_charge(self):
        print(
            "WARNING: the property 'voltage_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'voltage_charge' with 'charge.voltage'."
        )
        return self.charge.voltage

    @property
    def voltage_discharge(self):
        print(
            "WARNING: the property 'voltage_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'voltage_discharge' with 'discharge.voltage'."
        )
        return self.discharge.voltage

    @property
    def current_charge(self):
        print(
            "WARNING: the property 'current_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'current_charge' with 'charge.current'."
        )
        return self.charge.current

    @property
    def current_discharge(self):
        print(
            "WARNING: the property 'current_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'current_discharge' with 'discharge.current'."
        )
        return self.discharge.current

    @property
    def power_charge(self):
        print(
            "WARNING: the property 'power_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'power_charge' with 'charge.power'."
        )
        return self.charge.power

    @property
    def power_discharge(self):
        print(
            "WARNING: the property 'power_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'power_discharge' with 'discharge.power'."
        )
        return self.discharge.power

    @property
    def energy_charge(self):
        print(
            "WARNING: the property 'energy_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'energy_charge' with 'charge.energy'."
        )
        return self.charge.energy

    @property
    def energy_discharge(self):
        print(
            "WARNING: the property 'energy_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'energy_discharge' with 'discharge.energy'."
        )
        return self.discharge.energy

    @property
    def capacity_charge(self):
        print(
            "WARNING: the property 'capacity_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'capacity_charge' with 'charge.capacity'."
        )
        return self.charge.capacity

    @property
    def capacity_discharge(self):
        print(
            "WARNING: the property 'capacity_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'capacity_discharge' with 'discharge.capacity'."
        )
        return self.discharge.capacity

    @property
    def Q_charge(self):
        print(
            "WARNING: the property 'Q_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'Q_charge' with 'charge.Q'."
        )
        return self.charge.Q

    @property
    def Q_discharge(self):
        print(
            "WARNING: the property 'Q_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'Q_discharge' with 'discharge.Q'."
        )
        return self.discharge.Q

    @property
    def total_energy_charge(self):
        print(
            "WARNING: the property 'total_energy_charge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'total_energy_charge' with 'charge.total_energy'."
        )
        return self.charge.total_energy

    @property
    def total_energy_discharge(self):
        print(
            "WARNING: the property 'total_energy_discharge' is being deprecated and will no longer be available in future releases!"
        )
        print(
            "Please update your script and replace all occurrences of 'total_energy_discharge' with 'discharge.total_energy'."
        )
        return self.discharge.total_energy


class HalfCycle:
    """
    HalfCycle object (for storing charge or discharge data)
    """

    def __init__(self, time, voltage, current, halfcycle_type, timestamp):
        """
        Parameters
        ----------
        time : Pandas Series
            Series containing time data (in s)
        voltage : Pandas Series
            Series containing voltage data (in V)
        current : Pandas Series
            Series containing current data (in A)
        halfcycle_type : str
            Should either be "charge" or "discharge"
        """
        self._timestamp = timestamp
        self._time = time
        self._voltage = voltage
        self._current = current
        self._halfcycle_type = halfcycle_type

        self._Q, self._capacity = self.calculate_Q()
        self._power, self._energy, self._total_energy = self.calculate_energy()

    def calculate_Q(self):
        """
        Calculate the capacity C (mAh) of the charge half-cycle as the 
        accumulated charge over time
        """
        # accumulated charge dq at each measurement step (mA.h)
        dq = abs(self._current * self._time.diff()) / 3.6

        # charge as cumulative sum (mA.h)
        Q = dq.cumsum()

        # capacity as last value of accumulated charge (mA.h)
        capacity = Q.iloc[-1]

        return Q, capacity

    def calculate_energy(self):
        """
        Calculate the total energy E (mWh) of the charge half-cycle as the 
        cumulative sum of energy over time
        """

        # instantaneous power (W)
        power = abs(self._current * self._voltage)

        # istantaneous energy dE (mWh) at each measurement step and cumulative
        dE = (power * self._time.diff()) / 3.6
        energy = dE.cumsum()

        # total energy (mWh)
        total_energy = energy.iloc[-1]

        return power, energy, total_energy

    # TIMESTAMP
    @property
    def timestamp(self):
        """Timestamp reporting the date and time at which the measurment was collected"""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        """Timestamp reporting the date and time at which the measurment was collected"""
        if type(value) != datetime:
            raise TypeError
        self._timestamp = value

    # HALFCYCLE TYPE (charge/discharge)
    @property
    def halfcycle_type(self):
        """Type of half-cycle (charge or discharge)"""
        return self._halfcycle_type

    # TIME
    @property
    def time(self):
        """DataFrame containing the time data points (in s) for the selected half-cycle"""
        return self._time

    # VOLTAGE
    @property
    def voltage(self):
        """DataFrame containing the voltage data points (in V) for the selected half-cycle"""
        return self._voltage

    # CURRENT
    @property
    def current(self):
        """DataFrame containing the current data points (in A) for the selected half-cycle"""
        return self._current

    # ACCUMULATED CHARGE
    @property
    def Q(self):
        """DataFrame containing the accumulated charge data points (in mAh) for the selected half-cycle"""
        return self._Q

    # CAPACITY
    @property
    def capacity(self):
        """Capacity (in mAh) for the selected half-cycle, calculated as the total accumulated charge"""
        return self._capacity

    # POWER
    @property
    def power(self):
        """DataFrame containing the instantaneous power data points (in W) for the selected half-cycle"""
        return self._power

    # ENERGY
    @property
    def energy(self):
        """DataFrame containing the instantaneous energy data points (in mWh) for the selected half-cycle"""
        return self._energy

    # TOTAL ENERGY
    @property
    def total_energy(self):
        """Total energy (in mWh) for the selected half-cycle, calculated as the total accumulated energy"""
        return self._total_energy


def join_HalfCycles(join_list: List[HalfCycle]) -> HalfCycle:
    """
    Join HalfCycles objects containing partial data into a single complete HalfCycle

        Parameters:
        -----------
            join_list: List[HalfCycle]
                list containing all the HalfCycle objects to be joined
        
        Returns:
        --------
            obj : HalfCycle
                single halfcycle object obtained from the concatenation of the input data.
                The timestamp of the output object is set according to the first (oldest) dataset. 
    """

    # Set timestamp and halfcycle_type according to the first halfcycle file
    timestamp = join_list[0]._timestamp
    halfcycle_type = join_list[0]._halfcycle_type

    # Do a sanity check on the halfcycle_type associated to the given objects
    for obj in join_list:
        if obj._halfcycle_type != halfcycle_type:
            raise RuntimeError

    # Concatenate the data series for voltage and current
    voltage = pd.concat([obj._voltage for obj in join_list], ignore_index=True)
    current = pd.concat([obj._current for obj in join_list], ignore_index=True)

    time_list = []
    for i, obj in enumerate(join_list):
        offset = 0 if i == 0 else time_list[-1]
        for t in obj.time:
            time_list.append(t + offset)

    time = pd.Series(time_list, name="Time (s)")

    return HalfCycle(time, voltage, current, halfcycle_type, timestamp)


def build_DTA_cycles(filelist, clean, verbose=False):
    """builds a list of cycles from a list containing charge/discharge file paths from 
    

    Parameters
    ----------
    filelist : list
        file list containing .DTA file paths.
    clean : bool
        if True, only displays cycles with physical meaning (efficiencies < 100% and both charge + 
        discharge available). If False (default), load everything.

    Returns
    -------
    cycles : list
        list containing various Cycles objects built according to the given list pairs
    """

    halfcycles = []

    for filepath in filelist:

        filename = path.basename(filepath)
        extension = path.splitext(filename)[1]

        if verbose:
            print("Loading: {}".format(filepath))

        if extension.lower() == ".dta":

            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                beginning = None  # line at which the table begins
                npoints = None  # number of data points
                halfcycle_type = None  # charge/discharge

                date_str, time_str = None, None  # Date and time string buffers
                timestamp = None  # Timestamp reported in the file

                # finding the "CURVE TABLE npoints" line in file
                for line_num, line in enumerate(file):

                    if line.startswith("DATE"):
                        date_str = line.split()[2]
                    elif line.startswith("TIME"):
                        time_str = line.split()[2]

                    if "Step 1 Current (A)" in line:
                        if float(line.split()[2]) > 0:
                            halfcycle_type = "charge"  # positive current = charge
                        elif float(line.split()[2]) < 0:
                            halfcycle_type = "discharge"  # negative current = discharge

                    if "CURVE" in line:
                        beginning = line_num + 2
                        npoints = int(line.split()[-1])
                        break

                # build timestamp object
                if date_str != None and time_str != None:
                    month, day, year = date_str.split("/")
                    hours, minutes, seconds = time_str.split(":")
                    timestamp = datetime(
                        int(year),
                        int(month),
                        int(day),
                        int(hours),
                        int(minutes),
                        int(seconds),
                    )
                else:
                    print("WARNING: Failed to build file timestamp.")

                # reading data from file
                data = pd.read_table(
                    filepath,
                    delimiter="\t",
                    skiprows=beginning,
                    decimal=".",
                    nrows=npoints,
                    encoding_errors="ignore",
                )

                # renaming columns to standard format
                if "V vs. Ref." in data.columns:
                    data.rename(
                        columns={
                            "s": "Time (s)",
                            "V vs. Ref.": "Voltage vs. Ref. (V)",
                            "A": "Current (A)",
                        },
                        inplace=True,
                    )

                elif "V" in data.columns:
                    data.rename(
                        columns={
                            "s": "Time (s)",
                            "V": "Voltage vs. Ref. (V)",
                            "A": "Current (A)",
                        },
                        inplace=True,
                    )

                time = data["Time (s)"]
                voltage = data["Voltage vs. Ref. (V)"]
                current = data["Current (A)"]

                if halfcycle_type is None:
                    if current[0] > 0:
                        halfcycle_type = "charge"
                    elif current[0] < 0:
                        halfcycle_type = "discharge"

                halfcycles.append(
                    HalfCycle(time, voltage, current, halfcycle_type, timestamp)
                )

        else:
            print("This is not a .DTA file!")
            sys.exit()

    cycles = []
    cycle_number = 0

    while halfcycles:
        half = halfcycles.pop(0)
        if half.halfcycle_type == "charge":
            charge = half
            try:
                discharge = halfcycles.pop(0)
                cycle = Cycle(number=cycle_number, charge=charge, discharge=discharge)
            except:
                cycle = Cycle(number=cycle_number, charge=charge, discharge=None)
                pass
        else:
            discharge = half
            cycle = Cycle(number=cycle_number, charge=None, discharge=discharge)
        cycles.append(cycle)
        cycle_number += 1

    for cycle in cycles:
        if cycle.energy_efficiency and cycle.energy_efficiency > 100 and clean:
            cycle._hidden = True
            print(f"Cycle {cycle.number} hidden due to unphsyical nature")
        elif not cycle.charge or not cycle.discharge and clean:
            cycle._hidden = True
            print(f"Cycle {cycle.number} hidden due to missing charge/discharge")

    return cycles


def read_mpt_cycles(filelist, clean):
    """reads a list of cycles from a list containing cell cycling file paths from BIOLOGIC 
    instruments (.mpt files)
    

    Parameters
    ----------
    filelist : list
        file list containing .mpt file paths.
    clean : bool
        if True, only displays cycles with physical meaning (efficiencies < 100% and both charge + 
        discharge available). If False (default), load everything.

    Returns
    -------
    cycles : list
        list containing various Cycles objects built according to the given list pairs
    """

    cycles = []

    # this variable tracks the GLOBAL cycle numbers and increases between
    # files. Not to be confused with current_mpt_cycle_num!
    cycle_number = 0

    for filepath in filelist:
        print("Loading:", filepath, "\n")

        filename = path.basename(filepath)
        extension = path.splitext(filename)[1]

        if extension.lower() == ".mpt":

            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                delims = []  # contains cycle number, first and last line number
                beginning = None
                ncycles = 1

                for line_num, line in enumerate(file):
                    if "Number of loops : " in line:
                        ncycles = int(line.split(" ")[-1])

                    # Before the output of the experiment, EClab lists the
                    # starting and ending line of each loop. These will be used
                    # to slice the pandas dataframe into the different cycles.
                    if "Loop " in line:
                        loop_num = int(line.split(" ")[1])
                        first_pos = int(line.split(" ")[-3])
                        second_pos = int(line.split(" ")[-1])
                        delims.append([loop_num, first_pos, second_pos])

                    if "mode\t" in line:
                        beginning = line_num
                        break

                # if no cycles are found, default to "read everything"
                if len(delims) == 0:
                    delims = [[0, 0, -2]]  # -2 will be converted to -1 later

                # reading data from file
                data = pd.read_table(
                    filepath,
                    dtype=np.float64,
                    delimiter="\t",
                    skiprows=beginning,
                    decimal=",",
                    encoding_errors="ignore",
                )

                # renaming columns to standard format
                data.rename(
                    columns={
                        "time/s": "Time (s)",
                        "Ewe/V": "Voltage vs. Ref. (V)",
                        "I/mA": "Current (A)",  # note: these are mA
                    },
                    inplace=True,
                )

                # convert mA to A
                data["Current (A)"] = data["Current (A)"].divide(1000)

                # initiate Cycle object providing dataframe view within delims

                # this variable iterates over the cycles of the specific file
                # and is reinitialized every file, not to be confused with
                # cycle_number!
                current_mpt_cycle_num = 0
                while current_mpt_cycle_num < ncycles:
                    first_row = delims[current_mpt_cycle_num][1]
                    last_row = delims[current_mpt_cycle_num][2] + 1

                    try:
                        charge = HalfCycle(
                            data["Time (s)"][first_row:last_row][data["ox/red"] == 1],
                            data["Voltage vs. Ref. (V)"][first_row:last_row][
                                data["ox/red"] == 1
                            ],
                            data["Current (A)"][first_row:last_row][data["ox/red"] == 1],
                            "charge",
                        )
                    except:
                        charge = None

                    try:
                        discharge = HalfCycle(
                            data["Time (s)"][first_row:last_row][data["ox/red"] == 0],
                            data["Voltage vs. Ref. (V)"][first_row:last_row][
                                data["ox/red"] == 0
                            ],
                            data["Current (A)"][first_row:last_row][data["ox/red"] == 0],
                            "discharge",
                        )
                    except:
                        discharge = None

                    cycle = Cycle(number=cycle_number, charge=charge, discharge=discharge)

                    if charge and discharge:
                        unphysical = (
                            cycle.energy_efficiency > 100,
                            cycle.coulomb_efficiency > 100,
                            cycle.voltage_efficiency > 100,
                        )

                    elif charge and not discharge and clean:
                        print(
                            f"WARNING: cycle {cycle._number} will be discarded due to missing discharge data"
                        )
                        cycle._hidden = True

                    elif discharge and not charge and clean:
                        print(
                            f"WARNING: cycle {cycle._number} will be discarded due to missing charge data"
                        )
                        cycle._hidden = True

                    if any(unphysical) and clean:
                        print(
                            f"WARNING: cycle {cycle._number} will be discarded due to unphysical efficiencies"
                        )
                        cycle._hidden = True

                    cycles.append(cycle)

                    cycle_number += 1
                    current_mpt_cycle_num += 1

        else:
            print("This is not a .mpt file!")
            sys.exit()

    return cycles


def read_cycles(filelist, clean=False):
    if type(filelist) is str:
        filelist = [filelist]

    cycles = read_mpt_cycles(filelist, clean)

    return CellCycling(cycles)


def build_cycles(filelist, clean=False):
    cycles = build_DTA_cycles(filelist, clean)

    return CellCycling(cycles)


def time_adjust(cycle, reverse=False):

    if cycle.discharge.time.iloc[0] != cycle.charge.time.iloc[0]:
        charge_time = cycle.charge.time.subtract(cycle.charge.time.iloc[0])
        discharge_time = cycle.discharge.time.subtract(cycle.discharge.time.iloc[-1])
    else:
        charge_time = cycle.charge.time
        discharge_time = cycle.discharge.time

    if reverse is True:
        switch = discharge_time - charge_time.iloc[-1]
        discharge_time = abs(switch)

    return charge_time, discharge_time
