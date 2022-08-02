# %% ADD MODULE TO SYSPATH
import os
import sys
from pathlib import Path

current_path = os.path.realpath(__file__)

path = Path(current_path)
parent_path = str(path.parents[2].absolute())
sys.path.insert(0, parent_path)

# %% IMPORTS
import pytest
import pandas as pd
from os.path import abspath, join
from datetime import datetime
from io import TextIOWrapper, BytesIO
from numpy.testing import assert_array_almost_equal

from echemsuite.cellcycling.cycles import HalfCycle
from echemsuite.cellcycling.read_input import (
    build_DTA_cycles,
    read_mpt_cycles,
    FileManager,
    Instrument,
)


# %% DEFINE FILE EMULATION FIXTURES FOR GAMRY .DTA FILES


def generate_minimal_dta_file_content(charge: bool, time: str) -> str:

    sign = "" if charge else "-"

    content = """
...
DATE	LABEL	12/25/2022	Date
TIME	LABEL	{1}	Time
...
ISTEP1	QUANT	{0}1.00000E+000	Step 1 Current (A)
...
CURVE	TABLE	5
    Pt	T	Vf	Im	Vu	Sig	Ach	IERange	Over	Temp
    #	s	V vs. Ref.	A	V	V	V	#	bits	deg C
    0	-1	1.00000E+000	1.00000E-004	0.00000E+000	5.00000E-005	1.80000E-003	20	..........a	-273.15
    1	0	1.00000E+000	1.00000E-004	0.00000E+000	5.00000E-005	1.80000E-003	20	..........a	-273.15
    2	1	1.10000E+000	{0}1.00000E+000	0.00000E+000	{0}1.00000E+000	1.80000E-003	20	..........a	-273.15
    3	2	1.20000E+000	{0}1.00000E+000	0.00000E+000	{0}1.00000E+000	1.80000E-003	20	..........a	-273.15
    4	3	1.30000E+000	{0}1.00000E+000	0.00000E+000	{0}1.00000E+000	1.80000E-003	20	..........a	-273.15
EXPERIMENTABORTED	TOGGLE	T	Experiment Aborted    
""".format(
        sign, time
    )
    return content


# Fixture to emulate a folder containing two regular charge/discharge files
@pytest.fixture(scope="session")
def folder_with_minimal_dta_files(tmp_path_factory):
    folder = tmp_path_factory.mktemp("minimal_dta_files")
    data = {}
    for cycle_idx in [1, 2]:
        for charge in [True, False]:
            timestamp = "{}:{}:00".format(
                str(12 + cycle_idx), "30" if charge is False else "00"
            )
            type = "charge" if charge else "discharge"
            filename = type + "_" + str(cycle_idx) + ".DTA"
            content = generate_minimal_dta_file_content(charge, timestamp)
            file_path = folder / filename
            file_path.write_text(content)
            data[filename] = [content, type, timestamp]
    return folder, data


# Fixture to emulate a folder containing a charge halfcycle and two discharge hlafcycles files
@pytest.fixture(scope="session")
def folder_with_partial_dta_files(tmp_path_factory):
    folder = tmp_path_factory.mktemp("partial_dta_files")

    filename = "discharge_2.DTA"
    content = generate_minimal_dta_file_content(False, "13:45:00")
    file_path = folder / filename
    file_path.write_text(content)

    filename = "charge_1.DTA"
    content = generate_minimal_dta_file_content(True, "13:00:00")
    file_path = folder / filename
    file_path.write_text(content)

    filename = "discharge_1.DTA"
    content = generate_minimal_dta_file_content(False, "13:30:00")
    file_path = folder / filename
    file_path.write_text(content)

    return folder


# %% DEFINE FILE EMULATION FIXTURES FOR BIOLOGIC .MPT FILES


