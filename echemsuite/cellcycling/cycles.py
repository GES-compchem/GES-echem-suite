from __future__ import annotations
from typing import List, Tuple
import pandas as pd
from scipy.stats import linregress
from datetime import datetime

from echemsuite.utils import deprecation_warning


class CellCycling:
    """
    The ``CellCycling`` class contains all the cycles associated to a given experiment. The
    class gives to user the possibility of computing properties describing the behavior
    of the system capacity/efficiency during multiple charge/discharge cycles. Every cycle
    can be included or excluded from the computation by toggling its hided/unhided state.
    The class offers a ``__getitem__`` method returning the cycle corresponding to a given
    index and an ``__iter__`` method yelding the complete set of not hiddend cycles. The
    ``__len__`` method is set accordingly by returning the total number of non-hidden cycles.

    Arguments
    ---------
    cycles : List[Cycle]
        list of Cycle objects used to build the cellcycling sequence

    Attributes
    ----------
    reference : int
        index of the cycle to be used as a reference in computing retentions properties
    """

    def __init__(self, cycles: List[Cycle]) -> None:
        self._cycles = cycles

        self._numbers: list = None  # initialized by get_numbers()

        self._capacity_retention: list = (
            None  # initialized in capacity_retention() property
        )
        self.reference: int = 0  # used for calculating retentions

        self._retention_fit_parameters = None  # initialized by fit_retention()
        self._capacity_fade = None  # initialized by fit_retention()

    def __getitem__(self, cycle_number):
        if self._cycles[cycle_number]._hidden is False:
            return self._cycles[cycle_number]
        else:
            print(f"ERROR: cycle {self._cycles[cycle_number].number} is currently hidden.")
            print("To reinstate it, use the unhide() function")
            return None

    def __iter__(self):
        for cycle in self._cycles:
            if cycle._hidden is False:
                yield cycle

    def __len__(self):
        return len([cycle for cycle in self])

    def __repr__(self):
        return f"""
<echemsuite.cellcycling.cycles.CellCycling at {hex(id(self))}>
    ├─ total number of cycles:    {len(self._cycles)}
    ├─ number of visible cycles:  {len(self)}
    └─ reference cycle:           {self.reference}"""
    
    def __str__(self) -> str:
        return repr(self)

    def get_numbers(self) -> None:
        self._numbers = [cycle.number for cycle in self]

    def hide(self, hide_indices: List[int]) -> None:
        """Cycle masking/hiding feature. Prevents certain cycles from being
        used/shown in calculations.

        Parameters
        ----------
        hide_indices : List[int]
            list of indices to mask/hide
        """
        for i in hide_indices:
            self._cycles[i]._hidden = True

        self.get_numbers()

    def unhide(self, unhide_indices: List[int]) -> None:
        """Cycle unmasking/unhiding feature. Reinstate cycles from being
        used/shown in calculations.

        Parameters
        ----------
        unhide_indices : List[int]
            list of indices to unmask/unhide
        """
        for i in unhide_indices:
            self._cycles[i]._hidden = False

        self.get_numbers()

    @property
    def capacity_retention(self) -> List[float]:
        """
        List of capacity retentions calculated as the ratios between the discharge capacity
        at cycle ``n`` and the discharge capacity of the reference cycle (by default,
        first cycle). To change the reference cycle, set the
        :py:attr:`~echemsuite.cellcycling.cycles.CellCycling.reference` property

        Returns
        -------
        List[float]
        """
        initial_capacity = self._cycles[self.reference].discharge.capacity

        self._capacity_retention = []

        for cycle in self:
            if cycle.discharge:
                self._capacity_retention.append(
                    cycle.discharge.capacity / initial_capacity * 100
                )
            else:
                self._capacity_retention.append(None)

        return self._capacity_retention

    def fit_retention(self, start: int, end: int) -> None:
        """Fits the currently available retention data with a linear fit. The routine used
        in the fitting process is the :py:func:`scipy.stats.linregress` function.

        Parameters
        ----------
        start : int
            starting cycle number for the fitting procedure
        end : int
            ending cycle number for the fitting procedure
        """

        retention_array = self.capacity_retention[start:end]

        print(f"INFO: fitting Capacity Retention data from cycle {start} to {end}")
        self._retention_fit_parameters = linregress(range(start, end), retention_array)

        print(
            f"INFO: fit equation: retention = {self._retention_fit_parameters.slope} * cycle_number + {self._retention_fit_parameters.intercept}"
        )
        print(f"INFO: R^2 = {self._retention_fit_parameters.rvalue**2}")

        # capacity fade calculated between consecutive cycles, taken as the slope of the linear fit

        self._capacity_fade = -(self._retention_fit_parameters.slope)

    @property
    def fit_parameters(self):
        """Fitting parameters obtained from the linear fit of the capacity retention.

        Returns
        -------
        fit_parameters : ``LinregressResult`` instance
            Result is an LinregressResult object with the following attributes:
            slope
            intercept
            rvalue
            pvalue
            stderr
            intercept_stderr
        """
        return self._retention_fit_parameters

    @property
    def capacity_fade(self) -> float:
        """
        Percentual of capacity retention lost between two consecutive cycles. Please notice
        how this does not represent the total capacity fade.

        Returns
        -------
        float
            the value of capacity fade computing during the fitting operation performed by
            :py:func:`~echemsuite.cellcycling.cycles.CellCycling.fit_retention`.
        """
        return self._capacity_fade

    def predict_retention(self, cycle_numbers: List[int]) -> List[float]:
        """Predicts the retention for a given number of cycles, given the series of fit
        parameters computed by :py:func:`~echemsuite.cellcycling.cycles.CellCycling.fit_retention`.

        Parameters
        ----------
        cycle_numbers : List[int]
            list containing the cycle numbers for which you want to predict the retention

        Returns
        -------
        predicted_retentions : List[float]
            list containing the predicted retention values
        """

        predicted_retentions = []
        for cycle_number in cycle_numbers:
            retention = (
                self._retention_fit_parameters.slope * cycle_number
                + self._retention_fit_parameters.intercept
            )
            predicted_retentions.append(retention)

        return predicted_retentions

    def retention_threshold(self, thresholds: List[float]) -> List[int]:
        """Predicts, based on the linear fit parameters computed by
        :py:func:`~echemsuite.cellcycling.cycles.CellCycling.fit_retention`, the cycle numbers
        for which the capacity retention reaches the threshold specified in the input list.

        Parameters
        ----------
        thresholds : List[float]
            list containing the retention thresholds for which you want to predict the cycle number

        Returns
        -------
        predicted_thresholds : List[int]
            list containing the predicted cycle numers
        """

        predicted_cycle_numbers = []
        for retention in thresholds:
            cycle_number = int(
                (
                    (retention - self._retention_fit_parameters.intercept)
                    / self._retention_fit_parameters.slope
                )
                // 1
            )
            predicted_cycle_numbers.append(cycle_number)

        return predicted_cycle_numbers

    @property
    def coulomb_efficiencies(self) -> List[float]:
        """List of all the coulombic efficiencies associated to non-hidden cycles

        Returns
        -------
        List[float]
        """
        return [cycle.coulomb_efficiency for cycle in self]

    @property
    def voltage_efficiencies(self) -> List[float]:
        """List of all the voltaic efficiencies associated to non-hidden cycles

        Returns
        -------
        List[float]"""
        return [cycle.voltage_efficiency for cycle in self]

    @property
    def energy_efficiencies(self) -> List[float]:
        """List of all the energy efficiencies associated to non-hidden cycles

        Returns
        -------
        List[float]"""
        return [cycle.energy_efficiency for cycle in self]

    @property
    def numbers(self) -> List[int]:
        """Returns a list of all the available, not hidden, cycle numbers

        Returns
        -------
        List[int]
        """
        self.get_numbers()
        return self._numbers


