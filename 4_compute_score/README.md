# Scores and summary figures

## Information 
This step of the snow evaluation process concerns the computation of the scores, and the generation of the different associated figures and maps.  

## Errors metrics
A large set of errors metrics can be computed using the evaluation package. Note that so far only deterministic score can be computed in `snow_benhch`. The associated abbeviations and their meaning are given below:

| Abbreviations  | Meaning  | Forecast Type (Deterministic, Ensemble, Both) |
|:----------:|:-------------:|:-------------:|
| bias | Bias | Both |
| crps | Continuous Rank Probability Score | Ensemble |
| crps_rel | Reliability component of the Continuous Rank Probability Score | Ensemble |
| crps_pot | Potential component of the Continuous Rank Probability Score | Ensemble |
| mae  | Mean Absolute Error  | Deterministic |
| medea  | Median Absolute Error  | Deterministic |
| stde  | Standard Deviation of the Error | Deterministic |
| ss    | Spread-skill | Ensemble |
| rbias | Relative Bias | Ensemble |
| rmse  | Root Mean Squared Error | Both |
| nrmse | Normalized Root Mean Squared Error | Both |
| nse   | Nash Sutcliffe Efficiency | Deterministic |
| pbias | Percent Bias | Deterministic |
| cor   | Coefficient of Correlation | Deterministic |
| det   | Coefficient of Determination | Deterministic |
| kge09 | Kling Gupta Efficiency (original; Gupta et al., 2009) | Deterministic |
| kge12 | Kling Gupta Efficiency (modified; Kling et al., 2012) |Deterministic |
| alpha | alpha parameter used in KGE09 | Deterministic |
| beta  | beta parameter used in KGE09 and KGE12 | Deterministic |
| gamma | gamma parameter used in KGE12 | Deterministic |

## Domains

The scripts in this subdirecroty require to specify a list of regions of interest defined as in the Emet evaluation tool used internally at ECCC(see the list of Emet domains and their names https://wiki.cmc.ec.gc.ca/wiki/EMET\_/\_Domaines_g%C3%A9ographiques\_de\_v%C3%A9rification). If needed, more domains can be added in `util_score.py` (see function `emetDomain`). Shapefile can also be used to specify the domain of interest for the evaluation. 

## Steps
The scores need to be computed first using the different scripts `compute_*`. The figure summarizing the scores can then be plotted using the different scripts `plot_*`. The table below summarizes the relationships betwenn the scripts used to compute scores and to plot them. 

| Plotting script  | Corresponding script to compute scores |
|:----------:|:-------------:|
| plot_score_histo_period.py | compute_score_snow_domain.py |
| plot_score_series_domain.py | compute_score_snow_domain.py  |
| plot_score_card_comb.py | compute_score_snow_domain.py  |
| plot_maps_score_stations_comp.py | compute_score_snow_stations.py  | 
| generate_interactive_map.py | compute_score_snow_stations.py | 

## Scripts to compute scores

For each script, a help message can be obtained by typing `python script_name.py -h`

**compute_score_snow_domain.py**

* Script used to compute error metrics for different sub-regions for selected time periods
* The user can define the value of the maximum elevation difference between the stations and the corresponding grid cell used to select the relevant stations for the evaluation. The key `ref_exp_alti` allows the selection of stations to be restricted to the stations that match the selection criteria for a specific experiment (chosen among `list_exp`) or all experiments (use `ref_exp_alti=all`). Note that by default the elevation criteria is applied for each experiment individually  
* Four different time period are available: 
	*  'month': score are computed for each month between `date_beg` `date_end`
	*  'bi-month': score are computed bi-monthly for a 12-day period centered the 1st and 15th of each month between `date_beg` `date_end` (usefule for manual snow survey)
	*  'daily': score are computed daily between `date_beg` `date_end` (useful for automatic snow stations) 
	*  'period': score are computed over the full time period between `date_beg` `date_end` (useful to summarize seasonal performances) 

*Usage* compute_score_snow_domain.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI]
                                    [-exp LIST_EXP [LIST_EXP ...]]
                                    [-var LIST_VAR [LIST_VAR ...]]
                                    [-reg LIST_REG [LIST_REG ...]]
                                    [-t {auto,manual,all}]
                                    [-freq {day,month,bi-month,period}]
                                    [-sco LIST_SCORE [LIST_SCORE ...]]
                                    [-b DATE_BEG] [-e DATE_END]
				    [-ref_exp_alti [EXP]]


*Arguments*
  -cf, File containing experiments info

  -m, Maximum elevation difference in m used to select the stations (default 150 m)

  -ref_exp_alti,  Only use stations that match the elevation criteria for a specific experiment (among `list_exp`) or all experiments (use `all`). Not used by default. 

  -exp, List of experiments to evaluated

  -var, List of variables to extract

  -reg, --list_reg List of domains used for the evaluation

  -t {auto,manual,all}, Station type to be used when computing scores

  -freq {day,month,bi-month,period}, Score frequency

  -sco, List of scores to compute (see above the list of scores available)

  -b, Beginning date, format YYYYMMDD

  -e,  End date, format YYYYMMDD

