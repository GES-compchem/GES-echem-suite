import pandas as pd
import numpy as np
import scipy.integrate as integrate


class CellCycling:
    """
    Contains all the cycles
    """
    def __init__(self, cycles):
        self._cycles = cycles

    def __getitem__(self, cycle):
        return self._cycles[cycle]

    def __iter__(self):
        for obj in self._cycles:
            yield obj

    def calculate_retention(self, reference = 0):
        """
        Calculates capacity retention between cycles, as the ratio between 
        capacity of cycle n (discharge) minus cycle 1 (discharge)
        """

        initial_capacity = self._cycles[reference].capacity_discharge

        self._retention = []

        for cycle in self._cycles:
            self._retention.append(cycle.capacity_discharge / initial_capacity * 100)

        return self._retention

    def calculate_efficiency(self):
        """
        Calculates capacity efficiency of the cycles, as the ratio between 
        capacity of cycle n in charge and discharge
        """

        self._efficiency = []

        for cycle in self._cycles:
            self._efficiency.append(cycle.capacity_discharge / cycle.capacity_charge * 100) 

    @property
    def retention(self):
        return self._retention

    @property
    def efficiency(self):
        return self._efficiency


class Cycle:
    """
    Contains the charge and discharge half-cycles
    """

    def __init__(self, number):
        self._number = number

    @property
    def number(self):
        return self._number

    def add_charge(self, charge):
       
        self._time_charge = charge[0]
        self._voltage_charge = charge[1]
        self._current_charge = charge[2]
        
        """
        Calculate the capacity C (mA.h) of the charge half-cycle as the 
        integral of current over time
        """
        
        self._capacity_charge = abs(integrate.trapz(self._current_charge, self._time_charge)) / 3.6 

        """
        Calculate the total energy E (W.h) of the charge half-cycle as the 
        integral of instantaneous energy over time
        """
        
        # instantaneous power (W)
        self._power_charge = abs(self._current_charge * self._voltage_charge)
        
        # accumulated charge (mA.h)
        dq = self._power_charge.div(3.6) * self._time_charge.diff()
        self._Q_charge = abs(dq.cumsum())

        # instantaneous energy (Wh)
        self._energy_charge = dq * self._voltage_charge / 1000
                    
        # total energy (W.h)
        self._total_energy_charge = abs(integrate.trapz(self._power_charge, self._time_charge)) / 3600


    def add_discharge(self, discharge):
        
        self._time_discharge = discharge[0]
        self._voltage_discharge = discharge[1]
        self._current_discharge = discharge[2]
        
        """
        Calculate the capacity C (mA.h) of the discharge half-cycle as the 
        integral of current over time
        """
        
        self._capacity_discharge = abs(integrate.trapz(self._current_discharge, self._time_discharge)) / 3.6 
        
        """
        Calculates the total energy E (W.h) of the charge half-cycle as the 
        integral of instantaneous energy over time
        
        """
        # instantaneous power (W)
        self._power_discharge = abs(self._current_discharge * self._voltage_discharge)

        # accumulated charge (mA.h)
        dq = self._power_discharge.div(3.6) * self._time_discharge.diff()
        self._Q_discharge = abs(dq.cumsum())

        # instantaneous energy (Wh)
        self._energy_discharge = dq * self._voltage_discharge / 1000
        
        # total energy (W.h)
        self._total_energy_discharge = abs(integrate.trapz(self._power_discharge, self._time_discharge)) / 3600


    # time
    @property
    def time_charge(self):                       
        return self._time_charge
    @property
    def time_discharge(self):                       
        return self._time_discharge

    # voltage
    @property
    def voltage_charge(self):                       
        return self._voltage_charge        
    @property
    def voltage_discharge(self):                       
        return self._voltage_discharge
    
    # current
    @property
    def current_charge(self):                       
        return self._current_charge
    @property
    def current_discharge(self):                       
        return self._current_discharge

    # power
    @property
    def power_charge(self):
        return self._power_charge
    @property
    def power_discharge(self):
        return self._power_discharge

    # energy
    @property
    def energy_charge(self):
        return self._energy_charge
    @property
    def energy_discharge(self):
        return self._energy_discharge

    # accumulated charge
    @property
    def Q_charge(self):
        return self._Q_charge
    @property
    def Q_discharge(self):
        return self._Q_discharge

    # capacity
    @property
    def capacity_charge(self):                       
        return self._capacity_charge
    @property
    def capacity_discharge(self):    
        return self._capacity_discharge

    # energy
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

        self._coulomb_efficiency = self._capacity_discharge / self._capacity_charge * 100
        self._energy_efficiency = self._total_energy_discharge / self._total_energy_charge * 100
        self._voltage_efficiency = self._energy_efficiency / self._coulomb_efficiency * 100

        return self._coulomb_efficiency, self._energy_efficiency, self._voltage_efficiency


    # efficiencies
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
    cycle_number = 1

    for filepath in filelist:

        print("Loading:", filepath, "\n")

        if filepath.endswith(".DTA"):                                        
        
            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                beginning = None    # line at which the table begins
                npoints = None      # number of data points
                cycle_type = None   # 1 for charge, 0 for discharge

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
                        filepath, delimiter = '\t', skiprows=beginning, 
                        decimal=".", nrows=npoints,
                        encoding_errors='ignore'

                )

                # renaming columns to standard format
                data.rename(
                    columns={
                        's': 'Time (s)', 
                        'V vs. Ref.': 'Voltage vs. Ref. (V)',
                        'A': 'Current (A)'
                    }, inplace=True
                )

                if cycle_type == 1:
                    charge = (
                        data['Time (s)'],
                        data['Voltage vs. Ref. (V)'],
                        data['Current (A)']
                    )
                    cyc = Cycle(cycle_number)
                    cyc.add_charge(charge)

                elif cycle_type == 0:
                    discharge = (
                        data['Time (s)'],
                        data['Voltage vs. Ref. (V)'],
                        data['Current (A)']
                    )
                    cyc.add_discharge(discharge)
                    cyc.calculate_efficiencies()

                    if cyc.energy_efficiency < 100:
                        cycles.append(cyc)
                    cycle_number += 1
                     
                    
        else:
            print("This is not a .DTA file!")
            exit()  

    return cycles


