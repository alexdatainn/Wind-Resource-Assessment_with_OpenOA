# -*- coding: utf-8 -*-
"""
Created on Sat Jan 21 13:40:01 2023

@author: aebrahimi
"""

## to download data from site 
import cdsapi

from netCDF4 import Dataset
import numpy as np
import pandas as pd
import os
import numpy.ma as ma  #Return the data of a masked array as an ndarray
from datetime import datetime, timedelta


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



#this part of API call is from website : https://cds.climate.copernicus.eu/api-how-to
c = cdsapi.Client()

#corrdinate to use in ERA part
#[N,W,S,E]
Corrd = {'SL' : [49.5, -98.125, 49.499,-98.124,], 'AMHST' : [44.15, -76.700, 44.149,-76.699,], 'MN' : [40.530, -88.590, 40.529,-88.589,],
         'MOR' : [50.5, -106.875, 50.499,-106.874,] , 'RLWEP' : [50.140, -101.470, 50.139,-101.469,], 'SNDY' : [40.430, -78.170, 40.429,-78.169,],
         'SENT' : [33.25, -98.25, 33.24,-98.24,],'SO' : [42, -88.75, 41.999,-88.749,],'DAMA' : [48.370, -67.510, 48.369,-67.509,],
         'DFS' : [44.000, -82.88, 43.999, -82.87,] , 'OWF' : [44.000, -94.375, 43.999, -94.374,] , 'MAV' : [31.140, -99.510, 31.139, -99.509,],
         'SUGR' : [40.800, -89.320, 40.799, -89.319,] }


path = './ERA5_20yrs/'
SiteCorrd = Corrd['SL']

years=[['2001','2002','2003',],['2004','2005','2006',],['2007','2008','2009',],['2010','2011','2012',],['2013','2014','2015',],['2016','2017','2018',],['2019','2020','2021',],['2022',]]


result_df = pd.DataFrame()#[columns=['datetime', 'u_100', 'v_100', 't_2m', 'surf_pres','ws_100m']]

for yr in years:
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'variable': [
                '100m_u_component_of_wind', '100m_v_component_of_wind', '2m_temperature','surface_pressure',
            ],
            'year': yr,
            
            'month': [
            '01', '02', '03',
            '04', '05', '06',
            '07', '08', '09',
            '10','11','12',
            ],
            'day': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
                '13', '14', '15',
                '16', '17', '18',
                '19', '20', '21',
                '22', '23', '24',
                '25', '26', '27',
                '28', '29', '30',
                '31',
            ],
            'time': [
                '00:00', '01:00', '02:00',
                '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00',
                '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00',
                '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00',
                '21:00', '22:00', '23:00',
            ],
            'area': SiteCorrd,
            'format': 'netcdf',
        },
        path + f'ERA5_{yr}.nc' )
    
    data  = Dataset( path + f'ERA5_{yr}.nc', 'r')
    print( (len(data.variables['time']), len(data.variables['latitude']), len(data.variables['longitude'])) )
    # print(data.variables.keys())
    # print(data.variables)
    
    u_100 = data.variables['u100'][:]
    v_100 = data.variables['v100'][:]
    t_2m = data.variables['t2m'][:]
    surf_pres = data.variables['sp'][:]
    
    #pythagorean theorem
    ws_100m = np.sqrt(v_100**2 + u_100**2)
    
    
    # get data from masked array, 
    ws_100m =  [val[0][0] for val in ma.getdata(ws_100m[:])]
    u_100= [val[0][0] for val in ma.getdata(u_100[:])]
    v_100= [val[0][0] for val in ma.getdata(v_100[:])]
    t_2m= [val[0][0] for val in ma.getdata(t_2m[:])]
    surf_pres= [val[0][0] for val in ma.getdata(surf_pres[:])]
    
    
    ERA_start= datetime(1900,1,1,0,0,0,0)
    ERA_datetime = data.variables['time'][:]
    ERA_datetime = [ERA_start + timedelta(hours=int(dt)) for dt in ma.getdata(ERA_datetime)[:]]
    
    
    df = pd.DataFrame({'datetime':ERA_datetime, 'u_100':u_100, 'v_100':v_100, 't_2m':t_2m, 'surf_pres':surf_pres,'ws_100m': ws_100m })
    
    #calculate density (from OpenOA function)
    df['dens_100m']= compute_air_density(df['t_2m'], df['surf_pres'])

    result_df = pd.concat([result_df,df], axis=0, ignore_index=True)
    
    data.close()
    
    print(f'{years[0]}-------------------------- Done')


result_df.to_csv( './ERA5_20yrs/ERA5_20yrs.csv')



