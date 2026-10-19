import fstd2nc
from os import environ
import pdb
import os, sys, glob 
import numpy as np 
import pandas as pd 
import datetime as dt 
import xarray as xr
from importlib.machinery import SourceFileLoader
import argparse
import util_extract as ext
from joblib import Parallel, delayed
import multiprocessing

parser = argparse.ArgumentParser(description="Extract snow variables at the location of the stations for different SVS2 experiments")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-d","--dist_crit", help="Critical distance in km used to remove stations from the analysis",default=3,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-elev_4near",dest='elev_4near', action='store_true',help="Select the grid point with the smallest elevation difference among the 4 nearest grid points. Otherwise, the nearest grid point is used")
parser.add_argument("-n", "--n_jobs", help="Number of parallel jobs (-1: all CPUs, -2: all but one, 1: serial)", default=10, type=int)
args = parser.parse_args()

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SourceFileLoader('', configfile).load_module()
cfg_exp = X.cfg_exp

# List of experiments of interest
list_exp = args.list_exp

# List of variables of interest
list_var = args.list_var

crit_dis = args.dist_crit

# Key to activate a different method to select the grid point corresponding to the station 
lelev_4near = args.elev_4near

# Number of parallel jobs
n_jobs = args.n_jobs
parallel_mode = 'both'

dir_eval = X.dir_analysis
dir_store_snow = dir_eval + '/snow_data'

# Load config file
config_snow = X.dir_git + "/1_config/config_snow.py"
# Load info in config file
X2 = SourceFileLoader('', config_snow).load_module()

# Open file containing snow variables
netcdf_file_in = os.path.join(dir_store_snow, 'snow_data.nc')


