from enum import Enum
import logging
from os import listdir, path
from io import BytesIO, TextIOWrapper
from typing import Dict, List

from cellcycling.read_input import *

logger = logging.getLogger(__name__)


class Instrument(Enum):
    '''
    Simple enumeration to easily reference instrument types
    '''
    GAMRY = "GAMRY"


class FileManager:
    '''
    Universal loader for cellcycling files
    '''
    def __init__(self, verbose: bool = False) -> None:
        
        self.verbose: bool = verbose                    # Enable output to the terminal
        self._bytestreams: Dict[str, BytesIO] = {}      # Dictionary for the BytesIO streams containing the datafiles
        self._halfcycles: Dict[str, HalfCycle] = {}     # List of the loaded halfcycles
        self._instrument: Instrument = None             # Instrument from which the data are obtained

    @property
    def bytestreams(self):
        for stream in self._bytestreams:
            stream.seek(0)
        return self._bytestreams

    @bytestreams.setter
    def bytestreams(self, value):
        
        if type(value) != dict:
            logger.error(f"Bytestream setter expects a Dict type. Received '{type(value)}' instead")
            raise TypeError
        
        for key, item in value.items():
            if type(key) != str or type(item) != BytesIO:
                logger.error(f"Bytestream dictionary must be of type Dict[str, BytesIO]. Received 'Dict[{type(key)}, {type(item)}]' instead.")
                raise ValueError
        
        self._bytestreams = value

    @bytestreams.deleter
    def bytestreams(self):
        self._bytestreams = {}

    
    @property
    def halfcycles(self):
        return self._halfcycles
    
    @halfcycles.setter
    def halfcycles(self, value):
        if type(value) != dict:
            logger.error(f"Halfcycles setter expects a Dict type. Received '{type(value)}' instead")
            raise TypeError
        
        for key, item in value.items():
            if type(key) != str or type(item) != HalfCycle:
                logger.error(f"Halfcycles dictionary must be of type Dict[str, HalfCycle]. Received 'Dict[{type(key)}, {type(item)}]' instead.")
                raise ValueError

        self._halfcycles = value

    
    @property
    def instrument(self) -> str:
        return self._instrument.name
        
    
    def fetch_from_folder(self, folder: str, extension: str, autoparse: bool = True) -> None:
        '''
        Loads, as BytesIO streams, multiple files from a folder filtering them by extension.
        '''

        # Check if directory exists
        if path.isdir(folder) == False:
            logger.error(f"The path '{folder}' does not correspond to a folder.")
            raise ValueError
        folder = path.abspath(folder)
        
        # Check if the extension matches any of the existing instrument profiles
        if extension.lower() == ".dta":
            self._instrument = Instrument.GAMRY
        else:
            logger.error(f"The extension '{extension}' does not appear among the known file types.")
            raise TypeError

        # Load the file in the bytestream buffer
        self._bytestreams = {}
        for filename in listdir(folder):
            if filename.endswith(extension):
                if self.verbose:
                    print(f"-> Loading: {filename}")

                filepath = path.join(folder, filename)

                # Veryfiy if the file is empty or if it is not encoded in utf-8
                try:
                    with open(filepath, 'r') as file:
                        if file.read() == "":
                            if self.verbose:
                                print(f"\u001b[35;1mWARNING:\u001b[0m empty file found. Skipping {filename}.")
                            logger.warning(f"Empty file found. Skipping {filename}.")
                            continue
                except UnicodeDecodeError:
                    if self.verbose:
                        print(f"\u001b[35;1mWARNING:\u001b[0m unable to decode file. Skipping {filename}.")
                    logger.warning(f"Unable to decode file. Skipping {filename}.")
                    continue
                
                # Load the whole file in the bytestreams buffer
                with open(filepath, 'rb') as file:
                    if filename in self._bytestreams:
                        if self.verbose:
                            print(f"\u001b[35;1mWARNING:\u001b[0m duplicate filename found. Skipping {filename}.")
                        logger.warning(f"Duplicate filename found. Skipping {filename}.")
                        continue
                    self._bytestreams[filename] = BytesIO(file.read())
        
        if self.verbose:
            print(f"A total of {len(self._bytestreams)} files have been loaded")
        
        if autoparse:
            self.parse()


    def parse(self) -> None:
        '''
        Parse the BytesIO streams contained in the "bytestreams" buffer and update the "halfcycles" dictionary.
        '''
        
        # Check if the bytestreams buffer is empty
        if self._bytestreams == {}:
            logger.error("Parse function called on empty bytestreams dictionary.")
            raise RuntimeError

        # Load the halfcycles from data in the bytestreams buffer based on the type of instrument
        self._halfcycles = {}
        if self._instrument == Instrument.GAMRY:
            for filename, bytestream in self._bytestreams.items():

                if self.verbose:
                    print(f"-> Parsing: {filename}")

                beginning = None                                # line at which the table begins
                npoints = None                                  # number of data points
                halfcycle_type = None                           # charge/discharge

                date_str, time_str = None, None                 # Date and time string buffers
                timestamp = None                                # Timestamp reported in the file

                data = pd.DataFrame()                           # Empty pandas dataframe to store data
                    
                # Parsing the file
                textStream = TextIOWrapper(bytestream, encoding='utf-8')
                for line_num, line in enumerate(textStream.readlines()):
                    
                    line = line.strip('\n')

                    # Read the time and date lines
                    if line.startswith("DATE"):
                        date_str = line.split()[2]
                    elif line.startswith("TIME"):
                        time_str = line.split()[2]

                    # Read the sign of the current to define halfcycle type
                    if "Step 1 Current (A)" in line:
                        if float(line.split()[2]) > 0:
                            halfcycle_type = "charge"           # positive current = charge
                        elif float(line.split()[2]) < 0:
                            halfcycle_type = "discharge"        # negative current = discharge

                    # Search the "CURVE TABLE npoints" line and load the data
                    if line.startswith("CURVE"):
                        beginning = line_num + 2
                        npoints = int(line.split()[-1])

                        textStream.seek(0)                      # Rewind the pointer to the beginning of the stream
                        data = pd.read_table(
                            textStream,
                            delimiter="\t",
                            skiprows=beginning,
                            decimal=".",
                            nrows=npoints,
                            encoding_errors="ignore",
                        )

                        textStream.detach()                     # Detaches the TextIOWrapper from the BytesIO stream to avoid bytestream closing on wrapper out of scope
                        break
                
                # Confirm that the data has been loaded
                if data.empty:
                    logger.error("Failed to locate the CURVE section.")
                    raise RuntimeError

                # Build the timestamp object
                if date_str != None and time_str != None:
                    month, day, year = date_str.split("/")
                    hours, minutes, seconds = time_str.split(":")
                    timestamp = datetime(int(year), int(month), int(day), int(hours), int(minutes), int(seconds))
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
                        columns={"s": "Time (s)", "V": "Voltage vs. Ref. (V)", "A": "Current (A)",},
                        inplace=True,
                    )
                
                # Drop the lines corresponding to t<=0 and skip whe detecting empty dataframes
                data.drop(data[data["Time (s)"] <= 0].index, inplace=True)

                if data.empty:
                    continue

                time = data["Time (s)"]
                voltage = data["Voltage vs. Ref. (V)"]
                current = data["Current (A)"]

                if halfcycle_type is None:
                    if current[0] > 0:
                        halfcycle_type = "charge"
                    elif current[0] < 0:
                        halfcycle_type = "discharge"
                
                self._halfcycles[filename] = HalfCycle(time, voltage, current, halfcycle_type, timestamp)
            
        if self.verbose:
            print("Parsing completed")
    

    def suggest_ordering(self) -> List[str]:
        '''
        Examine the bytestreams buffer and suggest a possible file ordering and merging scheme based on half-cycle type and timestamp
        '''
        ordered_items = sorted(self._halfcycles.items(), key = lambda x: x[1].timestamp)
        
        order: List[List[str]] = []

        ncycles, index = 0, 0
        while index < len(ordered_items)-1:
            halfcycle_type = ordered_items[index][1].halfcycle_type
            order.append([ordered_items[index][0]])
            while True:
                index += 1
                if index == len(ordered_items)-1:
                    break
                elif ordered_items[index][1].halfcycle_type == halfcycle_type:
                    order[ncycles].append(ordered_items[index][0])
                else:
                    break
            ncycles += 1

        return order
    

    def get_cycles(self, custom_order: List[str] = [], clean = False) -> List[Cycle]:
        '''
        Build the Cycles list from a given halfcycles order. 
        '''
        
        order: List[List[str]] = self.suggest_ordering() if custom_order == [] else custom_order

        halfcycles = []
        for block in order:
            if len(block) == 1:
                halfcycles.append(self._halfcycles[block[0]])
            else:
                merge_list = [self._halfcycles[name] for name in block]
                halfcycles.append(join_HalfCycles(merge_list))

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
    

    def build_cycles(self, custom_order: List[str] = [], clean = False):
        cycles = self.get_cycles(custom_order=custom_order, clean=clean)
        return CellCycling(cycles)

