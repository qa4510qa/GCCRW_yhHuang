# -*- coding: utf-8 -*-
"""
Created on Fri May 28 13:16:44 2021
@author: jhuang
Modified on Fri May 28 22:18:50 2021
@author: yhHuang
"""

import os
from netCDF4 import Dataset, num2date, date2num
import numpy as np
import pandas as pd

def ncdump(nc_fid, verb=True):
    '''
    http://schubert.atmos.colostate.edu/~cslocum/netcdf_example.html
    
    ncdump outputs dimensions, variables and their attribute information.
    The information is similar to that of NCAR's ncdump utility.
    ncdump requires a valid instance of Dataset.

    Parameters
    ----------
    nc_fid : netCDF4.Dataset
        A netCDF4 dateset object
    verb : Boolean
        whether or not nc_attrs, nc_dims, and nc_vars are printed
	
    Returns
    -------
    nc_attrs : list
        A Python list of the NetCDF file global attributes
    nc_dims : list
        A Python list of the NetCDF file dimensions
    nc_vars : list
        A Python list of the NetCDF file variables
	'''
    def print_ncattr(key):
        """
        Prints the NetCDF file attributes for a given key

        Parameters
        ----------
        key : unicode
            a valid netCDF4.Dataset.variables key
        """
        try:
            print("\t\ttype:", repr(nc_fid.variables[key].dtype))
            for ncattr in nc_fid.variables[key].ncattrs():
                print('\t\t%s:' % ncattr,\
                      repr(nc_fid.variables[key].getncattr(ncattr)))
        except KeyError:
            print( "\t\tWARNING: %s does not contain variable attributes" % key)
    
    # NetCDF global attributes
    nc_attrs = nc_fid.ncattrs()
    if verb:
        print( "NetCDF Global Attributes:")
        for nc_attr in nc_attrs:
            print ('\t%s:' % nc_attr, repr(nc_fid.getncattr(nc_attr)))
    nc_dims = [dim for dim in nc_fid.dimensions]  # list of nc dimensions
    # Dimension shape information.
    if verb:
        print( "NetCDF dimension information:")
        for dim in nc_dims:
            print ("\tName:", dim )
            print ("\t\tsize:", len(nc_fid.dimensions[dim]))
            print_ncattr(dim)
    # Variable information.
    nc_vars = [var for var in nc_fid.variables]  # list of nc variables
    if verb:
        print( "NetCDF variable information:")
        for var in nc_vars:
            if var not in nc_dims:
                print ('\tName:', var)
                print ("\t\tdimensions:", nc_fid.variables[var].dimensions)
                print ("\t\tsize:", nc_fid.variables[var].size)
                print_ncattr(var)
    return nc_attrs, nc_dims, nc_vars

def getNC(nc_fp,file_name):
    nc_fid=None
    #'D:\\IPCC_GCM\\NASA\\pr_day_BCSD_historical_r1i1p1_bcc-csm1-1_1986.nc'
    f = nc_fp+file_name
    print(f)
    #nc_f=glob.glob(f)[0]
    nc_f=f
    if os.path.exists(nc_f):
        #print(nc_f)
        nc_fid = Dataset(nc_f, 'r')  # Dataset is the class behavior to open the file
                             # and create an instance of the ncCDF4 class
        nc_attrs, nc_dims, nc_vars = ncdump(nc_fid,verb=False)
    else :
        print ("Your file doesn't exist")
    return nc_fid

# def ncgetValue(nc_fid,factor,location,time):   
#     # Extract data from NetCDF file
#     alats = nc_fid.variables['lat'][:]  # extract/copy the data
#     alons = nc_fid.variables['lon'][:]
#     lat_idx = np.abs(alats - location[1]).argmin()
#     lon_idx = np.abs(alons - location[0]).argmin()
#     times = nc_fid.variables['time']
#     dates = num2date(times[:],units=times.units,calendar=times.calendar)      
#     str_time = [i.strftime("%Y-%m-%d %H:%M") for i in dates]
#     v=nc_fid.variables[factor][:, lat_idx, lon_idx]
#     result_dict={
#             'lon':alons[lon_idx],
#             'lat':alats[lat_idx],
#             'time':str_time,
#             'value':np.ma.MaskedArray.tolist(v)
#             }
#     data=pd.DataFrame(result_dict)
#     data1=data[data['time']>=str(time[0])+'-01-01']
#     data1=data1[data1['time']<=str(time[1]+1)+'-01-01']
#     return data1

def main(argv):
    path ="./" 
    file=argv[0]
    nc_fid=getNC(path,file)

    #list all variables
    # print(nc_fid.variables)

    #list latitude and longitude
    alons = nc_fid.variables['lon'][:]
    alats = nc_fid.variables['lat'][:]

    #nearest latitude and longitude
    location = [120.2, 24.97] # the location of the farm in 中壢區
    lon_idx = np.abs(alons - location[0]).argmin()
    lat_idx = np.abs(alats - location[1]).argmin()
    # print(alons[lon_idx])
    # print(alats[lat_idx])

    #list date
    times = nc_fid.variables['time']
    dates = num2date(times[:],units=times.units,calendar=times.calendar)      
    str_time = [i.strftime("%Y-%m-%d %H:%M") for i in dates]

    #without pressure level
    v=nc_fid.variables[argv[2]][:, lat_idx, lon_idx]


    time = argv[1]
    result_dict={
                'lon':alons[lon_idx],
                'lat':alats[lat_idx],
                'time':str_time,
                'value':v.tolist()
                }
    data=pd.DataFrame(result_dict)
    data1=data[data['time']>=str(time[0])+'-01-01']
    data1=data1[data1['time']<=str(time[1]+1)+'-01-01']

    return data1

if __name__ == "__main__":
    import sys
    main(sys.argv)