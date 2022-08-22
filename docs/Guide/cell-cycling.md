(CellCyclingModule)=
# The `cellcycling` module

The `echemsuite.cellcycing` module is dedicated to the analysis of data deriving from the cycling of electrochemical cells. The module gives to the user instrument level support from the parsing of the output data-files to the computation of the cell properties during the cycling process.

:::{admonition} Supported file types
The module currently supports GAMRY `.DTA` single-halfcycle files and Biologic `.mpt` cell-cycling files. The US/European number format conversion is automatically done for all `.DTA` files.
:::


## Structure of the module

The `echemsuite.cellcycing` module is articolated in two sub-modules: the `read_input` sub-module that contains all the tools required to load and parse experimental data files, and the `cycles` sub-module that contains all the main object holding, in a structurated manner, the experimental data.

Before moving on with the discussion on how to operate the library, let us discuss the organization of the data-structure implemented in the `echemsuite.cellcycing.cycles` sub-module. In general, a cell-cycling experiment consists of a series of charge and discharge operatons intended to characterize the properties associated to a given electrochemical cell in terms of time/usage of the device. The `echemsuite.cellcycing` sub-module is organized with the same logic. The cell-cycling experiment is defined by a `CellCycling` class that internally carries a variable number of `Cycle` objects. Each `Cycle` object represents a complete charge/discharge battery cycle and, as such, it is composed by two `HalfCycles`, one for the charge and one for the discharge.

In terms of data, each halfcycle is initialized with the current and voltage time series of the correspondent charge/discharge process and hold all the derived quantities such as accumulated/dissipated charge, instantaneous power, energy,  etc. All these data are then available to the `Cycle` and `CellCycling` objects that can compute derived properties such as
columbic/voltaic/energy efficiencies, capacity retention and capacity fade data.

For a detailed description of all the available features associated to the discussed data-objects please reference the API documentation for the [`cycles` sub-module](API-cellcycling-cycles).

### Using the module

A set of simple tutorials covering the basic operation of the package are also provided. 
The list of available tutorials is the following:

* [Loading data from a cycling experimental file](CellCycling_Loading)
* [Acessing the experimental data and derived quantities](CellCycling_AccessingData)