class Cycle:
    """
    The ``Cycle`` class contains both a charge and a discharge half-cycle. The class wraps
    the properties of the :py:class:`~echemsuite.cellcycling.cycles.HalfCycle` and defines
    the efficiencies associated to a charge/discharge cycle.

    Arguments
    ---------
    number : int
        a univocal index indicating the number of the charge/discharge cycle
    charge : HalfCycle
        the charge half-cycle
    discharge : HalfCycle
        the discharge halfcycle

    Raises
    ------
    TypeError
        if either one of the given charge/discharge half-cycles are of the wrong type
    """

    def __init__(
        self, number: int, charge: HalfCycle = None, discharge: HalfCycle = None
    ) -> None:

        self._number = number

        self._charge: HalfCycle = charge
        self._discharge: HalfCycle = discharge

        if charge and charge._halfcycle_type != "charge":
            raise TypeError

        if discharge and discharge._halfcycle_type != "discharge":
            raise TypeError
        
        if not charge and not discharge:
            raise RuntimeError

        self._hidden: bool = False

        (
            self._coulomb_efficiency,
            self._energy_efficiency,
            self._voltage_efficiency,
        ) = self.calculate_efficiencies()
    
    def __repr__(self):
        if self._charge and self._discharge:
            status = "Both charge and discharge"
        elif self._charge:
            status = "Charge only"
        elif self._discharge:
            status = "Discharge only"

        return f"""
<echemsuite.cellcycling.cycles.Cycle at {hex(id(self))}>
    ├─ number:     {self.number}
    ├─ halfcycles: {status}
    └─ hidden:     {self._hidden}"""
    
    def __str__(self) -> str:
        return repr(self)

    # CYCLE NUMBER
    @property
    def number(self) -> int:
        """Cycle number

        Returns
        -------
        int
        """
        return self._number

    # CHARGE / DISCHARGE
    @property
    def charge(self) -> HalfCycle:
        """The charge half-cycle

        Returns
        -------
        HalfCycle
        """
        return self._charge

    @property
    def discharge(self) -> HalfCycle:
        """The discharge half-cycle

        Returns
        -------
        HalfCycle
        """
        return self._discharge

    # TIME
    @property
    def time(self) -> pd.Series:
        """pandas Series containing the time data points (in s) for the complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.time, self.discharge.time])
        elif self.charge and not self.discharge:
            return self.charge.time
        elif self.discharge and not self.charge:
            return self.discharge.time

    # VOLTAGE
    @property
    def voltage(self) -> pd.Series:
        """pandas Series containing the voltage data (in V) points for the complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.voltage, self.discharge.voltage])
        elif self.charge and not self.discharge:
            return self.charge.voltage
        elif self.discharge and not self.charge:
            return self.discharge.voltage

    # CURRENT
    @property
    def current(self) -> pd.Series:
        """pandas Series containing the current data points (in A) for the complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.current, self.discharge.current])
        elif self.charge and not self.discharge:
            return self.charge.current
        elif self.discharge and not self.charge:
            return self.discharge.current

    # POWER
    @property
    def power(self) -> pd.Series:
        """pandas Series containing the instantaneous power data points (in W) for the
        complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.power, self.discharge.power])
        elif self.charge and not self.discharge:
            return self.charge.power
        elif self.discharge and not self.charge:
            return self.discharge.power

    # ENERGY
    @property
    def energy(self) -> pd.Series:
        """pandas Series containing the instantaneous energy data points (in mWh) for the
        complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.energy, self.discharge.energy])
        elif self.charge and not self.discharge:
            return self.charge.energy
        elif self.discharge and not self.charge:
            return self.discharge.energy

    # ACCUMULATED CHARGE
    @property
    def Q(self) -> pd.Series:
        """pandas Series containing the accumulated charge data points (in mAh) for the
        complete cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        if self.charge and self.discharge:
            return pd.concat([self.charge.Q, self.discharge.Q])
        elif self.charge and not self.discharge:
            return self.charge.Q
        elif self.discharge and not self.charge:
            return self.discharge.Q

    def calculate_efficiencies(self) -> Tuple[float, float, float]:
        """
        Computes the coulombic and energy efficiency of the cycle as the ratio
        between the discharge and charge energies, provided they exist.

        Returns
        -------
            Tuple[float or None, float or None, float of None]
                a tuple containing, in order, the coulomb efficiency, the energy efficiency
                and the voltaic efficiency. If either the charge or discharge capacity is
                found to be non-positive, the sentinel value o ``101`` will be returned.
        """

        if self.charge and self.discharge:

            if self.charge.capacity <= 0 or self.charge.total_energy <= 0:
                # 101 is a sentinel value
                self._coulomb_efficiency = 101
                self._energy_efficiency = 101
                self._voltage_efficiency = 101
            else:
                self._coulomb_efficiency = (
                    self.discharge.capacity / self.charge.capacity * 100
                )
                self._energy_efficiency = (
                    self.discharge.total_energy / self.charge.total_energy * 100
                )
                self._voltage_efficiency = (
                    self._energy_efficiency / self._coulomb_efficiency * 100
                )

            return (
                self._coulomb_efficiency,
                self._energy_efficiency,
                self._voltage_efficiency,
            )

        else:
            return None, None, None

    # EFFICIENCIES
    @property
    def coulomb_efficiency(self) -> float:
        r"""Coulombic efficiency of the cycle computed according to
        :math:`100 \cdot Q_{\mathrm{discharge}}/ Q_{\mathrm{charge}}` where
        :math:`Q_{\mathrm{charge}}` and :math:`Q_{\mathrm{discharge}}` represent the capacity
        of the charge and discharge cycle respectively.

        Returns
        -------
        float
        """
        return self._coulomb_efficiency

    @property
    def energy_efficiency(self) -> float:
        r"""Energy efficiency of the cycle computed according to
        :math:`100 \cdot E_{\mathrm{discharge}}/ E_{\mathrm{charge}}` where
        :math:`E_{\mathrm{charge}}` and :math:`E_{\mathrm{discharge}}` represent the total
        energy associated to the charge and discharge cycle respectively.

        Returns
        -------
        float
        """
        return self._energy_efficiency

    @property
    def voltage_efficiency(self) -> float:
        r"""Voltaic efficiency of the cycle computed according to :math:`\eta_{E}/\eta_{Q}`
        where :math:`\eta_{E}` represents the energy efficiency of the cycle while
        :math:`\eta_{Q}` represent the correspondent coulombic efficiency.

        Returns
        -------
        float
        """
        return self._voltage_efficiency

    # LEGACY PROPERTIES

    @property
    def time_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.time``.

        Returns the time data points (in s) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.time_charge", "Cycle.charge.time")
        return self.charge.time

    @property
    def time_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.time``.

        Returns the time data points (in s) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.time_disharge", "Cycle.discharge.time")
        return self.discharge.time

    @property
    def voltage_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.voltage``.

        Returns the voltage data points (in V) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.voltage_charge", "Cycle.charge.voltage")
        return self.charge.voltage

    @property
    def voltage_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.voltage``.

        Returns the voltage data points (in V) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.voltage_discharge", "Cycle.discharge.voltage")
        return self.discharge.voltage

    @property
    def current_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.current``.

        Returns the current data points (in A) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.current_charge", "Cycle.charge.current")
        return self.charge.current

    @property
    def current_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.current``.

        Returns the current data points (in A) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.current_discharge", "Cycle.discharge.current")
        return self.discharge.current

    @property
    def power_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.power``.

        Returns the power data points (in W) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.power_charge", "Cycle.charge.power")
        return self.charge.power

    @property
    def power_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.power``.

        Returns the power data points (in W) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.power_discharge", "Cycle.discharge.power")
        return self.discharge.power

    @property
    def energy_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.energy``.

        Returns the energy data points (in mWh) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.energy_charge", "Cycle.charge.energy")
        return self.charge.energy

    @property
    def energy_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.energy``.

        Returns the energy data points (in mWh) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.energy_discharge", "Cycle.discharge.energy")
        return self.discharge.energy

    @property
    def capacity_charge(self) -> float:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.capacity``.

        Returns the capacity data points (in mAh) for the charge half-cycle

        Returns
        -------
        float
        """
        deprecation_warning("Cycle.capacity_charge", "Cycle.charge.capacity")
        return self.charge.capacity

    @property
    def capacity_discharge(self) -> float:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.capacity``.

        Returns the capacity data points (in mAh) for the discharge half-cycle

        Returns
        -------
        float
        """
        deprecation_warning("Cycle.capacity_discharge", "Cycle.discharge.capacity")
        return self.discharge.capacity

    @property
    def Q_charge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.Q``.

        Returns the cumulative charge data points (in mAh) for the charge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.Q_charge", "Cycle.charge.Q")
        return self.charge.Q

    @property
    def Q_discharge(self) -> pd.Series:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.Q``.

        Returns the cumulative charge data points (in mAh) for the discharge half-cycle

        Returns
        -------
        ``pandas.core.series.Series``
        """
        deprecation_warning("Cycle.Q_discharge", "Cycle.discharge.Q")
        return self.discharge.Q

    @property
    def total_energy_charge(self) -> float:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.charge.total_energy``.

        Returns the total energy (in mWh) for the charge half-cycle

        Returns
        -------
        float
        """
        deprecation_warning("Cycle.total_energy_charge", "Cycle.charge.total_energy")
        return self.charge.total_energy

    @property
    def total_energy_discharge(self) -> float:
        """
        .. deprecated:: 0.1.17a
            Should be substituted by the direct call to the halfcycle property ``Cycle.discharge.total_energy``.

        Returns the total energy (in mWh) for the discharge half-cycle

        Returns
        -------
        float
        """
        deprecation_warning("Cycle.total_energy_discharge", "Cycle.discharge.total_energy")
        return self.discharge.total_energy


