---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

(CyclicVoltammetryModule)=
# The `echemsuite.cyclicvoltammetry` module

The `echemsuite.cyclicvoltammetry` module is dedicated to the analysis of data deriving from cyclic-voltammetry experiments.

:::{admonition} Supported file types
The module currently supports GAMRY `.DTA` files, Biologic `.mpt` files and CH instruments `.txt` ASCII files.
:::


## Structure of the module

The `echemsuite.cyclicvoltammetry` module is articulated in a single sub-module named `read_input`. The module is resposible to load the experimental files, parse them and allow an easy access to the user. The core element of the module is the `CyclicVoltammetry` class that represents the digital equivalent of a cyclic-voltammetry experiment.


### Basic operation of the module

An instance of a `CyclicVoltammetry` object can be created directly form an experimental file according to the syntax:

```{code-cell} python
from echemsuite.cyclicvoltammetry import CyclicVoltammetry

cv = CyclicVoltammetry("../utils/cv_sample.DTA")
```

The number of cycles loaded can be accessed using the `__len__` attribute according to:

```{code-cell} python
ncycles = len(cv)
print(f"The loaded experiment contains {ncycles} cycles")
```

The `CyclicVoltammetry` class allows easy access to each cycles in the experiment thanks to the built-in `__getitem__` attribute. To access the current and potential values associated with a given cycle, it is sufficient to access the desired index using the square brakets notation. As an example, the following code can be used to access the current `I` and the potential `V` associated to the first CV cycle (index `0`):

```{code-cell} python
I, V = cv[0]
print(I)
```

The `CyclicVoltammetry` class also provides a simple `__iter__` method returning for each cycle the series containing the current and potential values associated to each cycle. As an example:

```{code-cell} python
for index, (I, V) in enumerate(cv):
    print(f"Cycle {index}: {I}")
```

## Example: A simple script to plot the experimental data

The following scipt can be used to plot the experimental data associated to a CV experiment. The data will be plotted using the `matplotlib` library.

```{code-cell} python
# Import all the required packages
import matplotlib.pyplot as plt
from echemsuite.cyclicvoltammetry import CyclicVoltammetry

# Load the data to plot
cv = CyclicVoltammetry("../utils/cv_sample.DTA")

# Setup a figure and set a global font size
fig = plt.figure(figsize= (8, 8))
plt.rcParams.update({'font.size': 18}) 

# Plot all the cycles contained in the cyclic-voltammetry experiment
for index, (current, voltage) in enumerate(cv):
    plt.plot(voltage, [1e6*i for i in current], label=f"{index}")

# Set the axis labels
plt.xlabel(r"V vs $\mathrm{V}_\mathrm{ref}$ [$V$]", size=22)
plt.ylabel(r"I [$\mu A$]", size=22)

# Add a legend to the plot
plt.legend(title="Cycle")

# Setup a grid
plt.grid(which="major", c="#DDDDDD")
plt.grid(which="minor", c="#EEEEEE")

# Render the plot
plt.tight_layout()
plt.show()
```
