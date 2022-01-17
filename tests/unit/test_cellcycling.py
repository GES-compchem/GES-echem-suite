# %% ADD MODULE TO SYSPATH
from os import getcwd
import sys
from pathlib import Path

current_path = getcwd()

path = Path(current_path)
parent_path = str(path.parent.absolute())
sys.path.insert(0, parent_path)

# %% IMPORTS
from echemsuite.cellcycling.read_input import Cycle
import pandas as pd
import numpy
from numpy.testing import assert_array_almost_equal as assert_array
from numpy.testing import assert_almost_equal


# %% TEST FUNCTIONS
def test_Cycle___init__():
    # Setup
    cycle_num = 0

    # Exercise
    cycle = Cycle(cycle_num)

    # Verify
    assert cycle._number == cycle_num

    # Cleanup


def test_Cycle_add_charge():
    # Setup
    time = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    voltage = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
    current = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8])
    charge_data = (time, voltage, current)

    Q = pd.Series([numpy.NAN, 0.222222, 0.444444, 0.666667, 0.888889])
    power = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8])
    energy = pd.Series([numpy.NAN, 0.222222, 0.444444, 0.666667, 0.888889])
    total_capacity = 0.888888888888889
    total_energy = 0.888888888888889

    # Exercise
    cycle = Cycle(0)
    cycle.add_charge(charge_data)
    print("hey")
    print("charge:\n", cycle.Q)
    print("total_capacity:\n", cycle.capacity_charge)
    print("power_charge:\n", cycle.power_charge)
    print("energy_charge:\n", cycle.energy_charge)
    print("total energy:\n", cycle.total_energy_charge)
    #  cycle.capacity_charge, cycle.power_charge, cycle.energy_charge)

    # Verify
    assert_array(cycle.Q, Q, decimal=6)
    assert_array(cycle.power_charge, power, decimal=6)
    assert_array(cycle.energy_charge, energy, decimal=6)

    assert_almost_equal(cycle.capacity_charge, total_capacity, decimal=6)
    assert_almost_equal(cycle.total_energy_charge, total_energy, decimal=6)

    # Cleanup
