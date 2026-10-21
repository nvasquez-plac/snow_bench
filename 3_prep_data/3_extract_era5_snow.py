try:
    import fstd2nc  # ECCC lib, only needed to read FST files; does not build on macOS
except ImportError:
    fstd2nc = None
from os import environ
import pdb
import os 
import numpy as np 
import pandas as pd 
import datetime as dt 
import xarray as xr
import runpy
from types import SimpleNamespace
import argparse
import util_extract as ext

parser = argparse.ArgumentParser(description="Extract snow variables at the location of the stations for ERA-5")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-d","--dist_crit", help="Critical distance in km used to remove stations from the analysis",default=3,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-elev_4near",dest='elev_4near', action='store_true',help="Select the grid point with the smallest elevation difference among the 4 nearest grid points")
parser.add_argument("-b","--date_beg", help="Beginning date for extraction, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date for extraction,, format YYYYMMDD")
#parser.add_argument("-mask_mtn",dest='mask_mtn', action='store_true',help="Add masks for mountainous regions")
#parser.add_argument("-mask_eco",dest='mask_eco', action='store_true',help="Add masks for ecozones")


args = parser.parse_args()

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SimpleNamespace(**runpy.run_path(configfile))  # load_module() was removed in Python 3.15
cfg_exp = X.cfg_exp

# List of experiments of interest
list_exp=args.list_exp

# List of variables of interest
list_var = args.list_var

crit_dis = args.dist_crit

# Key to activate a different method to select the grid point correspondingt to the station 
lelev_4near = args.elev_4near

# Option to generate add mask : Not available at the moment
lmask_mtn = False#args.mask_mtn
lmask_eco = False#args.mask_eco

# Dates for which we want to extract the snow data
date_beg = args.date_beg
date_end = args.date_end

dir_eval = X.dir_analysis
dir_store_snow = dir_eval+'/snow_data'

# Define the years to use for the extraction
yy_beg = int(date_beg[0:4])
yy_end = int(date_end[0:4])+1 

list_year=np.arange(yy_beg,yy_end,1)


#if(lmask_mtn):
#   if('fic_mtn' in cfg_exp[exp].keys()):
#      b2 = fstd2nc.Buffer(cfg_exp[exp]['fic_mtn'],vars='MASK', subgrid_axis=True,ignore_etiket=True)
#      xmtn = b2.to_xarray()
#      xmtn = xmtn.reindex(lat=xmtn.lat[::-1])
#      mtn = xmtn['MASK'].values
#   else:
#      print('fic_mtn must be defined for exp: '+exp)
#      quit()
#
#if(lmask_eco):
#   if('fic_eco' in cfg_exp[exp].keys()):
#      b2 = fstd2nc.Buffer(cfg_exp[exp]['fic_eco'],vars='MASK', subgrid_axis=True,ignore_etiket=True)
#      xeco = b2.to_xarray()
#      xeco = xeco.reindex(lat=xeco.lat[::-1])
#      eco = xeco['MASK'].values
#   else:
#      print('fic_eco must be defined for exp: '+exp)
#      quit()

