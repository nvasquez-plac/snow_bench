#!/usr/bin/env python

# This function generate interactive maps in html format: 
#       - the color of the dots/square shows the % change in the score of interest between two experiements
#       - when clicking on the dots a popup appears showing the time series of the variable of interest for the selected station

#
# Author: - Vincent Vionnet  - vincent.vionnet(at)ec.gc.ca
#    Based on initial developements from Nicolas Leroux.        
#
#

from os import environ
import glob
import pdb
import os,sys
import numpy as np 
import pandas as pd 
import datetime as dt 
import calendar
import matplotlib as mpl 
mpl.use('Agg')
import matplotlib.cm as cm  # For colormap
import matplotlib.pyplot as plt
import xarray as xr
from mpl_toolkits.basemap import Basemap, maskoceans
import geopandas as gpd
import base64
import branca.colormap as branca_colormap
from folium import plugins

import util_maps_score as utilmp
import util_score as util
import runpy
from types import SimpleNamespace
import argparse
try:
    import fstd2nc  # ECCC lib, only needed to read FST files; does not build on macOS
except ImportError:
    fstd2nc = None
import folium
from folium import Tooltip
from PIL import Image
import io

parser = argparse.ArgumentParser(description="Plot maps showing scores for two experiments and comparing them")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="maximum elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to be evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to evalute ",nargs='+',default=['SMA'])
parser.add_argument("-sco","--list_score", help="List of scores to show ",nargs='+')
parser.add_argument("-ref","--exp_ref", help="Reference experiment (to be selected among list_exp")
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['period','accu'],default='period')
parser.add_argument("-reg","--list_reg", help="List of domains used for the generation of maps",nargs='+')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
#parser.add_argument("-nobs","--nobs_min", help="Minimal number of observations required to plot score",default=3,type=float)


args = parser.parse_args()

# Get name of configuration file/module
configfile = args.configfile

# Load in configuration file as module
X = SimpleNamespace(**runpy.run_path(configfile))  # load_module() was removed in Python 3.15
cfg_exp = X.cfg_exp

#Reference Directory
dir_eval = X.dir_analysis
dir_eval_snow = dir_eval+'/snow'
dir_nc = dir_eval_snow+'/fic_nc'
dir_maps = dir_eval_snow+'/maps'
dir_series = dir_eval_snow+'/series'

# Make if does not exist
os.makedirs(dir_maps,exist_ok=True)

# List of experiments of interest
list_exp=args.list_exp

if(len(list_exp)>2):
    print('Only 2 experiments can be considered when plotting interactive maps')
    sys.exit()  

# Reference experiment
exp_ref = args.exp_ref

# List of variables of interest
list_var = args.list_var

# Type of station
#type_sta=args.type_sta

# Score frequency
score_freq=args.score_freq

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Minimum number of observations required to plot scores on the maps
#nobs_min =args.nobs_min

# Define beginning and end dated to compute scores
date_beg = args.date_beg
date_end = args.date_end

if(args.date_beg is None or args.date_end is None):
    print('date_end and/or date_beg must be defined')
    sys.exit()  

# List of regions to be considered
list_reg = args.list_reg

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15
dic_var = X2.dic_var
dic_varname=X2.dic_varname
dic_score_title=X2.dic_score_title

if(args.list_score is None):
    list_score=['rmse']
else: 
    list_score=args.list_score

if('dir_html' not in X.__dict__):    
    print('Variable dic_html must be defined in the configuration file when generating interactive maps')
    sys.exit()    

for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp
# Find variables that correspond to snow or soil in list of variables given
vars_soil_2D = ['TGRD','WSOL']
vars_1D = [x for x in list_var if x not in vars_soil_2D]
vars_2D = [x for x in list_var if x in vars_soil_2D]

