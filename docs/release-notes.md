(ReleaseNotes)=
# Release notes

* Version 0.2.1b2
    * Added classmethod to `RateExperiment` to load ARBIN `.csv` files.
    * Added timestamp propery to `CellCycling` class to more easily track the start of the experiment.
    * Added a `quickload_folder` method to the `cellcycling.read_input` module.
    * Added classmethod to `RateExperiment` to load GAMRY standard folder format.
    * Update to the documentation with more examples and new types of plot

* Version 0.2.1b
    * Added a graphicaltools module to help the user in the creation of graphs and plots 
        * Defined a simple `Color` class to hold, manipulate and carry around RGB color values.
        * Defined a `ColorShader` class to generate multiple shades of a given color (e.g. to be used when plotting capacity/voltage curves of the same cell during multiple cycles)
        * Defined a `Palette` class to handle generic color palettes to be used in plotting different experiments. 
    * Created an early version of the documentation of the module with examples. 

* Version 0.2.1a
    * Refactoring of the `cyclicvoltammetry` module:
        * Easier access to the current and voltage data of each cycle.
        * Implemented early version of the documentation with examples.
    * Added `experiments` submodule to the `cellcycling` module:
        * Introduced the `RateExperiment` class to handle multiple cellcycling experiments at different currents.
        * Updated the documentation with the new features.
        * Dropped support for old legacy functions.

* Version 0.2.0a:
    * Refacoring of the `cellcycling` module: Separated the file loader module (`echemsuite.cellcycling.read_input`) from the analysis one (`echemsuite.cellcycling.cycles`).
    * Added `FileManager` class to handle the loading and manipulation of `.DTA` and `.mpt` files
    * Refactoring of the code and set to deprecated the functions:
        * `build_DTA_cycles`
        * `read_mpt_cycles`
        * `read_cycles`
        * `build_cycles`
    * Added documentation
    * Added unit testing