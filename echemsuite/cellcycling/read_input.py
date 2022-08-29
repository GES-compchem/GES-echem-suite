from copy import deepcopy
import logging
import pandas as pd
import numpy as np
from os import listdir, path
from enum import Enum
from io import BytesIO, TextIOWrapper
from typing import Dict, List
from datetime import datetime, timedelta

from echemsuite.utils import deprecation_warning
from echemsuite.cellcycling.cycles import CellCycling, Cycle, HalfCycle, join_HalfCycles


logger = logging.getLogger(__name__)


class Instrument(Enum):
    """
    Simple enumeration class to easily reference instrument types.

    Attributes
    ----------
    GAMRY
        GAMRY instrument producing .DTA files (value [str]: "GAMRY")
    BIOLOGIC
        BIOLOGIC instrument producing .mpt files (value [str]: "BIOLOGIC")
    """

    GAMRY = "GAMRY"
    BIOLOGIC = "BIOLOGIC"


class FileManager:
    """
    Universal loader class for cell-cycling files. The class provides a simple interface to
    load .dta and .mpt files from a user-specified path. The class stores the loaded files
    in memory using a dictionary of BytesIO objects. The class implements parse and sorting
    functions that allow the user to read the halfcycles files, organize them based on their
    timestamp and join them in a specified order to build a list of complete cycles. The
    class also supports the joining of partial halfcycles files.

    Arguments
    ---------
    verbose : bool
        if set to True, a progress report for the main functions will be reported on terminal
    """

    def __init__(self, verbose: bool = False) -> None:

        self.verbose: bool = verbose  # Enable output to the terminal

        # Dictionary for the BytesIO streams containing the datafiles ordered by a valid path string
        self._bytestreams: Dict[str, BytesIO] = {}

        self._halfcycles: Dict[str, HalfCycle] = {}  # List of the loaded halfcycles
        self._instrument: Instrument = None  # Instrument from which the data are obtained

    @property
    def bytestreams(self) -> Dict[str, BytesIO]:
        """
        Dictionary containing the BytesIO of the loaded files orderd by a filename sting key.

        Returns
        -------
        Dict[str, BytesIO]
        """
        for stream in self._bytestreams.values():
            stream.seek(0)
        return self._bytestreams

    @bytestreams.setter
    def bytestreams(self, value: Dict[str, BytesIO]) -> None:
        if type(value) != dict:
            logger.error(
                f"Bytestream setter expects a Dict type. Received '{type(value)}' instead"
            )
            raise TypeError

        for key, item in value.items():
            if type(key) != str or type(item) != BytesIO:
                logger.error(
                    f"Bytestream dictionary must be of type Dict[str, BytesIO]. Received 'Dict[{type(key)}, {type(item)}]' instead."
                )
                raise ValueError

        self._bytestreams = value

    @bytestreams.deleter
    def bytestreams(self) -> None:
        self._bytestreams = {}

    @property
    def halfcycles(self) -> Dict[str, HalfCycle]:
        """
        Dictionary containing the :py:class:`~echemsuite.cellcycling.cycles.HalfCycle`
        objects parsed from the bytestreams register each object is associated with a key
        that coincides with the filename in the case of .dta files or with a fictitious key
        (reporting type and cycle number o the halfcycle) in case of the .mpt files.

        Retuns
        ------
        Dict[str, :py:class:`~echemsuite.cellcycling.cycles.HalfCycle`]
        """
        return self._halfcycles

    @halfcycles.setter
    def halfcycles(self, value: Dict[str, HalfCycle]):
        if type(value) != dict:
            logger.error(
                f"Halfcycles setter expects a Dict type. Received '{type(value)}' instead"
            )
            raise TypeError

        for key, item in value.items():
            if type(key) != str or type(item) != HalfCycle:
                logger.error(
                    f"Halfcycles dictionary must be of type Dict[str, HalfCycle]. Received 'Dict[{type(key)}, {type(item)}]' instead."
                )
                raise ValueError
        self._halfcycles = value

    @property
    def instrument(self) -> str:
        """
        Type of instrument used to acquire the loaded dataset. The strings are encoded as
        key of the :py:class:`~echemsuite.cellcycling.read_input.Instrument` enumeration

        Returns
        -------
        str
        """
        return self._instrument.name

    def fetch_files(self, filelist: List[str], autoparse: bool = True) -> None:
        """
        Loads, as ``BytesIO`` streams, multiple files contained in a user defined filelist.

        Arguments
        ---------
        filelist : List[str]
            list containing the path to the files that needs to be loaded
        autoparse : bool
            if set to True, will automatically call the
            :py:func:`~echemsuite.cellcycling.read_input.FileManager.parse` member function
            at the end of the fetching operation

        Raises
        ------
        ValueError
            if the extensions of the files in the provided file-list do not match
        TypeError
            if the extensions of the provided files does not match the supported types (.DTA
            or .mpt)
        """

        # Convert all the given paths to absolute paths
        buffer = [path.abspath(filepath) for filepath in filelist]
        filelist = deepcopy(buffer)

        # Take the extension of the first file as reference
        extension = path.splitext(path.basename(filelist[0]))[1]

        self._bytestreams = {}  # Empty the bytestream buffer

        # Load each file in the filelist
        for filepath in filelist:

            filename = path.basename(filepath)

            if self.verbose:
                print(f"-> Loading: {filename}")

            # Check if the extension of each file matches the extension taken from the first
            file_extension = path.splitext(filename)[1]
            if file_extension != extension:
                logger.error("file extensions in filelist do not match")
                raise ValueError

            # Check if the extension matches any of the existing instrument profiles
            if extension.lower() == ".dta":
                self._instrument = Instrument.GAMRY
            elif extension.lower() == ".mpt":
                self._instrument = Instrument.BIOLOGIC
            else:
                logger.error(
                    f"The extension '{extension}' does not appear among the known file types."
                )
                raise TypeError

            # Load the whole file in the bytestreams buffer
            with open(filepath, "r", encoding="utf-8", errors="ignore") as file:

                if file.readlines() == []:
                    if self.verbose:
                        print(
                            f"\u001b[35;1mWARNING:\u001b[0m empty file found. Skipping {filename}."
                        )
                    logger.warning(f"Empty file found. Skipping {filename}.")
                    continue

                file.seek(0)
                self._bytestreams[filename] = BytesIO(file.read().encode("utf-8"))

        if self.verbose:
            print(f"A total of {len(self._bytestreams)} files have been loaded")

        if autoparse:
            self.parse()

    def fetch_from_folder(
        self, folder: str, extension: str, autoparse: bool = True
    ) -> None:
        """
        Loads, as BytesIO streams, multiple files from a folder filtering them by extension.

        Parameters
        ----------
        folder : str
            string containing the path to the folder from which the files needs to be loaded
        extension : str
            string containing the extension of the files to be loaded
        autoparse : bool
            if set to True will automatically call the parse member function at the end of
            the fetching operation

        Raises
        ------
        ValueError
            if the provided path does not correspond to a valid folder
        TypeError
            if the extensions of the provided files does not match the supported types (.DTA
            or .mpt)
        """

        # Check if directory exists
        if path.isdir(folder) == False:
            logger.error(f"The path '{folder}' does not correspond to a folder.")
            raise ValueError
        folder = path.abspath(folder)

        # Check if the extension matches any of the existing instrument profiles
        if extension.lower() not in [".dta", ".mpt"]:
            logger.error(
                f"The extension '{extension}' does not appear among the known file types."
            )
            raise TypeError

        # Load the file in the bytestream buffer
        filelist = []
        for filename in listdir(folder):
            if filename.endswith(extension):
                filelist.append(path.join(folder, filename))

        self.fetch_files(filelist, autoparse=autoparse)

    def parse(self) -> None:
        """
        Parse the BytesIO streams contained in the "bytestreams" buffer and update the
        "halfcycles" dictionary.

        Raises
        ------
        RuntimeError
            if the bytestream buffer is empty or if one of the required fields is not present
            in one of the loaded files
        """

        # Check if the bytestreams buffer is empty
        if self.bytestreams == {}:
            logger.error("Parse function called on empty bytestreams dictionary.")
            raise RuntimeError

        # Load the halfcycles from data in the bytestreams buffer based on the type of instrument
        self._halfcycles = {}
        if self._instrument == Instrument.GAMRY:
            for filename, bytestream in self.bytestreams.items():

                if self.verbose:
                    print(f"-> Parsing: {filename}")

                beginning = None  # line at which the table begins
                npoints = None  # number of data points
                halfcycle_type = None  # charge/discharge

                date_str, time_str = None, None  # Date and time string buffers
                timestamp = None  # Timestamp reported in the file

                data = pd.DataFrame()  # Empty pandas dataframe to store data

                # Flag to check the format of the numbers used in the file
                US_number_format: bool = True

                # Parsing the file
                textStream = TextIOWrapper(bytestream, encoding="utf-8")
                textStream_lines = textStream.readlines()
                for line_num, line in enumerate(textStream_lines):

                    line = line.strip("\n")

                    # Read the time and date lines
                    if line.startswith("DATE"):
                        date_str = line.split()[2]
                    elif line.startswith("TIME"):
                        time_str = line.split()[2]

                    # Read the sign of the current to define halfcycle type
                    if "Step 1 Current (A)" in line:
                        if float(line.split()[2]) > 0:
                            halfcycle_type = "charge"  # positive current = charge
                        elif float(line.split()[2]) < 0:
                            halfcycle_type = "discharge"  # negative current = discharge

                    # Search the "CURVE TABLE npoints" line and load the data
                    if line.startswith("CURVE"):
                        beginning = line_num + 2
                        npoints = int(line.split()[-1])

                        # Check if the first number of the data line contains ","
                        if "," in textStream_lines[beginning + 1].split()[3]:
                            US_number_format = False  # If yes switch to european format

                        # Rewind the pointer to the beginning of the stream
                        textStream.seek(0)
                        data = pd.read_table(
                            textStream,
                            delimiter="\t",
                            skiprows=beginning,
                            decimal="." if US_number_format else ",",
                            nrows=npoints,
                            encoding_errors="ignore",
                        )

                        textStream.detach()  # Detaches the TextIOWrapper from the BytesIO stream to avoid bytestream closing on wrapper out of scope
                        break

                # Confirm that the data has been loaded
                if data.empty:
                    logger.error("Failed to locate the CURVE section.")
                    raise RuntimeError

                # Build the timestamp object
                if date_str is not None and time_str is not None:

                    # Custom time format switch based on the number format used in the file
                    if US_number_format:
                        month, day, year = date_str.split("/")
                    else:
                        day, month, year = date_str.split("/")

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
                    logger.error("Failed to build file timestamp.")
                    raise RuntimeError

                # Renaming columns to standard format
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

                # Drop the lines corresponding to t<=0 and skip whe detecting empty dataframes
                data.drop(data[data["Time (s)"] <= 0].index, inplace=True)

                if data.empty:
                    continue

                start_time = data["Time (s)"].iloc[0]
                time = data["Time (s)"].subtract(start_time)
                voltage = data["Voltage vs. Ref. (V)"]
                current = data["Current (A)"]

                if halfcycle_type is None:
                    if current[0] > 0:
                        halfcycle_type = "charge"
                    elif current[0] < 0:
                        halfcycle_type = "discharge"

                self._halfcycles[filename] = HalfCycle(
                    time, voltage, current, halfcycle_type, timestamp
                )

        elif self._instrument == Instrument.BIOLOGIC:

            for filename, bytestream in self.bytestreams.items():

                if self.verbose:
                    print(f"-> Parsing: {filename}")

                delims = []  # contains cycle number, first and last line number
                beginning = None  # line at which the data table begins
                ncycles = 1  # number of charge/discharge cycles

                date_str, time_str = None, None  # Date and time string buffers
                timestamp = None  # Timestamp reported in the file

                # Flag to check the format of the numbers used in the file
                US_number_format: bool = True

                # Parsing the file
                textStream = TextIOWrapper(bytestream, encoding="utf-8")
                textStream_lines = textStream.readlines()
                for line_num, line in enumerate(textStream_lines):

                    line = line.strip("\n")

                    if "Acquisition started on :" in line:
                        time_str = line.split(" ")[-1]
                        date_str = line.split(" ")[-2]

                    elif "Number of loops : " in line:
                        ncycles = int(line.split(" ")[-1])

                    # Before the output of the experiment, EClab lists the
                    # starting and ending line of each loop. These will be used
                    # to slice the pandas dataframe into the different cycles.
                    elif "Loop " in line:
                        loop_num = int(line.split(" ")[1])
                        first_pos = int(line.split(" ")[-3])
                        second_pos = int(line.split(" ")[-1])
                        delims.append([loop_num, first_pos, second_pos])

                    elif "mode\t" in line:
                        beginning = line_num

                        # if no cycles are found, default to "read everything"
                        if len(delims) == 0:
                            delims = [[0, 0, -2]]  # -2 will be converted to -1 later

                        # Check if the first number of the data line contains ","
                        if "," in textStream_lines[beginning + 1].split()[4]:
                            US_number_format = False  # If yes switch to european format

                        # Rewind the pointer to the beginning of the stream
                        textStream.seek(0)

                        # reading data from file
                        data = pd.read_table(
                            textStream,
                            dtype=np.float64,
                            delimiter="\t",
                            skiprows=beginning,
                            decimal="." if US_number_format else ",",
                            encoding_errors="ignore",
                        )

                        textStream.detach()  # Detaches the TextIOWrapper from the BytesIO stream to avoid bytestream closing on wrapper out of scope
                        break

                # Confirm that the data has been loaded
                if data.empty:
                    logger.error("Failed to locate the header section.")
                    raise RuntimeError

                # Build the timestamp object
                if date_str is not None and time_str is not None:

                    # Custom time format switch based on the number format used in the file
                    if US_number_format:
                        month, day, year = date_str.split("/")
                    else:
                        day, month, year = date_str.split("/")

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
                    logger.error("Failed to build file timestamp.")
                    raise RuntimeError

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

                # Iterate on the provided data and build the halfcycles dictionary
                cycle_num = 0
                while cycle_num < ncycles:

                    first_row = delims[cycle_num][1]
                    last_row = delims[cycle_num][2] + 1

                    # Extract a view of the charge/discharge cycle
                    cycle_sub_data = data[first_row:last_row]

                    # Extract dataset view of the charge cycle, compute timestamp and create HalfCycle object
                    charge = None
                    charge_data = cycle_sub_data[cycle_sub_data["ox/red"] == 1]
                    if charge_data.empty == False:

                        charge_timestamp = timestamp + timedelta(
                            seconds=charge_data["Time (s)"].tolist()[0]
                        )

                        start_time = charge_data["Time (s)"].iloc[0]
                        shifted_timescale = charge_data["Time (s)"].subtract(start_time)

                        charge = HalfCycle(
                            shifted_timescale,
                            charge_data["Voltage vs. Ref. (V)"],
                            charge_data["Current (A)"],
                            "charge",
                            charge_timestamp,
                        )

                    # Extract dataset view of the discharge cycle, compute timestamp and create HalfCycle object
                    discharge = None
                    discharge_data = cycle_sub_data[cycle_sub_data["ox/red"] == 0]
                    if discharge_data.empty == False:

                        discharge_timestamp = timestamp + timedelta(
                            seconds=discharge_data["Time (s)"].tolist()[0]
                        )

                        start_time = discharge_data["Time (s)"].iloc[0]
                        shifted_timescale = discharge_data["Time (s)"].subtract(start_time)

                        discharge = HalfCycle(
                            shifted_timescale,
                            discharge_data["Voltage vs. Ref. (V)"],
                            discharge_data["Current (A)"],
                            "discharge",
                            discharge_timestamp,
                        )

                    if charge is not None and discharge is not None:

                        # Apply a preventive ordering in halfcycle insertion into dictionary
                        if charge_timestamp < discharge_timestamp:
                            self._halfcycles[f"charge_{cycle_num}_{filename}"] = charge
                            self._halfcycles[
                                f"discharge_{cycle_num}_{filename}"
                            ] = discharge
                        else:
                            self._halfcycles[
                                f"discharge_{cycle_num}_{filename}"
                            ] = discharge
                            self._halfcycles[f"charge_{cycle_num}_{filename}"] = charge

                    elif charge is not None:
                        self._halfcycles[f"charge_{cycle_num}_{filename}"] = charge

                    elif discharge is not None:
                        self._halfcycles[f"discharge_{cycle_num}_{filename}"] = discharge

                    cycle_num += 1

        if self.verbose:
            print("Parsing completed")

    def suggest_ordering(self) -> List[List[str]]:
        """
        Examine the bytestreams buffer and suggests a possible file ordering and merging
        scheme based on half-cycle type and timestamp.

        Returns
        -------
        List[List[str]]
            list of lists of filenames. Each list contains the halfcycles entries that must
            be merged in a single HalfCycle class.
        """
        # Sort the halfcycles files accorging to their timestamp
        ordered_items = sorted(self._halfcycles.items(), key=lambda x: x[1].timestamp)

        order: List[List[str]] = []

        ncycles, index = 0, 0
        while index <= len(ordered_items) - 1:

            name, ref_obj = ordered_items[index]  # Take the first object as a reference
            order.append([name])  # Add the first object name to the list
            index += 1  # Move the pointer to the next element in the ordered_items list

            # Check if the index reached the end of the list
            if index >= len(ordered_items):
                break

            # Start a iteration loop to search for partial halfcycles
            while True:

                # Check if the halfcycle pointed by index is the same type as the reference one
                if ordered_items[index][1].halfcycle_type == ref_obj.halfcycle_type:
                    # Append the partial halfcycle to the current halfcycle index and move the pointer
                    order[ncycles].append(ordered_items[index][0])
                    index += 1
                else:
                    break

                # Check if the index reached the end of the list (double brake catched by while loop condition)
                if index >= len(ordered_items):
                    break

            ncycles += 1  # Increment the halfcycle index

        return order

    def get_cycles(self, custom_order: List[str] = [], clean: bool = False) -> List[Cycle]:
        """
        Build the Cycles list from a given halfcycles order.

        Parameters:
        -----------
        custom_order: List[str]
            list of lists of filenames. Each list contains the half-cycles entries that must
            be merged in a single HalfCycle object. If left empty the ordering generated by
            the suggest_ordering method will be used.
        clean : bool
            if set to True, only displays cycles with physical meaning (efficiencies < 100%
            and both charge + discharge available). If False (default), load everything.

        Returns:
        --------
        List[:py:class:`~echemsuite.cellcycling.cycles.Cycle`]
            list containing the set of charge/discharge Cycles objects created from the
            given dataset
        """

        # If available use user ordering as order list else use the suggested one
        order: List[List[str]] = (
            self.suggest_ordering() if custom_order == [] else custom_order
        )

        # Create a local list of subsequent halfcycles by joining partial ones if existent
        halfcycles = []
        for block in order:  # Iterate over each ordering block
            if len(block) == 1:
                # If the halfcycle is complete append it to the halfcycle list as it is
                halfcycles.append(self._halfcycles[block[0]])
            else:
                # Else create a list of partial halfcycles and join them in a single one
                merge_list = [self._halfcycles[name] for name in block]
                halfcycles.append(join_HalfCycles(merge_list))

        cycles = []  # Empty list to hold the cycles
        cycle_number = 0  # Cycle counter to give to the cycles subsequent integer numbering

        # Iterate over the ordered list of complete halfcycles and build the cycles
        # ASSUMPTION: a cycle always starts with a charge
        while halfcycles:
            half = halfcycles.pop(0)  # Extract the first halfcycle from the list

            # If the type is a charge search for the discharge and complete the cycle
            if half.halfcycle_type == "charge":
                charge = half
                try:
                    discharge = halfcycles.pop(0)
                    cycle = Cycle(number=cycle_number, charge=charge, discharge=discharge)
                except:
                    cycle = Cycle(number=cycle_number, charge=charge, discharge=None)
                    pass

            # If the type is a discharge start the first cycle with a None charge cycle
            else:
                discharge = half
                cycle = Cycle(number=cycle_number, charge=None, discharge=discharge)

            # Append the newly created cycle to the list and increment the counter
            cycles.append(cycle)
            cycle_number += 1

        # Perform the cleaning operation if clean is set to true
        for cycle in cycles:

            # Remove cycles with efficiencies higher than 100%
            if cycle.energy_efficiency and cycle.energy_efficiency > 100 and clean:
                cycle._hidden = True
                print(f"Cycle {cycle.number} hidden due to unphsyical nature")

            # Remove cycle with only a charge or a discharge
            elif (not cycle.charge or not cycle.discharge) and clean:
                cycle._hidden = True
                print(f"Cycle {cycle.number} hidden due to missing charge/discharge")

        return cycles  # Return the cycle list to the user

    def get_cellcycling(
        self, custom_order: List[str] = [], clean: bool = False
    ) -> CellCycling:
        """
        Build a CellCycling object from a given halfcycles order.

        Parameters:
        -----------
        custom_order: List[str]
            list of lists of filenames. Each list contains the half-cycles entries that must
            be merged in a single HalfCycle object. If left empty the ordering generated by
            the suggest_ordering method will be used.
        clean : bool
            if set to True, only displays cycles with physical meaning (efficiencies < 100%
            and both charge + discharge available). If False (default), load everything.

        Returns:
        --------
        :py:class:`~echemsuite.cellcycling.cycles.CellCycling`
            CellCycling instance containing all the charge/discharge Cycles objects.
        """

        cycles = self.get_cycles(custom_order=custom_order, clean=clean)
        return CellCycling(cycles)