def generate_regular_mpt_file_content() -> str:

    content = """
...
Acquisition started on : 25/12/2022 13:00:00
...
Number of loops : 2
Loop 0 from point number 0 to 5
Loop 1 from point number 6 to 11

mode	ox/red	error	control changes	time/s	control/V/mA	Ewe/V	I/mA	dq/mA.h	(Q-Qo)/mA.h	Q charge/discharge/mA.h	Ece/V	P/W	Q discharge/mA.h	Q charge/mA.h	Capacity/mA.h	control/V	control/mA	Ewe-Ece/V	
1	1	0	1	1,000000000000000E+002	8,0000000E+002	1,0000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	1	0	1	1,010000000000000E+002	8,0000000E+002	1,1000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	1	0	1	1,020000000000000E+002	8,0000000E+002	1,2000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	0	0	0	1,030000000000000E+002	-8,0000000E+002	9,0000000E-001	-8,0000000E+002	-4,000000000000000E-005	1,100000000000000E+003	-4,000000000000000E-005	-8,0000000E-004	-4,0000000E-001	5,000000000000000E-005	0,000000000000000E+000	5,000000000000000E-005	0,0000000E+000	-8,0000000E+002	6,0000000E-001
1	0	0	0	1,040000000000000E+002	-8,0000000E+002	8,5000000E-001	-8,0000000E+002	-4,000000000000000E+000	1,100000000000000E+003	-4,000000000000000E+000	-8,0000000E-005	-4,0000000E-001	5,000000000000000E+000	0,000000000000000E+000	5,000000000000000E+000	0,0000000E+000	-8,0000000E+002	6,0000000E-001
1	0	0	0	1,050000000000000E+002	-8,0000000E+002	8,2000000E-001	-8,0000000E+002	-4,000000000000000E+000	1,100000000000000E+003	-4,000000000000000E+000	-8,0000000E-004	-4,0000000E-001	5,000000000000000E+000	0,000000000000000E+000	5,000000000000000E+000	0,0000000E+000	-8,0000000E+002	6,0000000E-001
1	1	0	1	1,060000000000000E+002	8,0000000E+002	1,0000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	1	0	1	1,070000000000000E+002	8,0000000E+002	1,1000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	1	0	1	1,080000000000000E+002	8,0000000E+002	1,2000000E+000	8,0000000E+002	4,000000000000000E+000	1,100000000000000E+003	1,100000000000000E+003	3,0000000E-006	1,0000000E+000	0,000000000000000E+000	1,000000000000000E+003	1,000000000000000E+003	0,0000000E+000	8,0000000E+002	1,0000000E+000
1	0	0	0	1,090000000000000E+002	-8,0000000E+002	9,0000000E-001	-8,0000000E+002	-4,000000000000000E-005	1,100000000000000E+003	-4,000000000000000E-005	-8,0000000E-004	-4,0000000E-001	5,000000000000000E-005	0,000000000000000E+000	5,000000000000000E-005	0,0000000E+000	-8,0000000E+002	6,0000000E-001
1	0	0	0	1,100000000000000E+002	-8,0000000E+002	8,5000000E-001	-8,0000000E+002	-4,000000000000000E+000	1,100000000000000E+003	-4,000000000000000E+000	-8,0000000E-005	-4,0000000E-001	5,000000000000000E+000	0,000000000000000E+000	5,000000000000000E+000	0,0000000E+000	-8,0000000E+002	6,0000000E-001
1	0	0	0	1,110000000000000E+002	-8,0000000E+002	8,2000000E-001	-8,0000000E+002	-4,000000000000000E+000	1,100000000000000E+003	-4,000000000000000E+000	-8,0000000E-004	-4,0000000E-001	5,000000000000000E+000	0,000000000000000E+000	5,000000000000000E+000	0,0000000E+000	-8,0000000E+002	6,0000000E-001"""
    return content


