#!/usr/bin/env python

# This function is to compute error metrics for different sub-regions for selected time period
# The script handle different time periods: daily, bi-monthly, monthly, specific time period defined by beginning and end date
# The user can chose to compute score for all stations and/or to separate manual and automatic stations

# Author: Vincent Vionnet  - vincent.vionnet(at)ec.gc.ca
#
#
# Example of use to compute 2 scores (bias and RMSE) for the domain NorthAmericaEast extract snow data from 20 December 2019 to 20 February 2020
#python compute_score_snow_domain.py  -cf ../1_config/config_exp_CalDAS_MIST.py -exp OI MIST -var SD -reg NorthAmericaEast -sco bias rmse -freq period -b 20191220 -e 20200220


import os,shutil,pdb,sys
import datetime as dt
import numpy as np
import pandas as pd
import fstd2nc
import xarray as xr
from importlib.machinery import SourceFileLoader
import argparse
import util_score as util

parser = argparse.ArgumentParser(description="Compute scores for specific regions for different time period")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="Maximum elevation difference in m used to select the stations",default=150.,type=float)
parser.add_argument("-ref_exp_alti","--ref_exp_alti", help="Only use stations that match the elevation criteria for a specific experiment or all experiment ",nargs='+',default=[])
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-reg","--list_reg", help="List of domains used for the evaluation",nargs='+')
parser.add_argument("-t","--type_sta", help="Station type to be used when computing scores",choices=['auto','manual','all'],default='all')
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['day','month','bi-month','period'],default='bi-month')
parser.add_argument("-sco","--list_score", help="List of scores to compute ",nargs='+')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD, used if freq='period' or 'day'")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD, used if freq='period' or 'day'")
args = parser.parse_args()

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SourceFileLoader('', configfile).load_module()
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

# List of regions to be considered
list_reg = args.list_reg

# Type of station
type_sta=args.type_sta

# Score frequency
score_freq=args.score_freq

# Define dates and number of days to be considered to accumulate precip if month is not used
date_beg = args.date_beg
date_end = args.date_end

if(args.date_beg is None or args.date_end is None):
    print('date_end and/or date_beg must be defined')
    sys.exit()  


# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SourceFileLoader('', config_snow).load_module()
dic_var = X2.dic_var
dic_fac_max = X2.dic_fac_max


# Maximum elevation difference when plotting stations
max_alti =args.max_alti

#Only use stations that match the elevation criteria for a specific experiment or all experiments
ref_exp_alti =args.ref_exp_alti


if(ref_exp_alti):
    ref_exp = ref_exp_alti[0]
    if(ref_exp not in list_exp and ref_exp!='all'):
        print('ref_exp_alti is not correct. Please revise the value using an experiment among list_exp or use "all" to select stations that match the elevation criteria for all experiments')
        sys.exit()


# Determine if the altitude check can be activated
if(max_alti>0 ):
    lcheck_alti= True
else:
    lcheck_alti=False

# List of score to consider
if(args.list_score is None):
    list_score=['cor','bias','rmse','medae','nse','pbias','stde']
else: 
    list_score=args.list_score

# Add necessary variables
list_score = list_score + ['nobs','moyobs','moymod']

# Dates for which we want to compute the simulated values
date_beg = args.date_beg
date_end = args.date_end


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


# Define the list of dates to consider when computing the scores depending on the option selected by the user
ld_beg,ld_end,ld_mid = util.gen_date(score_freq,res_fin,date_beg,date_end)


# Create Xarray Structure to store scores
yy        = np.nan*np.empty((len(list_var), len(list_exp), len(list_reg), len(ld_mid)))

score_snw = xr.DataArray(yy, 
                        coords={'variable':list_var,'exp':list_exp,'domain':list_reg,'time':ld_mid},
                        dims=('variable','exp','domain','time'))
score_snw = score_snw.to_dataset(name=list_score[0])

# Add scores 
for ii, score in enumerate(list_score):
    if(ii>0):
        score_snw[score] = xr.full_like(score_snw[list_score[0]], fill_value=0)

# Create time stamp 
ll_stamp=[]

for idate,date_ref in enumerate(ld_mid):
    db = ld_beg[idate]
    de = ld_end[idate]
    ts = db.strftime("%Y%m%d")+'-'+de.strftime("%Y%m%d")
    ll_stamp.append(ts)

# Add time stamp to file containing scores
score_snw['time_stamp'] = xr.DataArray(np.array(ll_stamp),coords={'time':score_snw.time},dims=('time'))

# Compute elevation mask
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

# Loop over the regions
for reg in list_reg:

    # Add mask that determines the location of the stations
    util.find_sta(reg,res_fin,X)
    mask_reg=res_fin['mask_'+reg]

    for idate,date_ref in enumerate(ld_mid):
    
        db = ld_beg[idate]
        de = ld_end[idate]

        for var in list_var:
            for exp in list_exp:

                name_var = var+'_'+exp

                # Mask based on elevation
                if(not ref_exp_alti): 
                    if(lcheck_alti):# The elevation mask is specific to each experiment
                        mask_dif = (np.abs(res_fin['Elevation_'+exp].values-res_fin['elevation'].values)<max_alti)
                    else:  
                        mask_dif = np.full((len(res_fin.lat.values)), True)

                # Mask based on station type
                if(type_sta=='manual'):
                    mask_sta = (res_fin['type_mes'].values<=1)
                    mask_sel =  mask_dif & mask_sta
                elif(type_sta=='auto'):
                    mask_sta = [tt  in [2,3,4] for tt in res_fin['type_mes'].values]
                    mask_sel =  mask_dif & mask_sta
                else:
                    mask_sel = mask_dif
                    
                #Apply regional mask
                mask_sel = mask_sel & mask_reg

                # Extract simulated and observed data
                if(score_freq in ['bi-month','month'] and type_sta=='all'):
                    mod = res_fin[name_var].loc[dict(time=slice(db,de))].mean('time').values[mask_sel]
                    obs = res_fin[dic_var[var]].loc[dict(time=slice(db,de))].mean('time').values[mask_sel]
                else:
                    mod = res_fin[name_var].loc[dict(time=slice(db,de))].values[mask_sel,:]
                    obs = res_fin[dic_var[var]].loc[dict(time=slice(db,de))].values[mask_sel,:]
                            
                mod = mod.flatten()
                
                # Remove unrealistic model values (glacierized areas)
                mask_unreal = mod>dic_fac_max[var]
                mod[mask_unreal]=np.nan

                obs = obs.flatten()

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
                    if(nobs>5): # Compute score if enough valid pair of observed and simulated data are available
                        obs_sel = obs[mask_ok_obs]
                        mod_sel = mod[mask_ok]

                        score_snw[score].loc[(dict(variable=var,exp=exp,domain=reg,time=date_ref))] = util.compute_score(score,obs_sel,mod_sel)
                    else:
                        score_snw[score].loc[(dict(variable=var,exp=exp,domain=reg,time=date_ref))] = np.nan

for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp

# Generate Netcdf file containing scores
fic_out = dir_nc+'/score_snw_domain_'+type_sta+'_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+score_freq+'_'+date_beg+'_'+date_end+'.nc'
score_snw.to_netcdf(fic_out)

print('------------------')
print('Computation of scores completed')
print('------------------')