for exp in list_exp:

    # Create list of variables
    list_var_mod = []
    str_var=''
    for ivar,var in enumerate(list_var):
        if(ivar==0):
            str_var = var
        else:
            str_var = str_var+ ','+var
        list_var_mod.append(var+'_'+exp)

    # Open file containing elevation 
    xgeo = xr.open_dataset(cfg_exp[exp]['fic_geo'])
    zs = xgeo[cfg_exp[exp]['var_geo']].values

    for iyear,yy in enumerate(list_year):
        print (yy,iyear)

        # Extract ERA5 data
        x = xr.open_mfdataset(cfg_exp[exp]['dir_in']+'/*'+str(yy)+'.nc')

        # Rename variables:
        x = x.rename({'sd':'SMA','sde':'SDA','rsn':'DNA'})

        # Add SD variable to make sure ISBA can be evaluated VS ERA5-Land
        x['SD'] = x['SDA'].copy()

        # Add variable for open and forest to allow comparison with the different snowpacks in SVS1 and SVS2
        x['SML'] = x['SMA'].copy()
        x['SMH'] = x['SMA'].copy()
        x['SNDP'] =x['SDA'].copy()
        x['SVDP'] =x['SDA'].copy()

        # Adjust simulation hour to match observation hour
        if('offset' in cfg_exp[exp].keys()):
            offset = cfg_exp[exp]['offset']
            x.coords['time']=x.coords['time']+np.timedelta64(offset,'h')

        # Extract position and create 2d lat and lon fields
        lon,lat = np.meshgrid(x.longitude.values,x.latitude.values)
        x['lat'] = xr.DataArray(lat,coords={'latitude':x.latitude,'longitude':x.longitude}, dims=['latitude','longitude'])
        x['lon'] = xr.DataArray(lon,coords={'latitude':x.latitude,'longitude':x.longitude}, dims=['latitude','longitude'])

        # Prepare the lat/lon file for the nearest neighbor extraction
        latlon_simu = np.dstack((x.lat,x.lon))

        # Read observations in NetCDF Format
        netcdf_file_in= os.path.join(dir_store_snow,'snow_data.nc')
        data_obs = xr.open_dataset(netcdf_file_in)

        # Extract observations for relevant time period  
        date_b = dt.datetime(yy,1,1)
        date_e = dt.datetime(yy+1,1,1)
        data_obs_time = data_obs.sel(time=slice(date_b,date_e))

        # Add variables to store model output at stations locations
        for var in list_var_mod:
            data_obs_time[var] = xr.full_like(data_obs_time.snw,fill_value=np.nan)
        data_obs_time['Elevation_'+exp] =  xr.full_like(data_obs_time.station_id,fill_value=np.nan)

