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
import numpy as np
from datetime import datetime
from copy import deepcopy
from typing import Tuple
from numpy.testing import assert_almost_equal, assert_array_almost_equal

from echemsuite.cellcycling.read_input import Cycle, HalfCycle, join_HalfCycles


# %% DEFINE CONSTANT DATASET TO BE USED IN TESTING


def get_dataset_const() -> Tuple[pd.Series, pd.Series, pd.Series, datetime]:
    time = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    voltage = pd.Series([1.2, 1.2, 1.2, 1.2, 1.2])
    current = pd.Series([0.8, 0.8, 0.8, 0.8, 0.8])
    timestamp = datetime(1908, 1, 22, 0, 0, 0)
    return time, voltage, current, timestamp


@pytest.fixture
def halfcycle_obj_const() -> HalfCycle:
    """
    Generates a HalfCycle with a constant voltage of 1.2V and current of 0.8A for 4.0s with a timestep of 1.0s
    """
    time, voltage, current, timestamp = get_dataset_const()
    return HalfCycle(time, voltage, current, "charge", timestamp)


@pytest.fixture
def cycle_obj_const() -> Cycle:
    """
    Generates a Cycle with a charge and discharge halfcycles. Each halfcycle is generated with a constant 
    voltage of 1.2V and current of 0.8A for 4.0s with a timestep of 1.0s
    """
    time, voltage, current, timestamp = get_dataset_const()
    charge_halfcycle = HalfCycle(time, voltage, current, "charge", timestamp)
    discharge_halfcycle = HalfCycle(time, voltage, current, "discharge", timestamp)

    return Cycle(0, charge=charge_halfcycle, discharge=discharge_halfcycle)


@pytest.fixture
def expected_values_const() -> Tuple[pd.Series, float, pd.Series, pd.Series, float]:
    """
    Returns the expected values for the defined constant dataset
    """
    Q = [np.NaN, 0.222222222222222, 0.444444444444444, 0.666666666666667, 0.888888888888889]
    total_capacity = 0.888888888888889
    power = [0.96, 0.96, 0.96, 0.96, 0.96]
    energy = [np.NAN, 0.266666666666667, 0.533333333333333, 0.8, 1.06666666666667]
    total_energy = 1.06666666666667
    return pd.Series(Q), total_capacity, pd.Series(power), pd.Series(energy), total_energy


# %% TEST FUNCTIONS FOR THE HALFCYCLE CLASS USING THE CONSTANT DATASET

# Test function to check for exceptions raised during HalfCycle object construction
def test_HalfCycle___init__() -> None:

    time, voltage, current, timestamp = get_dataset_const()

    try:
        HalfCycle(time, voltage, current, "charge", timestamp)
    except Exception as exc:
        assert False, f"An exception occurred on HalfCycle object construction:\n\n{exc}\n"
    else:
        assert True


# Test to check the correct assignment of class properties
def test_HalfCycle_properties(halfcycle_obj_const):

    halfcycle = halfcycle_obj_const

    assert halfcycle.timestamp == halfcycle._timestamp
    assert halfcycle.halfcycle_type == halfcycle._halfcycle_type
    assert_almost_equal(halfcycle.capacity, halfcycle._capacity, decimal=6)
    assert_almost_equal(halfcycle.total_energy, halfcycle._total_energy, decimal=6)
    assert_array_almost_equal(halfcycle.time, halfcycle._time, decimal=6)
    assert_array_almost_equal(halfcycle.voltage, halfcycle._voltage, decimal=6)
    assert_array_almost_equal(halfcycle.current, halfcycle._current, decimal=6)
    assert_array_almost_equal(halfcycle.Q, halfcycle._Q, decimal=6)
    assert_array_almost_equal(halfcycle.power, halfcycle._power, decimal=6)
    assert_array_almost_equal(halfcycle.energy, halfcycle._energy, decimal=6)


