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

(Examples-plot-cyclicvoltammetry)=
# Plotting cyclic voltammetry experiments


## Plotting a single cyclic-voltammetry experiment
The following scipt can be used to plot the experimental data associated to a single cyclic-voltammetry experiment. The color of each cycle is set by the default matplotlib color sequence.

```{code-cell} python
import matplotlib.pyplot as plt
from echemsuite.cyclicvoltammetry import CyclicVoltammetry

# Load the data to plot in a CyclicVoltammetry object
cv = CyclicVoltammetry("../utils/cv_sample.DTA")

# Setup a figure and set a global font size
plt.rcParams.update({'font.size': 18}) 
fig = plt.figure(figsize= (6, 6))

# Plot all the cycles contained in the cyclic-voltammetry experiment
for index, (current, voltage) in enumerate(cv):
    plt.plot(voltage, [1e6*i for i in current], label=f"{index}")

# Set the axis labels
plt.xlabel(r"V vs $\mathrm{V}_\mathrm{ref}$ [$V$]", size=20)
plt.ylabel(r"I [$\mu A$]", size=20)

# Add a legend to the plot
plt.legend(title="Cycle")

# Setup a grid
plt.grid(which="major", c="#DDDDDD")
plt.grid(which="minor", c="#EEEEEE")

# Render the plot
plt.tight_layout()
plt.show()
```

## Plotting multiple cyclic-voltammetry experiments on the same figure

If more than one experiments needs to be plotted on the same graph the following script can be used as a template. The script make use of the `graphicaltools` module to generate colors appropriate to the task.

```{code-cell} python
import matplotlib.pyplot as plt
from echemsuite.cyclicvoltammetry.read_input import CyclicVoltammetry
from echemsuite.graphicaltools import Palette, ColorShader

# Define a dictionary to store the experiments to be plotted
experiments = {}
experiments["Sample A"] = CyclicVoltammetry("../utils/cv_example_A.DTA")
experiments["Sample B"] = CyclicVoltammetry("../utils/cv_example_B.DTA")

# Define a color palette to be used in the plot
palette = Palette("vivid")

# Setup a figure object
plt.rcParams.update({'font.size': 18}) 
fig = plt.figure(figsize= (6, 6))

# Iterate over all the experiments in the dictionary
for i, (name, experiment) in enumerate(experiments.items()):

    # Define a shader with the basecolor provided by the palette
    shader = ColorShader(palette[i], levels=len(experiment), saturate=True, reversed=True, luminance_range=(0.6, 0.9))

    # Plot each trace recorded in the experiment
    for j, (current, voltage) in enumerate(experiment):
        plt.plot(voltage, [1e3*im for im in current], c=shader[j].RGB, label=name if j==0 else None)

# Add labels to the axes
plt.xlabel(r"V vs $\mathrm{V}_\mathrm{ref}$ [V]", size=20)
plt.ylabel("I [mA]", size=20)

# Add a grid to the plot
plt.grid(which="major", c="#DDDDDD")
plt.grid(which="minor", c="#EEEEEE")

# Plot the legend
plt.legend()

# Render the graph
plt.tight_layout()
plt.show()
```
