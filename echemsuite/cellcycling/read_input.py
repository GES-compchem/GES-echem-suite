import pandas as pd
import numpy as np
import sys
from os import path


class CellCycling:
    """
    Contains all the cycles
    """

    def __init__(self, cycles: list):
        self._cycles = cycles
        self._number_of_cycles = len(self._cycles)

        self._indices = [cycle.index for cycle in cycles]

        self._capacity_retention: list = None  # initialized in capacity_retention() property
        self.reference: int = 0  # used for calculating retentions

    def __getitem__(self, cycle):
        return self._cycles[cycle]

    def __iter__(self):
        for index in self._indices:
            yield self._cycles[index]

    def mask(self, masked_indices: list):
        """Cycle masking/hiding feature. Prevents certain cycles from being
        used/shown in calculations.

        Parameters
        ----------
        masked_indices : list
            list of indices to mask/hide
        """
        for i in masked_indices:
            try:
                self._indices.remove(i)
            except ValueError:
                print(f"ERROR: cycle {i} already masked or not present")
                pass

    def unmask(self, unmasked_indices: list):
        """Cycle unmasking/unhiding feature. Reinstate cycles from being
        used/shown in calculations.

        Parameters
        ----------
        unmasked_indices : list
            list of indices to unmask/unhide
        """
        for i in unmasked_indices:
            if i not in self._indices:
                if i < self._number_of_cycles:
                    self._indices.append(i)
                    self._indices.sort()
                else:
                    print(f"ERROR: cycle {i} does not exist")
                    pass
            else:
                print(f"ERROR: cycle {i} already present")
                pass


    @property
    def capacity_retention(self):

        initial_capacity = self._cycles[self.reference].capacity_discharge

        self._capacity_retention = []

        for index in self._indices:
            self._capacity_retention.append(
                self[index].capacity_discharge / initial_capacity * 100
            )

        return self._capacity_retention

    @property
    def coulomb_efficiencies(self):
        return [self[index].coulomb_efficiency for index in self._indices]
    
    @property
    def voltage_efficiencies(self):
        return [self[index].voltage_efficiency for index in self._indices]
    
    @property
    def energy_efficiencies(self):
        return [self[index].energy_efficiency for index in self._indices]
    
    @property
    def number_of_cycles(self):
        return self._number_of_cycles
    
    @property
    def indices(self):
        return self._indices


