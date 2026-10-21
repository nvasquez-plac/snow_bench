#!/usr/bin/env python

# This function is to compute error metrics per stations for selected time period
# The script handle different time periods: bi-monthly, monthly, specific time period defined by beginning and end date
#                                           accumulation period, melt period

# Author: Vincent Vionnet  - vincent.vionnet(at)ec.gc.ca
#


import os,shutil,pdb
import datetime as dt
import numpy as np
import pandas as pd
try:
    import fstd2nc  # ECCC lib, only needed to read FST files; does not build on macOS
except ImportError:
    fstd2nc = None
import xarray as xr
import runpy
from types import SimpleNamespace
import argparse
import util_score as util

parser = argparse.ArgumentParser(description="Compute scores at all stations for different time period")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="Maximum elevation difference in m used to select the stations",default=150.,type=float)
parser.add_argument("-ref_exp_alti","--ref_exp_alti", help="Only use stations that match the elevation criteria for a specific experiment or all experiment ",nargs='+',default=[])
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['month','bi-month','period','accu','melt'],default='period')
parser.add_argument("-sco","--list_score", help="List of scores to compute ",nargs='+')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD, used if freq='period'")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD, used if freq='period'")
#parser.add_argument("-explorer",dest='explorer', action='store_true',help="Prepare data for Snow Explorer visualisation tool")
parser.add_argument("-add_tpi",dest='add_tpi', action='store_true',help="Add Topographic Position Index")
args = parser.parse_args()

# Set explorer to False
#parser.set_defaults(explorer=False)

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SimpleNamespace(**runpy.run_path(configfile))  # load_module() was removed in Python 3.15
cfg_exp = X.cfg_exp

#Reference Directory
dir_eval = X.dir_analysis
dir_eval_snow = dir_eval+'/snow'
dir_nc = dir_eval_snow+'/fic_nc'
dir_store_snow = dir_eval+'/snow_data'

# Make if does not exist
os.makedirs(dir_eval,exist_ok=True)
os.makedirs(dir_eval_snow,exist_ok=True)
os.makedirs(dir_nc,exist_ok=True)

# List of experiments of interest
list_exp=args.list_exp

# List of variables of interest
list_var = args.list_var

# Score frequency
score_freq=args.score_freq

# Boolean to activate prearation of times series data for Snow Explorer
#lexplorer = args.explorer

# Boolean to add TPI in file containing scores
ladd_tpi = args.add_tpi

# Define beginning and end dated to compute scores
date_beg = args.date_beg
date_end = args.date_end

if(args.date_beg is None or args.date_end is None):
    print('date_end and/or date_beg must be defined')
    sys.exit()  

 
# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15
dic_var = X2.dic_var
dic_fac_max = X2.dic_fac_max

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Determine if the altitude check can be activated
if(max_alti>0 ):
    lcheck_alti= True
else:
    lcheck_alti=False

#Only use stations that match the elevation criteria for a specific experiment or all experiments
ref_exp_alti =args.ref_exp_alti    
if(ref_exp_alti):
    ref_exp = ref_exp_alti[0]
    if(ref_exp not in list_exp and ref_exp!='all'):
        print('ref_exp_alti is not correct. Please revise the value using an experiment among list_exp or use "all" to select stations that match the elevation criteria for all experiments')
        sys.exit()

# List of score to consider
if(args.list_score is None):
    list_score=['cor','bias','rmse','medae','nse','pbias','stde']
else: 
    list_score=args.list_score

# Add necessary variables
list_score = list_score + ['nobs','moyobs','moymod']
if 'rbias' in list_score:
    sys.exit('Relative bias is only available to calculate over the domain')


# List of variables added to the final xarray that contains the scores
list_var_add = ['lat','lon','elevation','type_mes','station_name','source','network']

# Merge results from the different stations
for iexp,exp in enumerate(list_exp): 

    # netcdf file containing model extraction:
    #netcdf_file_in = cfg_exp[exp]['dir_outall']+'/res_snow.nc'
    netcdf_file_in =  dir_store_snow+'/res_snow_'+exp+'.nc'
    res = xr.open_dataset(netcdf_file_in)

    if(iexp==0):
        res_fin = res
    else:
        res_fin=xr.merge([res_fin,res])

# Load file to ensure fast iteration through the list of stations
res_fin.load()

# Define the list of dates to consider when computing the scores depending on the option selected by the user
ld_beg,ld_end,ld_mid = util.gen_date(score_freq,res_fin,date_beg,date_end)

# Get list of stations
list_sta = res_fin.station_id

# Create Xarray Structure to store scores
yy=np.zeros((len(list_var),len(list_exp),len(list_sta),len(ld_mid)))
score_snw = xr.DataArray(yy,coords={'variable':list_var,'exp':list_exp,'station_id':list_sta,'time':ld_mid},
     dims=('variable','exp','station_id','time'))
score_snw = score_snw.to_dataset(name=list_score[0])

# Add scores 
for ii,score in enumerate(list_score):
    if(ii>0):
        score_snw[score] = xr.full_like(score_snw[list_score[0]],fill_value=0)

# Add auxiliary variables        
for var in list_var_add:
    score_snw[var] = res_fin[var]

# Create time stamp 
ll_stamp=[]

for idate,date_ref in enumerate(ld_mid):
    db = ld_beg[idate]
    de = ld_end[idate]
    ts = db.strftime("%Y%m%d")+'-'+de.strftime("%Y%m%d")
    ll_stamp.append(ts)

     

