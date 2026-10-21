#!/usr/bin/env python

# This function plot maps showing scores for two experiments and compare them. 
#
# Author: Vincent Vionnet  - vincent.vionnet(at)ec.gc.ca
#
#
# Example of use to compare scores for two CaLDAS experiments in the Great Lakes regions from 1 Octobre 2021 to 1 July 2022
# python plot_maps_score_stations_comp.py  -cf ../1_config/config_exp_CalDAS_2021_2022.py  -exp CTL ANA -ref CTL -var SMA  -sco rmse bias pbias -freq period -b 20211001 -e 20220701  -reg GLS SouthOntario -t manual -nobs 3



from os import environ
import pdb
import os,sys
import numpy as np 
import pandas as pd 
import datetime as dt 
import calendar
import matplotlib as mpl 
mpl.use('Agg')
import matplotlib.pyplot as plt
import xarray as xr
from mpl_toolkits.basemap import Basemap, maskoceans

import util_maps_score as utilmp
import util_score as util
import runpy
from types import SimpleNamespace
import argparse

parser = argparse.ArgumentParser(description="Plot maps showing scores for two experiments and comparing them")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="maximum elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to be evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to evalute ",nargs='+',default=['SMA'])
parser.add_argument("-sco","--list_score", help="List of scores to show ",nargs='+')
parser.add_argument("-ref","--exp_ref", help="Reference experiment (to be selected among list_exp")
parser.add_argument("-t","--type_sta", help="Station type to be used when plotting maps",choices=['auto','manual','all','both'],default='all')
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['period'],default='period')
parser.add_argument("-reg","--list_reg", help="List of domains used for the generation of maps",nargs='+')
parser.add_argument("-sel_reg","--list_sel_reg", help="List of domains used for the selection of stations",nargs='+')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
parser.add_argument("-add_elev",dest='add_elev', action='store_true',help="Add elevation of the grid in the background")
parser.add_argument("-add_poly",dest='add_poly', action='store_true',help="Add polygon of region selected to the map")
parser.add_argument("-nobs","--nobs_min", help="Minimal number of observations required to plot score",default=3,type=float)


parser.set_defaults(add_elev=False)
parser.set_defaults(add_poly=False)

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

# Make if does not exist
os.makedirs(dir_maps,exist_ok=True)

# List of experiments of interest
list_exp=args.list_exp

if(len(list_exp)>2):
    print('Only 2 experiments can be considered for this tools')
    sys.exit()  

# Reference experiment
exp_ref = args.exp_ref

# List of variables of interest
list_var = args.list_var

# Type of station
type_sta=args.type_sta

# Score frequency
score_freq=args.score_freq

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Minimum number of observations required to plot scores on the maps
nobs_min =args.nobs_min


# Define beginning and end dated to compute scores
date_beg = args.date_beg
date_end = args.date_end


if(args.date_beg is None or args.date_end is None):
    print('date_end and/or date_beg must be defined')
    sys.exit()  


# Boolean to add elevation on the maps 
ladd_elev = args.add_elev

# Boolean to add polygon on the maps 
ladd_poly = args.add_poly

# List of regions to be considered
list_reg = args.list_reg

# List of domains for the selection of stations
list_sel_reg = args.list_sel_reg

if(args.list_sel_reg is None): # No selection of station is applied
    list_sel_reg=list_reg

#don't create a polygon if list_reg is All:
if(list_reg ==['All']) & (ladd_poly):
    print("Polygon will not be created if list_reg is All")
    ladd_poly=False

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15
dic_var = X2.dic_var
dic_fac_max = X2.dic_fac_max

if(args.list_score is None):
    list_score=['cor','bias','rmse','medae','nse','pbias','stde']
else: 
    list_score=args.list_score

for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp
        

# Read and open file containing scores
if(score_freq=='period'):
    fic_in = dir_nc+'/score_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_beg+'_'+date_end+'.nc'
elif(score_freq=='period_wd'):
    fic_in = dir_nc+'/score_snw_station_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_'+date_beg+'_'+date_end+'_WD_'+wday_beg+'_'+wday_end+'.nc'


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

res = xr.open_dataset(fic_in) 

# Determine the stations to be plotted on the maps based on the list of specified regions
for ireg,reg in enumerate(list_sel_reg):
    # Add mask that determines the location of the stations
    util.find_sta(reg,res,X)
    mask_reg=res['mask_'+reg] 
    if(ireg==0):
        mask_sel=mask_reg.values
    else:
        mask_sel=np.logical_or(mask_sel,mask_reg.values)

# Extract list of stations to be selected and keep only these stations. 
list_sta = res.station_id.values[mask_sel]
res=res.where(res.station_id.isin(list_sta),drop=True)


for var in list_var:
    for score in list_score:
        for reg in list_reg:
            nexp=len(list_exp)
            if(len(list_exp)==1):
                ncol=1
            else:
                ncol=len(list_exp)+1

            if(type_sta=='both'):
                nrow=2
            else: 
                nrow=1

            fig, ax = plt.subplots(nrow,ncol, sharex='col',figsize=(5*ncol,5*nrow),squeeze=False)

            plt.subplots_adjust(wspace=0.,hspace=0.2)
           
            for ii,exp in enumerate(list_exp):
                print(exp)
                
                if(type_sta=='both'):

                    utilmp.add_fig_score(ax.ravel()[ii],reg,var,res,score,exp,'manual','val_score',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly)
                    utilmp.add_fig_score(ax.ravel()[ii+ncol],reg,var,res,score,exp,'auto','val_score',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly)  
                    if(exp!=exp_ref) :
                        utilmp.add_fig_score(ax.ravel()[2],reg,var,res,score,exp,'manual','comp_ref',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly,exp_ref=exp_ref)
                        utilmp.add_fig_score(ax.ravel()[5],reg,var,res,score,exp,'auto','comp_ref',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly,exp_ref=exp_ref)
                    
                else:
                    utilmp.add_fig_score(ax.ravel()[ii],reg,var,res,score,exp,type_sta,'val_score',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly)
                    if(exp!=exp_ref):
                        utilmp.add_fig_score(ax.ravel()[2],reg,var,res,score,exp,type_sta,'comp_ref',xgeo[exp],cfg_exp[exp]['var_geo'],ladd_elev,True,X,X2,nobs_min,ladd_poly,exp_ref=exp_ref)
            if(score_freq=='period'):
                if len(list_exp)>1:
                    exp_1 = list_exp[0]
                    exp_2 = list_exp[1]
                    if exp_1!=exp_ref:
                        exp = exp_1
                    else:
                        exp = exp_2
                plt.savefig(dir_maps+'/maps_scorestations_comp_'+type_sta+'_'+reg+'_'+var+'_'+score+'_'+exp+'_'+exp_ref+'_'+date_beg+'_'+date_end+'.png',bbox_inches = "tight",dpi=300)
            plt.close()