*Example*:
see `/examples/run_eval.sh`

**compute_score_snow_stations.py**

* Script used to compute error metrics at all individuals stations for selected time period
* The user can define the value of the maximum elevation difference between the stations and the corresponding grid cell used to select the relevant stations for the evaluation. The key `ref_exp_alti` allows the selection of stations to be restricted to the stations that match the selection criteria for a specific experiment (chosen among `list_exp`) or all experiments (use `ref_exp_alti=all`). Note that by default the elevation criteria is applied for each experiment individually   
* Three different time period are available: 
	*  'month': score are computed for each month between `date_beg` `date_end`
	*  'bi-month': score are computed bi-monthly for a 12-day period centered the 1st and 15th of each month between `date_beg` `date_end` (usefule for manual snow survey)
	*  'period': score are computed over the full time period between `date_beg` `date_end` (useful to summarize seasonal performances) 


*Usage*  compute_score_snow_stations.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI] [-exp LIST_EXP [LIST_EXP ...]]
                                      [-var LIST_VAR [LIST_VAR ...]] [-freq {month,bi-month,period}]
                                      [-sco LIST_SCORE [LIST_SCORE ...]] [-b DATE_BEG] [-e DATE_END] [-ref_exp_alti [EXP]] 

*Arguments*
  -cf, --configfile    File containing experiments info

  -m, --max_alti
                        Maximum elevation difference in m used to select the stations (default 150m)

  -ref_exp_alti,  Only use stations that match the elevation criteria for a specific experiment (among `list_exp`) or all experiments (use `all`). Not used by default. 

  -exp, --list_exp
                        List of experiments to evaluated

  -var, --list_var
                        List of variables to extract

  -freq {month,bi-month,period}, --score_freq {month,bi-month,period}
                        Score frequency

  -sco, --list_score     List of scores to compute

  -b, --date_beg          Beginning date, format YYYYMMDD, used if freq='period'

  -e, --date_end         End date, format YYYYMMDD, used if freq='period'

*Example*:
see `/examples/run_eval.sh`

## Scripts to generates figures

For each script, an help message can be obtained by typing `python script_name.py -h`

**plot_score_series_domain.py**

* Script used to plot time series of scores for a given set of scores and regions
* For a given score, one figure can be generated by region (`type_graph=single`) of one figure showing all the regions can be generated (`type_graph=multi`)
* The value of `MAX_ALTI` should correspond to the value used when computing the scores. 


*Usage*: plot_score_series_domain.py [-h] [-m MAX_ALTI] [-cf CONFIGFILE]
                                   [-exp LIST_EXP [LIST_EXP ...]]
                                   [-var LIST_VAR [LIST_VAR ...]]
                                   [-reg LIST_REG [LIST_REG ...]]
                                   [-sco LIST_SCORE [LIST_SCORE ...]]
                                   [-t {auto,manual,all}]
                                   [-graph {single,multi}]
                                   [-freq {day,month,bi-month}] [-b DATE_BEG]
                                   [-e DATE_END] [-add_nobs]
                                   [-limit_graph {auto,fix}] [-tile LIST_TILE [LIST_TILE ...]]

*Arguments*
  -m, maximum elevation difference in m used to select the
                        stations (default 150 m)

  -cf, File containing experiments info

  -exp, List of experiments to evaluated

  -var, List of variables to extract

  -reg, List of domains used for the generation of figures

  -sco, List of scores to compute

  -t {auto,manual,all}, Station type to be used when computing scores

  -graph {single,multi}, Type of figure: single or multiple regions on a figure

  -freq {day,month,bi-month}, Score frequency.

  -b, Beginning date, format YYYYMMDD

  -e, End date, format YYYYMMDD

  -add_nobs, Add on the figures the number of observations used to compute the scores

  -limit_graph {auto,fix}, Options to define the limits of the y-axis on the graphs. If set to fix, information provided in the config. file are used to determine the limits of the y axis for each variable and each score. 

  -tile LIST_TILE [LIST_TILE ...],  Add score for specific tile (only for SVS and SVS2). Only active when averaged scores are computed. Can be 'open' and/or 'forest'


*Example*:
see `/examples/run_eval.sh`


**plot_score_histo_period.py**

* Script used to plot barplots summarizing scores for different regions and experiments
* The barplots can be generated for the manual stations (`type=manual`) only or the automatic stations only (`type=auto`). It is also possible to generate figure that shows the results for manual and automatic stations on different subplots (`type=comb` and `superpose` not activated) or  the results for manual and automatic stations on the same subplot  (`type=comb` and `superpose` activated)
* The value of `MAX_ALTI` should correspond to the value used when computing the scores. 