#  if lmask_mtn:
#    for reg in np.arange(1,12):
#      data_obs_time['mask_mtn_'+str(reg)] =  xr.full_like(data_obs_time.station_id,fill_value=np.nan)
#
#  if lmask_eco:
#    for reg in np.arange(1,13):
#      data_obs_time['mask_eco_'+str(reg)] =  xr.full_like(data_obs_time.station_id,fill_value=np.nan)


        # Determine time in common between observations and model simulations
        com_time = np.intersect1d(x.time, data_obs_time.time)
        if len(com_time)==0:
            raise ValueError("no common time found with experience: "+exp)
    
        # Look for nearest neighbor (only needed for 1st year)
        if(iyear==0): 
            # Determine the position of the closest grid points
            ll_pos = []
            dist_sta = []

            # Organize data to provide input to the ckdtree to find nearest neighbor
            data_sta = data_obs_time[['lon', 'lat', 'station_name']].to_dataframe().reset_index()
            data_mod = x[['lon', 'lat']].to_dataframe().reset_index()
            data_mod['lon'] = data_mod['lon'] 

            sta_obs=np.transpose(np.vstack((data_sta['lon'],data_sta['lat'])))
            grid_mod=np.transpose(np.vstack((data_mod['lon'],data_mod['lat'])))

            # Get nearest neighbor and distance between each station and the grid
            if lelev_4near:
                kn = [1,2,3,4]
            else:
                kn=1

            dists, indexes = ext.get_nearest_ckdt(sta_obs,grid_mod,kn)

            # Get indexes i, j of the nearest neighbors 
            ind_sta = np.unravel_index(indexes, x.lon.shape)

        # Loop over stations to extract the corresponding grid point
            for ii,sta in enumerate(data_obs['station_id'].values):
                data_sta = data_obs_time.loc[dict(station_id=sta)]

                if lelev_4near:
                    # Define default reference point that will be modified if the station is within the domain
                    ij_ref=[ind_sta[0][ii][0],ind_sta[1][ii][0]]
                    dist_ref = ext.haversine_cst_lat(data_sta.lat.values,dists[ii][0])
                else:
                    ij_ref=[ind_sta[0][ii],ind_sta[1][ii]]
                    dist_ref = ext.haversine_cst_lat(data_sta.lat.values,dists[ii])

                if(dist_ref<crit_dis):

                    if(lelev_4near):   
                        zs_sta = data_obs_time['elevation'].loc[dict(station_id=sta)]

                        # Extract elevation from the 4 nearest points
                        zs_4near = []
                        for inear in np.arange(0,4):
                            zs_4near.append(zs[0,ind_sta[0][ii][inear],ind_sta[1][ii][inear]])

                        # Find the nearest point in elevation among the 4 nearest grid points and use this point as the reference.  
                        ind_min = np.argmin(np.abs(zs_4near-zs_sta.values))

                        ij_ref=[ind_sta[0][ii][ind_min],ind_sta[1][ii][ind_min]]
                        dist_ref = ext.haversine_cst_lat(data_sta.lat.values,dists[ii][ind_min])

        #         if lmask_mtn:
        #           for reg in np.arange(1,12):
        #             data_obs_time['mask_mtn_'+str(reg)].loc[dict(station_id=sta)] = mtn[reg-1,ij_ref[0],ij_ref[1]]
        #
        #         if lmask_eco:
        #           for reg in np.arange(1,13):
        #             data_obs_time['mask_eco_'+str(reg)].loc[dict(station_id=sta)] = eco[reg-1,ij_ref[0],ij_ref[1]]

                ll_pos.append(ij_ref)
                dist_sta.append(dist_ref) 


        # Extract Elevation
        for ii,sta in enumerate(data_obs['station_id'].values):
            if(dist_sta[ii]<crit_dis):
                ij = ll_pos[ii]
                data_obs_time['Elevation_'+exp].loc[dict(station_id=sta)] = zs[ij[0],ij[1]]

        # Extract time-dependant variables
        mask_time = [s in com_time for s in x.time.values]
        for var in list_var:
            name_var = var+'_'+exp
          # Keep only the simulations dates in common with the observations. 
        #  var_mod_sel = var_mod[var][mask_time,:,:]
            var_mod_sel = x[var].loc[dict(time=com_time)].values
            if(var in ['SMA','SML','SMH']):
                var_mod_sel = var_mod_sel *1000. # Convert from m to kg/m2 
            #if(var in ['SDA','SD','SNDP','SVDP'] ):
            if(var in ['SD','SNDP','SVDP'] ):
                var_mod_sel = var_mod_sel *100. # Convert from m to cm to be consistent with fst files 
                                                # This need to done in a different place in a future version of snow_eval. 

            # Mask out region where snow cover is not defined (water bodies, ...)
            mask_nosnow = (var_mod_sel==-999)
            var_mod_sel[mask_nosnow] = np.nan

            # Extract variable of interest at data where observations are available. 
            for ii,sta in enumerate(data_obs['station_id'].values):
                if(dist_sta[ii]<crit_dis):
                    ij = ll_pos[ii]
                    data_obs_time[name_var].loc[dict(time=com_time,station_id=sta)] = var_mod_sel[:,ij[0],ij[1]]

        if(iyear==0):
            data_fin = data_obs_time
        else:
            data_fin = xr.concat([data_fin,data_obs_time],dim='time',data_vars='minimal')

    # Save netcdf
    data_fin['Elevation_'+exp] = data_fin['Elevation_'+exp].astype('float')

    comp = dict(zlib=True, complevel=8)
    encoding = {var: comp for var in data_fin.data_vars}
    string_vars = ['source', 'network', 'station_name','time_stamp']
    for v in string_vars:
        if v in encoding:
            encoding[v] = {}
    netcdf_file_out =  dir_store_snow+'/res_snow_'+exp+'.nc'
    data_fin.to_netcdf(netcdf_file_out,format='NETCDF4', encoding=encoding)

print('------------------')
print('Extraction of simulated time series completed for ERA5-like experiments')
print('------------------')