class HalfCycle:
    """
    The ``HalfCycle`` class stores the data relative to either a charge or a discharge half-cycle
    and esposes to the user all the relevant derived observables such as accumulated/depleted
    charge and energy, istantaneous power, total capacity of the cell and total energy stored.

    Parameters
    ----------
    time : ``pandas.core.series.Series``
        pandas Series containing time-step data (in s)
    voltage : ``pandas.core.series.Series``
        Series containing voltage data (in V)
    current : ``pandas.core.series.Series``
        Series containing current data (in A)
    halfcycle_type : str
        Should either be "charge" or "discharge"
    timestamp : ``datetime.datetime``
        The timestam indicating the start of the data acquisition process or other time
        labels useful in indicating the cronological sequence of halfcycles

    Raises
    ------
    ValueError
        if the halfcycle_type does not match any of the accepted values
    """

    def __init__(
        self,
        time: pd.Series,
        voltage: pd.Series,
        current: pd.Series,
        halfcycle_type: str,
        timestamp: datetime,
    ) -> None:

        if halfcycle_type != "discharge" and halfcycle_type != "charge":
            raise ValueError

        self._timestamp = timestamp
        self._time = time
        self._voltage = voltage
        self._current = current
        self._halfcycle_type = halfcycle_type

        self._Q, self._capacity = self.calculate_Q()
        self._power, self._energy, self._total_energy = self.calculate_energy()
    
    def __repr__(self):
        return f"""
<echemsuite.cellcycling.cycles.HalfCycle at {hex(id(self))}>
    ├─ timestamp: {self.timestamp}
    ├─ type:      {self.halfcycle_type}
    └─ points:    {len(self.time)}"""
    
    def __str__(self) -> str:
        return repr(self)

    def calculate_Q(self) -> Tuple[pd.Series, float]:
        """
        Calculate the capacity C (mAh) of the charge/discharge half-cycle as the
        accumulated/depleted charge over time. Please notice ho the values are given without
        any sign.

        Returns
        -------
        ``pandas.core.series.Series``
            the cumulative capacity data points (in mAh) for the half-cycle
        float
            the total capacity of the cell (last point of the cumulative capacity series)
        """
        # accumulated charge dq at each measurement step (mA.h)
        dq = abs(self._current * self._time.diff()) / 3.6

        # charge as cumulative sum (mA.h)
        Q = dq.cumsum()

        # capacity as last value of accumulated charge (mA.h)
        capacity = Q.iloc[-1]

        return Q, capacity

    def calculate_energy(self) -> Tuple[pd.Series, pd.Series, float]:
        """
        Calculate the istantaneous power (in W), the instantaneous energy (in mWh) and the
        total energy E (mWh) of the half-cycle. Please notice ho the values are given without
        any sign.

        Returns
        -------
        ``pandas.core.series.Series``
            the instantaneous power adsorbed/generated by the cell (in W) at each time-step
        ``pandas.core.series.Series``
            the instantaneous energy adsorbed/generated by the cell (in mWh) at each time-step
        float
            the total energy excanged by the cell (last point of the cumulative sum of
            the energy series)
        """

        # instantaneous power (W)
        power = abs(self._current * self._voltage)

        # istantaneous energy dE (mWh) at each measurement step and cumulative
        dE = (power * self._time.diff()) / 3.6
        energy = dE.cumsum()

        # total energy (mWh)
        total_energy = energy.iloc[-1]

        return power, energy, total_energy

    # TIMESTAMP
    @property
    def timestamp(self) -> datetime:
        """
        Timestamp reporting the date and time at which the measurment was collected.
        (both getter and setter are provided)

        Returns
        -------
        ``datetime.datetime``
            the ``datetime`` object reporting the timestamp associated to the measurment
        """
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        if type(value) != datetime:
            raise TypeError
        self._timestamp = value

    # HALFCYCLE TYPE (charge/discharge)
    @property
    def halfcycle_type(self) -> str:
        """
        The type of the half-cycle object

        Returns
        -------
        str
            a string set to either "charge" or "discharge"
        """
        return self._halfcycle_type

    # TIME
    @property
    def time(self) -> pd.Series:
        """
        pandas Series containing the time data points (in s) for the half-cycle object

        Returns
        ------
        ``pandas.core.series.Series``
            the time series originally given as argument to the class constructor
        """
        return self._time

    # VOLTAGE
    @property
    def voltage(self) -> pd.Series:
        """
        Series containing the voltage data points (in V) for the selected half-cycle

        Returns
        ------
        ``pandas.core.series.Series``
            the voltage series originally given as argument to the class constructor
        """
        return self._voltage

    # CURRENT
    @property
    def current(self) -> pd.Series:
        """
        Series containing the current data points (in A) for the selected half-cycle

        Returns
        ------
        ``pandas.core.series.Series``
            the current series originally given as argument to the class constructor
        """
        return self._current

    # ACCUMULATED CHARGE
    @property
    def Q(self) -> pd.Series:
        """
        Series containing the cumulative charge data points (in mAh) computed at each time-step
        by the :py:func:`~echemsuite.cellcycling.cycles.HalfCycle.calculate_Q` function.

        Returns
        -------
        ``pandas.core.series.Series``
            the cumulative charge for each time-step in (mAh)
        """
        return self._Q

    # CAPACITY
    @property
    def capacity(self) -> float:
        """
        Capacity (in mAh) for the half-cycle object, calculated as the total accumulated
        charge by the :py:func:`~echemsuite.cellcycling.cycles.HalfCycle.calculate_Q` function.

        Returns
        -------
        float
            the capacity of the cell observed during the half-cycle
        """
        return self._capacity

    # POWER
    @property
    def power(self) -> pd.Series:
        """
        Series containing the instantaneous power data points (in W) for the selected half-cycle
        as computed by the :py:func:`~echemsuite.cellcycling.cycles.HalfCycle.calculate_energy` function.

        Returns
        -------
        ``pandas.core.series.Series``
            the instantaneous power for each time-step in (W)
        """
        return self._power

    # ENERGY
    @property
    def energy(self) -> pd.Series:
        """
        Series containing the instantaneous energy data points (in mWh) for the selected half-cycle
        as computed by the :py:func:`~echemsuite.cellcycling.cycles.HalfCycle.calculate_energy` function.

        Returns
        -------
        ``pandas.core.series.Series``
            the instantaneous energy for each time-step in (mWh)
        """
        return self._energy

    # TOTAL ENERGY
    @property
    def total_energy(self) -> float:
        """
        Total energy (in mWh) for the selected half-cycle, calculated as the total accumulated energy
        by the :py:func:`~echemsuite.cellcycling.cycles.HalfCycle.calculate_energy` function.

        Returns
        -------
        float
            the total energy exchanged by the cell in (mWh)
        """
        return self._total_energy


