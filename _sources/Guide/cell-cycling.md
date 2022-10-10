(CellCyclingModule)=
# The `cellcycling` module

The `echemsuite.cellcycing` module is dedicated to the analysis of data deriving from the cycling of electrochemical cells.

:::{admonition} Supported file types
The module currently supports GAMRY `.DTA` single-halfcycle files and Biologic `.mpt` cell-cycling files. The US/European number format conversion is automatically done for all `.DTA` files.
:::


## Structure of the module

The `echemsuite.cellcycing` module is articulated in two sub-modules: `read_input`, which contains the tools required to load and parse experimental data files, and `cycles`, in which all the main code objects holding and structuring the experimental data are stored.

Before moving on with the discussion on how to operate the library, let us discuss the organization of the data-structure implemented in the `echemsuite.cellcycing.cycles` sub-module. In general, a cell-cycling experiment consists of a series of charge and discharge operations intended to characterize the properties associated with a given electrochemical cell in terms of time/usage of the device. The `echemsuite.cellcycing` sub-module is organized with the same logic. The cell-cycling experiment is defined by a `CellCycling` class which internally carries a variable number of `Cycle` objects. Each `Cycle` object represents a complete charge/discharge battery cycle and, as such, it is composed by two `HalfCycles`, one for the charge and one for the discharge.

In terms of data, each halfcycle is initialized with the current and voltage time series of the corresponding charge/discharge process and holds all the derived quantities such as accumulated/dissipated charge, instantaneous power, energy, etc. All this data is then exposed to the `Cycle` and `CellCycling` objects for computing derived properties such as
coulombic/voltaic/energy efficiencies, capacity retention and capacity fade data.

For a detailed description of all the available features associated with the discussed data-objects, the interested reader is referred to the API documentation for the [`cycles` sub-module](API-cellcycling-cycles).

### Using the module

A set of simple tutorials covering the basic operations of the package is also provided. 
The list of available tutorials is as follows:

* [Loading data from a cycling experimental file](CellCycling_Loading)
* [Accessing the experimental data and derived quantities](CellCycling_AccessingData)