# Test function to check the calculate_Q function
def test_HalfCycle_calculate_Q_function(halfcycle_obj_const, expected_values_const):

    halfcycle = halfcycle_obj_const

    Q_exp, tQ_exp, _, _, _ = expected_values_const

    assert len(halfcycle._Q) == len(halfcycle._time)
    assert_array_almost_equal(
        halfcycle._Q, Q_exp, decimal=6,
    )
    assert halfcycle._Q.iloc[-1] == halfcycle._capacity
    assert_almost_equal(halfcycle.capacity, tQ_exp, decimal=6)


# Test function to check the calculate_energy function
def test_HalfCycle_calculate_energy_function(halfcycle_obj_const, expected_values_const):

    halfcycle = halfcycle_obj_const

    _, _, P_exp, E_exp, tE_exp = expected_values_const

    assert len(halfcycle._power) == len(halfcycle._time)
    assert_array_almost_equal(halfcycle._power, P_exp, decimal=6)
    assert_array_almost_equal(halfcycle._energy, E_exp, decimal=6)
    assert_almost_equal(halfcycle._total_energy, tE_exp, decimal=6)


# %% TEST FUNCTIONS FOR THE JOIN HALFCYCLE FUNCTION USING THE CONSTANT DATASET

# Test regular operation of the join_HalfCycles function
def test_join_HalfCycles_function(halfcycle_obj_const):

    # Prepare new_halfcycle by concatenating two halfcycles
    first = halfcycle_obj_const
    second = deepcopy(first)

    second._timestamp = datetime.now()
    new_halfcycle = join_HalfCycles([first, second])

    # Prepare expected series for time, voltage and current
    time, voltage, current, timestamp = get_dataset_const()

    shifted_time = [t + 4.0 for t in time.tolist()]
    new_time = pd.Series([*time.tolist(), *shifted_time])
    new_voltage = pd.concat([voltage, voltage], ignore_index=True)
    new_current = pd.concat([current, current], ignore_index=True)

    assert new_halfcycle._timestamp == first._timestamp
    assert new_halfcycle._timestamp == timestamp
    assert_array_almost_equal(new_halfcycle.time, new_time, decimal=6)
    assert_array_almost_equal(new_halfcycle.voltage, new_voltage, decimal=6)
    assert_array_almost_equal(new_halfcycle.current, new_current, decimal=6)


# Test that the join_HalfCycles function raises an error when different types of halfcycles are considered
def test_join_HalfCycles_function_different_type_error(halfcycle_obj_const):

    first = halfcycle_obj_const
    second = deepcopy(first)

    second._halfcycle_type = "discharge"

    assert first._halfcycle_type != second._halfcycle_type

    try:
        join_HalfCycles([first, second])
    except Exception as exc:
        assert True
    else:
        assert False


# %% TEST FUNCTIONS FOR THE CYCLE CLASS USING THE CONSTANT DATASET


# Test function to check for exceptions raised during HalfCycle object construction
def test_Cycle___init__():

    cycle_number = 0

    try:
        cycle = Cycle(cycle_number)
    except Exception as exc:
        assert False, f"An exception occurred on Cycle object construction:\n\n{exc}\n"
    else:
        assert True

    assert cycle._number == cycle_number


# Test function to trigger exception when wrong type of halfcycles are used as arguments
@pytest.mark.xfail
def test_Cycle_charge_discharge_parameters_monitoring(halfcycle_obj_const):

    halfcycle = halfcycle_obj_const

    try:
        Cycle(0, charge=halfcycle, discharge=halfcycle)
    except Exception as exc:
        assert True
    else:
        assert False


