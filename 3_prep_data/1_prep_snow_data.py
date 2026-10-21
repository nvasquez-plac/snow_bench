#!/usr/bin/env python

# This function is to extract SWE and SD data from different networks (including CanSWE) over a given time period.
# SWE and SD must be available in a netcdf format that corresponds to the CanSWE format. The data are then merged together to produce a single netcdf file that contains
# all the observed snow data over a given time period.
# We recommend the user to carry out the extraction over the period covering the whole water year of interest (From September 1st to August 31)
#
# Author: Vincent Vionnet  - vincent.vionnet(at)ec.gc.ca
#
# Example of use to extract snow data from the CANSWE database from 1 September 2019 to 31 July 2020
#   python 1_prep_snow_data.py -cf ../1_config/config_exp_CalDAS_MIST.py -src CANSWE -b 20190901 -e 20100731


from os import environ
import pdb
import os,sys
import numpy as np 
import pandas as pd 
import datetime as dt 
import xarray as xr
import argparse
import runpy
from types import SimpleNamespace
import util_extract as ext


parser = argparse.ArgumentParser(description="Prepare snow data from different sources for a specific period")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-src","--list_src", help="List of sources to consider among CANSWE, NHSWE, NORSWE",nargs='+',default=['CANSWE'])
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
args = parser.parse_args()


# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SimpleNamespace(**runpy.run_path(configfile))  # load_module() was removed in Python 3.15
cfg_exp = X.cfg_exp

dir_eval = X.dir_analysis
dir_store_snow = dir_eval+'/snow_data'

# Make if does not exist
os.makedirs(dir_eval,exist_ok=True)
os.makedirs(dir_store_snow,exist_ok=True)

# List of sources to consider
list_src = args.list_src

# Dates for which we want to extract the snow data
date_beg = args.date_beg
date_end = args.date_end

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2= SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15
dic_snow_db = X2.dic_snow_data


for isrc,src in enumerate(list_src):


    if(src not in dic_snow_db.keys()):
        print(src+' is an unknown source of snow data. Please check its name.')
        sys.exit()

    print('--------')
    print('Import snow data from database '+src)
    print('--------')

    data = dic_snow_db[src]['path']

    da_fin = xr.open_dataset(data)

    # Restrict the data to the dates needed for the evaluation
    start = dt.datetime(int(date_beg[0:4]), int(date_beg[4:6]), int(date_beg[6:8]))
    start= start - dt.timedelta(hours=24)
    end = dt.datetime(int(date_end[0:4]), int(date_end[4:6]), int(date_end[6:8]))
    da_fin = da_fin.loc[dict(time=slice(start,end))]

    # Identify stations with No SWE and No SD Data over the period of interest
    sta_id = da_fin.station_id.values.tolist()
    list_drop_both = []

    for sta in sta_id:
        if 'snw' in da_fin.data_vars:
            lswe = da_fin.snw.loc[dict(station_id=sta)].isnull().all().item()
        else: 
            lswe = False
        if 'snd' in da_fin.data_vars:
            lsd = da_fin.snd.loc[dict(station_id=sta)].isnull().all().item()
        else:
            lsd=False
        if(lswe and lsd):
            list_drop_both.append(sta)

    # Remove all the stations without SWE and SD
    if(len(list_drop_both)==len(sta_id)):
        print('No station with valid snow data found over the period '+date_beg+'-'+date_end+' for network: '+src)
        print('Please remove this network from the list of sources or adjust the dates')
        sys.exit()
    else:
        da_fin2=da_fin.where(~da_fin.station_id.isin(list_drop_both),drop=True)

            

    if(src=='CANSWE'):
        list_var_drop = ['data_flag_snw','data_flag_snd','qc_flag_snw','qc_flag_snd','merge_snw','merge_snd','update_2020','merge_key','station_name_sec','station_name_ter','station_id_sec','station_id_ter','RMD','RMD2']
        # Set time to 18 UTC (reference time for CanSWE)
        da_fin2.coords['time']=da_fin2.coords['time']+np.timedelta64(18,'h')
        da_fin2['network'] = xr.full_like(da_fin2.station_name, 'CANSWE')
        da_fin2['network'].attrs = {
        'long_name': 'snow_eval network identifier',
        'standard_name': 'network'}

        
    elif(src=='NHSWE'):
        da_fin2 = da_fin2.rename({'Elevation_NTK':'elevation'})
        list_var_drop = ['qco','gap','data_flag_snw','data_flag_snd']

        da_fin2['network'] = xr.full_like(da_fin2.station_name, 'NHSWE')
        da_fin2['network'].attrs = {
        'long_name': 'snow_eval network identifier',
        'standard_name': 'network'}

        # Remove data obtained from neural network and linear gap filling
        # See NHSWE paper for more info. 
        mask_nn = da_fin2.gap.values=='N'
        mask_ll = da_fin2.gap.values=='L'
        mask_gap = np.logical_or(mask_nn, mask_ll)
        for var in ['den','snd','snw']:
            da_fin2[var].values[mask_gap] = np.nan

        # Consider NHSWE SWE and density data as NaN since they do not correspond to observations
        da_fin2['snw']  = np.nan
        da_fin2['den']  = np.nan

        da_fin2['snd'] = da_fin2['snd']*0.01 # Convert SD from cm to m

       
                
    if(len(list_var_drop)>0):
        for var in list_var_drop:
            if var in da_fin2.data_vars:
                da_fin2 = da_fin2.drop_vars(var)

    if(isrc==0):
        xref = da_fin2
    else:
        xref = xr.concat([xref,da_fin2],dim='station_id') 

da_fin = xref.copy()

da_fin['source'] = da_fin.source.astype('<U64')
da_fin['network'] = da_fin.network.astype('<U64')
da_fin['station_name'] = da_fin.station_name.astype('<U64')

# Check for duplicates
duplicates = da_fin.indexes['station_id'].duplicated()
if duplicates.any():
    print("Found duplicates in station_id index")
da_fin = da_fin.sel(station_id=~duplicates)

print('Import completed for all databases')

# Remove stations in the black list
da_fin = da_fin.drop_sel(station_id=X2.station_black_list,errors='ignore')

# Remove stations without defined elevation 
list_sta_elev=[]
for ii,sta in enumerate(da_fin['station_id'].values):
    zs_sta = da_fin['elevation'].loc[dict(station_id=sta)].values   
    if(np.isnan(zs_sta)):
        list_sta_elev.append(sta)
da_fin = da_fin.drop_sel(station_id=list_sta_elev,errors='ignore')

# Remove duplicates in the following situations: 
#      - when NHWE is used and CANSWE are used
if( ('NHSWE' in list_src) and   ('CANSWE' in list_src)  ):
    print('Remove duplicates for NHSWE and CANSWE ')
    da_fin = ext.remove_duplicates_nhswe(da_fin,list_src)

# Remove stations from NHSWE without data in winter. 
if('NHSWE' in list_src):    
    print('Remove stations from NHSWE without data in winter')
    da_fin =ext.clean_nhswe(da_fin)

# Generate netcdf containing snow observations
netcdf_file_out= os.path.join(dir_store_snow,'snow_data.nc')
da_fin.to_netcdf(netcdf_file_out,format='NETCDF4')

print('------------------')
print('Preparation of observed snow data completed')
print('------------------')
