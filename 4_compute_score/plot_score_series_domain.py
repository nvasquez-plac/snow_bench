import numpy as np
import xarray as xr
import pdb,os,sys 
import datetime as dt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from importlib.machinery import SourceFileLoader
import argparse
import util_score as util


parser = argparse.ArgumentParser(description="Plot time series of scores for different regions")
parser.add_argument("-m","--max_alti", help="maximum elevation difference in m used to select the stations",default=150,type=float)
parser.add_argument("-cf","--configfile", help="File containing experiments info")
parser.add_argument("-exp","--list_exp", help="List of experiments to evaluated",nargs='+')
parser.add_argument("-var","--list_var", help="List of variables to extract ",nargs='+',default=['SMA'])
parser.add_argument("-reg","--list_reg", help="List of domains used for the generation of figures",nargs='+')
parser.add_argument("-sco","--list_score", help="List of scores to compute ",nargs='+')
parser.add_argument("-t","--type_sta", help="Station type to be used when computing scores",choices=['auto','manual','all'],default='all')
parser.add_argument("-graph","--type_graph", help="Type of graphic: single or multiple regions",choices=['single','multi'],default='single')
parser.add_argument("-freq","--score_freq", help="Score frequency",choices=['day','month','bi-month'],default='bi-month')
parser.add_argument("-b","--date_beg", help="Beginning date, format YYYYMMDD")
parser.add_argument("-e","--date_end", help="End date, format YYYYMMDD")
parser.add_argument("-add_nobs","--add_nobs", action='store_true',help="Add on the figures the number of observations used to compute the scores ")
parser.add_argument("-limit_graph","--limit_graph", help="Options to define the limits of the y-axis on the graphs.",choices=['auto','fix'],default='auto')
parser.add_argument("-tile","--list_tile", help="Add score for specific tile (only for SVS and SVS2). Only active when averaged scores are computed. Can be 'open' and/or 'forest'",nargs='+',default='')


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

# Score frequency
score_freq=args.score_freq

# Type of graphics
type_graph=args.type_graph

# Maximum elevation difference when plotting stations
max_alti =args.max_alti

# Define dates and number of days to be considered to accumulate precip if month is not used
date_beg = args.date_beg
date_end = args.date_end

# List of regions to be considered
list_reg = args.list_reg

# Boolean to add time series below high veg
ladd_nobs = args.add_nobs

#Options to define the limits of the y-axis on the graphs.
limit_graph = args.limit_graph

#Add score for specific tile (only for SVS and SVS2).
list_tile = args.list_tile 

# Load config file
config_snow = X.dir_git+"/1_config/config_snow.py"
# Load info in config file
X2 = SourceFileLoader('', config_snow).load_module()


if(args.list_score is None):
	list_score=['cor','bias','rmse','medae','nse','pbias','stde']
else: 
	list_score=args.list_score

# Check consistency between list of regions and type of graphs. 
if(type_graph=='multi' and len(list_reg)==1):
	print('type_graph=multi can only be used when a minmum of two regions is listed. Please revise the list of regions or change the type of graph')
	sys.exit()

if(len(list_tile)>0 and len(list_exp)>1):
	print('list_tile can only be defined when 1 experiment is considered')
	sys.exit()

name_fic =''
for exp in list_exp:
    name_fic = name_fic+exp+'_'
      
fic_in_1D = dir_nc+'/score_snw_domain_'+type_sta+'_diff_alti_'+str(int(max_alti))+'_'+name_fic+score_freq+'_'+date_beg+'_'+date_end+'.nc'
score = xr.open_dataset(fic_in_1D)

for reg in list_reg:
    if(reg not in score.domain):
        print('The requested region '+reg+' is not present in the file containg the snow scores. Please revise the list of regions.')
        sys.exit()

dir_scores   = os.path.join(dir_eval_snow ,'scores')

# Make if does not exist
os.makedirs(dir_scores,exist_ok=True)

suffix = score_freq+'_'+date_beg+'_'+date_end
    
for sco in list_score:
    print(sco)
    for var in list_var:
        if(type_graph=='multi'): # Put all regions on the same graph
            util.plot_score_multi_reg(score,sco,var,dir_scores,type_sta, X2,X,score_freq,list_reg,suffix) #not updated for ensemble
        else:
            for reg in list_reg: # One graph per region
               util.plot_score(score,sco,reg,score.exp.values,var,dir_scores,type_sta, X2,X,score_freq,suffix,ladd_nobs,limit_graph,list_tile)
