import pytest
from copy import deepcopy
from os.path import dirname, abspath, join

from numpy.testing import assert_array_almost_equal, assert_almost_equal

from echemsuite.cellcycling.read_input import FileManager
from echemsuite.cellcycling.cycles import CellCycling, Cycle, HalfCycle
from echemsuite.cellcycling.experiments import RateExperiment


# Get the path of the tests directory
TEST_DIR = dirname(abspath(__file__))

# Fixture to emulate a folder containing a regular .mpt cycling file
@pytest.fixture(scope="session")
def generate_sample_cellcycling(tmp_path_factory):
    mpt_content = """
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

    folder = tmp_path_factory.mktemp("regular_mpt_files")
    file_path = folder / "myCellcycling.mpt"
    file_path.write_text(mpt_content)

    manager = FileManager()
    manager.fetch_from_folder(folder, ".mpt", autoparse=True)
    
    return manager.get_cellcycling()


# Test the RateExperiment __init__ method with no arguments
def test_RateExperiment___init__():

    try:
        obj = RateExperiment()
    except:
        assert False, "Exception occurred during RateExperiment construction"
    
    assert obj.current_steps == []
    assert obj.cycles == []
    assert obj.reference == (0, 0)

# Test the RateExperiment __init__ method with user provided arguments
def test_RateExperiment___init___with_arguments(generate_sample_cellcycling):

    cc = deepcopy(generate_sample_cellcycling)

    obj = RateExperiment(current_steps=[0.1, 0.2], cellcycling_steps=[cc, cc])

    assert obj.numbers == [1, 2, 3, 4]
    assert len(obj.cycles) == 4
    assert obj.reference == (0, 0)
    assert_array_almost_equal(obj.current_steps, [0.1, 0.1, 0.2, 0.2], decimal=6)


# Test the RateExperiment from_Biologic_battery_module classmethod
def test_RateExperiment_from_Biologic_battery_module():

    BASE_FOLDER = join(TEST_DIR, "../..")
    BMFILE = join(BASE_FOLDER, "docs/Guide/CellCycling/example_Biologic_BatteryModule/example_BattModule.mpt")
    
    try:
        obj = RateExperiment.from_Biologic_battery_module(BMFILE)
    except:
        assert False, "Exception raised duting classmethod call"

    assert obj.reference == (0, 0)
    assert len(obj.cycles) == 46
    assert_array_almost_equal(obj.current_steps, 
        [
        0.5, 1. , 1. , 1. , 1. , 1. , 1.5, 1.5, 1.5, 1.5, 1.5, 2. , 2. ,
        2. , 2. , 2. , 2.5, 2.5, 2.5, 2.5, 2.5, 3. , 3. , 3. , 3. , 3. ,
        3.5, 3.5, 3.5, 3.5, 3.5, 4. , 4. , 4. , 4. , 4. , 4.5, 4.5, 4.5,
        4.5, 4.5, 5. , 5. , 5. , 5. , 5. 
        ],
        decimal=6
    )

    assert obj.numbers == [n+1 for n in range(46)]


# Test the RateExperiment reference property
def test_RateExperiment_reference_property():

    BASE_FOLDER = join(TEST_DIR, "../..")
    BMFILE = join(BASE_FOLDER, "docs/Guide/CellCycling/example_Biologic_BatteryModule/example_BattModule.mpt")
    obj = RateExperiment.from_Biologic_battery_module(BMFILE)

    assert obj.reference == (0, 0)
    assert_almost_equal(obj.capacity_retention[0], 100, decimal=6)

    obj.reference = (2, 1)
    assert obj.reference == (2, 1)
    assert_almost_equal(obj.capacity_retention[7], 100, decimal=6)

    try:
        obj.reference = (20, 0)
    except ValueError:
        assert True
    else:
        assert False, "Exception not rised when index out of bounds in provided"
    