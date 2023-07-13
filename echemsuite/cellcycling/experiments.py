from __future__ import annotations
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from copy import deepcopy
from warnings import warn
from os import listdir
from os.path import isfile, isdir, join

import openpyxl
import pandas as pd
import numpy as np

from echemsuite.cellcycling.read_input import quickload_folder
from echemsuite.cellcycling.cycles import CellCycling, Cycle, HalfCycle


class RateExperiment:
    """
    The RateExperiment class provides a simple interface to charge rate experiments in which a cell is charged and
    discharged at different constant current values and the voltage and charge time are recorded and monitored. The
    class can be constructed manually, using the default __init__ method, providing the list of single current
    steps and the list of cell-cycling experiments carried out at a given current. The class can also be constructed
    using the `from_Biologic_battery_module` classmethod that is setup to be able to directly parse Biologic modules
    sequences.

    Arguments
    ---------
    current_steps: List[float]
        The list of current steps associated to each cell-cycling sequence.
    cellcycling_steps: List[CellCycling]
        The list of cellcycling object encoding the electrochemical data collected at various current steps.

    Raises
    ------
    RuntimeError
        Exception raised if a mismatch between the length fo the two lists has been detected.
    """

    def __init__(self, current_steps: List[float] = [], cellcycling_steps: List[CellCycling] = []) -> None:
        if len(current_steps) != len(cellcycling_steps):
            raise RuntimeError("The current step list and the cellcycling one cannot have different lenght.")

        self.__current_steps: List[float] = deepcopy(current_steps)
        self.__cellcycling_steps: List[CellCycling] = deepcopy(cellcycling_steps)
        self.__reference: Tuple[int, int] = (0, 0)

    def __str__(self) -> str:
        msg = "Rate Experiment\n"
        msg += "----------------------------------------\n"
        for rate, cellcycling in zip(self.__current_steps, self.__cellcycling_steps):
            msg += f"{rate}A : {len(cellcycling)} cycles\n"
        msg += "----------------------------------------\n"
        return msg

    def __repr__(self) -> str:
        return str(self)

    def __iter__(self):
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                yield cycle

    @property
    def reference(self) -> Tuple[int, int]:
        """
        The reference datapoint in respect to which the capacity retention will be computed.

        Returns
        -------
        Tuple[int, int]
            The tuple of two integer values the first of which indicates the cell-cycing experiment to which the datapoint
            belongs to, while the second one represents the point within the selected cell-cycling sequence.
        """
        return self.__reference

    @reference.setter
    def reference(self, input: Tuple[int, int]) -> None:
        cellcycling, step = input
        if cellcycling < 0 or cellcycling >= len(self.__cellcycling_steps):
            raise ValueError(
                f"Cannot use the cellcycling {cellcycling} as reference. Only {len(self.__cellcycling_steps)} are available."
            )

        if step < 0 or step >= len(self.__cellcycling_steps[cellcycling]):
            raise ValueError(
                f"Cannot select the datapoint number {cellcycling} is a cellcycling sequence of {len(self.__cellcycling_steps[cellcycling])} points."
            )

        self.__reference = (cellcycling, step)

    @classmethod
    def from_Biologic_battery_module(cls, path: str) -> RateExperiment:
        """
        Classmethod dedicated to the construction of a RateExperiment object starting from a Biologic battery module
        file.

        Arguments
        ---------
        path: str
            The path to the Biologic battery module file.

        Raises
        ------
        ValueError
            Exception raised if the sepcified path to the datafile is invalid.
        """
        if not isfile(path):
            raise ValueError(f"The file `{path}` does not exist.")

        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            # Define buffers for store the strings encoding date and time
            time_str, date_str = None, None

            raw_data: Dict[str, str] = {}
            keywords = ["Ns", "ctrl1_val", "ctrl_type", "charge/discharge"]

            # Read the beginning of the file to obtain all the fields containing the parameters describing the sequence
            # of operations in the module. End the cycle when the header of the table is encountered.
            for line in file:
                for keyword in keywords:
                    if line.startswith(f"{keyword} "):
                        raw_data[keyword] = line.split()[1::]

                if "Acquisition started on :" in line:
                    time_str = line.split(" ")[-1]
                    date_str = line.split(" ")[-2]

                if line.startswith("mode"):
                    break

            # Check if the current field (float) contains `,` or `.` to establish data format.
            US_number_format = False if "," in raw_data["ctrl1_val"] else True

            # Build the timestamp object
            timestamp = None
            if date_str is not None and time_str is not None:
                # Custom time format switch based on the number format used in the file
                if US_number_format:
                    month, day, year = date_str.split("/")
                else:
                    day, month, year = date_str.split("/")

                hours, minutes, seconds = time_str.split(":")

                # Check if the seconds field contains a decimal part and discard it
                if "." in seconds:
                    seconds = seconds.split(".")[0]

                # TO BE CHANGED AS SOON AS MORE INFO ABOUT .mpt FILES ARE AVAILABLE
                # TEMPORARY FIX to solve the issue of US date format with european
                if int(month) > 12:
                    tmp = month
                    month = day
                    day = tmp

                timestamp = datetime(
                    int(year),
                    int(month),
                    int(day),
                    int(hours),
                    int(minutes),
                    int(seconds),
                )

            else:
                raise RuntimeError("Failed to build file timestamp.")

            # Build conversion dictionaries to define operation type and associated charge/discharge rates
            operation_dict: Dict[int, str] = {}
            current_dict: Dict[int, float] = {}
            for n, optype, ctrl, current in zip(
                raw_data["Ns"],
                raw_data["charge/discharge"],
                raw_data["ctrl_type"],
                raw_data["ctrl1_val"],
            ):
                if ctrl.lower() == "loop":
                    continue

                operation_dict[int(n)] = optype
                current_dict[int(n)] = float(current.replace(",", "."))

            # Define buffer arrays to store the experimental step halfcycles together with their identifier
            halfcycles: List[HalfCycle] = []
            identifiers: List[int] = []

            # Define temporary variables to store values carried on during the parsing iterations
            last_label: int = None
            time, current, voltage = [], [], []

            # Parse all the lines of the table and extract all the experiment steps in the form of a list of halfcycles
            for line in file:
                sline = line.split()

                # If not yet set, set the lable of the experiment in the buffer
                if last_label == None:
                    last_label = int(sline[6])

                # If the label of the new line differs from the previous a new halfcyle is about to begin. Pack the old
                # data in an HalfCycle object, store it in the halfcyles buffer and clean all the temporary variables
                elif last_label != int(sline[6]):
                    halfcycle = HalfCycle(
                        time=pd.Series(time),
                        voltage=pd.Series(voltage),
                        current=pd.Series(current),
                        halfcycle_type=operation_dict[last_label].lower(),
                        timestamp=timestamp + timedelta(seconds=time[0]),
                    )
                    halfcycles.append(halfcycle)
                    identifiers.append(last_label)
                    time, current, voltage = [], [], []
                    last_label = int(sline[6])

                # Parse the new line extracting time, current and volage values
                time.append(float(sline[8].replace(",", ".")))
                current.append(float(sline[11].replace(",", ".")) / 1000)
                voltage.append(float(sline[10].replace(",", ".")))

            # When the end of the file is reached, the conversion usually triggered by a change in the line label will
            # not happen, as such run a manual conversion of the data remaining in the buffer
            halfcycle = HalfCycle(
                time=pd.Series(time),
                voltage=pd.Series(voltage),
                current=pd.Series(current),
                halfcycle_type=str(operation_dict[last_label]).lower(),
                timestamp=timestamp + timedelta(seconds=time[0]),
            )
            halfcycles.append(halfcycle)
            identifiers.append(last_label)

            # Just to be sure delete all the temporary variable previously defined
            del last_label
            del time
            del current
            del voltage

            # Create an empty RateExperiment object to be filled with the desired data
            obj = cls()

            # Define a set of temporary variables to store data used during the CellCycing object construction
            cycles = []
            current_rate = None
            charge, discharge = None, None
            for identifier, halfcycle in zip(identifiers, halfcycles):
                # If the current rate is not set, set it.
                if current_rate is None:
                    current_rate = current_dict[identifier]

                # If the new current rate of the step is different from the stored one, a new cell-cycling experiment is
                # about to start. Pack all the data in a CellCycling object and add it to the experiment being built
                elif current_rate != current_dict[identifier]:
                    # If data is left in the buffer convert it into a cycle and add it to the cycles buffer
                    if charge is not None or discharge is not None:
                        cycle = Cycle(number=len(cycles), charge=charge, discharge=discharge)
                        cycles.append(cycle)
                        charge, discharge = None, None

                    # Create the cellcycling object for the given current step, append it to the cellcycling list and
                    # clean the cycles buffer
                    cellcycling = CellCycling(cycles=cycles)
                    obj.__cellcycling_steps.append(cellcycling)
                    obj.__current_steps.append(current_rate)
                    current_rate = current_dict[identifier]
                    cycles = []

                # Build the cycles storing charge and dischage values in the buffers and add them into a Cylce object
                if halfcycle.halfcycle_type == "charge":
                    charge = halfcycle
                else:
                    discharge = halfcycle
                    cycle = Cycle(number=len(cycles), charge=charge, discharge=discharge)
                    cycles.append(cycle)
                    charge, discharge = None, None

            del halfcycles

            # Manually trigger the creation of the cellcycling object for the last current step, append it to the
            # cellcycling list and clean the cycles buffer.
            cellcycling = CellCycling(cycles=cycles)
            obj.__cellcycling_steps.append(cellcycling)
            obj.__current_steps.append(current_rate)
            current_rate = current_dict[identifier]
            cycles = []

            return obj

    @classmethod
    def from_ARBIN_csv_file(cls, csv_path: str, variation_threshold: float = 1.) -> RateExperiment:
        """
        Classmethod dedicated to the construction of a RateExperiment object starting from a ARBIN csv file. Please
        notice that the ARBIN .csv files do not specify the current associated to each step explicitly, as such the 
        average current per halfcycle will be used in the definition of the various rate steps. The division of
        the cell-cyclicing objects in different rate steps is generated automatically by the method using a fixed
        percentage threshold value. When the percentage variation threshold is exceeded the cell-cycling object is
        moved to a new current step.

        Arguments
        ---------
        csv_path: str
            The path to the `.csv` file generated from the ARBIN battery cycler.
        variation_threshold: float
            The threshold (in percentage) to be used in the indetification of a new current step (default: 1%)

        Raises
        ------
        ValueError
            Exception raised if the sepcified path to the datafile is invalid.
        """
        # Check if the specified file exists
        if not isfile(csv_path):
            raise ValueError(f"The file `{csv_path}` does not exist.")

        # Define temporary variable used to store parsed values useful in the definition of the halfcycles list
        timestamp: datetime = None  # Timestamp recorded at the start of a new data block
        step_idx: int = None  # Index associated to the current measurement step type
        time, current, voltage = [], [], []  # Lists to store time, current and voltage values of each halfcycle

        # List to store the parsed halfcycles
        halfcycles: List[HalfCycle] = []

        def parse_arbin_timestamp(timestamp_str: str) -> datetime:
            date_str = timestamp_str.split(" ")[0]
            time_str = timestamp_str.split(" ")[1]
            month, day, year = (int(n) for n in date_str.split("/"))
            hour, minute, second = (int(float(n)) for n in time_str.split(":"))
            timestamp = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
            return timestamp

        # Open the specified ARBIN csv datafile
        with open(csv_path, "r") as file:
            # Skip the first line containing the header
            _ = file.readline()

            # Iterate on the file line by line
            for line in file:
                # Remove the end of line character and split the comma separated values
                sline = line.rstrip("\n").split(",")

                # If this is the first iteration set the step index and read the first timestamp
                if step_idx is None:
                    step_idx = int(sline[5])
                    timestamp_str = sline[1].lstrip("\t")
                    timestamp = parse_arbin_timestamp(timestamp_str)

                # If a step index change is encountered (end of a charge/discharge process) pack the data in an halfcycle,
                # add the halfcycle to the halfcycles list, empty the buffer values, update the timestamp and step index
                if step_idx != int(sline[5]):
                    halfcycle = HalfCycle(
                        time=pd.Series(time),
                        voltage=pd.Series(voltage),
                        current=pd.Series(current),
                        halfcycle_type="charge" if current[0] > 0 else "discharge",
                        timestamp=timestamp,
                    )

                    halfcycles.append(halfcycle)

                    time, current, voltage = [], [], []
                    step_idx = int(sline[5])
                    timestamp_str = sline[1].lstrip("\t")
                    timestamp = parse_arbin_timestamp(timestamp_str)

                # Parse the current line and extract time, current, voltage
                time.append(float(sline[3]))
                current.append(float(sline[6]))
                voltage.append(float(sline[7]))

            # At the end of the file, process the data remaining in the buffer and create the last halfcycle
            halfcycle = HalfCycle(
                time=pd.Series(time),
                voltage=pd.Series(voltage),
                current=pd.Series(current),
                halfcycle_type="charge" if current[0] > 0 else "discharge",
                timestamp=timestamp,
            )

            halfcycles.append(halfcycle)

        # From the list of halfcycles eliminate those halfcycles with length equal to 1 and those containing only steps
        # recorded at zero current.
        halfcycles = [h for h in halfcycles if len(h) > 1 and all([i != 0 for i in h.current])]

        # Define empty lists to store current steps and the corresponding cell-cycling sequences
        current_steps, cellcycling_steps = [], []

        # Define temporary variables to store the charge halfcycle of each cycle and a list to store the cycles to be
        # used in composing the cell-cycling objects
        charge = None
        cycles_buffer = []

        # Iterate over all the halfcycles
        for hidx, halfcycle in enumerate(halfcycles):
            # Average magnitude of the current in the halfcycle
            iavg = abs(sum(halfcycle.current)) / len(halfcycle)

            # If this is the first iteration add the average current in the current steps list
            if current_steps == []:
                current_steps.append(iavg)

            # Compute the error between the stored average current value and the current average value.
            relative_error = 100 * abs(iavg - current_steps[-1]) / current_steps[-1]

            # If the relative error exceeds the 1% threshold or we reached the end of the halfcycles list trigger the
            # creation of the cell-cycling object corresponding to the current step
            if relative_error > 1 or hidx == len(halfcycles) - 1:
                # If a charge halfcycle is left in the buffer conclude the cycle buffer with the last charge
                if charge is not None:
                    cycle = Cycle(number=len(cycles_buffer) + 1, charge=charge, discharge=None)
                    cycles_buffer.append(cycle)
                    charge = None

                # Create the cellcycling object from the cycles buffer
                cellcycling = CellCycling(cycles_buffer)
                cellcycling_steps.append(cellcycling)
                cycles_buffer = []

                # If this is not the last halfcycle in the halfcyles list append the new current value to the current step list
                if hidx != len(halfcycles) - 1:
                    current_steps.append(iavg)

            # If the current halfcycle is a charge add it to the buffer else complete the cycle using the buffered object,
            # append the cycle to the cycles buffer and clean the charge buffer
            if halfcycle.halfcycle_type == "charge":
                charge = halfcycle
            else:
                cycle = Cycle(number=len(cycles_buffer) + 1, charge=charge, discharge=halfcycle)
                cycles_buffer.append(cycle)
                charge = None

        # Format the current steps list by rounding the current values to the third decimal place
        current_steps = [round(i, 3) for i in current_steps]

        # Creat a RateExperiment object with the obtained data ad return it
        obj = cls(current_steps=current_steps, cellcycling_steps=cellcycling_steps)
        return obj

    @classmethod
    def from_GAMRY_folder_tree(cls, basefolder: str, current_digits: int = 3) -> RateExperiment:
        """
        Classmethod dedicated to the construction of a RateExperiment object starting from a folder tree generated by
        GAMRY instruments during multi-step cycling experiments. The folder structure expected is the following: a 
        `basefolder` containing a set of step data-folders (with variable names) each of which contains a `CHARGE_DISCHARGE`
        folder containing the desired .DTA files encoding the charge/discharge cell-cycling at a given current.
        The current steps of the experiments are computed automatically as averages and rounded to a user specified
        number of digits (default: 3)

        Arguments
        ---------
        basefolder: str
            The path to the `basefolder` containing the data-folders for each step.
        current_digits: int
            Number of digits to be kept in saving the average current values computed form the data-files (default: 3).
        
        Raises
        ------
        ValueError
            Exception raised if the specified basefolder does not exist
        RuntimeError
            Exception raised if no cell-cycing data is found in the specified path.
        """
        # Check if the specified basefolder exists
        if not isdir(basefolder):
            raise ValueError(f"The folder '{basefolder}' does not exist.")
        
        # Define an empty list to store all the cell-cycling experimental data
        cellcycling_steps: List[CellCycling] = []

        # Cycle over the content of the basefolder
        for folder_name in listdir(basefolder):
            
            # Define an hypotetical search path for the CHARGE_DISCHARGE target folder
            path = join(join(basefolder, folder_name), "CHARGE_DISCHARGE")

            # Check if the folder containing the data is found
            if not isdir(path):
                continue
            
            # Try to load the data from the CHARGE_DISCHARGE folder if the load fails (e.g. the folder is empty)
            # return a warning messange to the user
            cellcycling: CellCycling = None
            try:
                cellcycling = quickload_folder(path, ".DTA")
            except:
                warn(f"Failed to load file from {path}. The folder will be skipped")
            else:
                cellcycling_steps.append(cellcycling)
        
        # Check if data has been loaded, if not raise an exception
        if cellcycling_steps == []:
            raise RuntimeError("No valid GAMRY cell-cycling data has been found in the specified folder.")

        # Sort the cell-cycling objects based on their timestamp
        cellcycling_steps.sort(key=lambda x: x.timestamp)
        
        # Evaluate the current value for each step computing the average current during the charge and discharge halfcyles
        current_steps: List[float] = []
        for cellcycling in cellcycling_steps:
            
            iavg: float = 0
            nsamples: int = 0
            for cycle in cellcycling:
                for halfcycle in [cycle.charge.current, cycle.discharge.current]:
                    for current in halfcycle:
                        iavg += abs(current)
                        nsamples += 1
            
            iavg = round(iavg/nsamples, current_digits)
            current_steps.append(iavg)

        # Create a RateExperiment object and return it
        obj = cls(current_steps=current_steps, cellcycling_steps=cellcycling_steps)
        return obj

    @property
    def capacity_retention(self) -> List[float]:
        """
        List of capacity retentions calculated as the ratios between the discharge capacity at cycle ``n`` and the
        discharge capacity of the reference cycle. To change the reference cycle, set the
        :py:attr:`~echemsuite.cellcycling.experiments.RateExperiment.reference` property.

        Returns
        -------
        List[float]
            The list of float values encoding the capacity retention of each step in the experiment in respect to the
            selected reference datapoint.
        """
        cellcycling_id, cycle_number = self.reference
        initial_capacity = self.__cellcycling_steps[cellcycling_id][cycle_number].discharge.capacity

        capacity_retention = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                if cycle.discharge:
                    capacity_retention.append(cycle.discharge.capacity / initial_capacity * 100)
                else:
                    capacity_retention.append(None)

        return capacity_retention

    @property
    def coulomb_efficiencies(self) -> List[float]:
        """
        List of all the coulombic efficiencies associated to the experimental datapoints. The list contains all the steps
        contained in all the cell-cycling experiments. Coulombic efficiency of the cycle computed according to
        :math:`100 \cdot Q_{\mathrm{discharge}}/ Q_{\mathrm{charge}}` where :math:`Q_{\mathrm{charge}}` and
        :math:`Q_{\mathrm{discharge}}` represent the capacity of the charge and discharge cycle respectively.

        Returns
        -------
        List[float]
            List of all the columbic efficiencies values associated to each datapoints of the experiment.
        """
        coulomb_efficiency = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                if cycle.charge and cycle.discharge:
                    if cycle.charge.capacity <= 0 or cycle.charge.total_energy <= 0:
                        coulomb_efficiency.append(101)

                    else:
                        coulomb_efficiency.append(cycle.discharge.capacity / cycle.charge.capacity * 100)

                else:
                    coulomb_efficiency.append(None)

        return coulomb_efficiency

    @property
    def energy_efficiencies(self) -> List[float]:
        """
        List of all the energy efficiencies associated to the experimental datapoints. The list contains all the steps
        contained in all the cell-cycling experiments. Energy efficiency of the cycle computed according to
        :math:`100 \cdot E_{\mathrm{discharge}}/ E_{\mathrm{charge}}` where :math:`E_{\mathrm{charge}}` and
        :math:`E_{\mathrm{discharge}}` represent the total energy associated to the charge and discharge cycle respectively.

        Returns
        -------
        List[float]
            List of all the energy efficiencies values associated to each datapoints of the experiment.
        """
        energy_efficiency = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                if cycle.charge and cycle.discharge:
                    if cycle.charge.capacity <= 0 or cycle.charge.total_energy <= 0:
                        energy_efficiency.append(101)

                    else:
                        energy_efficiency.append(cycle.discharge.total_energy / cycle.charge.total_energy * 100)

                else:
                    energy_efficiency.append(None)

        return energy_efficiency

    @property
    def voltage_efficiency(self) -> List[float]:
        """
        List of all the voltaic efficiencies associated to the experimental datapoints. The list contains all the steps
        contained in all the cell-cycling experiments. Voltaic efficiency of the cycle computed according to
        :math:`\eta_{E}/\eta_{Q}` where :math:`\eta_{E}` represents the energy efficiency of the cycle while
        :math:`\eta_{Q}` represent the correspondent coulombic efficiency.

        Returns
        -------
        List[float]
            List of all the voltaic efficiencies values associated to each datapoints of the experiment.
        """
        return [
            100 * EE / CE if EE is not None and CE is not None else None
            for EE, CE in zip(self.energy_efficiencies, self.coulomb_efficiencies)
        ]

    @property
    def capacity(self) -> List[float]:
        """
        List of all the capacities (in mAh) for the discharge half-cycle objects of all the cycles in the experiment.

        Returns
        -------
        List[float]
            the discharge capacity of the cell observed during all the half-cycle in the experiment.
        """
        capacity = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                capacity.append(cycle.discharge.capacity if cycle.discharge is not None else None)

        return capacity

    @property
    def total_energy(self) -> List[float]:
        """
        List of all the energies values (in mWh) for the discharge half-cycle objects of all the cycles in the experiment.

        Returns
        -------
        List[float]
            the discharge energy of the cell observed during all the half-cycle in the experiment.
        """
        total_energy = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                total_energy.append(cycle.discharge.total_energy if cycle.discharge is not None else None)

        return total_energy

    @property
    def average_power(self) -> List[float]:
        """
        The Average power (in W) for the discharge half-cycle of all the cycles in the experiment.

        Returns
        -------
        List[float]
            the average power value for all the discharge half-cycles.
        """
        average_power = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                average_power.append(cycle.discharge.average_power if cycle.discharge is not None else None)

        return average_power

    @property
    def numbers(self) -> List[int]:
        """
        Returns a simple array with a progressive number for all datapoints.

        Returns
        -------
        List[int]
            A simple array with a progressive number for all datapoints.
        """
        return [i + 1 for i, _ in enumerate(self)]

    @property
    def current_steps(self) -> List[float]:
        """
        Returns an array containing the current values associated with each cycle in the experiment

        Returns
        -------
        List[float]
            A simple array with a progressive number for all datapoints.
        """
        current_steps = []
        for current, cellcycling in zip(self.__current_steps, self.__cellcycling_steps):
            for _ in cellcycling:
                current_steps.append(current)

        return current_steps

    @property
    def cycles(self) -> List[Cycle]:
        """
        Returns the array containing all the cycles object associated to each current step

        Returns
        -------
        List[Cycle]
            A simple array containing the sequece of Cycle objects associated to each explored current value
        """
        cycles = []
        for cellcycling in self.__cellcycling_steps:
            for cycle in cellcycling:
                cycles.append(cycle)

        return cycles

    def dump_to_excel(self, path: str, volume: float, area: float) -> None:
        """
        Dump an excel report containing all the information associated with the experiment.

        Arguments
        ---------
        path: str
            The path in which the .xlsx file will be saved.
        volume: float
            The electrolyte volume to be used in computing the volumetric densities.
        area: float
            The electrode area to be used in the calculatrion of densities values.
        """
        csv = "N°,C.D,A.P.D.,C,E,C.R.,CE,VE,EE,V.C,E.D\n"
        csv += "N°,mA/cm2,mW/cm2,mAh,mWh,%,%,%,%,Ah/L,Wh/L\n"

        for i, N in enumerate(self.numbers):
            CD = 1000 * self.current_steps[i] / area
            APD = 1000 * self.average_power[i] / area
            C = self.capacity[i]
            E = self.total_energy[i]
            CR = self.capacity_retention[i]
            CE = self.coulomb_efficiencies[i]
            VE = self.voltage_efficiency[i]
            EE = self.energy_efficiencies[i]
            VC = self.capacity[i] / volume
            ED = self.total_energy[i] / volume
            csv += f"{N},{CD},{APD},{C},{E},{CR},{CE},{VE},{EE},{VC},{ED}\n"

        # Convert the csv file into xlsx format
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        for r, row in enumerate(csv.split("\n")):
            if r < 2:
                sheet.append(row.split(","))
            else:
                sheet.append([float(x) if x != "" and x != "None" else x for x in row.split(",")])

        workbook.save(path)

    def append(self, object: RateExperiment) -> None:
        """
        Concatenate to the curren object the rate experiments datapoints provided by a second RateExperiment object

        Arguments
        ---------
        object: RateExperiment
            The rate experiment object providing the data to be included in the current experiment dataset
        """
        if type(object) != RateExperiment:
            raise TypeError(f"The type of `object` must be `RateExperiment` not `{type(object)}`")

        for current, cellcycling in zip(object.__current_steps, object.__cellcycling_steps):
            self.__current_steps.append(current)
            self.__cellcycling_steps.append(cellcycling)
