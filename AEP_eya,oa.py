# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 11:33:24 2023

@author: aebrahimi
"""
import numpy as np
import pandas as pd
from project_ENGIE import Project_Engie

from operational_analysis.methods import plant_analysis
from operational_analysis.methods import turbine_long_term_gross_energy
from operational_analysis.methods import electrical_losses
from operational_analysis.methods import eya_gap_analysis

import os
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
import pandas as pd
import copy


# Load plant object and process plant data
project = Project_Engie('./analysis_data')
project.prepare()


######################################################################################################
############## Calculate AEP ####
pa = plant_analysis.MonteCarloAEP(project, reanal_products = ['era5','merra2'])


pa.plot_reanalysis_normalized_rolling_monthly_windspeed().show() #Review reanalysis data
pa.plot_reanalysis_gross_energy_data(outlier_thres=3).show()  #Review energy and loss data
pa.plot_aggregate_plant_data_timeseries().show()

pa.run(num_sim=20000, reanal_subset=['era5','merra2'])
# Plot a distribution of AEP values from the Monte Carlo OA method
pa.plot_result_aep_distributions().show()
'''
############## Post-analysis visualization ####
# Produce histograms of the various MC-parameters
mc_reg = pd.DataFrame(data = {'slope': pa._mc_slope.ravel(),
                             'intercept': pa._mc_intercept,
                              'num_points': pa._mc_num_points,
                              'metered_energy_fraction': pa._inputs.metered_energy_fraction,
                              'loss_fraction': pa._inputs.loss_fraction,
                              'num_years_windiness': pa._inputs.num_years_windiness,
                              'loss_threshold': pa._inputs.loss_threshold,
                              'reanalysis_product': pa._inputs.reanalysis_product})

# Boxplot of AEP based on choice of reanalysis product
tmp_df=pd.DataFrame(data={'aep':pa.results.aep_GWh,'reanalysis_product':mc_reg['reanalysis_product']})
tmp_df.boxplot(column='aep',by='reanalysis_product',figsize=(8,6))
plt.ylabel('AEP (GWh/yr)')
plt.xlabel('Reanalysis product')
plt.title('AEP estimates by reanalysis product')
plt.suptitle("")
plt.show()
'''
############## Calculate TIE ####
ta = turbine_long_term_gross_energy.TurbineLongTermGrossEnergy(project, UQ=False)
ta.run(reanal_subset = ['era5','merra2'],
       
        max_power_filter = 0.85,
        wind_bin_thresh = 2.0, # Exclude data outside 2 standard deviations of the median for each power bin
        correction_threshold = 0.90, # Don't apply bin filter above 0.9 of turbine capacity
       
       # wind_bin_thresh=(1, 3), #set tuple if UQ=True
       # max_power_filter=(0.8, 0.9), #set tuple if UQ=True
       # correction_threshold=(0.85, 0.95), #set tuple if UQ=True
       enable_plotting = False,
       plot_dir = None)

# What is the long-term annual TIE for whole plant
print('Long-term turbine ideal energy is %s GWh/year' %np.round(np.mean(ta._plant_gross/1e6),1))
#is based on the mean TIE resulting from the two reanalysis products considered.


############## Calculate electrical losses
el = electrical_losses.ElectricalLosses(project)
el.run()
# Electrical losses for the wind farm
print('Electrical losses are %s percent' % np.round(el._electrical_losses[0][0]*100,1))
#Now let’s plot electrical losses by month
plt.figure(figsize = (8,4))
monthly_merge = el._merge_df.resample('MS').sum()
plt.plot((monthly_merge['corrected_energy'] - monthly_merge['energy_kwh']) / monthly_merge['corrected_energy'] * 100)
plt.xlabel('Month')
plt.ylabel('Electrical Losses (%)')

'''
##Electrical loss estimation including uncertainty quantification
## Create Electrical Loss object
el = electrical_losses.ElectricalLosses(project, UQ = True, # enable UQ
                                        num_sim = 3000 # number of Monte Carlo simulations to perform
                                       )
el.run(uncertainty_meter=0.005, # 0.5% uncertainty in meter data
       uncertainty_scada=0.005, # 0.5% uncertainty in scada data
       uncertainty_correction_thresh=(0.9, 0.995) # If dealing with monthly meter data, exclude months with less than 95%
                                          # data coverage
      )
#Electrical losses for the wind farm
print('Electrical losses are %s percent' % np.round(np.mean(el._electrical_losses)*100,1))

print('Uncertainty in the electrical loss estimate is %s percent' % np.round(np.std(el._electrical_losses)*100,1))
'''
############## First summarize key operational results
aep = pa.results.aep_GWh.mean()
avail = pa.results.avail_pct.mean()
elec = el._electrical_losses[0][0]
# tie = ta._plant_gross[0][0]/1e6
tie = np.mean(ta._plant_gross/1e6)

print(aep, avail, elec, tie)


# Define operational data list
oa_list = [aep, avail, elec, tie]
# AEP (GWh/yr), availability loss (fraction), electrical loss (fraction), turbine ideal energy (GWh/yr)

# Define EYA data list (we are fabricating these values here as an example)
# [540.1, 680.5, 0.946, 0.967, 0.952, 0.01, 0.926]
eya_list = [350.8, 402.4, 0.034, 0.02, 0.01, 0.01, 0.033]
# AEP (GWh/yr), Gross energy (GWh/yr), availability loss (fraction), electrical loss (fraction), turbine performance loss (fraction)
# blade degradation loss (fraction), wake loss (fraction)



gap_anal = eya_gap_analysis.EYAGapAnalysis(plant = 'St Leon', eya_estimates = eya_list, oa_results = oa_list)
gap_anal.run()

######################################################################################################
## Initializing QC and Performing the Run Method
import numpy as np
import pandas as pd

from operational_analysis.methods.quality_check_automation import WindToolKitQualityControlDiagnosticSuite as QC

scada_df = pd.read_csv('./analysis_data/SCADADATA_2021,2022.csv')

# date = [s[0:10] for s in scada_df['Date_time']]
# time = [s[11:19] for s in scada_df['Date_time']]
# datetime = [date[s] + ' ' + time[s] for s in np.arange(len(date))]
# scada_df['datetime'] = pd.to_datetime(datetime, format = "%Y-%m-%d %H:%M:%S")

# scada_df.set_index('datetime', inplace = True, drop = False)


qc = QC(
    data=scada_df,
    ws_field='Ws_avg',
    power_field= 'P_avg',
    time_field='Date_time',
    id_field='Wind_turbine_name',
    freq='10T',
    lat_lon=(49.37775, -98.60280555),
    # It is highly recommended to add the local timezone even if it may not be present
    local_tz="America/Chicago",
    timezone_aware=True,  # We should indicate that the timezone in the data is unknown
    check_tz=False,  # True for WIND ToolKit-valid locations only, though will not break the code if outside
)

qc._df.head()
qc._df.dtypes
qc.run()


qc.column_histograms() #Perform a general scan of the distributions for each numeric variable
qc._max_min #Check ranges of each variable

qc._time_duplications #Identify any timestamp duplications and timestamp gaps
qc.daylight_savings_plot()