# Fixture to emulate a folder containing a regular .mpt cycling file
@pytest.fixture(scope="session")
def folder_with_regular_mpt_file(tmp_path_factory):
    folder = tmp_path_factory.mktemp("regular_mpt_files")
    content = generate_regular_mpt_file_content()
    file_path = folder / "myCellcycling.mpt"
    file_path.write_text(content)
    return folder


# %% DEFINE TEST FUNCTIONS FOR THE FILEMANAGER CLASS USING GAMBRY FILES


# Test function to check for exceptions raised during FileManager object construction
def test_FileManager___init__():

    try:
        manager = FileManager(verbose=True)
    except Exception as exc:
        assert (
            False
        ), f"An exception occurred on FileManager object construction:\n\n{exc}\n"
    else:
        assert True

    assert manager.verbose == True


# Test function to check the FileManager fetch_from_folder function
def test_FileManager_fetch_from_folder_function(folder_with_minimal_dta_files):

    manager = FileManager()

    folder, data = folder_with_minimal_dta_files

    try:
        manager.fetch_from_folder(folder, ".DTA", autoparse=False)
    except Exception as exc:
        assert (
            False
        ), f"An exception occurred during fetching from DTA files folder\n\n{exc}\n"

    assert manager._instrument == Instrument.GAMRY

    # Check if all the expected files have been loaded to the BytesIO buffer
    for key in data.keys():
        if key not in manager._bytestreams.keys():
            assert False, f"The file '{name}' has not been loaded in the BytesIO buffer."

    for name, stream in manager._bytestreams.items():

        # Check if extra entry where created during the buffer loading process
        if name not in data.keys():
            assert False, f"Filename '{name}' found in the BytesIO buffer should not exist."

        # Check if the buffer stores the expected data
        buffer_content = TextIOWrapper(stream, encoding="utf-8").read()
        assert buffer_content == data[name][0]


# Test function to check the FileManager parse function
def test_FileManager_parse_function(folder_with_minimal_dta_files):

    manager = FileManager()

    folder, data = folder_with_minimal_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=False)

    try:
        manager.parse()
    except Exception as exc:
        assert (
            False
        ), f"An exception occurred during parsing DTA files bytestreams\n\n{exc}\n"

    # Check if all the BytesIO object in the bytestream have been parsed int halfcycles
    for name in data.keys():
        if name not in manager._halfcycles.keys():
            assert False, f"The bytestream '{name}' has not been parsed into halfcycle"

    for key, halfcycle in manager._halfcycles.items():

        # Check if extra entry where created during the buffer loading process
        if key not in data.keys():
            assert (
                False
            ), f"The object '{name}' found in the halfcycle buffer should not exist."

        # Check that all the halfcycle informations have been parsed correctly
        assert halfcycle._halfcycle_type == data[key][1]
        assert halfcycle._timestamp.strftime("%m/%d/%Y") == "12/25/2022"
        assert halfcycle._timestamp.strftime("%H:%M:%S") == data[key][2]
        assert_array_almost_equal(halfcycle._time.tolist(), [1.0, 2.0, 3.0], decimal=4)
        assert_array_almost_equal(halfcycle._voltage.tolist(), [1.1, 1.2, 1.3], decimal=4)

        if halfcycle._halfcycle_type == "charge":
            assert_array_almost_equal(
                halfcycle._current.tolist(), [1.0, 1.0, 1.0], decimal=4
            )
        else:
            assert_array_almost_equal(
                halfcycle._current.tolist(), [-1.0, -1.0, -1.0], decimal=4
            )


# Test function to check the FileManager suggest_ordering function with regular charge/discharge
def test_FileManager_suggest_ordering_function_regular(folder_with_minimal_dta_files):

    manager = FileManager()
    folder, _ = folder_with_minimal_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    suggested_ordering = manager.suggest_ordering()

    expected_ordering = [
        ["charge_1.DTA"],
        ["discharge_1.DTA"],
        ["charge_2.DTA"],
        ["discharge_2.DTA"],
    ]

    assert suggested_ordering == expected_ordering


