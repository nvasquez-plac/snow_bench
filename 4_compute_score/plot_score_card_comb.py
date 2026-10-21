import numpy as np
import pandas as pd
import xarray as xr
import pdb,os 
import datetime as dt


import argparse
import util_score as util
import runpy
from types import SimpleNamespace


parser = argparse.ArgumentParser(description="Plot scores card for several regions for manual and  automatic stations")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="maximum elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-ref","--exp_ref", help="Reference experiment among list_exp")
#parser.add_argument("-comp","--exp_comp", help="Experience to be compared among list_exp ")
parser.add_argument("-var","--list_var", help="List of variables",nargs='+',default=['SMA'])
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")

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

# List of experiments of interest
list_exp=args.list_exp

if(len(list_exp)>2):
    print('Only 2 experiments can be considered for this tools')
    sys.exit()  

# Experiment of reference
exp_ref=args.exp_ref

for exp in list_exp:
    if(exp!=exp_ref):
        exp_comp=exp

# Experiment to be compared with reference
#exp_comp=args.exp_comp

# List of variables of interest
list_var = args.list_var

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Dates for which we want to compute the scores
date_beg = args.date_beg
date_end = args.date_end

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15

for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp

fic_in = dir_nc+'/score_snw_domain_manual_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_beg+'_'+date_end+'.nc'
score_man = xr.open_dataset(fic_in)

fic_in = dir_nc+'/score_snw_domain_auto_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_beg+'_'+date_end+'.nc'
score_auto = xr.open_dataset(fic_in)

list_score=['bias','stde','rmse']

list_sco_man= [i for i in score_man.data_vars]
list_sco_auto= [i for i in score_auto.data_vars]
for sco in list_score:
    if(sco not in list_sco_man):
         print(sco+' is needed for the score card and is missing for manual stations')
    if(sco not in list_sco_auto):
         print(sco+' is needed for the score card and is missing for automatic stations')


dir_scores   = os.path.join(dir_eval_snow ,'scores')
# Make if does not exist
os.makedirs(dir_scores,exist_ok=True)

for var in list_var:

    fig_name = dir_scores+'/card_'+var+'_'+date_beg+'_'+date_end+'_'+exp_comp+'_vs_'+exp_ref+'.png'
    per = date_beg+'-'+date_end

    util.plot_score_card(list_score,score_man.loc[dict(variable=var)],score_auto.loc[dict(variable=var)],var,X,X2,fig_name,exp_ref, exp_comp, per)
