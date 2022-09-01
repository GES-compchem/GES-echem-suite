(ReleaseNotes)=
# Release notes

* Version 2.0.0:
    * Refacoring of the `cellcycling` module: Separated the file loader module (`echemsuite.cellcycling.read_input`) from the analysis one (`echemsuite.cellcycling.cycles`).
    * Added `FileManager` class to handle the loading and manipulation of `.DTA` and `.mpt` files
    * Refactoring of the code and set to deprecated the functions:
        * `build_DTA_cycles`
        * `read_mpt_cycles`
        * `read_cycles`
        * `build_cycles`
    * Added documentation
    * Added unit testing