def process_single_year(yy, exp, exp_config, list_var, list_var_mod, str_var, 
                       netcdf_file_in, xgeo_dict, zs, config_snow_path, crit_dis, 
                       ll_pos, dist_sta, station_ids,
                       lelev_4near=False):
    """
    Process a single year of data for one experiment.
    
    Returns:
    --------
    dict with 'success', 'year', and 'data' or 'error'
    """
    try:
        print(f"[{exp}][Year {yy}] Starting processing")
        
        # Load config module in this process
        from importlib.machinery import SourceFileLoader
        X2 = SourceFileLoader('', config_snow_path).load_module()
        
        # Load observations in this process
        data_obs = xr.open_dataset(netcdf_file_in)

        # Load SVS2 file for a given year
        files = glob.glob(exp_config['dir_outall'] + '/svs2*' + str(yy) + '*nc')
        files.sort()
           
        if not files:
            return {'success': False, 'year': yy, 'error': 'No files found'}

        x = xr.open_mfdataset(exp_config['dir_outall'] + '/svs2*' + str(yy) + '*nc')

        if 'time' not in x.coords and 'time' not in x.dims:
            return {'success': False, 'year': yy, 'error': 'No time dimension found'}
        
        if zs.shape[0] != len(x.rlat) or zs.shape[1] != len(x.rlon):
            return {'success': False, 'year': yy, 'error': 'Grid size mismatch'}
        
        if 'offset' in exp_config.keys():
            x = ext.apply_time_offset(x, exp_config['offset'])

        date_b = dt.datetime(yy, 1, 1)
        date_e = dt.datetime(yy + 1, 1, 1)
        if 'offset' in exp_config.keys():
            date_b = dt.datetime(yy, 1, 1) + dt.timedelta(hours=exp_config['offset'])

        # Create dataset to store the extracted data
        data_obs_time = data_obs.sel(time=slice(date_b, date_e))
        for var in list_var_mod:
           data_obs_time[var] = xr.full_like(data_obs_time.snw, fill_value=np.nan)
 
        # Add variable containing elevation                
        data_obs_time['Elevation_' + exp] = xr.full_like(data_obs_time.station_id, fill_value=np.nan)

        # Find date in common between model and obs
        com_time = np.intersect1d(x.time, data_obs_time.time)
        if len(com_time) == 0:
            return {'success': False, 'year': yy, 'error': 'No common time found'}
        
        for var in list_var:
            name_var = var + '_' + exp
            var_ext = var
            var_mod_sel = x[var_ext].loc[dict(time=com_time)].values
            
            # Set Nan values 
            mask_nosnow = (var_mod_sel == -999)
            var_mod_sel[mask_nosnow] = np.nan
            
            # Loop over station and extract corresponding grid cel
            for ii, sta in enumerate(station_ids):
                if dist_sta[ii] < crit_dis:
                    ij = ll_pos[ii]
                    data_obs_time[name_var].loc[dict(time=com_time, station_id=sta)] = var_mod_sel[:, ij[0], ij[1]]
        
        for ii, sta in enumerate(station_ids):
            if dist_sta[ii] < crit_dis:
                ij = ll_pos[ii]
                data_obs_time['Elevation_' + exp].loc[dict(station_id=sta)] = zs[ij[0], ij[1]]

        # Remove density for snowpack less than 10 mm
        dic_density = {'DNA':'SMA','SNDN':'SML','SVDN':'SMH'}
        for var in ['DNA','SNDN','SVDN']:
            if(var in list_var):
                name_swe = dic_density[var]+'_'+exp
                data_obs_time[var+'_'+exp] = xr.where(data_obs_time[name_swe] >10.,data_obs_time[var+'_'+exp],np.nan)
                
        print(f"[{exp}][Year {yy}] Completed")
        
        return {
            'success': True,
            'year': yy,
            'data': data_obs_time
        }
    
    except Exception as e:
        print(f"[{exp}][Year {yy}] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'year': yy, 'error': str(e)}


def process_experiment(exp, cfg_exp_all, list_var, crit_dis, lelev_4near, 
                      netcdf_file_in, config_snow, dir_store_snow,
                      n_jobs_years):
    """
    Process a single experiment (potentially parallelizing over years).
    
    Parameters:
    -----------
    exp : str
        Experiment name
    cfg_exp_all : dict
        All experiment configurations
    list_var : list
        Variables to extract
    crit_dis : float
        Critical distance
    lelev_4near : bool
        Use 4-nearest neighbor
    netcdf_file_in : str
        Path to observation file
    config_snow : str
        Path to config_snow.py
    dir_store_snow : str
        Directory to store output
    n_jobs_years : int
        Number of parallel jobs for years
    
    Returns:
    --------
    dict with experiment results
    """
    try:
        print(f"\n{'='*70}")
        print(f"Processing experiment: {exp}")
        print(f"{'='*70}\n")
        
        # Load observations
        data_obs = xr.open_dataset(netcdf_file_in)
        
        exp_config = cfg_exp_all[exp]
        
        os.chdir(exp_config['dir_outall'])
        
        # Determine years
        list_fic = glob.glob('svs2*')
        list_fic.sort()
        fic_beg = list_fic[0].replace('svs2_', '')
        yy_beg = max(int(fic_beg[0:4]), pd.to_datetime(data_obs.time.values).year.min())
        fic_end = list_fic[-1].replace('svs2_', '')
        yy_end = min(int(fic_end[0:4]) + 1, pd.to_datetime(data_obs.time.values).year.max() + 1)
        
        list_year = np.arange(yy_beg, yy_end, 1)
        
        print(f"Years to process: {yy_beg} to {yy_end-1} ({len(list_year)} years)")
        
        
        list_var_mod = []
        str_var = ''
        for ivar, var in enumerate(list_var):
            if ivar == 0:
                str_var = var
            else:
                str_var = str_var + ',' + var
            
            list_var_mod.append(var + '_' + exp)
        

        # Open file containing elevation 
        xgeo = xr.open_dataset(cfg_exp[exp]['fic_geo'])
        zs = xgeo[cfg_exp[exp]['var_geo']].values
        
        xgeo_dict = {
            'lat': xgeo.lat.values,
            'lon': xgeo.lon.values,
            'shape': xgeo.lat.shape
        }
        
        # Station matching
        data_sta = data_obs[['lon', 'lat', 'station_name']].to_dataframe().reset_index()
        data_mod = xgeo[['lon', 'lat']].to_dataframe().reset_index()
        data_mod['lon'] = data_mod['lon'] - 360.
        
        sta_obs = np.transpose(np.vstack((data_sta['lon'], data_sta['lat'])))
        grid_mod = np.transpose(np.vstack((data_mod['lon'], data_mod['lat'])))
        
        if lelev_4near:
            kn = [1, 2, 3, 4]
        else:
            kn = 1
        
        dists, indexes = ext.get_nearest_ckdt(sta_obs, grid_mod, kn)
        ind_sta = np.unravel_index(indexes, xgeo.lon.shape)
        
        ll_pos = []
        dist_sta = []
        
        for ii, sta in enumerate(data_obs['station_id'].values):
            data_sta_single = data_obs.loc[dict(station_id=sta)]
            
            if lelev_4near:
                ij_ref = [ind_sta[0][ii][0], ind_sta[1][ii][0]]
                dist_ref = ext.haversine_cst_lat(data_sta_single.lat.values, dists[ii][0])
            else:
                ij_ref = [ind_sta[0][ii], ind_sta[1][ii]]
                dist_ref = ext.haversine_cst_lat(data_sta_single.lat.values, dists[ii])
            
            if dist_ref < crit_dis:
                if lelev_4near:
                    zs_sta = data_obs['elevation'].loc[dict(station_id=sta)]
                    zs_4near = []
                    for inear in np.arange(0, 4):
                        zs_4near.append(zs[ind_sta[0][ii][inear], ind_sta[1][ii][inear]])
                    ind_min = np.argmin(np.abs(zs_4near - zs_sta.values))
                    ij_ref = [ind_sta[0][ii][ind_min], ind_sta[1][ii][ind_min]]
                    dist_ref = ext.haversine_cst_lat(data_sta_single.lat.values, dists[ii][ind_min])
            
            ll_pos.append(ij_ref)
            dist_sta.append(dist_ref)
        
        station_ids = data_obs['station_id'].values
        
        # Process years
        print(f"Processing {len(list_year)} years with {n_jobs_years} cores")
        
        results = Parallel(n_jobs=n_jobs_years, verbose=5, backend='loky')(
            delayed(process_single_year)(
                yy, exp, dict(exp_config), list_var, list_var_mod, str_var,
                netcdf_file_in, xgeo_dict, zs, config_snow, crit_dis, 
                ll_pos, dist_sta, station_ids,
                lelev_4near
            )
            for yy in list_year
        )
        
        successful_results = []
        failed_years = []
        
        for result in results:
            if result['success']:
                successful_results.append(result['data'])
            else:
                failed_years.append((result['year'], result.get('error', 'Unknown error')))
        
        if failed_years:
            print(f"\nWarning: {len(failed_years)} year(s) failed:")
            for year, error in failed_years[:5]:  # Show first 5
                print(f"  Year {year}: {error}")
        
        if not successful_results:
            return {'success': False, 'exp': exp, 'error': 'No valid years'}
        
        # Concatenate years
        print(f"\nConcatenating {len(successful_results)} years...")
        data_fin = xr.concat(successful_results, dim='time', data_vars='minimal')
        
        _, index = np.unique(data_fin['time'], return_index=True)
        data_fin = data_fin.isel(time=index)
        

        # Save
        data_fin['source'] = data_fin.source.astype('<U64')
        data_fin['network'] = data_fin.network.astype('<U64')
        data_fin['station_name'] = data_fin.station_name.astype('<U64')
        data_fin['Elevation_' + exp] = data_fin['Elevation_' + exp].astype('float')
        
        comp = dict(zlib=True, complevel=4)
        encoding = {var: comp.copy() for var in data_fin.data_vars}
        string_vars = ['source', 'network', 'station_name']
        for v in string_vars:
            if v in encoding:
                encoding[v] = {}
        netcdf_file_out = dir_store_snow + '/res_snow_' + exp + '.nc'
        data_fin.to_netcdf(netcdf_file_out, format='NETCDF4', encoding=encoding)
        
        print(f"\n{'='*70}")
        print(f"✓ Completed: {exp}")
        print(f"  Output: {netcdf_file_out}")
        print(f"  Years: {len(successful_results)}/{len(list_year)}")
        print(f"{'='*70}\n")
        
        return {
            'success': True,
            'exp': exp,
            'output_file': netcdf_file_out,
            'n_years': len(successful_results),
            'failed_years': failed_years
        }
        
    except Exception as e:
        print(f"\n[{exp}] EXPERIMENT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'exp': exp, 'error': str(e)}


# ==============================================================
# MAIN EXECUTION
# ==============================================================

# Determine parallelization strategy
if n_jobs == -1:
    n_jobs_total = multiprocessing.cpu_count()
elif n_jobs == -2:
    n_jobs_total = max(1, multiprocessing.cpu_count() - 1)
elif n_jobs == 1:
    n_jobs_total = 1
else:
    n_jobs_total = max(1, min(n_jobs, multiprocessing.cpu_count()))

print(f"\n{'='*70}")
print(f"PARALLEL PROCESSING CONFIGURATION")
print(f"{'='*70}")
print(f"Total CPUs available: {multiprocessing.cpu_count()}")
print(f"CPUs to use: {n_jobs_total}")
print(f"Parallelization mode: {parallel_mode}")
print(f"Number of experiments: {len(list_exp)}")

if parallel_mode == 'experiments':
    # Parallelize over experiments only
    n_jobs_exp = n_jobs_total
    n_jobs_years = 1
    print(f"  - Experiments in parallel: {n_jobs_exp}")
    print(f"  - Years processed serially within each experiment")
    
elif parallel_mode == 'years':
    # Parallelize over years only (original behavior)
    n_jobs_exp = 1
    n_jobs_years = n_jobs_total
    print(f"  - Experiments processed serially")
    print(f"  - Years in parallel within each experiment: {n_jobs_years}")
    
else:  # 'both'
    # Split cores between experiments and years
    n_exp = len(list_exp)
    if n_exp >= n_jobs_total:
        # More experiments than cores: parallelize experiments only
        n_jobs_exp = n_jobs_total
        n_jobs_years = 1
        print(f"  - Experiments in parallel: {n_jobs_exp}")
        print(f"  - Years processed serially (too many experiments)")
    else:
        # Distribute cores: some for experiments, rest for years
        n_jobs_exp = min(n_exp, max(1, n_jobs_total // 2))
        n_jobs_years = max(1, n_jobs_total // n_jobs_exp)
        print(f"  - Experiments in parallel: {n_jobs_exp}")
        print(f"  - Years in parallel within each experiment: {n_jobs_years}")

print(f"{'='*70}\n")

# Execute based on strategy
if n_jobs_exp > 1:
    # Parallel over experiments
    print("Processing experiments in parallel...\n")
    
    exp_results = Parallel(n_jobs=n_jobs_exp, verbose=10, backend='loky')(
        delayed(process_experiment)(
            exp, cfg_exp, list_var, crit_dis, lelev_4near,
            netcdf_file_in, config_snow, dir_store_snow,
            n_jobs_years
        )
        for exp in list_exp
    )
    
else:
    # Serial over experiments (original loop)
    print("Processing experiments serially...\n")
    
    exp_results = []
    for exp in list_exp:
        result = process_experiment(
            exp, cfg_exp, list_var, crit_dis, lelev_4near,
            netcdf_file_in, config_snow, dir_store_snow,
            n_jobs_years
        )
        exp_results.append(result)

# Summary
print(f"\n{'='*70}")
print("PROCESSING SUMMARY")
print(f"{'='*70}")

successful_exps = [r for r in exp_results if r['success']]
failed_exps = [r for r in exp_results if not r['success']]

print(f"\nTotal experiments: {len(list_exp)}")
print(f"Successful: {len(successful_exps)}")
print(f"Failed: {len(failed_exps)}")

if successful_exps:
    print(f"\n{'─'*70}")
    print("SUCCESSFUL EXPERIMENTS:")
    print(f"{'─'*70}")
    for result in successful_exps:
        print(f"  ✓ {result['exp']}")
        print(f"    Output: {result['output_file']}")
        print(f"    Years: {result['n_years']}")
        if result['failed_years']:
            print(f"    Failed years: {len(result['failed_years'])}")

if failed_exps:
    print(f"\n{'─'*70}")
    print("FAILED EXPERIMENTS:")
    print(f"{'─'*70}")
    for result in failed_exps:
        print(f"  ✗ {result['exp']}: {result.get('error', 'Unknown error')}")

print(f"\n{'='*70}")
print("✓ ALL PROCESSING COMPLETED")
print(f"{'='*70}\n")
