#!/bin/bash

# Example of script to run the evaluation of an SVS2 experiment


# Load necessary environment

# Activate python environment
. ssmuse-sh -p /fs/ssm/eccc/cmd/cmds/env/python/cmds_python_latest


# Define git repo, working directory and dates of interest
dir_git=/home/vvi001/scripts/eval_snow/snow_bench

# Select the dates of evaluation
dat1=20171101
dat2=20180601

# Set absolute path to config file:
file_cfg=/home/vvi001/scripts/eval_snow/config_eval/snow_bench/config_svs2_era5l.py

# Step 1: Move to the git repo
cd $dir_git

# Step 2: collect simulated data and compute necessary snow variables

# Step 3: collect observed data and extract colocated simulated data

# Prepare snow observations
python 3_prep_data/1_prep_snow_data.py -cf $file_cfg -src CANSWE -b $dat1 -e $dat2 # manual and auto st.

# Extract SVS2 simulations
python 3_prep_data/2_extract_SVS2_snow.py -cf $file_cfg -d 10 -exp SVS2 -var SDA SMA SML -n 3

# Extract ERA5L simulations
python 3_prep_data/3_extract_era5_snow.py -cf $file_cfg -d 10 -exp ERA5L -var SMA SDA DNA SML -b $dat1 -e $dat2

exp_name="SVS2 ERA5L"

var_name="SMA SML"

# Step 4: produce evaluation figures

# Create time series for each station and variable (png format)
python 4_compute_score/plot_time_series_snow.py -cf $file_cfg -var $var_name -reg NorthAmericaPlus -b $dat1 -e $dat2 -exp $exp_name  -m 200 -n 80

# List of domains to summarize scores
ldom='Arctic_Land_CLIM West_Boreal_CLIM East_Boreal_CLIM Pacific_North_West_CLIM Mt_West_CLIM Central_CLIM Great_Lakes_CLIM East_CLIM  Pacific_South_West_CLIM Desert_CLIM Canada' # list of CLIM domain

# Compute score per domain for manual and automatic stations for a given time period
python 4_compute_score/compute_score_snow_domain.py	-cf $file_cfg  -exp $exp_name   -var  $var_name   -reg $ldom  -m 200 -sco bias pbias rmse nrmse stde -freq period	-b $dat1 -e $dat2 -t manual -ref_exp_alti all
python 4_compute_score/compute_score_snow_domain.py	-cf $file_cfg  -exp $exp_name  -var  $var_name   -reg $ldom  -m 200  -sco bias pbias rmse nrmse stde  -freq period	-b $dat1 -e $dat2 -t auto -ref_exp_alti all

# Plot barplots summarizing scores per domain  for a given time period
python 4_compute_score/plot_score_histo_period.py	-cf $file_cfg  -exp $exp_name   -var $var_name  -m 200 -sco bias pbias rmse nrmse	-b $dat1 -e $dat2 -t comb -superpose
python 4_compute_score/plot_score_histo_period.py	-cf $file_cfg  -exp $exp_name  -var $var_name  -m 200 -sco bias pbias rmse nrmse	-b $dat1 -e $dat2 -t comb 
python 4_compute_score/plot_score_histo_period.py	-cf $file_cfg  -exp $exp_name  -var $var_name  -m 200 -sco bias pbias rmse nrmse	-b $dat1 -e $dat2 -t manual

# Plot score card summarizing changes in performances between two experiments.
python 4_compute_score/plot_score_card_comb.py  -cf $file_cfg  -exp  $exp_name  -ref ERA5L -var $var_name    -b $dat1 -e $dat2 -m 200

# Compute and plot score per domain for automatic stations at a daily time scale
python 4_compute_score/compute_score_snow_domain.py -cf $file_cfg  -exp $exp_name  -var  $var_name   -reg $ldom  -m 200  -sco bias pbias rmse nrmse stde  -freq day	-b $dat1 -e $dat2 -t auto -ref_exp_alti all
python 4_compute_score/plot_score_series_domain.py -cf $file_cfg  -exp  $exp_name  -var $var_name  -reg Canada  -sco bias rmse -freq day -b $dat1 -e $dat2 -graph single -t auto -m 200

# Compute score per stations for a given time period
python 4_compute_score/compute_score_snow_stations.py -cf $file_cfg -exp $exp_name   -var $var_name   -sco bias rmse pbias nrmse -freq period -b $dat1 -e $dat2 -ref_exp_alti all -m 200 

# Compute score per stations for the accumulation period
python 4_compute_score/compute_score_snow_stations.py -cf $file_cfg -exp $exp_name  -var $var_name  -sco bias rmse pbias nrmse -freq accu -b $dat1 -e $dat2 -ref_exp_alti all -m 200 

# Generate boxplot summarizing the distribution of score per regions
python 4_compute_score/plot_scores_stations_boxregions.py -cf $file_cfg -exp $exp_name   -var  $var_name     -sco bias rmse  -freq period -b $dat1 -e $dat2 -m 200 -reg $ldom -t manual -suf classic -type_plot val 
python 4_compute_score/plot_scores_stations_boxregions.py -cf $file_cfg -exp $exp_name   -var  $var_name     -sco bias rmse  -freq accu -b $dat1 -e $dat2 -m 200 -reg $ldom -t comb -suf classic -type_plot val 
python 4_compute_score/plot_scores_stations_boxregions.py -cf $file_cfg -exp $exp_name  -exp_ref ERA5L  -var  $var_name     -sco rmse  -freq period -b $dat1 -e $dat2 -m 200 -reg $ldom -t comb -suf classic -type_plot dif_rel

# Generate boxplot summarizing the distribution of score per elevation bands within a given domain
alti_cat='0 1500 2000 2500 3000 4000'
python 4_compute_score/plot_scores_stations_boxcat.py -cf $file_cfg -exp  $exp_name   -var $var_name -sco  rmse -freq period -b $dat1 -e $dat2 -m 200 -cat $alti_cat -type_cat alti  -t comb -reg Mt_West_CLIM  -type_plot val -nobs 1
python 4_compute_score/plot_scores_stations_boxcat.py -cf $file_cfg -exp  $exp_name  -exp_ref ERA5L -var $var_name -sco  rmse -freq period -b $dat1 -e $dat2 -m 200 -cat $alti_cat -type_cat alti  -t comb -reg Mt_West_CLIM  -type_plot dif_rel -nobs 1

# Generate static maps comparing score between two experiments for a given region. 
python 4_compute_score/plot_maps_score_stations_comp.py  -cf $file_cfg -exp  $exp_name   -var $var_name  -ref ERA5L -sco rmse bias pbias -freq period -b $dat1 -e $dat2   -reg Canada -t both -nobs 1 -m 200

# Generate interactive map - 3 steps
# Add dir_html in config file

# 1st step: Create figures for each station and variable (png format)
#python 4_compute_score/plot_time_series_snow.py -cf $file_cfg -var $var_name  -reg NorthAmericaPlus -b $dat1 -e $dat2 -exp  $exp_name  -m 200 -n 80 -ref_exp_alti all

# 2nd step: Compute score for the different stations and different variables
#python 4_compute_score/compute_score_snow_stations.py -cf $file_cfg -exp $exp_name -var $var_name   -sco rmse -freq period -b $dat1 -e $dat2 -m 200 -ref_exp_alti all

# 3rd step: Generate interactive map : one for each score and each variable
#python 4_compute_score/generate_interactive_map.py -cf $file_cfg -exp  $exp_name  -ref ERA5L -var $var_name  -sco rmse  -freq period -b $dat1 -e $dat2 -reg NorthAmericaPlus -m 200

