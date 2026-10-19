import fstd2nc
import numpy as np
import pandas as pd
import xarray as xr
import pdb,os 
import datetime as dt


import argparse
import util_score as util
from importlib.machinery import SourceFileLoader


parser = argparse.ArgumentParser(description="Plot histogram presenting scores for several regions and experiments over a given time period")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="maximukm elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-t","--type_sta", help="Station type",choices=['auto','manual','all','comb'])
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
parser.add_argument("-sco","--list_score", help="List of scores to compute ",nargs='+')
parser.add_argument("-superpose",dest='superpose', action='store_true',help="Superpose resuls of manual and automatic stations (when type_sta==comb) ")
parser.add_argument("-suf","--suffix", help="Suffix added at the end of the figure name",default="")


parser.set_defaults(superpose=False)

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

# List of experiments of interest
list_exp=args.list_exp

# List of variables of interest
list_var = args.list_var

# Type of station
type_sta=args.type_sta

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Dates for which we want to compute the scores
date_b = args.date_beg
date_e = args.date_end

# Boolean to superpose graphs when type_sta=comb
lsuperpose = args.superpose

# Suffix added at the end of the figure name
suffix= args.suffix

# Load config file
config_snow =  X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SourceFileLoader('', config_snow).load_module()

if(args.list_score is None):
	list_score=['bias','rmse']
else: 
	list_score=args.list_score

# Check consistency between list of regions and type of graphs. 
if(type_sta!='comb' and lsuperpose):
	print('The superpose option can only be used with type_sta=comb')
	sys.exit()



for ii,exp in enumerate(list_exp):
    if(ii==0):
        name_fic = exp
    else:
        name_fic = name_fic+'_'+exp


######################################
# Do plots for snow and FRPD metrics (1D variables)
######################################
# Open file containing scores
if(type_sta=='comb'):
    fic_in = dir_nc+'/score_snw_domain_manual_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_b+'_'+date_e+'.nc'
    score_man = xr.open_dataset(fic_in)

    fic_in = dir_nc+'/score_snw_domain_auto_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_b+'_'+date_e+'.nc'
    score_auto = xr.open_dataset(fic_in)
else:
    fic_in = dir_nc+'/score_snw_domain_'+type_sta+'_diff_alti_'+str(int(max_alti))+'_'+name_fic+'_period_'+date_b+'_'+date_e+'.nc'
    score = xr.open_dataset(fic_in)

dir_scores   = os.path.join(dir_eval_snow ,'scores')
# Make if does not exist
os.makedirs(dir_scores,exist_ok=True)

for var in list_var:

    if(lsuperpose):
        if(suffix==""):
            fig_name = dir_scores+'/summary_'+type_sta+'_superp_'+var+'_'+date_b+'_'+date_e+'.png'
        else:
            fig_name = dir_scores+'/summary_'+type_sta+'_superp_'+var+'_'+date_b+'_'+date_e+'_'+suffix+'.png'
    else:
        if(suffix==""):            
           fig_name = dir_scores+'/summary_'+type_sta+'_'+var+'_'+date_b+'_'+date_e+'.png'
        else:
           fig_name = dir_scores+'/summary_'+type_sta+'_'+var+'_'+date_b+'_'+date_e+'_'+suffix+'.png'

    if(type_sta=='auto'):
        per = 'Automatic stations \n'+date_b+' '+date_e
    elif(type_sta=='manual'):         
        per = 'Manual stations '+date_b+' '+date_e
    else:
        per = date_b+'-'+date_e

    if(type_sta=='comb'):
        util.plot_histo_comb(list_score,score_man.loc[dict(variable=var)],score_auto.loc[dict(variable=var)],var,X2,X,fig_name,per,lsuperpose)
    else:
        util.plot_histo(list_score,score.loc[dict(variable=var)],var,X2,X,fig_name,per)
