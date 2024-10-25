# -*- coding: utf-8 -*-
"""
Created on Fri Mar 19 11:42:00 2021

@author: aebrahimi
"""


import requests
# To go around netCDF4 files 
from netCDF4 import Dataset
import netCDF4
import numpy as np
import pandas as pd
import os
import numpy.ma as ma  #Return the data of a masked array as an ndarray
from datetime import datetime, timedelta

#https://goldsmr4.gesdisc.eosdis.nasa.gov/opendap/MERRA2/M2T1NXSLV.5.12.4/2019/12/MERRA2_400.tavg1_2d_slv_Nx.20191230.nc4.nc4?U50M[0:23][279:279][131:131],V50M[0:23][279:279][131:131],time,lat[279:279],lon[131:131]

def compute_air_density(temp_col, pres_col, humi_col=None):
    """
    Calculate air density from the ideal gas law based on the definition provided by IEC 61400-12
    given pressure, temperature and relative humidity.

    This function assumes temperature and pressure are reported in standard units of measurement
    (i.e. Kelvin for temperature, Pascal for pressure, humidity has no dimension).

    Humidity values are optional. According to the IEC a humiditiy of 50% (0.5) is set as default value.

    Args:
        temp_col(:obj:`array-like`): array with temperature values; units of Kelvin
        pres_col(:obj:`array-like`): array with pressure values; units of Pascals
        humi_col(:obj:`array-like`): optional array with relative humidity values; dimensionless (range 0 to 1)

    Returns:
        :obj:`pandas.Series`: Rho, calcualted air density; units of kg/m3
    """
    # Check if humidity column is provided and create default humidity array with values of 0.5 if necessary
    if humi_col is not None:
        rel_humidity = humi_col
    else:
        rel_humidity = np.repeat(0.5, temp_col.shape[0])
    # Send exception if any negative data found
    if np.any(temp_col < 0) | np.any(pres_col < 0) | np.any(rel_humidity < 0):
        raise Exception(
            "Some of your temperature, pressure or humidity data is negative. Check your data."
        )

    # protect against python 2 integer division rules
    temp_col = temp_col.astype(float)
    pres_col = pres_col.astype(float)

    R_const = 287.05  # Gas constant for dry air, units of J/kg/K
    Rw_const = 461.5  # Gas constant of water vapour, unit J/kg/K
    rho = (1 / temp_col) * (
        pres_col / R_const
        - rel_humidity * (0.0000205 * np.exp(0.0631846 * temp_col)) * (1 / R_const - 1 / Rw_const)
    )

    return rho


path = './MERRA2_20yrs/'
path_in = './MERRA2_20yrs/netfiles/'

   
    
with open(path + 'MERRA2_20yrs.txt', 'r') as a_file:
    file_line = a_file.readlines()[1:]
    # for line in file_line:

# WindSpeed_total = np.empty(0)
u_50 = []
v_50 = []
T2M = []
PS = []
DateTimes = [] 

for line in file_line:
    # Set the URL string to point to a specific data URL. Some generic examples are:
    #   https://servername/data/path/file
    #   https://servername/opendap/path/file[.format[?subset]]
    #   https://servername/daac-bin/OTF/HTTP_services.cgi?KEYWORD=value[&KEYWORD=value]
    
    URL = line.strip()
    
    # Set the FILENAME string to the data file name, the LABEL keyword value, or any customized name. 
    FILENAME = line[108:116] + '-site.nc4'
    print('--------------------------------------'+FILENAME)
    result = requests.get(URL)
    try:
       result.raise_for_status()
       f = open(path_in+FILENAME,'wb')
       f.write(result.content)
       f.close()
       print('contents of URL written to '+FILENAME)
    except:
       print('requests.get() returned an error code '+str(result.status_code))
       
    #reading saved nec4 file
    data  = Dataset(path_in+FILENAME, 'r')   
    # print( 'key' ,('time', 'latitude', 'longitude') , (len(data.variables['time']), len(data.variables['lat']), len(data.variables['lon'])) )
    # print(data.variables.keys())
    # print(data.variables)
    
    u_50.extend([val[0][0] for val in ma.getdata(data.variables['U50M'][:])])
    v_50.extend([val[0][0] for val in ma.getdata(data.variables['V50M'][:])]) 
    T2M.extend([val[0][0] for val in ma.getdata(data.variables['T2M'][:])]) 
    PS.extend([val[0][0] for val in ma.getdata(data.variables['PS'][:])]) 
    
    dates = netCDF4.num2date(data.variables['time'][:],data.variables['time'].units)
    DateTimes.extend([val for val in ma.getdata(dates)]) 

    # #pythagorean theorem
    # WindSpeed = np.sqrt(v_100**2 + u_100**2)
    # # get data from masked array, reshape it to use into data frame
    # WindSpeed = ma.getdata(WindSpeed[:]).reshape(len(WindSpeed[:]),)
    # WindSpeed_total = np.append(WindSpeed_total, WindSpeed)
    
    data.close()
    os.remove(path_in + FILENAME)

#reference:  https://unidata.github.io/cftime/api.html
DateTimes_dt = [pd.to_datetime(dt.strftime('%Y-%m-%d %H:%M:%S')) for dt in DateTimes] 
  
df = pd.DataFrame({'datetime': DateTimes_dt, 'surface_pressure':PS, 'u_50':u_50, 'v_50':v_50, 'temp_2m':T2M})

#calculate density (from OpenOA function)
df['dens_50m']= compute_air_density(df['temp_2m'], df['surface_pressure'])   

df['ws_50m']= np.sqrt(df['u_50']**2 + df['v_50']**2)
df['datetime']= [datetime.strftime(dt, '%Y-%m-%d %H:%M:%S') for dt in df['datetime']]


df.to_csv(path + 'MERRA2_20yrs.csv')

 

     




# data  = Dataset(path + 'MERRA2_400.tavg1_2d_slv_Nx.20191230.nc4.nc4', 'r')   
# print( 'key' ,('time', 'latitude', 'longitude') , (len(data.variables['time']), len(data.variables['lat']), len(data.variables['lon'])) )
# # print(data.variables.keys())
# # print(data.variables)

# u_100 = data.variables['U50M'][:]
# v_100 = data.variables['V50M'][:]
# #pythagorean theorem
# WindSpeed = np.sqrt(v_100**2 + u_100**2)
# # get data from masked array, reshape it to use into data frame
# WindSpeed = ma.getdata(WindSpeed[:]).reshape(len(WindSpeed[:]),)