def join_HalfCycles(join_list: List[HalfCycle]) -> HalfCycle:
    """
    Join :py:class:`~echemsuite.cellcycling.cycles.HalfCycle` instances containing partial
    data into a single complete :py:class:`~echemsuite.cellcycling.cycles.HalfCycle` object
    following the order specified in the list. The timestamp of the resulting object will
    match the one associated with the first element of the list. The data are concatenated
    ignoring the input indeces. As such,  the output object will have ordered series with a
    progressive index series.

    Parameters
    ----------
    join_list: List[:py:class:`~echemsuite.cellcycling.cycles.HalfCycle`]
        list containing all the HalfCycle objects to be joined

    Raises
    ------
    RuntimeError
        if there is a mismatch in the :py:attr:`~echemsuite.cellcycling.cycles.HalfCycle.halfcycle_type`
        of the objects in the given list

    Returns
    -------
    :py:class:`~echemsuite.cellcycling.cycles.HalfCycle`
        single halfcycle object obtained from the concatenation of the input data.
        The timestamp of the output object is set according to the first (oldest) dataset.
    """

    # Set timestamp and halfcycle_type according to the first halfcycle file
    timestamp = join_list[0]._timestamp
    halfcycle_type = join_list[0]._halfcycle_type

    # Do a sanity check on the halfcycle_type associated to the given objects
    for obj in join_list:
        if obj._halfcycle_type != halfcycle_type:
            raise RuntimeError

    # Concatenate the data series for voltage and current
    voltage = pd.concat([obj._voltage for obj in join_list], ignore_index=True)
    current = pd.concat([obj._current for obj in join_list], ignore_index=True)

    dt = 0
    time_list = []
    for i, obj in enumerate(join_list):
        offset = 0 if i == 0 else time_list[-1]
        for t in obj.time:
            time_list.append(t + offset + dt)
        dt = time_list[-1] - time_list[-2]

    time = pd.Series(time_list, name="Time (s)")

    return HalfCycle(time, voltage, current, halfcycle_type, timestamp)


