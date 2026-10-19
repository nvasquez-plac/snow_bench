import fstd2nc
from os import environ
import pdb
import os 
import numpy as np 
import pandas as pd 
import datetime as dt 
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import xarray as xr
from importlib.machinery import SourceFileLoader
import argparse
import util_score as util
import shutil
import cartopy
import cartopy.mpl.geoaxes
import cartopy.feature as cfeature
from mpl_toolkits.axes_grid1.inset_locator import inset_axes  
from multiprocessing import Pool, cpu_count

parser = argparse.ArgumentParser(description="Plot time series at the stations for different experiments and domains")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="Maximum elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-ref_exp_alti","--ref_exp_alti", help="Only use stations that match the elevation criteria for a specific experiment or all experiment ",nargs='+',default=[])
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-reg","--list_reg", help="List of domains used for the evaluation",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to be plotted ",nargs='+',default=['SMA'])
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
parser.add_argument("-add_vgh","--add_vgh", action='store_true',help="Add time series for the snow below high vegetation")
parser.add_argument("-n","--n_processes", help="Number of parallel processes (default: 1)", type=int, default=1)

args = parser.parse_args()

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SourceFileLoader('', configfile).load_module()
cfg_exp = X.cfg_exp

#Reference Directory
dir_eval = X.dir_analysis
dir_sto = dir_eval+'/snow/series'
dir_store_snow = dir_eval+'/snow_data'

os.makedirs(dir_eval+'/snow', exist_ok=True)

os.makedirs(dir_sto, exist_ok=True)

# Create symbolic link between dir_eval/snow and dir_html if the link does not exist already
if('dir_html' in X.__dict__):
    os.makedirs(os.path.dirname(X.dir_html),exist_ok=True)
    if(not os.path.islink(X.dir_html)):
        os.symlink(dir_eval+'/snow',X.dir_html)

# List of experiments of interest
list_exp=args.list_exp

# List of variables of interest
list_var = args.list_var

# List of regions to be considered
list_reg = args.list_reg

# Dates for which we want to plot the output
date_beg = args.date_beg
date_end = args.date_end

# Boolean to add time series below high veg
ladd_vgh = args.add_vgh
   
# Number of processes
n_processes = args.n_processes
#cpu_count()

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SourceFileLoader('', config_snow).load_module()
dic_var = X2.dic_var
dic_varname = X2.dic_varname
dic_units = X2.dic_var_units
dic_vgh = X2.dic_vgh

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

# Merge results from the different stations
for iexp,exp in enumerate(list_exp): 
    # netcdf file containing model extraction:
    netcdf_file_in =  dir_store_snow+'/res_snow_'+exp+'.nc'
    res = xr.open_dataset(netcdf_file_in)

    if(iexp==0):
        res_fin = res
    else:
        res_fin=xr.merge([res_fin,res],compat='override')

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

print(f"Using {n_processes} parallel processes for image generation")


for reg in list_reg:
    
    # Add mask that determines the location of the stations
    util.find_sta(reg,res_fin,X)
    mask=res_fin['mask_'+reg]

    if(ref_exp_alti): 
         mask= mask & mask_dif

    dir_sto_reg = dir_sto+'/'+reg
    os.makedirs(dir_sto_reg , exist_ok=True)

    for var in list_var:
        print(f"Processing region {reg}, variable {var}")
        
        # Prepare arguments for parallel processing
        tasks = []
        for ii, sta in enumerate(res_fin['station_id'].values[mask]):
            alt_sta = res_fin['elevation'].loc[dict(station_id=sta)].values
            lalti_ok = []
            
            for iexp, exp in enumerate(list_exp):
                alt_mod = res_fin['Elevation_'+exp].loc[dict(station_id=sta)].values
                if ref_exp_alti:
                    # Elevation criteria is already met
                    lalti_ok.append(True)
                else:
                    # Elevation criteria is applied individually for each experiment  
                    lalti_ok.append(np.abs(alt_mod-alt_sta) < max_alti)
            
            # Package arguments for the worker function
            task_args = (sta, var, reg, res_fin, cfg_exp, list_exp, date_beg, date_end, 
                       ladd_vgh, max_alti, lcheck_alti, ref_exp_alti, lalti_ok, 
                       dic_var,  dic_varname, dic_units, 
                       dic_vgh, dir_sto_reg)
            tasks.append(task_args)
        
        # Execute tasks in parallel
        if tasks:
            with Pool(processes=n_processes) as pool:
                if var not in ['TGRD','WSOL']:
                    results = pool.map(util.plot_station_timeseries, tasks)
                else: # Soil variables
                    results = pool.map(util.plot_station_timeseries_soil, tasks)
            
            # Print results summary
            successful = sum(1 for r in results if "Successfully created" in r)
            print(f"Completed {successful} plots for region {reg}, variable {var}")
            
            # Print any errors
            for result in results:
                if "Error" in result:
                    print(result)


    # Create html index to browse through the figures
    shutil.copyfile(X.dir_git+"/4_compute_score/create_index.sh", dir_sto_reg+'/create_index.sh')
    os.chdir(dir_sto_reg)
    os.system("chmod 755 create_index.sh")
    os.system("./create_index.sh")
    os.remove("create_index.sh")