# Test function to check the FileManager suggest_ordering function with partial charge/discharge
def test_FileManager_suggest_ordering_function_partial(folder_with_partial_dta_files):

    manager = FileManager()
    folder = folder_with_partial_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    suggested_ordering = manager.suggest_ordering()

    expected_ordering = [["charge_1.DTA"], ["discharge_1.DTA", "discharge_2.DTA"]]

    assert suggested_ordering == expected_ordering


# Test function to check the FileManager get_cycles function with with regular charge/discharge
def test_FileManager_get_cycles_function_regular(folder_with_minimal_dta_files):

    manager = FileManager()
    folder, _ = folder_with_minimal_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    cycles = manager.get_cycles()

    assert len(cycles) == 2

    for n, cycle in enumerate(cycles):
        assert cycle.charge == manager._halfcycles[f"charge_{n+1}.DTA"]
        assert cycle.discharge == manager._halfcycles[f"discharge_{n+1}.DTA"]


# Test function to check the FileManager get_cycles function with with partial charge/discharge
def test_FileManager_get_cycles_function_partial(folder_with_partial_dta_files):

    manager = FileManager()
    folder = folder_with_partial_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    cycles = manager.get_cycles()

    assert len(cycles) == 1

    assert cycles[0].charge == manager._halfcycles["charge_1.DTA"]

    assert_array_almost_equal(
        cycles[0].discharge.time, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], decimal=4
    )
    assert_array_almost_equal(
        cycles[0].discharge.voltage, [1.1, 1.2, 1.3, 1.1, 1.2, 1.3], decimal=4
    )
    assert_array_almost_equal(
        cycles[0].discharge.current, [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0], decimal=4
    )


# Test function to check the FileManager get_cycles function with with partial charge/discharge and custom ordering
def test_FileManager_get_cycles_function_partial_custom_ordering(
    folder_with_partial_dta_files,
):

    manager = FileManager()
    folder = folder_with_partial_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    my_order = [["discharge_2.DTA"], ["charge_1.DTA"], ["discharge_1.DTA"]]

    cycles = manager.get_cycles(custom_order=my_order)

    assert len(cycles) == 2

    assert cycles[0].charge == None
    assert cycles[0].discharge == manager._halfcycles["discharge_2.DTA"]
    assert cycles[1].charge == manager._halfcycles["charge_1.DTA"]
    assert cycles[1].discharge == manager._halfcycles["discharge_1.DTA"]

    assert cycles[0]._hidden == False
    assert cycles[1]._hidden == False


# Test function to check the FileManager get_cycles function with with partial charge/discharge and custom ordering with clean
def test_FileManager_get_cycles_function_partial_custom_ordering_with_clean(
    folder_with_partial_dta_files,
):

    manager = FileManager()
    folder = folder_with_partial_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    my_order = [["discharge_2.DTA"], ["charge_1.DTA"], ["discharge_1.DTA"]]

    cycles = manager.get_cycles(custom_order=my_order, clean=True)

    assert len(cycles) == 2

    assert cycles[0].charge == None
    assert cycles[0].discharge == manager._halfcycles["discharge_2.DTA"]
    assert cycles[1].charge == manager._halfcycles["charge_1.DTA"]
    assert cycles[1].discharge == manager._halfcycles["discharge_1.DTA"]

    assert cycles[0]._hidden == True
    assert cycles[1]._hidden == False


# Test function to check the FileManager get_cellcycling function with with regular charge/discharge
def test_FileManager_get_cellcycling_function_regular(folder_with_minimal_dta_files):

    manager = FileManager()
    folder, _ = folder_with_minimal_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    cycles = manager.get_cycles()
    cellcycling = manager.get_cellcycling()

    for i, cycle in enumerate(cellcycling._cycles):
        assert cycle.charge == cycles[i].charge
        assert cycle.discharge == cycles[i].discharge