# Compute elevation mask when ref_exp_alti is defined
if(ref_exp_alti and lcheck_alti): # The elevation mask is computed for all experiments
    ref_exp = ref_exp_alti[0]
    if(ref_exp=='all'):
        for iexp,exp in enumerate(list_exp):
            if(iexp==0):
                mask_dif = (np.abs(res_fin['Elevation_'+exp].values-res_fin['elevation'].values)<max_alti)
            else:
                mask_dif = mask_dif & (np.abs(res_fin['Elevation_'+exp].values-res_fin['elevation'].values)<max_alti)
    else:
        mask_dif = (np.abs(res_fin['Elevation_'+ref_exp].values-res_fin['elevation'].values)<max_alti)

# Compute score at stations
for idate,date_ref in enumerate(ld_mid):

    db = ld_beg[idate]
    de = ld_end[idate]

    for var in list_var:
        for exp in list_exp:

            name_var = var+'_'+exp

            # Mask based on elevation when ref_exp_alti not defined
            if(not ref_exp_alti):   # The elevation mask is specific to each experiment          
                if(lcheck_alti):
                    mask_dif = (np.abs(res_fin['Elevation_'+exp].values-res_fin['elevation'].values)<max_alti)
                else:  
                    mask_dif = np.full((len(res_fin.lat.values)), True)

            # Loop over the stations
            for ista,sta in enumerate(list_sta):
                if(mask_dif[ista]):

                    # Update dates to correspond to the station of interest when accu or melt options are used
                    obs_full = res_fin[dic_var[var]].loc[dict(station_id=sta)]
                    if(score_freq=='accu'):
                       # print(sta.values,var)
                        db,de = util.get_date_accu(obs_full,sta,db,de,dic_var[var],res_fin['type_mes'].loc[dict(station_id=sta)] )
                       # print(sta.values,db,de,var)
                    elif(score_freq=='melt'):
                        db,de = util.get_date_melt(res_fin,sta,db,de,dic_var[var],res_fin['type_mes'].loc[dict(station_id=sta)] )

                    # Extract observed and simulated values
                    mod = res_fin[name_var].loc[dict(station_id=sta,time=slice(db,de))].values[:,]
                    obs = res_fin[dic_var[var]].loc[dict(station_id=sta,time=slice(db,de))].values[:,]

                    # Remove unrealistic model values (glacierized areas)
                    mask_unreal = mod>dic_fac_max[var]
                    mod[mask_unreal]=np.nan

                    # Define mask where observations and simulations are valid (not nan)
                    mask_obs = np.isnan(obs)
                    mask_mod =  np.isnan(mod)
                    mask_ok = ~mask_obs& ~mask_mod

                    if(len(mask_mod.shape)>1): # Ensemble
                        nobs = int(np.sum(mask_ok)/len(mask_mod))
                        mask_ok_obs = mask_ok[0,:]
                    else: 
                        nobs = np.sum(mask_ok)
                        mask_ok_obs = mask_ok


                    for score in list_score:
                        if(nobs>0): # Compute score if enough valid pair of observed and simulated data are available
                            obs_sel = obs[mask_ok_obs]
                            mod_sel = mod[mask_ok]

                            score_snw[score].loc[(dict(variable=var,exp=exp,station_id=sta))] = util.compute_score(score,obs_sel,mod_sel)

                        else:
                            score_snw[score].loc[(dict(variable=var,exp=exp,station_id=sta))] = np.nan

                else:
                    for score in list_score:
                        score_snw[score].loc[(dict(variable=var,exp=exp,station_id=sta))] = np.nan

# Remove stations that contains only NaN values for all scores amd all experiments:
#    - stations without any observations over the period of interest
#    - stations outside the simulation domain
#    - stations that do not meet the elevation criteria
list_drop = util.list_empty_stations(score_snw)

# Remove all the stations without valid experiements and observations
score_snw = score_snw.load()
score_snw=score_snw.where(~score_snw.station_id.isin(list_drop),drop=True)

# Add time stamp to file containing scores
score_snw['time_stamp'] = xr.DataArray(np.array(ll_stamp),coords={'time':score_snw.time},dims=('time'))  

# Add topographic position index
dtpi = 10 # in km
if(ladd_tpi):
    util.add_tpi(score_snw,dtpi)

for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp

# Generate Netcdf file containing scores
score_snw['station_name'] = score_snw.station_name.astype('<U64')

comp = dict(zlib=True, complevel=4)
encoding = {var: comp for var in score_snw.data_vars}
string_vars = ['source', 'network', 'station_name','time_stamp']
for v in string_vars:
  if v in encoding:
    encoding[v] = {}
fic_out = dir_nc+'/score_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+score_freq+'_'+date_beg+'_'+date_end+'.nc'
score_snw.to_netcdf(fic_out,format='NETCDF4', encoding=encoding)

# Check if the file exists
if os.path.isfile(fic_out):
    print(f"File '{fic_out}' was created successfully.")
else:
    print(f"File '{fic_out}' was not created.")
    
# Create file containing time series for Snow Explorer 
#if(lexplorer):
#    fic_out = dir_nc+'/series_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+score_freq+'_'+date_beg+'_'+date_end+'.nc'
#    util.prep_data_explorer(res_fin,list_var,list_exp,list_drop,X2,fic_out,cfg_exp)
    
#    # Check if the file exists
#    if os.path.isfile(fic_out):
#        print(f"File '{fic_out}' was created successfully.")
#    else:
#        print(f"File '{fic_out}' was not created.")
        
    

print('------------------')
print('Computation of scores completed')
print('------------------')
