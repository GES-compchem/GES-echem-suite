(API-cellcycling-read_input)=
# The `echemsuite.cellcycling.read_input` sub-module

## The `Instrument` enumeration

```{eval-rst}
.. autoclass:: echemsuite.cellcycling.read_input.Instrument
    :members:
```

---

## The `FileManager` class

```{eval-rst}
.. autoclass:: echemsuite.cellcycling.read_input.FileManager
    :members:
```

---

## Legacy functions

:::{admonition} Legacy warning
:class: warning
All the functions listed in this sections, namely:

* `build_DTA_cycles`
* `build_cycles`
* `read_cycles`
* `read_mpt_cycles`

are considered deprecated since version 0.2.0a and should be substituted by a direct call to
the `FileManager` class.
:::

### The `build_DTA_cycles` function

```{eval-rst}
.. autofunction:: echemsuite.cellcycling.read_input.build_DTA_cycles
```

---

### The `build_cycles` function

```{eval-rst}
.. autofunction:: echemsuite.cellcycling.read_input.build_cycles
```

---

### The `read_cycles` function

```{eval-rst}
.. autofunction:: echemsuite.cellcycling.read_input.read_cycles
```

---

### The `read_mpt_cycles` function

```{eval-rst}
.. autofunction:: echemsuite.cellcycling.read_input.read_mpt_cycles
```