def read_mpt_cycles(filelist):

    cycles = []
    cycle_number = 1

    for filepath in filelist:

        print("Loading:", filepath, "\n")

        if filepath.endswith(".mpt"):  
      
            with open(filepath, "r", encoding="utf8", errors="ignore") as file:

                delims=[]   # contains cycle number, first and last line number
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
                        filepath, dtype=np.float64, delimiter = '\t', 
                        skiprows=beginning, decimal=",", 
                        encoding_errors='ignore'
                )

                # renaming columns to standard format
                data.rename(
                    columns={
                        'time/s': 'Time (s)', 
                        'Ewe/V': 'Voltage vs. Ref. (V)',
                        'I/mA': 'Current (A)'      # note: these are mA
                    }, inplace=True
                )  

                # convert mA to A
                data['Current (A)'] = data['Current (A)'].divide(1000)    

                cycle_num = 0

                # initiate Cycle object providing dataframe view within delims
                while cycle_num < ncycles:
                    first_row = delims[cycle_num][1]
                    last_row = delims[cycle_num][2]

                    charge = (
                        data['Time (s)'][first_row:last_row][data['ox/red'] == 1],
                        data['Voltage vs. Ref. (V)'][first_row:last_row][data['ox/red'] == 1],
                        data['Current (A)'][first_row:last_row][data['ox/red'] == 1]
                    )

                    discharge = (
                        data['Time (s)'][first_row:last_row][data["ox/red"] == 0],
                        data['Voltage vs. Ref. (V)'][first_row:last_row][data['ox/red'] == 0],
                        data['Current (A)'][first_row:last_row][data['ox/red'] == 0]
                    )
                                                      
                    cyc = Cycle(cycle_number)
                    cyc.add_charge(charge)
                    cyc.add_discharge(discharge)

                    cyc.calculate_efficiencies()

                    if cyc.energy_efficiency < 100:
                        cycles.append(cyc)
                   
                    cycle_number += 1
                    
                    cycle_num +=1   
                
        else:
            print("This is not a .mpt file!")
            exit() 

    return cycles


def read_cycles(filelist):
 
    cycles = read_mpt_cycles(filelist)
              
    return CellCycling(cycles)


def build_cycles(filelist):

    cycles = build_DTA_cycles(filelist)

    return CellCycling(cycles)    


def time_adjust(cycle):

    if cycle.time_discharge.iloc[0] != cycle.time_charge.iloc[0]:
        time_charge = cycle.time_charge.subtract(cycle.time_charge.iloc[0])
        time_discharge = cycle.time_discharge.subtract(cycle.time_charge.iloc[-1])
    else:
        time_charge = cycle.time_charge
        time_discharge = cycle.time_discharge

    return time_charge, time_discharge
