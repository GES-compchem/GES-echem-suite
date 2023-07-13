from echemsuite.cellcycling import read_cycles, build_cycles, time_adjust
import matplotlib.pyplot as plt

import numpy as np

################################################################################
#                               OPENING FILES                                  #
################################################################################

# Make a new empty list for each different experiment
experiment_1 = [ 
    r"C:/Users/EnekoAzàceta/Green Energy Storage/GES_Ricerca - Documenti/Projects/RD/XXXXYYYY - Ti Standardization/20220722-0,7TiOSO4 in 3H2SO4 vs 0,5FeCl2 in 3H2SO4/0,3 Cycling/CHARGE_DISCHARGE/0,3A Charge_#1.DTA",
    r"C:/Users/EnekoAzàceta/Green Energy Storage/GES_Ricerca - Documenti/Projects/RD/XXXXYYYY - Ti Standardization/20220722-0,7TiOSO4 in 3H2SO4 vs 0,5FeCl2 in 3H2SO4/0,3 Cycling/CHARGE_DISCHARGE/0,3A D-Charge_#1.DTA",
    # r"", 
    # r"",
    # r"", 
    # r"",
    # r"", 
    # r"",
    ]


################################################################################
#                               READING FILES                                  #
################################################################################

# Make a "cycles" list for each different experiment. Remember, use
# build_cycles() for .DTA files
# read_cycles() for .mpt files

cycles_1 = build_cycles(experiment_1)


################################################################################
#                               CREATING PLOT                                  #
################################################################################

plt.title("CH/DCH Profiles vs. H2 pressure")  # plot title
plt.xlabel("Capacity (mAh)",
           fontsize =14, 
           fontweight="bold")  # x axis label
plt.ylabel("Voltage vs. Ref (V)",
           fontsize =14, 
           fontweight="bold")  # y axis label

# Create separate plots for each experiment. They will all be shown in the same graph!
#
# NOTE: if you want to display all the cycles, set each plots_X variable to:
#
# plots_X = range(cycles_X.number_of_cycles)
#
# If instead you want to select specific cycles, use
#
# plots_X = [a, b, c]
#
# where a, b, c are the number of the cycles you want to display
#
# plots_1 = [0, 1, 2]

# V = 20 #Volume elettrolita (mL)
# plots_1 = range(cycles_1.number_of_cycles)
# for i in plots_1:
#     plt.plot(
#         cycles_1[i].Q/V, cycles_1[i].voltage, label=f"Cycle #{cycles_1[i].number}",
#)

# lst_colore = ["#696969","#000000","#696969","#000000"]
# lst_shapes = [":","-","-.","-"]
# V = 1 #Volume elettrolita (mL)
for cycle in cycles_1:
    plt.plot(
        cycle.Q,  
        cycle.voltage, label=f"Cycle #{cycle.number+1}",
        # ls= lst_shapes.pop(0),
        # c=lst_colore.pop(0)
        )

plt.xticks(np.arange(0, 1500, 100))
plt.xlim(0, )
plt.yticks(np.arange(0,2.0,0.2))
#plt.ylim(0.6, 1.8)
################################################################################
#                           ADDITIONAL PLOT SETTINGS                           #
################################################################################

plt.grid(which="major", c="#DDDDDD")
plt.grid(which="minor", c="#EEEEEE")
plt.legend() #da impostare posizione/taglia/font...
plt.tight_layout()

plt.show()