# LEGACY FUNCTIONS


def build_DTA_cycles(
    filelist: List[str], clean: bool, verbose: bool = False
) -> List[Cycle]:
    """
    .. deprecated:: 0.2.0a
        Should be substituted by the direct call to the
        :py:class:`~echemsuite.cellcycling.read_input.FileManager` class structure

    Builds a list of cycles from a list containing charge/discharge file paths

    Parameters
    ----------
    filelist : List[str]
        file list containing the .DTA file paths.
    clean : bool
        if set to True, only displays cycles with physical meaning (efficiencies < 100% and
        both charge + discharge available). If False (default), load everything.

    Returns
    -------
    List[:py:class:`~echemsuite.cellcycling.cycles.Cycle`]
        list containing various cycles objects built according to the given list pairs
    """
    deprecation_warning("build_DTA_cycles", "FileManager")

    manager = FileManager(verbose=verbose)
    manager.fetch_files(filelist)
    cycles = manager.get_cycles(clean=clean)

    return cycles


def read_mpt_cycles(filelist: List[str], clean: bool, verbose: bool = False):
    """
    .. deprecated:: 0.2.0a
        Should be substituted by the direct call to the
        :py:class:`~echemsuite.cellcycling.read_input.FileManager` class structure

    Reads a list of cycles from a list containing cell cycling file paths from BIOLOGIC
    instruments (.mpt files)

    Parameters
    ----------
    filelist : List[str]
        file list containing .mpt file paths.
    clean : bool
        if True, only displays cycles with physical meaning (efficiencies < 100% and both
        charge + discharge available). If False (default), load everything.

    Returns
    -------
    List[:py:class:`~echemsuite.cellcycling.cycles.Cycle`]
        list containing various Cycles objects built according to the given list pairs
    """
    deprecation_warning("read_mpt_cycles", "FileManager")

    manager = FileManager(verbose=verbose)
    manager.fetch_files(filelist)
    cycles = manager.get_cycles(clean=clean)

    return cycles


