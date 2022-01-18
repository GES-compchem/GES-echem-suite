# %% ADD MODULE TO SYSPATH
from os import getcwd
import sys
from pathlib import Path

current_path = getcwd()

path = Path(current_path)
parent_path = str(path.parent.absolute())
sys.path.insert(0, parent_path)

# %% IMPORTS
import pytest
from echemsuite.cellcycling.read_input import Cycle
import pandas as pd
import numpy
from numpy.testing import assert_array_almost_equal as assert_array
from numpy.testing import assert_almost_equal


# %% TEST FUNCTIONS
@pytest.fixture
def cycle_object():
    # Setup
    time = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    voltage = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
    current = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8])
    data = (time, voltage, current)

    # Exercise
    cycle = Cycle(0)
    cycle.add_charge(data)
    cycle.add_discharge(data)

    return cycle


def test_Cycle___init__():
    # Setup
    cycle_num = 0

    # Exercise
    cycle = Cycle(cycle_num)

    # Verify
    assert cycle._number == cycle_num

    # Cleanup


def test_Cycle_add_charge(cycle_object):
    # Setup
    Q = pd.Series([numpy.NAN, 0.222222, 0.444444, 0.666667, 0.888889])
    power = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8])
    energy = pd.Series([numpy.NAN, 0.222222, 0.444444, 0.666667, 0.888889])
    total_capacity = 0.888888888888889
    total_energy = 0.888888888888889

    # Exercise
    cycle = cycle_object

    # Verify
    # Charge
    assert_array(cycle._Q_charge, Q, decimal=6)
    assert_array(cycle._power_charge, power, decimal=6)
    assert_array(cycle._energy_charge, energy, decimal=6)

    assert_almost_equal(cycle._capacity_charge, total_capacity, decimal=6)
    assert_almost_equal(cycle._total_energy_charge, total_energy, decimal=6)

    # Discharge
    assert_array(cycle._Q_discharge, Q, decimal=6)
    assert_array(cycle._power_discharge, power, decimal=6)
    assert_array(cycle._energy_discharge, energy, decimal=6)

    assert_almost_equal(cycle._capacity_discharge, total_capacity, decimal=6)
    assert_almost_equal(cycle._total_energy_discharge, total_energy, decimal=6)

    # Cleanup


def test_Cycle_properties(cycle_object):
    """
    Test all the properties of the Cycle object. Multiple tests at once should not be done,
    but since they just return a value...
    """
    # Setup
    cycle_number = 0

    # Exercise
    cycle = cycle_object

    # Verify
    assert cycle.number == cycle_number


def test_Cycle_calculate_efficiencies(cycle_object):
    """
    """
    # Setup
    # cycle0 has a capacity charge of 0
    cycle0 = Cycle(0)
    cycle0._capacity_charge = 0
    cycle0._total_energy_charge = 0

    cycle1 = Cycle(1)
    cycle1._capacity_charge = 1
    cycle1._capacity_discharge = 1
    cycle1._total_energy_charge = 1
    cycle1._total_energy_discharge = 1

    # Exercise
    cycle0.calculate_efficiencies()
    cycle1.calculate_efficiencies()

    # Verify
    assert cycle0._coulomb_efficiency == 101
    assert cycle0._energy_efficiency == 101
    assert cycle0._voltage_efficiency == 101

    assert cycle1._coulomb_efficiency == 100
    assert cycle1._energy_efficiency == 100
    assert cycle1._voltage_efficiency == 100