# Test to check the correct assignment of class properties
def test_Cycle_properties(cycle_obj_const, expected_values_const):

    # Load dataset constant and concatenate to form a cycle
    time, voltage, current, _ = get_dataset_const()

    cycle_time = pd.concat([time, time])
    cycle_voltage = pd.concat([voltage, voltage])
    cycle_current = pd.concat([current, current])

    # Load expected values for a single HalfCycle and concatenate to form a cycle
    Q_exp, _, P_exp, E_exp, _ = expected_values_const

    cycle_Q_exp = pd.concat([Q_exp, Q_exp])
    cycle_P_exp = pd.concat([P_exp, P_exp])
    cycle_E_exp = pd.concat([E_exp, E_exp])

    cycle = cycle_obj_const

    assert_array_almost_equal(cycle.time, cycle_time, decimal=6)
    assert_array_almost_equal(cycle.voltage, cycle_voltage, decimal=6)
    assert_array_almost_equal(cycle.current, cycle_current, decimal=6)
    assert_array_almost_equal(cycle.power, cycle_P_exp, decimal=6)
    assert_array_almost_equal(cycle.energy, cycle_E_exp, decimal=6)
    assert_array_almost_equal(cycle.Q, cycle_Q_exp, decimal=6)

    assert_almost_equal(cycle.coulomb_efficiency, cycle._coulomb_efficiency, decimal=6)
    assert_almost_equal(cycle.energy_efficiency, cycle._energy_efficiency, decimal=6)
    assert_almost_equal(cycle.voltage_efficiency, cycle._voltage_efficiency, decimal=6)

    assert type(cycle.charge) == HalfCycle
    assert cycle.charge == cycle._charge

    assert type(cycle.discharge) == HalfCycle
    assert cycle.discharge == cycle._discharge


# Test function to check the calculate_efficiencies function
def test_Cycle_calculate_efficiencies_function(cycle_obj_const):

    cycle = cycle_obj_const

    assert_almost_equal(cycle.coulomb_efficiency, 100, decimal=6)
    assert_almost_equal(cycle.energy_efficiency, 100, decimal=6)
    assert_almost_equal(cycle.voltage_efficiency, 100, decimal=6)


# Test function to check the sentinel value implementation in calculate_efficiencies function
def test_Cycle_calculate_efficiencies_sentinel_value_feature(halfcycle_obj_const):

    # Generate a test charge HalfCycle with a negative current sign
    wrong_halfcycle = halfcycle_obj_const
    wrong_halfcycle._halfcycle_type = "discharge"
    wrong_halfcycle._capacity *= -1
    wrong_halfcycle._total_energy *= -1

    normal_halfcycle = halfcycle_obj_const

    cycle = Cycle(0, charge=normal_halfcycle, discharge=wrong_halfcycle)

    assert_almost_equal(cycle.coulomb_efficiency, 101, decimal=6)
    assert_almost_equal(cycle.energy_efficiency, 101, decimal=6)
    assert_almost_equal(cycle.voltage_efficiency, 101, decimal=6)


# Cumulative test to verify the functions marked as legacy
def test_Cycle_legacy_functions(cycle_obj_const):

    cycle = cycle_obj_const

    assert_array_almost_equal(cycle.time_charge, cycle.charge.time, decimal=6)
    assert_array_almost_equal(cycle.time_discharge, cycle.discharge.time, decimal=6)
    assert_array_almost_equal(cycle.voltage_charge, cycle.charge.voltage, decimal=6)
    assert_array_almost_equal(cycle.voltage_discharge, cycle.discharge.voltage, decimal=6)
    assert_array_almost_equal(cycle.current_charge, cycle.charge.current, decimal=6)
    assert_array_almost_equal(cycle.current_discharge, cycle.discharge.current, decimal=6)
    assert_array_almost_equal(cycle.power_charge, cycle.charge.power, decimal=6)
    assert_array_almost_equal(cycle.power_discharge, cycle.discharge.power, decimal=6)
    assert_array_almost_equal(cycle.energy_charge, cycle.charge.energy, decimal=6)
    assert_array_almost_equal(cycle.energy_discharge, cycle.discharge.energy, decimal=6)
    assert_array_almost_equal(cycle.Q_charge, cycle.charge.Q, decimal=6)
    assert_array_almost_equal(cycle.Q_discharge, cycle.discharge.Q, decimal=6)

    assert_almost_equal(cycle.capacity_charge, cycle.charge.capacity, decimal=6)
    assert_almost_equal(cycle.capacity_discharge, cycle.discharge.capacity, decimal=6)
    assert_almost_equal(cycle.total_energy_charge, cycle.charge.total_energy, decimal=6)
    assert_almost_equal(
        cycle.total_energy_discharge, cycle.discharge.total_energy, decimal=6
    )