def time_adjust(cycle: Cycle, reverse: bool = False) -> Tuple[pd.Series, pd.Series]:
    """
    Adjust the time-scale of the charge and discharge half-cycles. If the time series of both
    charge and discharge half-cycles starts with the same value leave them unchanged, else
    make the charge time-scale start from zero and subtract to the discharge one its last value.
    If reverse is set to True subtract from the discharge time the last point of the charge
    time-series and compute the absolute value.

    Arguments
    ---------
    cycle : :py:class:`~echemsuite.cellcycling.cycles.Cycle`
        the cycle to which the charge/discharge half-cycles belong to
    reverse : bool
        if True apply the time reversal to the discharge halfcycle
    
    Returns
    -------
    Tuple[``pandas.core.series.Series``, ``pandas.core.series.Series``]
        The charge and discharge time-series
    """

    if cycle.discharge.time.iloc[0] != cycle.charge.time.iloc[0]:
        charge_time = cycle.charge.time.subtract(cycle.charge.time.iloc[0])
        discharge_time = cycle.discharge.time.subtract(cycle.discharge.time.iloc[-1])
    else:
        charge_time = cycle.charge.time
        discharge_time = cycle.discharge.time

    if reverse is True:
        switch = discharge_time - charge_time.iloc[-1]
        discharge_time = abs(switch)

    return charge_time, discharge_time
