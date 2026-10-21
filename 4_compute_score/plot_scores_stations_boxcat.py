try:
    import fstd2nc  # ECCC lib, only needed to read FST files; does not build on macOS
except ImportError:
    fstd2nc = None
import numpy as np
import xarray as xr
import pdb,os,sys 
import datetime as dt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import argparse
import util_score as util
import runpy
from types import SimpleNamespace


parser = argparse.ArgumentParser(description="Plot boxplot of of scores for different categories of elevation, tpi, ... within a given region")
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-m","--max_alti", help="maximukm elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-exp_ref","--exp_ref", help="Reference experiment used if specified")
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-sco","--list_score", help="List of scores to compute ",nargs='+')
parser.add_argument("-t","--type_sta", help="Station type to be used when computing scores",choices=['comb'],default='comb')
#parser.add_argument("-t","--type_sta", help="Station type to be used when computing scores",choices=['auto','manual','all','comb'],default='all')
parser.add_argument("-type_plot","--type_plot", help="Type of plot",choices=['val','dif','dif_rel'],default='val')
parser.add_argument("-cat","--cat", help="Limit of categories",nargs='+')
parser.add_argument("-type_cat","--type_cat", help="Type of categories used for classification",choices=['alti','tpi'],default='alti')
#parser.add_argument("-type_cat","--type_cat", help="Type of categories used for classification",choices=['alti'],'cfia'],default='alti')
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['period'],default='period')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
parser.add_argument("-nobs","--nobs_min", help="Minimal number of observations required to plot score",default=3,type=float)
parser.add_argument("-reg","--reg", help="Region considered when doing the analysis")
parser.add_argument("-add_nsta",dest='add_nsta', action='store_true',help="Add number of station as boxplot")

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


dir_scores   = os.path.join(dir_eval_snow ,'scores')
# Make if does not exist
os.makedirs(dir_scores,exist_ok=True)


# List of experiments of interest
list_exp=args.list_exp

# List of variables of interest
list_var = args.list_var

# Type of station
type_sta=args.type_sta

# Limit for elevation categories
cat = args.cat

# Type of categories
type_cat=args.type_cat

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Score frequency
score_freq=args.score_freq

# Minimum number of observations required to plot scores in the boxplot
nobs_min =args.nobs_min

# Region considered when doing the analysis
reg = args.reg

# Add number of station as boxplot (optional)
ladd_nsta = args.add_nsta

# Reference experiment to be considered 
exp_ref= args.exp_ref

# Type of categories
type_plot=args.type_plot

if(type_plot in ['dif','dif_rel']):
    if(args.exp_ref is None):
        print('exp_ref must be defined when type_plot is set to dif')
        sys.exit()  

# Define dates and number of days to be considered to accumulate precip if month is not used
date_beg = args.date_beg
date_end = args.date_end

if(score_freq=='period'):
   if(args.date_beg is None or args.date_end is None):
     print('date_end and/or date_beg must be defined when score_freq is set to period')
     sys.exit()   
else:  
   if(args.date_beg is not None or args.date_end is not None):
     print('date_end and/or date_beg cannot be used must when score_freq is not set to period')
     sys.exit()  

# Define ranges
dic_range= []
for icat, alti in enumerate(cat):
    if(icat<(len(cat)-1)):
        dic_range.append([cat[icat],cat[icat+1]])

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SimpleNamespace(**runpy.run_path(config_snow))  # load_module() was removed in Python 3.15

if(args.list_score is None):
    list_score=['bias','stde','rmse']
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


score = xr.open_dataset(fic_in)

# Add mask for region of interest
util.find_sta(reg,score,X)

for var in list_var:
    if(score_freq=='period'):
       fig_name = dir_scores+'/overview_'+type_cat+'_'+type_plot+'_'+reg+'_'+var+'_'+type_sta+'_'+date_beg+'_'+date_end+'.png'

    per = date_beg+'-'+date_end   
    if(type_sta=='comb'):
        util.plot_boxplot_comb(list_score,dic_range,type_sta,score.loc[dict(variable=var)],var,X,X2,fig_name,per,nobs_min,type_cat,reg,type_plot,exp_ref,ladd_nsta)