# Process snow variables
if len(vars_1D)>0:
    # Read and open file containing scores
    if(score_freq in ['period','accu']):
        fic_in = dir_nc+'/score_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+score_freq+'_'+date_beg+'_'+date_end+'.nc'
    elif(score_freq=='period_wd'):
        fic_in = dir_nc+'/score_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+date_beg+'_'+date_end+'_WD_'+wday_beg+'_'+wday_end+'.nc'

    res = xr.open_dataset(fic_in)
    xgeo={}
    for ii,exp in enumerate(list_exp):
        type_file=cfg_exp[exp]['fic_geo'].split('.') # Netcdf format
        if(len(type_file)>1 and type_file[-1]=='nc'):
            xgeo[exp] = xr.open_dataset(cfg_exp[exp]['fic_geo'])
        else:  # FST format
            # Read file containing elevation 
            b2 = fstd2nc.Buffer(
            cfg_exp[exp]['fic_geo'],
            vars= cfg_exp[exp]['var_geo'], subgrid_axis=True,ignore_etiket=True)

            xgeo[exp] = b2.to_xarray()

    if len(list_exp)>1:
        exp_1 = list_exp[0]
        exp_2 = list_exp[1]
        if exp_1!=exp_ref:
            exp = exp_1
        else:
            exp = exp_2

    for reg in list_reg: 
        print('##################')
        print('Region: ', reg)

        for score in list_score:

            for var in vars_1D: 

                # Check if png have been generated
                dir_figs = os.path.join(dir_series,reg)
                # Get list of files in the direcory 
                if (os.path.isdir(dir_figs) == 0):
                    print('Missing directory containing figures showing time series for region '+f'{reg}')
                    sys.exit() 
                else:
                    list_file = glob.glob(dir_figs+'/*'+var+'*png')
                    if(len(list_file)==0): # No file corresponding to the variable of interest
                        print('Figures showing time series for variable '+f'{var} for region '+f'{reg} are missing')
                        sys.exit() 

                map_name = os.path.join(dir_maps,"maps_inter_{}_{}_{}_{}_{}_{}_{}_{}.html".format(reg, var, score,exp,exp_ref,score_freq,date_beg,date_end))  
                utilmp.generate_interactive_map(reg,var,res,score,xgeo[exp_ref],X,X2,exp_ref,exp,date_beg,date_end,dir_series,map_name)

# Process soil variables
if len(vars_2D)>0:
    # Read and open file containing scores
    if(score_freq=='period'):
        fic_in = dir_nc+'/score_soil_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_beg+'_'+date_end+'.nc'
    elif(score_freq=='period_wd'):
        fic_in = dir_nc+'/score_soil_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+date_beg+'_'+date_end+'_WD_'+wday_beg+'_'+wday_end+'.nc'

    res = xr.open_dataset(fic_in).mean(dim='layer_svs', skipna=True)

    xgeo={}
    for ii,exp in enumerate(list_exp):
        type_file=cfg_exp[exp]['fic_geo'].split('.') # Netcdf format
        if(len(type_file)>1 and type_file[-1]=='nc'):
            xgeo[exp] = xr.open_dataset(cfg_exp[exp]['fic_geo'])
        else:  # FST format
            # Read file containing elevation 
            b2 = fstd2nc.Buffer(
            cfg_exp[exp]['fic_geo'],
            vars= cfg_exp[exp]['var_geo'], subgrid_axis=True,ignore_etiket=True)

            xgeo[exp] = b2.to_xarray()

    if len(list_exp)>1:
        exp_1 = list_exp[0]
        exp_2 = list_exp[1]
        if exp_1!=exp_ref:
            exp = exp_1
        else:
            exp = exp_2

    for reg in list_reg: 
        print('##################')
        print('Region: ', reg)

        for score in list_score:

            for var in vars_2D: 

                # Check if png have been generated
                dir_figs = os.path.join(dir_series,reg)
                # Get list of files in the direcory 
                if (os.path.isdir(dir_figs) == 0):
                    print('Missing directory containing figures showing time series for region '+f'{reg}')
                    sys.exit() 
                else:
                    list_file = glob.glob(dir_figs+'/*'+var+'*png')
                    
                    if(len(list_file)==0): # No file corresponding to the variable of interest
                        print('Figures showing time series for variable '+f'{var} for region '+f'{reg} are missing')
                        sys.exit() 

                map_name = os.path.join(dir_maps,"maps_inter_{}_{}_{}_{}_{}_{}_{}.html".format(reg, var, score,exp,exp_ref,date_beg,date_end))  
                utilmp.generate_interactive_map(reg,var,res,score,xgeo[exp_ref],X,X2,exp_ref,exp,date_beg,date_end,dir_series,map_name)



   


   
