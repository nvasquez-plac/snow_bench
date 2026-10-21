#from sklearn.neighbors import BallTree
import numpy as np
from scipy.spatial import cKDTree
import pdb
import numpy as np
from numpy import sin, cos, radians, sqrt, arcsin
import geopandas as gpd
try:
    import fstd2nc  # ECCC lib, only needed to read FST files; does not build on macOS
except ImportError:
    fstd2nc = None
from os import environ
import os,sys,glob 
import pandas as pd 
import datetime as dt 
import xarray as xr
from pyproj import CRS,Transformer

def haversine_cst_lat(lat, dlon, earth_radius_km=6371):
    '''
    Given one given latitude and a delta of longitude , compute the haversine distancin km  between them on a spherical earth with mean radius of earth_radius_km
    
    '''
    lat = radians(lat)
    dlon = radians(dlon)
    aa = cos(lat) * cos (lat) * sin(dlon * 0.5) ** 2.


    return (2 * earth_radius_km * arcsin(sqrt(aa)))


def get_nearest_ckdt(src_points, candidates, k_neighbors):
    """Find nearest neighbors for all source points from a set of candidate points"""

    tree = cKDTree(candidates,balanced_tree=False)
    dists, indexes = tree.query(src_points,k=k_neighbors)

    return (dists, indexes)
  
def get_triyear(yy):
    if(yy in [2000,2001,2002]):
        return 2000
    if(yy in [2003,2004,2005]):
        return 2003
    if(yy in [2006,2007,2008]):
        return 2006
    if(yy in [2009,2010,2011]):
        return 2009
    if(yy in [2012,2013,2014]):
        return 2012
    if(yy in [2015,2016,2017,2018]):
        return 2015


def get_suffix(type_exp,member=-1):

    if(type_exp=='ANA'):
        if(member==-1):
            #suffix = '_000'
            suffix = ''
        else: 
            suffix = '_0'+str(member).zfill(2)
    elif(type_exp=='CTL'):
        suffix = '_000'
    elif(type_exp=='MIST'):
        suffix = '_0'+str(member).zfill(2)
    elif(type_exp=='OL'):
        suffix = '24h'     
    elif(type_exp=='GEM'):
        suffix = ''
    elif(type_exp=='ENS'):
        suffix = '_0'+str(member).zfill(2)        
    return(suffix)
    
def get_prefix(type_exp):
    if(type_exp=='OL'):
        return('pm')
    else:
        return('')

def get_middle(type_exp,time_ana=-1,time_fct=-1):

    if(type_exp=='ANA'):
        middle = str(time_ana).zfill(2)+'_'+str(time_fct).zfill(3)
    elif(type_exp=='CTL'):
        middle = '_000'
    elif(type_exp=='MIST'):
        middle = '' 
    elif(type_exp=='OL'):
        middle = '120000-00-00_0000'     
    elif(type_exp=='GEM'):
        middle = ''
    elif(type_exp=='ENS'):
        middle = ' '
    return(middle)    



def remove_duplicates_nhswe(da_fin,list_src): 


    buffer_size = 2000 # 2km buffer to select duplicates

    data = da_fin[['lon', 'lat', 'station_name','type_mes','source']].to_dataframe().reset_index()

    # esri:102002 (Canada Lambert Conformal Conic) but with WGS84 datum instead of NAD83
    crs_wgs84_lcc = CRS.from_proj4(
        '+proj=lcc +lat_1=50 +lat_2=70 +lat_0=40 +lon_0=-96 '
        '+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    )

    transformer = Transformer.from_crs('epsg:4326', crs_wgs84_lcc, always_xy=True)
    x, y = transformer.transform(data['lon'].values, data['lat'].values)

    stations = gpd.GeoDataFrame(
        data=data[['station_id', 'station_name', 'lon', 'lat','type_mes','source']],
        geometry=gpd.points_from_xy(x=x, y=y),
        crs=crs_wgs84_lcc
    )

    # Identify stations belonging to NHSWE
    mask_sta = da_fin.source == 'NH-SWE'
    sta_nhswe = da_fin.station_id.values[mask_sta].tolist()

    # Get list of stations in common wiht CanSWE and Snotel
    list_remove=clean_sta(stations, da_fin,sta_nhswe,buffer_size)

   # Drop duplicates
    da_fin2 = da_fin.drop_sel(station_id=list_remove,errors='ignore')

    return(da_fin2)


def clean_sta(stations, da_fin,sta_id,buffer_size):


    list_remove=[]
    for sta in sta_id: 
        currstat = stations.loc[stations['station_id'] == sta]
        currgeom = currstat['geometry'].iloc[0]
        nearby = stations.drop(currstat.index).loc[stations.intersects(currgeom.buffer(buffer_size))].copy()

        if(len(nearby) > 0):
            nearby['distance'] = nearby.distance(currgeom)
        else:
            continue

        for ista in np.arange(0,len(nearby)):
            if( (currstat.source.values[0]!=nearby.source.values[ista]) and (currstat.type_mes.values[0]==nearby.type_mes.values[ista])  ):
                #print('--------------')
                #print(currstat.iloc[0])
                #print(nearby.iloc[ista])
                #print('--------------')
                list_remove.append(sta)


    return(list_remove)


def clean_nhswe(da_fin):

    # Identify stations belonging to NHSWE
    mask_sta = da_fin.source == 'NH-SWE'
    sta_nhswe = da_fin.station_id.values[mask_sta].tolist()

    # List of stations to be removed
    list_remove=[]

    for sta in sta_nhswe:
        sd = da_fin.snd.loc[dict(station_id=sta)]  

        mask=sd.time.dt.month.isin([12,1,2,3])
        sd_sel = sd[mask]

        len_mask=np.sum(mask)
        len_nan = np.sum(np.isnan(sd_sel.values))

        # Compute the ratio of missing data over the period DJFM
        ratio = len_nan/len_mask

        # Remove station if more than 80% of the stations are missing.
        if(ratio>0.8):
            list_remove.append(sta)

   # Drop duplicates
    da_fin2 = da_fin.drop_sel(station_id=list_remove,errors='ignore')

    return(da_fin2)


def apply_time_offset(ds, offset):
    """
    Apply time offset to dataset, handling any time dimension name.
    
    Parameters:
    -----------
    ds : xarray.Dataset
        Dataset to modify
    offset : int
        Offset in hours
        
    Returns:
    --------
    xarray.Dataset with adjusted time
    """
    if offset == 0:
        return ds
    
    offset_td = np.timedelta64(offset, 'h')
    
    # Handle different time dimension names
    if 'time' in ds.coords:
        return ds.assign_coords(time=ds.time + offset_td)
    elif 'time1' in ds.coords and 'time2' in ds.coords:
        ds = ds.assign_coords(time1=ds.time1 + offset_td)
        ds = ds.assign_coords(time2=ds.time2 + offset_td)
        return ds
    elif 'time1' in ds.coords:
        return ds.assign_coords(time1=ds.time1 + offset_td)
    elif 'time2' in ds.coords:
        return ds.assign_coords(time2=ds.time2 + offset_td)
    else:
        print("Warning: No time dimension found to apply offset")
        return ds


