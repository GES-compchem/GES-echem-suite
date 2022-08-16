# The `cellcycling` module

The `echemsuite.cellcycing` module is dedicated to the analysis of data deriving from the 
cycling of electrochemical cells. The module gives to the user instrument level support from
the parsing of the output data-files to the computation of the cell properties during the
cycling process.

The module is articolated in two sub-modules:

* The `read_input` sub-module that contains all the tools required to load and parse data files
* The `cycles` sub-module that contains all the main object holding, in a structurated manner, the experimental data

A detailed API documentation is available for both the [`read_input` module](API-cellcycling-read_input)
and for the [`cycles` module](API-cellcycling-cycles).

A set of simple tutorials covering the basic operation of the package are also provided. 
The list of available tutorials is the following:

* [Basic loading of data-files from folder and bytestreams](BasicLoading)
* [Computing properties of the cell-cycling experiment](ComputingProperties)