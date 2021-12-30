# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 13:35:19 2020
@author: mpalermo
"""

import pandas as pd
import re
import matplotlib.pyplot as plt
from os import path
import os

# %% Reads MPT or DTA to common data structure


class CyclicVoltammetry:
    def __init__(self, path):
        self.filepath = path  # path of input file
        self.settings = {}  # info from input header
        self.data = None  # contains Pandas dataframe of CV

        self._load_cv()  # read input data

    def _load_cv(self):
        # choose input parser based on file extension
        filename = os.path.basename(self.filepath)
        root = path.splitext(filename)[0]
        extension = path.splitext(filename)[1]

        if extension.lower() == ".dta":
            self.settings["format"] = "Gamry"
            # self.settings['folder'] = ''
            self.settings["filename"] = filename
            self.settings["file_rootname"] = root
            self.settings["extension"] = "dta"
            self._read_DTA()
        elif extension.lower() == ".mpt":
            self.settings["format"] = "Biologic"
            self.settings["filename"] = filename
            self.settings["extension"] = "mpt"
            self.settings["file_rootname"] = root
            self._read_MPT()
        elif extension.lower() == "":
            print("No file selected")
            raise ValueError
        else:
            # if extension is not recognized, raise error
            raise ValueError

    def _read_MPT(self):
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

    def _read_DTA(self):
        # only consider data after label CURVE\d and ignore CURVEOCV
        is_it_curve = re.compile("CURVE\d")
        with open(self.filepath, "r", encoding="utf8", errors="ignore") as f:
            iterator = iter(f)  # iterator avoids checking settings after header

            # headers for self.settings dict
            row_idx = 0
            for line in iterator:
                row_idx += 1
                if "SCANRATE" in line:
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
            if float(v_init) == float(vlimit_1):
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
                    decimal=",",
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
                        line_float = [
                            float(ele)
                            for ele in line.strip().replace(",", ".").split("\t")[0:7]
                        ]
                        curves.append([curveN] + line_float)

                self.settings["n_cycles"] = curveN + 1
                header = ["Cycle n", "Pt", "T", "Vf", "Im", "Vu", "Sig0", "Ach"]
                # just keep the relevant ones and use cycle num as vertical key
                self.data = pd.DataFrame(curves, columns=header)[useful_keys]
                self.data.set_index("Cycle n", inplace=True)

    def _plot(self, cycle):
        curr = self[cycle]["Im"]
        volt = self[cycle]["Vf"]
        plt.rcParams.update({"font.size": 12})
        plt.rc("legend", fontsize=9)
        plt.xlabel("V vs ref [V]")
        plt.ylabel("i [mA]")

        plt.plot(volt, curr)

    def __getitem__(self, key):
        """
        Return table filtered by value key.
        Parameters
        ----------
        key : int or str
            If int, key is interpreted as cycle number, otherwise as pd column
        Returns
        -------
        Pandas dataframe
            Returns pandas filtered by cycle number if key is int
            Returns pandas filtered by column otherwise
        """
        if key in self.data.columns:
            return self.data[key]
        elif isinstance(key, int):
            return self.data.loc[key]
        # else:
        #    return self.data.filter(like = key, axis = 0)

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

    def __str__(self):
        return self.filepath

    def __iter__(self):
        # return pd table filtered by cycle number as in __getitem__
        for cycle in range(self.settings["n_cycles"]):
            yield self.data.loc[cycle]

    def _current_dens(self, area):
        self.data["Idens"] = self.data["Im"] * 1000 / area