# Test function to verify the correct assignment of the FileManager class properies
def test_FileManager_properties(folder_with_minimal_dta_files):

    manager = FileManager()
    folder, _ = folder_with_minimal_dta_files
    manager.fetch_from_folder(folder, ".DTA", autoparse=True)

    # Test the proper connection of propery getters
    assert manager.bytestreams == manager._bytestreams
    assert manager.halfcycles == manager._halfcycles
    assert manager.instrument == manager._instrument.name

    # Verify exception raise on wrong type submission to bytestream setter
    try:
        manager.bytestreams = "Wrong Type!"
    except Exception as exc:
        assert True
    else:
        assert (
            False
        ), "An exception was not raised when the wrong type was passed to the bytestream setter."

    # Verify exception raise on wrong dictionary type submission to bytestream setter
    try:
        manager.bytestreams = {"A key": "Wrong Type!"}
    except Exception as exc:
        assert True
    else:
        assert (
            False
        ), "An exception was not raised when the wrong dictionary type was passed to the bytestream setter."

    # Verify the proper working of the bytestream setter
    try:
        manager.bytestreams = {"A key": BytesIO(b"This is the stream content")}
    except Exception as exc:
        assert False, "An unexpected exception occurred on bytestream setter call."
    else:
        assert (
            manager._bytestreams["A key"].read().decode("utf-8")
            == "This is the stream content"
        )

    # Verify the proper working of the bytestream deleater
    try:
        del manager.bytestreams
    except Exception as exc:
        assert False, "An unexpected exception occurred on bytestream deleater call."
    else:
        assert manager._bytestreams == {}

    # Verify exception raise on wrong type submission to halfcycle setter
    try:
        manager.halfcycles = "Wrong Type!"
    except Exception as exc:
        assert True
    else:
        assert (
            False
        ), "An exception was not raised when the wrong type was passed to the halfcycle setter."

    # Verify exception raise on wrong dictionary type submission to halfcycle setter

    try:
        manager.halfcycles = {"A key": "Wrong Type!"}
    except Exception as exc:
        assert True
    else:
        assert (
            False
        ), "An exception was not raised when the wrong dictionary type was passed to the halfcycle setter."

    # Verify the proper working of the halfcycle setter

    halfcycle = HalfCycle(
        pd.Series([0.0, 1.0]),
        pd.Series([1.0, 1.0]),
        pd.Series([1.0, 1.0]),
        "charge",
        datetime.now(),
    )

    try:
        manager.halfcycles = {"A key": halfcycle}
    except Exception as exc:
        assert False, "An unexpected exception occurred on halfcycle setter call."
    else:
        assert manager._halfcycles["A key"] == halfcycle


# %% DEFINE TEST FUNCTIONS FOR THE FILEMANAGER CLASS USING BIOLOGIC FILES


# Test function to check the FileManager fetch_from_folder function using Biologic files
def test_FileManager_fetch_from_folder_function_biologic(folder_with_regular_mpt_file):

    manager = FileManager()
    folder = folder_with_regular_mpt_file

    try:
        manager.fetch_from_folder(folder, ".mpt", autoparse=False)
    except Exception as exc:
        assert (
            False
        ), f"An exception occurred during fetching from MPT files folder\n\n{exc}\n"

    assert manager._instrument == Instrument.BIOLOGIC
    assert len(manager._bytestreams) == 1
    assert [k for k in manager._bytestreams.keys()] == ["myCellcycling.mpt"]


