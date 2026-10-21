# This file contains the information about the different experiments 
# It needs to be defined by the user
#
    
# Directory containining the evaluation package
dir_git = '/Users/nvasquez/Github/snow_bench'

# Directory for analysis outputs (figures, etc.)
dir_analysis = '/Users/nvasquez/Github/snow_bench/eval'

# Path to public html to create http links to visualizes time series and scores.
dir_html = '/Users/nvasquez/Github/snow_bench/eval_html'  # must NOT exist yet: plot_time_series_snow.py creates it as a symlink to dir_analysis/snow

# File containing the elevation field
fic_geo_all = '/Users/nvasquez/Github/snow_bench/data_snow_bench/sample_svs2/geophy_svs2.nc'


# Dictionary containg the information for each experiment (identified by a given ID)
cfg_exp = {
    'SVS2':{
         'dir_outall':'/Users/nvasquez/Github/snow_bench/data_snow_bench/sample_svs2',# Directory where are stored the snow variables
         'fic_geo':fic_geo_all, # Path to the corresponding geophysical information (elevation) 
         'var_geo':'MF',        # Name of the variable used to find the evlevation in the geophysical file
         'offset':6,            # Time offset applied to the simulated data to make sure that they match the time of the snow data (18 UTC) 
         'lss':'SVS2',         # Land surface scheme used in the experiment (choose among SVS2, ECLand, SUMMA)
         'col':'blue', # Color used in the graphics.
},

    'ERA5L':{'dir_in':'/Users/nvasquez/Github/snow_bench/data_snow_bench/sample_era5l', # Directory containing the model outputs
         # TODO: topo_era5land_NorAm.nc is not in the sample data; get it from Vincent before running 3_extract_era5_snow.py
         'fic_geo':'/home/vvi001/store8/Eval_Data/ERA5_Land/Topo/topo_era5land_NorAm.nc', # Path to the corresponding geophysical information (elevation)
         'offset':6, # Time offset applied to the simulated data to make sure that they match the time of the snow data (18 UTC) 
         'var_geo':'z',  # Name of the variable used to find the elevation in the geophysical file
         'col':'#31a354',  # Color used in the graphics.
}

}


# Dictionary containing the maximal and minimal values used when plotting the graphics. They can be adjusted by the users to customize the graphics. 
dic_limits = {
     # Snow depth in m 
   'SD':{ 'min_g':{'bias':-0.7,'rmse':0,'medae':0,'nse':-1,'pbias':-50,'cor':-1,'stde':0, 'nrmse':0,'moymod':0},   
            'max_g':{'bias':0.3, 'rmse':1.2,'medae':0.30,'nse':1,'pbias':60,'cor':1,'stde':1.0, 'nrmse':1.6,'moymod':1.5}},

   'SDA':{ 'min_g':{'bias':-0.7,'rmse':0,'medae':0,'nse':-1,'pbias':-50,'cor':-1,'stde':0, 'nrmse':0,'moymod':0},   
            'max_g':{'bias':0.3, 'rmse':1.2,'medae':0.30,'nse':1,'pbias':60,'cor':1,'stde':1.0, 'nrmse':1.6,'moymod':1.5}},

   'SNDP':{ 'min_g':{'bias':-0.7,'rmse':0,'medae':0,'nse':-1,'pbias':-50,'cor':-1,'stde':0, 'nrmse':0,'moymod':0},   
            'max_g':{'bias':0.3, 'rmse':1.2,'medae':0.30,'nse':1,'pbias':60,'cor':1,'stde':1.0, 'nrmse':1.6,'moymod':1.5}},

    # SWE in kg/m2 
    'SMA':{ 'min_g':{'bias':-300,'rmse':0,'medae':0,'nse':-1,'pbias':-80,'cor':-1,'stde':0, 'nrmse':0, 'nobs':0,'moymod':0},   
        'max_g':{'bias':70, 'rmse':500,'medae':0.30,'nse':1,'pbias':100,'cor':1,'stde':500, 'nrmse':1.5, 'nobs':1000,'moymod':500}},

    # SWE in kg/m2 
    'SML':{ 'min_g':{'bias':-300,'rmse':0,'medae':0,'nse':-1,'pbias':-80,'cor':-1,'stde':0, 'nrmse':0, 'nobs':0,'moymod':0},   
        'max_g':{'bias':70, 'rmse':500,'medae':0.30,'nse':1,'pbias':100,'cor':1,'stde':500, 'nrmse':1.5, 'nobs':1000,'moymod':500}},


    # Density in kg/m3

    'SNDN':{ 'min_g':{'bias':-100,'rmse':0,'medae':0,'nse':-1,'pbias':-40,'cor':-1,'stde':0, 'nrmse':0,'moymod':0},   
            'max_g':{'bias':100, 'rmse':200,'medae':0.30,'nse':1,'pbias':50,'cor':1,'stde':1.0, 'nrmse':0.75,'moymod':600}},

     'DNA':{ 'min_g':{'bias':-100,'rmse':0,'medae':0,'nse':-1,'pbias':-40,'cor':-1,'stde':0, 'nrmse':0,'moymod':0},   
            'max_g':{'bias':100, 'rmse':200,'medae':0.30,'nse':1,'pbias':50,'cor':1,'stde':1.0, 'nrmse':0.75,'moymod':600}}

} 


