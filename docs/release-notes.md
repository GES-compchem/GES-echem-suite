(ReleaseNotes)=
# Release notes

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