# Test function to check the FileManager parse function using Biologic files
def test_FileManager_parse_function_biologic(folder_with_regular_mpt_file):

    manager = FileManager()

    folder = folder_with_regular_mpt_file
    manager.fetch_from_folder(folder, ".mpt", autoparse=False)

    try:
        manager.parse()
    except Exception as exc:
        assert (
            False
        ), f"An exception occurred during parsing MPT files bytestreams\n\n{exc}\n"

    assert len(manager._halfcycles) == 4

    for key, halfcycle in manager._halfcycles.items():
        skey = key.split("_")

        assert_array_almost_equal(
            halfcycle._time.tolist(), [0, 1, 2], decimal=4
        )

        if skey[0] == "charge":
            assert halfcycle._halfcycle_type == "charge"
            assert_array_almost_equal(
                halfcycle._voltage.tolist(), [1.0, 1.1, 1.2], decimal=4
            )
            assert_array_almost_equal(
                halfcycle._current.tolist(), [0.8, 0.8, 0.8], decimal=4
            )           

        else:
            assert halfcycle._halfcycle_type == "discharge"
            assert_array_almost_equal(
                halfcycle._voltage.tolist(), [0.9, 0.85, 0.82], decimal=4
            )
            assert_array_almost_equal(
                halfcycle._current.tolist(), [-0.8, -0.8, -0.8], decimal=4
            )


# Test function to check the FileManager get_cycles function with automatic ordering for biologic
def test_FileManager_get_cycles_function_biologic(folder_with_regular_mpt_file,):

    manager = FileManager()
    folder = folder_with_regular_mpt_file
    manager.fetch_from_folder(folder, ".mpt", autoparse=True)

    assert manager.suggest_ordering() == [
        ["charge_0_myCellcycling.mpt"],
        ["discharge_0_myCellcycling.mpt"],
        ["charge_1_myCellcycling.mpt"],
        ["discharge_1_myCellcycling.mpt"],
    ], "Unexpected suggested ordering"

    cycles = manager.get_cycles()

    assert len(cycles) == 2

    assert cycles[0].charge == manager._halfcycles["charge_0_myCellcycling.mpt"]
    assert cycles[0].discharge == manager._halfcycles["discharge_0_myCellcycling.mpt"]
    assert cycles[1].charge == manager._halfcycles["charge_1_myCellcycling.mpt"]
    assert cycles[1].discharge == manager._halfcycles["discharge_1_myCellcycling.mpt"]

    assert cycles[0]._hidden == False
    assert cycles[1]._hidden == False


# %% TEST OF THE LEGACY build_DTA_cycles FUNCTION

# Test function to check the build_DTA_cycles function with with regular charge/discharge
def test_build_DTA_cycles_function_regular(folder_with_minimal_dta_files):

    folder, data = folder_with_minimal_dta_files

    folder = abspath(folder)
    filelist = [
        join(folder, "charge_1.DTA"),
        join(folder, "discharge_1.DTA"),
        join(folder, "charge_2.DTA"),
        join(folder, "discharge_2.DTA"),
    ]
    cycles = build_DTA_cycles(filelist, False)

    assert len(cycles) == 2

    assert cycles[0]._hidden == False
    assert cycles[1]._hidden == False


# Test function to check the build_DTA_cycles function with with regular charge/discharge and clean option
def test_build_DTA_cycles_function_regular_with_clean(folder_with_minimal_dta_files):

    folder, data = folder_with_minimal_dta_files

    folder = abspath(folder)
    filelist = [
        join(folder, "charge_1.DTA"),
        join(folder, "discharge_1.DTA"),
        join(folder, "charge_2.DTA"),
    ]
    cycles = build_DTA_cycles(filelist, True)

    assert len(cycles) == 2

    assert cycles[0]._hidden == False
    assert cycles[1]._hidden == True


# %% TEST OF THE LEGACY read_mpt_cycles FUNCTION

# Test function to check the read_mpt_cycles function
def test_read_mpt_cycles_function_regular(folder_with_regular_mpt_file):

    folder = folder_with_regular_mpt_file

    folder = abspath(folder)
    filelist = [join(folder, "myCellcycling.mpt")]
    cycles = read_mpt_cycles(filelist, False)

    assert len(cycles) == 2

    assert cycles[0]._hidden == False
    assert cycles[1]._hidden == False