class Cycle:
    """
    Contains the charge and discharge half-cycles
    """

    def __init__(self, index: int):
        self._index = index

        # initialized by add_charge
        self._time_charge: pd.Series = None  
        self._voltage_charge: pd.Series = None
        self._current_charge: pd.Series = None

        self._Q_charge: pd.Series = None
        self._capacity_charge: np.float64 = None
        self._power_charge: pd.Series = None
        self._energy_charge: pd.Series = None
        self._total_energy_charge: np.float64 = None

        # initialized by add_discharge
        self._time_discharge: pd.Series = None
        self._voltage_discharge: pd.Series = None
        self._current_discharge: pd.Series = None
        
        self._Q_discharge: pd.Series = None
        self._capacity_discharge: np.float64 = None
        self._power_discharge: pd.Series = None
        self._energy_discharge: pd.Series = None
        self._total_energy_discharge: np.float64 = None

        # initialized by calculate_efficiencies
        self._coulomb_efficiency: np.float64 = None
        self._energy_efficiency: np.float64 = None
        self._voltage_efficiency: np.float64 = None


    def add_charge(self, charge):
        self._time_charge = charge[0]
        self._voltage_charge = charge[1]
        self._current_charge = charge[2]

        """
        Calculate the capacity C (mA.h) of the charge half-cycle as the 
        accumulated charge over time
        """
        # accumulated charge dq at each measurement step (mA.h)
        dq = abs(self._current_charge * self._time_charge.diff()) / 3.6

        # charge as cumulative sum (mA.h)
        self._Q_charge = dq.cumsum()

        # capacity as last value of accumulated charge (mA.h)
        self._capacity_charge = self._Q_charge.iloc[-1]
        """
        Calculate the total energy E (W.h) of the charge half-cycle as the 
        cumulative sum of energy over time
        """

        # instantaneous power (W)
        self._power_charge = abs(self._current_charge * self._voltage_charge)

        # istantaneous energy dE (W.h) at each measurement step and cumulative
        dE = (self._power_charge * self._time_charge.diff()) / 3.6
        self._energy_charge = dE.cumsum()

        # total energy (W.h)
        self._total_energy_charge = self._energy_charge.iloc[-1]

    def add_discharge(self, discharge):
        self._time_discharge = discharge[0]
        self._voltage_discharge = discharge[1]
        self._current_discharge = discharge[2]

        """
        Calculate the capacity C (mA.h) of the discharge half-cycle as the 
        accumulated charge over time
        """
        # accumulated charge dq at each measurement step (mA.h)
        dq = abs(self._current_discharge * self._time_discharge.diff()) / 3.6

        # charge as cumulative sum (mA.h)
        self._Q_discharge = dq.cumsum()    

        # capacity as last value of accumulated charge (mA.h)   
        self._capacity_discharge = self._Q_discharge.iloc[-1]   


        """
        Calculates the total energy E (W.h) of the charge half-cycle as the 
        cumulative sum of energy over time
        
        """
        # instantaneous power (W)
        self._power_discharge = abs(self._current_discharge * self._voltage_discharge)

        # istantaneous energy dE (W.h) at each measurement step and cumulative
        dE = (self._power_discharge * self._time_discharge.diff()) / 3.6
        self._energy_discharge = dE.cumsum()

        # total energy (W.h)
        self._total_energy_discharge = self._energy_discharge.iloc[-1]  # cheaper?

    ### TIME ###
    @property
    def index(self):
        return self._index
    
    @property
    def time_charge(self):
        return self._time_charge

    @property
    def time_discharge(self):
        return self._time_discharge

    @property
    def time(self):
        return self._time_charge.append(self._time_discharge)

    ### VOLTAGE ###
    @property
    def voltage_charge(self):
        return self._voltage_charge

    @property
    def voltage_discharge(self):
        return self._voltage_discharge

    @property
    def voltage(self):
        return self._voltage_charge.append(self._voltage_discharge)

    ### CURRENT ###
    @property
    def current_charge(self):
        return self._current_charge

    @property
    def current_discharge(self):
        return self._current_discharge

    @property
    def current(self):
        return self._current_charge.append(self._current_discharge)

    ### POWER ###
    @property
    def power_charge(self):
        return self._power_charge

    @property
    def power_discharge(self):
        return self._power_discharge

    @property
    def power(self):
        return self._power_charge.append(self._power_discharge)     

    ### ENERGY ###
    @property
    def energy_charge(self):
        return self._energy_charge

    @property
    def energy_discharge(self):
        return self._energy_discharge

    @property
    def energy(self):
        return self._energy_charge.append(self._energy_discharge)  

    ### ACCUMULATED CHARGE ###
    @property
    def Q_charge(self):
        return self._Q_charge

    @property
    def Q_discharge(self):
        return self._Q_discharge

    @property
    def Q(self):
        return self._Q_charge.append(self._Q_discharge)  

    ### CAPACITY ###
    @property
    def capacity_charge(self):
        return self._capacity_charge

    @property
    def capacity_discharge(self):
        return self._capacity_discharge

    ### ENERGY ###
    @property
    def total_energy_charge(self):
        return self._total_energy_charge

    @property
    def total_energy_discharge(self):
        return self._total_energy_discharge


    def calculate_efficiencies(self):
        """
        Computes the coulombic and energy efficiency of the cycle as the ratio 
        between the discharge and charge energies.
        """
        if any((self._capacity_charge <= 0, self._total_energy_charge <= 0)):
            # 101 is a sentinel value
            self._coulomb_efficiency = 101
            self._energy_efficiency = 101
            self._voltage_efficiency = 101
        else:
            self._coulomb_efficiency = (
                self._capacity_discharge / self._capacity_charge * 100
            )
            self._energy_efficiency = (
                self._total_energy_discharge / self._total_energy_charge * 100
            )
            self._voltage_efficiency = (
                self._energy_efficiency / self._coulomb_efficiency * 100
            )

        return (
            self._coulomb_efficiency,
            self._energy_efficiency,
            self._voltage_efficiency,
        )

    ### EFFICIENCIES ###
    @property
    def coulomb_efficiency(self):
        return self._coulomb_efficiency

    @property
    def energy_efficiency(self):
        return self._energy_efficiency

    @property
    def voltage_efficiency(self):
        return self._voltage_efficiency


