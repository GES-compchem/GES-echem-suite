import re, os
import pandas as pd
import numpy as np

from os import path
from typing import Tuple, List


class CyclicVoltammetry:
    """
    The CyclicVoltammetry class represent the digital equivalent of a cyclic-voltammetry experiment. The class
    stores all the informations about the experiment and is capable of loading Gamry `.DTA` files, Biologic `.mpt` files
    and CH Instruments ASCII files.

    Arguments
    ---------
    path: str
        The string encoding the path to the experiment file.

    Raises
    ------
    ValueError
        Exception raised if the specified file does not exists or if any kind of error happens during its parsing.

    Examples
    --------
    An instance of the class can be created calling the `__init__` method with a `path` argument specifying the location
    of the cyclic-voltammetry (CV) data file:

    >>> cv = CyclicVoltammetry("./file_to_load.DTA")

    The number of cycles associated to the CV measurement can be obtained using the `len` command of the CyclicVoltammetry
    class or can be found in the settings dictionary under the key `n_cycles`. The current and voltage values associated
    to each cycle can be obtained, in `pandas.DataFrame` format, by using the built in `__getitem__` method accoding to:

    >>> current, voltage = cv[index]

    The class provides also a built-in iterator yielding the sequence of current and voltage series for each cycle.
    """

    def __init__(self, path: str) -> None:
        if not os.path.isfile(path):
            raise ValueError(f"The specified file `{path}` does not exist.")

        self.__filepath = path  # path of input file
        self.settings = {}  # info from input header
        self.data = None  # contains Pandas dataframe of CV

        self.__load_cv()  # read input data

    @property
    def filepath(self) -> str:
        """
        The path from which the data have been loaded

        Returns
        -------
        str
            The string encoding the path to the original datafile.
        """
        return self.__filepath

    def __load_cv(self) -> None:
        """
        Function responsible for the loading and parsing of cyclic-voltammetry experimental files. The function
        reads the user-specified filepath and, based on the file extension, proceeds to load all the available data.

        Rasises
        -------
        ValueError
            Exception raised if the file spacified by the user does not match any known format.
        """
        filename = os.path.basename(self.filepath)
        root = path.splitext(filename)[0]
        extension = path.splitext(filename)[1]

        self.settings["filename"] = filename
        self.settings["file_rootname"] = root

        if extension.lower() == ".dta":
            self.settings["format"] = "Gamry"
            self.settings["extension"] = "dta"
            self.__read_DTA()
        elif extension.lower() == ".mpt":
            self.settings["format"] = "Biologic"
            self.settings["extension"] = "mpt"
            self.__read_MPT()
        elif extension.lower() == ".txt":
            self.settings["format"] = "CH Instruments"
            self.settings["extension"] = "txt"
            self.__read_TXT()
        else:
            raise ValueError(f"The extension `{extension}` is not recognized.")

    def __read_TXT(self) -> None:
        """
        Method dedicated to the parsing of CH Instruments `.txt` files.
        """
        with open(self.filepath, "r", encoding="utf8", errors="ignore") as f:
            iterator = iter(f)  # iterator avoids checking settings after header

            for row_number, line in enumerate(iterator):
                if "High E" in line:
                    v_init = float(line.split("=")[1])
                    self.settings["initial voltage"] = float(v_init)
                if "Low E" in line:
                    v_final = float(line.split("=")[1])
                    self.settings["final voltage"] = float(v_final)
                if "Potential/V, Current/A" in line:
                    header = line
                    break

            header = ["Vf", "Im", "Cycle n", "T"]

            data = pd.read_csv(
                self.filepath,
                sep=",",
                names=header,
                decimal=".",
                skiprows=row_number + 1,
                encoding_errors="ignore",
            )

            data["diff"] = data["Vf"].diff()
            data["diff"].iloc[0] = data["diff"].iloc[1]

            is_positive = True
            switches = 0
            for row in data.itertuples():
                condition = row.diff > 0
                if condition == is_positive:
                    data.at[row.Index, "Cycle n"] = switches // 2
                    continue
                else:
                    is_positive = condition
                    switches += 1
                    data.at[row.Index, "Cycle n"] = switches // 2

            self.settings["n_cycles"] = switches // 2 + 1

            data["Cycle n"] = data["Cycle n"].astype(int)
            self.data = data[["Cycle n", "T", "Vf", "Im"]]
            self.data.set_index("Cycle n", inplace=True)

    def __read_MPT(self) -> None:
        """
        Method dedicated to the parsing of Biologic `.mpt` files.
        """
        with open(self.filepath, "r", encoding="utf8", errors="ignore") as f:
            iterator = iter(f)  # iterator avoids checking settings after header

            for line in iterator:
                if "Nb header lines" in line:
                    skiprows = int(line.split()[4])
                elif "Ei (V)" in line:
                    v_init = line.replace(",", ".").split()[2]
                    self.settings["initial voltage"] = float(v_init)
                elif "E1 (V)" in line:
                    v_final = line.replace(",", ".").split()[2]
                    self.settings["final voltage"] = float(v_final)
                elif "mode	ox/red	error" in line:
                    break

            self.data = pd.read_csv(
                self.filepath,
                sep="\t",
                skiprows=skiprows - 1,
                decimal=",",
                encoding_errors="ignore",
            )

            uniques = self.data["cycle number"].value_counts()  #
            self.settings["n_cycles"] = len(uniques)
            self.data.rename(
                columns={
                    "time/s": "T",
                    "Ewe/V": "Vf",
                    "<I>/mA": "Im",
                    "cycle number": "Cycle n",
                },
                inplace=True,
            )

            self.data = self.data[["Cycle n", "T", "Vf", "Im"]]
            self.data["Cycle n"] -= 1  # switch to 0 based cycle indexing
            self.data.set_index("Cycle n", inplace=True)

    def __read_DTA(self) -> None:
        """
        Method dedicated to the parsing of Gamry `.DTA` files.
        """
        # only consider data after label CURVE\d and ignore CURVEOCV
        is_it_curve = re.compile("CURVE\d")
        with open(self.filepath, "r", encoding="utf8", errors="ignore") as f:
            iterator = iter(f)  # iterator avoids checking settings after header

            # Temporary fix to read LSV... to be checked in the future
            vlimit_1 = None  # Sentinel values
            vlimit_2 = None  # Sentinel values

            # headers for self.settings dict
            row_idx = 0
            for line in iterator:
                row_idx += 1
                if "SCANRATE" in line:
                    # Check if dot or comma is used as decimal separator
                    if "." in line:
                        separator = "."
                    else:
                        separator = ","
                    scanrate = line.replace(",", ".").split("\t")[2]
                    self.settings["scan rate"] = float(scanrate)
                elif "VINIT" in line:
                    v_init = line.replace(",", ".").split("\t")[2]
                    self.settings["initial voltage"] = float(v_init)
                elif "VLIMIT1" in line:
                    vlimit_1 = line.replace(",", ".").split("\t")[2]
                    self.settings["vlimit 1"] = float(vlimit_1)
                elif "VLIMIT2" in line:
                    vlimit_2 = line.replace(",", ".").split("\t")[2]
                    self.settings["vlimit 2"] = float(vlimit_2)
                elif "INSTRUMENTVERSION" in line:
                    break

            # Find peak (either maximum or minimum) in voltage scan...
            # This is gamry nonsense :@
            if (vlimit_1 is None) or (vlimit_2 is None):
                pass  # do nothing
            elif float(v_init) == float(vlimit_1):
                self.settings["final voltage"] = float(vlimit_2)
            else:
                self.settings["final voltage"] = float(vlimit_1)
            file_format = None
            header = None

            for line in iterator:
                row_idx += 1
                if "OCVCURVE" in line:
                    continue
                elif "CURVE" in line:
                    if "CURVE	TABLE" in line:
                        file_format = "Single table"
                        header = next(f)
                        header_units = next(f)
                        break
                    elif is_it_curve.match(line):
                        file_format = "Multiple tables"
                        next(f)
                        next(f)
                        break

            # DTA can come in two formats...
            useful_keys = ["Cycle n", "T", "Vf", "Im"]

            if file_format == "Single table":
                header = header.replace("Cycle", "Cycle n")
                header = header.split("\t")
                self.data = pd.read_csv(
                    self.filepath,
                    sep="\t",
                    skiprows=row_idx + 2,
                    names=header,
                    decimal=separator,
                    encoding_errors="ignore",
                )
                self.data = self.data.drop(self.data.columns[0], axis=1)
                uniques = self.data["Cycle n"].value_counts()  #
                self.settings["n_cycles"] = len(uniques)

                self.data = self.data[useful_keys]
                self.data.set_index("Cycle n", inplace=True)
                return
            else:
                curves = []
                curveN = 0
                # read CV data, multiple tables
                for line in iterator:
                    if is_it_curve.match(line):
                        curveN += 1
                        next(f)
                        next(f)
                        continue
                    if curveN >= 0:
                        line_float = [float(ele) for ele in line.strip().replace(",", ".").split("\t")[0:7]]
                        curves.append([curveN] + line_float)

                self.settings["n_cycles"] = curveN + 1
                header = ["Cycle n", "Pt", "T", "Vf", "Im", "Vu", "Sig0", "Ach"]
                # just keep the relevant ones and use cycle num as vertical key
                self.data = pd.DataFrame(curves, columns=header)[useful_keys]
                self.data.set_index("Cycle n", inplace=True)

    def __getitem__(self, index: int) -> Tuple[List[float], List[float]]:
        """
        Return voltage and current associated to the cycle `index` specified by the user.

        Arguments
        ---------
        index : int
            The index of the user-specified cycle

        Returns
        -------
        Tuple[List[float], List[float]]
            The tuple containing the current and voltage lists associated to the user-selected cycle.
        """
        Im, Vf = self.data.loc[index]["Im"], self.data.loc[index]["Vf"]
        
        if type(Im) == np.float64:
            return [float(Im)], [float(Vf)]
        else:
            return [float(i) for i in Im], [float(v) for v in Vf]

    def __iter__(self) -> Tuple[List[float], List[float]]:
        """
        Yields voltage and current associated to the various cycles as in __getitem__.

        Arguments
        ---------
        index : int
            The index of the user-specified cycle

        Yields
        ------
        Tuple[List[float], List[float]]
            The tuple containing the current and voltage lists associated to the user-selected cycle.
        """
        for cycle in range(self.settings["n_cycles"]):
            yield self[cycle]

    def __repr__(self):
        """
        Return __repr__ of the data Pandas dataframe.
        Returns
        -------
        str
            Representation of data Pandas dataframe.
        """
        return self.data.__repr__()
        # return self.filepath

    def __len__(self) -> int:
        """
        Return the number of cycles in the experiment

        Returns
        -------
        int
            The totla number of cycles
        """
        return self.settings["n_cycles"]

    def __str__(self):
        return self.filepath

