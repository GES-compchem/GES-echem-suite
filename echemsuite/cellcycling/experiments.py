from __future__ import annotations
from typing import List, Tuple, Dict
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from echemsuite.cellcycling.cycles import CellCycling, Cycle, HalfCycle


class RateExperiment:
    """
    The RateExperiment class provides a simple interface to charge rate experiments in which a cell is charged and
    discharged at different constant current values and the voltage and charge time are recorded and monitored. The
    class can be constructed manually, using the __init__ method, providing the list of single current steps and the list
    of cell-cycling experiments carried out at a given current. The class can also be constructed using the
    `from_Biologic_battery_module` classmethod that is setup to be able to directly parse Biologic modules sequences.

    Arguments
    ---------
    current_steps: List[float]
        The list of float values encoding the current (in Ampéres) used on each cell-cycling step.
    cellcycling_steps: List[CellCycling]
        The list of CellCycling objects encoding the measurement done at a given current.

    Raises
    ------
    RuntimeError
        Exception raised if a mismatch in lenght is detected between the given lists.
    """

    def __init__(self, current_steps: List[float] = [], cellcycling_steps: List[CellCycling] = []) -> None:
        if len(current_steps) != len(cellcycling_steps):
            raise RuntimeError("The current step list and the cellcycling one cannot have different lenght.")

        self.__current_steps: List[float] = current_steps
        self.__cellcycling_steps: List[CellCycling] = cellcycling_steps
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
    def reference(self, cellcycling: int, step: int) -> None:
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
    def from_Biologic_battery_module(self, path: str) -> RateExperiment:
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
            obj = RateExperiment()

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

            # Manually trigger the creation of the cellcycling object for the last current step, append it to the
            # cellcycling list and clean the cycles buffer.
            cellcycling = CellCycling(cycles=cycles)
            obj.__cellcycling_steps.append(cellcycling)
            obj.__current_steps.append(current_rate)
            current_rate = current_dict[identifier]
            cycles = []

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