def build_DTA_cycles(filelist):

    cycles = []
    cycle_index = 0

    for filepath in filelist:

        print("Loading:", filepath, "\n")

        filename = path.basename(filepath)
        extension = path.splitext(filename)[1]

        if extension.lower() == ".dta":

            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                beginning = None  # line at which the table begins
                npoints = None  # number of data points
                cycle_type = None  # 1 for charge, 0 for discharge

                # finding the "CURVE TABLE npoints" line in file
                for line_num, line in enumerate(file):

                    if "Step 1 Current (A)" in line:
                        if float(line.split()[2]) > 0:
                            cycle_type = 1  # positive current = charge
                        elif float(line.split()[2]) < 0:
                            cycle_type = 0  # negative current = discharge

                    if "CURVE" in line:
                        beginning = line_num + 2
                        npoints = int(line.split()[-1])
                        break

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
                data.rename(
                    columns={
                        "s": "Time (s)",
                        "V vs. Ref.": "Voltage vs. Ref. (V)",
                        "A": "Current (A)",
                    },
                    inplace=True,
                )

                if cycle_type == 1:
                    charge = (
                        data["Time (s)"],
                        data["Voltage vs. Ref. (V)"],
                        data["Current (A)"],
                    )
                    cyc = Cycle(cycle_index)
                    cyc.add_charge(charge)

                elif cycle_type == 0:
                    discharge = (
                        data["Time (s)"],
                        data["Voltage vs. Ref. (V)"],
                        data["Current (A)"],
                    )
                    cyc.add_discharge(discharge)
                    cyc.calculate_efficiencies()

                    if cyc.energy_efficiency < 100:
                        cycles.append(cyc)
                    cycle_index += 1

        else:
            print("This is not a .DTA file!")
            sys.exit()

    return cycles


def read_mpt_cycles(filelist, clean):

    cycles = []
    cycle_index = 0

    for filepath in filelist:
        print("Loading:", filepath, "\n")

        filename = path.basename(filepath)
        extension = path.splitext(filename)[1]

        if extension.lower() == ".mpt":

            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                delims = []  # contains cycle number, first and last line number
                beginning = None

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

                cycle_num = 0

                # initiate Cycle object providing dataframe view within delims
                while cycle_num < ncycles:
                    first_row = delims[cycle_num][1]
                    last_row = delims[cycle_num][2]+1

                    charge = (
                        data["Time (s)"][first_row:last_row][data["ox/red"] == 1],
                        data["Voltage vs. Ref. (V)"][first_row:last_row][
                            data["ox/red"] == 1
                        ],
                        data["Current (A)"][first_row:last_row][data["ox/red"] == 1],
                    )

                    discharge = (
                        data["Time (s)"][first_row:last_row][data["ox/red"] == 0],
                        data["Voltage vs. Ref. (V)"][first_row:last_row][
                            data["ox/red"] == 0
                        ],
                        data["Current (A)"][first_row:last_row][data["ox/red"] == 0],
                    )


                    missing_discharge = False

                    try:
                        cycle = Cycle(cycle_index)
                        cycle.add_charge(charge)
                        cycle.add_discharge(discharge)
                        
                        cycle.calculate_efficiencies()
                        unphysical = (
                            cycle.energy_efficiency > 100,
                            cycle.coulomb_efficiency > 100,
                            cycle.voltage_efficiency > 100,
                        )
                    except IndexError:
                        unphysical = [False]
                        missing_discharge = True
                        
                        
                    #fmt: off
                    if missing_discharge:
                        print(f"Warning: cycle {cycle._index} will be discarded "
                              "due to missing discharge data")                        
                    elif any(unphysical) and clean:
                        print(f"Warning: cycle {cycle._number} will be discarded "
                              "due to unphysical efficiencies")
                    #fmt:on
                    else:
                        cycles.append(cycle)

                    cycle_index += 1

                    cycle_num += 1

        else:
            print("This is not a .mpt file!")
            sys.exit()

    return cycles


def read_cycles(filelist, clean=False):
    if type(filelist) is str:
        filelist = [filelist]

    cycles = read_mpt_cycles(filelist, clean)

    return CellCycling(cycles)


def build_cycles(filelist):
    cycles = build_DTA_cycles(filelist)

    return CellCycling(cycles)


def time_adjust(cycle, reverse=False):

    if cycle.time_discharge.iloc[0] != cycle.time_charge.iloc[0]:
        time_charge = cycle.time_charge.subtract(cycle.time_charge.iloc[0])
        time_discharge = cycle.time_discharge.subtract(cycle.time_charge.iloc[-1])
    else:
        time_charge = cycle.time_charge
        time_discharge = cycle.time_discharge

    if reverse is True:
        switch = time_discharge-time_charge.iloc[-1]
        time_discharge = abs(switch)

    return time_charge, time_discharge