def read_cycles(filelist, clean=False):
    """
    .. deprecated:: 0.2.0a
        Should be substituted by the direct call to the
        :py:class:`~echemsuite.cellcycling.read_input.FileManager` class structure

    Reads a list of cycles from a list containing cell cycling file paths from BIOLOGIC
    instruments (.mpt files)

    Parameters
    ----------
    filelist : List[str]
        file list containing .mpt file paths.
    clean : bool
        if True, only displays cycles with physical meaning (efficiencies < 100% and both
        charge + discharge available). If False (default), load everything.

    Returns
    -------
    :py:class:`~echemsuite.cellcycling.cycles.CellCycling`
            CellCycling instance containing all the charge/discharge Cycles objects.
    """

    deprecation_warning("read_cycles", "FileManager")

    if type(filelist) is str:
        filelist = [filelist]

    cycles = read_mpt_cycles(filelist, clean)

    return CellCycling(cycles)


def build_cycles(filelist, clean=False):
    """
    .. deprecated:: 0.2.0a
        Should be substituted by the direct call to the
        :py:class:`~echemsuite.cellcycling.read_input.FileManager` class structure

    Builds a list of cycles from a list containing charge/discharge file paths

    Parameters
    ----------
    filelist : List[str]
        file list containing the .DTA file paths.
    clean : bool
        if set to True, only displays cycles with physical meaning (efficiencies < 100% and
        both charge + discharge available). If False (default), load everything.

    Returns
    -------
    :py:class:`~echemsuite.cellcycling.cycles.CellCycling`
            CellCycling instance containing all the charge/discharge Cycles objects.
    """

    deprecation_warning("build_cycles", "FileManager")

    cycles = build_DTA_cycles(filelist, clean)

    return CellCycling(cycles)
