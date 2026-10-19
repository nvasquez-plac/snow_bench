# SnowBench: Evaluation package for snow simulations

This repository contains an ensemble of scripts to process observed and simulated snow data, extract simulated snow data at specific locations, compute scores and generate graphics and maps showing these scores. This package can be used to evaluate SVS2 simulations. Simulated snow data from ERA5-Land can be evaluated as well and serve as benchmark. 


## Organisation of the repository

Several sub-directories are present. They all correspond to different stages of the data processing. 
1. `1_config`: Contains configurations files required by the package
2. `2_prep_model_file`: Can contains scripts to process model output from specific land surface models. 
3. `3_prep_data`: Contains scripts to extract and merge snow data from different networks and extract the simulated time series of snow variables at the location of observations. 
4. `4_compute_score`: Contains scripts to compute the errors metrics and generate graphics and maps showing these scores.
8. `examples`: Contains examples of configurations files and corresponding evaluation scripts. The user can use these examples to build its own configuration of the package. 

More information about the scripts contained in each sub-directory is given in the corresponding README.md. 
