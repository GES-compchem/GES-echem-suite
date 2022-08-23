# Getting started

The library can be installed using [anaconda](https://www.anaconda.com/products/distribution) either via the terminal or via the Anaconda Navigator application.

### From the terminal
To install the package on an existing conda environment load the environment with:

```
conda activate <ENV_NAME>
```
and then run the command:
```
conda install -c greenenergystorage GES-echem-suite
```

### With Anaconda Navigator

To install the package you must follow these steps:
- Open `Anaconda Navigator`
- Select `Environments` and then your personal virtual environment (e.g. "data_analysis")
- Click the `Update Index` button
- Search for `GES-echem-suite` in the top right search box
- Select the `GES-echem-suite` from the list
- Click `apply` on the bottom right and accept all the prompts


## Using the library

You can import the whole library in your python code using:
```
import echemsuite
```

or alternatively you can import specific objects with the syntax:
```
from echemsuite.cellcycling.cycles import Cycle
```