*Usage*:  plot_score_histo_period.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI]
                                  [-exp LIST_EXP [LIST_EXP ...]] [-var LIST_VAR [LIST_VAR ...]]
                                  [-t {auto,manual,all,comb}] [-b DATE_BEG] [-e DATE_END]
                                  [-sco LIST_SCORE [LIST_SCORE ...]] [-superpose]

*Arguments*
  -cf, File containing experiments info

  -m, maximum elevation difference in m used to select the stations (default 150 m)

  -exp, List of experiments to evaluated

  -var, List of variables to extract

  -t {auto,manual,all,comb}, Station type

  -b, Beginning date, format YYYYMMDD

  -e, End date, format YYYYMMDD

  -sco, List of scores to compute (list at least 2 scores)

  -superpose, Superpose resuls of manual and automatic stations (when type_sta==comb)

*Example*:
see `/examples/run_eval.sh`

**plot_maps_score_stations_comp.py**

* Script used to plot maps showing scores for (i) two experiments and comparing them or (ii) one experiment. 
* Two experiments can be specified in `list_exp` and the reference experiment (`exp_ref`) is then selected among these two experiments. 
* One experiment can be specified in `list_exp` and the reference experiment (`exp_ref`) is set to the same value. This allow the generation of maps showing scores for indivivual experiments.  
* The value of `MAX_ALTI` should correspond to the value used when computing the scores. 
* The maps can be generated for manual stations (`type=manual`) only or automatic stations only (`type=auto`). It is also possible to generate figures that show the results for manual and automatic stations on different subplots (`type=both`) or the results for manual and automatic stations on the same subplot with different markers for automatic and manual stations (`type=all`)
* The extend of the maps is defined based on the extend of the Emet domains speficied in `list_reg`.
* A list of regions can be provided in `sel_reg` to resctrict the stations shown on the map to certain regions. By default, only the stations within the `list_reg` regions will be shown on all figures created. 
* If needed, more domains can be added in `util_score.py` (see function `emetDomain`)
* If CRPS is being compared, this is in the form of the CRPS skill score, as defined by equation 9 in https://tc.copernicus.org/articles/16/1281/2022/. This modified CRPSS equation means improvements are positive and degradations are negative. CRPS of an ensemble can be compared to a deterministic forecast, where the CRPS of the deterministic forecast is the mean absolute error.

*Usage*:  plot_maps_score_stations_comp.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI] [-exp LIST_EXP [LIST_EXP ...]]
                                        [-var LIST_VAR [LIST_VAR ...]] [-sco LIST_SCORE [LIST_SCORE ...]] [-ref EXP_REF]
                                        [-t {auto,manual,all,both}] [-freq {period}] [-reg LIST_REG [LIST_REG ...]]  [-sel_reg LIST_SEL_REG ]
                                        [-b DATE_BEG] [-e DATE_END] [-add_elev] [-nobs NOBS_MIN]

*Arguments*:

  -cf, --configfile,     File containing experiments info

  -m, --max_alti,        Maximum elevation difference in m used to select the stations

  -exp, --list_exp       List of experiments to evaluate

  -var, --list_var       List of variables to evalute

  -sco, --list_score  List of scores to plot on the maps 

  -ref, --exp_ref  Reference experiment (to be selected among list_exp)

  -t {auto,manual,all,both}, --type_sta Station type to be used when plotting maps

  -freq {period} , --score_freq   Score frequency

  -reg, --list_reg    List of domains used for the generation of maps

  -sel_reg, --list_sel_reg    List of domains used for the selection of stations shown on the maps

  -b, --date_beg     Beginning date, format YYYYMMDD

  -e, --date_end     End date, format YYYYMMDD

  -add_elev          Add elevation of the grid in the background of the map
  
  -add_poly          Add polygon of region selected to the map

  -nobs, --nobs_min  Minimal number of observations required to plot score

*Example*:
see `/examples/run_eval.sh`

**plot_score_card_comb.py**

* Script used to plot score card comparing two experiments for a given variable for a given period for several regions. 
* Two experiments must be specified in `list_exp` and the reference experiment (`exp_ref`) is then selected among these two experiments. 
* The value of `MAX_ALTI` should correspond to the value used when computing the scores. 
* Relative changes in three scores are shown on the score card: bias, STDE and RMSE.
* The score card shows separate results for manual and automatic stations.
* The scores must be computed before plotting the score card using `compute_score_snow_domain.py` for manual and automatic stations selecting the`period` option for score frequqncy. 

