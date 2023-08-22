# Getting started

The latest version of the library can be downloaded directly from [our GitHub page](https://github.com/GES-compchem/GES-echem-suite) and then installed using pip. To do so, you can run the following commands:

```
git clone https://github.com/GES-compchem/GES-echem-suite
cd GES-echem-suite
pip install .
```

## Using the library

You can import the whole library in your python code using:
```
import echemsuite
```

or alternatively you can import specific objects with the syntax:
```
from echemsuite.cellcycling.cycles import Cycle
```

Once loaded, all the functions of the library can be accessed following the proper path to each module. A complete description of all the available functions can be found in the [API reference](API_Reference) page. A simple example of the typical structure of a script using the library is reported in what follows:

```
from typing import List
from echemsuite.cellcycling.read_input import FileManager
from echemsuite.cellcycling.cycles import Cycle

# Load and parse the .DTA files contained in the "my_folder" directory
manager = FileManager()
manager.fetch_from_folder("./my_folder", ".DTA")

# Obtain the list of charge/discharge cycles
cycles: List[Cycle] = manager.get_cycles()

# Do something with the loaded data
print(f"Hurray, you have loaded {len(cycles)} charge/discharge cycles!")
```