*Usage*:  plot_score_card_comb.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI] [-exp LIST_EXP [LIST_EXP ...]]
                                        [-var LIST_VAR [LIST_VAR ...]] [-ref EXP_REF]
                                        [-b DATE_BEG] [-e DATE_END] 

*Arguments*:

  -cf, --configfile,     File containing experiments info

  -m, --max_alti,        Maximum elevation difference in m used to select the stations

  -exp, --list_exp       List of experiments to evaluate

  -var, --list_var       List of variables to evalute

  -ref, --exp_ref      Reference experiment (to be selected among list_exp)

  -b, --date_beg     Beginning date, format YYYYMMDD

  -e, --date_end     End date, format YYYYMMDD

*Example*:
see `/examples/run_eval.sh`


**plot_time_series_snow.py**

* Script used to plot time series of observed and simulated snow variables 
* The images (png format) are stored in subdirectories (one per region) under `$dir_analysis/snow/series`
* Time seres are useful to better understand model behaviour and to interpret scores. 
* The user can define the value of the maximum elevation difference between the stations and the corresponding grid cell used to select the stations which are plotted. 
* The user can define the value of the maximum elevation difference between the stations and the corresponding grid cell used to select the relevant stations for the evaluation. The key `ref_exp_alti` allows the selection of stations to be restricted to the stations that match the selection criteria for a specific experiment (chosen among `list_exp`) or all experiments (use `ref_exp_alti=all`). Note that by default the elevation criteria is applied for each experiment individually  
* To visualize snow ensembles, the user can select different approaches to plot the spread of the ensemble.  
* The option `add_vgh` allows the user to plot time series for the snow below high vegetation in addition to the time series in the open or the agrregated one. For example, `SMH` will be added on the graph if the user ask to plot `SML` with the option `add_vgh` activated. 
* By default, the script used the maximal number of CPU available to speed up the generation of time series. The number of proc. `n` can be specified by the user. 

*Usage* plot_time_series_snow.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI] [-ref_exp_alti [EXP]]
                                [-exp LIST_EXP [LIST_EXP ...]]
                                [-reg LIST_REG [LIST_REG ...]]
                                [-var LIST_VAR [LIST_VAR ...]] [-b DATE_BEG]
                                [-e DATE_END] [-ens PLOT_ENS] [-add_vgh] [-n]

*Arguments*
  -cf, File containing experiments info

  -m, Maximum elevation difference in m used to select the
                        stations (default: 150 m)

  -ref_exp_alti,  Only use stations that match the elevation criteria for a specific experiment (among `list_exp`) or all experiments (use `all`). Not used by default. 

  -exp, List of experiments to evaluated (ID in config file)

  -reg, List of domains used for the evaluation 

  -var, List of variables to be plotted

  -b, Beginning date, format YYYYMMDD

  -e, End date, format YYYYMMDD   

  -ens,{'none','all_members','std','perc_5_95'} Option to plot the spread of the ensembles

  -add_vgh, option to add time series for the snow below high vegetation

  -n, Number of processor used for parallel generation of figures [int] 

*Example*: 
see `/examples/run_eval.sh`


**generate_interactive_map.py**

* Script used to generate interactive maps comparing scores between two experiments 
* Clicking on the location of the stations on the interactive map generate a popup that shows the time series of the variable of interest for the selected station
* Regions are specified in `list_reg` and maps will be generated for each region showing only the stations from the corresponding region.  
* The times series for the stations specified in `list_reg` must have been previoulys generated using the script `plot_time_series_snow.py` (see above)
* Two experiments can be specified in `list_exp` and the reference experiment (`exp_ref`) is then selected among these two experiments. 
* The value of `MAX_ALTI` should correspond to the value used when computing the scores. 
* The maps shows manual stations with a square and automatic stations with a circle


*Usage*:  generate_interactive_map.py [-h] [-cf CONFIGFILE] [-m MAX_ALTI] [-exp LIST_EXP [LIST_EXP ...]]
                                        [-var LIST_VAR [LIST_VAR ...]] [-sco LIST_SCORE [LIST_SCORE ...]] [-ref EXP_REF]
                                        [-freq {period}] [-reg LIST_REG [LIST_REG ...]] 
                                        [-b DATE_BEG] [-e DATE_END]

*Arguments*:

  -cf, --configfile,     File containing experiments info

  -m, --max_alti,        Maximum elevation difference in m used to select the stations

  -exp, --list_exp       List of experiments to evaluate

  -var, --list_var       List of variables to evalute

  -sco, --list_score  List of scores to plot on the maps 

  -ref, --exp_ref  Reference experiment (to be selected among list_exp)

  -freq {period} , --score_freq   Score frequency

  -reg, --list_reg    List of domains used for the generation of maps

  -b, --date_beg     Beginning date, format YYYYMMDD

  -e, --date_end     End date, format YYYYMMDD


*Example*:
see `/examples/run_eval.sh`


