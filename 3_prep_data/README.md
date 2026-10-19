# Scripts for the preparation and the extraction of snow data 

## Information 
This step of the evaluation process requires to extract and merged daily observed snow data from different networks and then to extract the simulated time series at the locations corresponding to the locations of the observations.  

## Networks
Snow data from the following sources can be used to evaluate model performances:

| Network Name  | Details | Type of data |  Dates | 
|:----------:|:-------------:|:-------------:|:-------------:| 
| CANSWE | Canadian Historical SWE dataset  | SWE, SD and derived bulk snow density (manual+ automatic) (Vionnet et al., 2021)|  1928-2025|  
| CANSD | Canadian Historical SD dataset  |  SD from ECCC manual and automatic stations (Brown et al., 2021) |  1840-2017|
| NHSWE |Northern Hemisphere SWE dataset (Fontrodona-Bach et al., 2023)  | SD (automatic) | 1950-2022  |

**Note**: 
* The simulatenous use of the datasets `CANSD` and `NHSWE` will generate duplicates. 

## Scripts

For each script, an help message can be obtained by typing `python script_name.py -h`

**1_prep_snow_data.py**

* Script that extracts snow data from different networks (including CanSWE) over a given time period.
* Obsevations must be available in a netcdf format that corresponds to the CanSWE format. The paths to the netcdf files is given in the config file *config/config_snow.py*
* We recommend the user to carry out the extraction over the period covering the whole water year of interest (from September 1st to August 31)
* The combined snow and soil data are stored in a final netcdf file `snow_data.nc`. 

*Usage*: 1_prep_snow_data.py [-h] [-cf CONFIGFILE]
                           [-src LIST_SRC [LIST_SRC ...]] [-b DATE_BEG]
                           [-e DATE_END]

*Arguments*:

  -cf, --configfile
                        File containing experiments info

  -src, --list_src
                        List of sources to consider among (see table above for more details)

  -b, --date_beg
                        Beginning date, format YYYYMMDD

  -e, --date_end
                        End date, format YYYYMMDD


*Example*: 
`python 1_prep_snow_data.py -cf ../examples/config_exp_CalDAS_MIST.py -src CANSWE SNT -b 20190901 -e 20100731`


**2_extract_SVS2_snow.py**

* Extract the times series of snow variables simulated by SVS2 at the positions of the stations listed in the file `snow_data.nc` obtained from `1_prep_snow_data.py`. 
* The requested snow variables need to be provided as input to the extraction script


*Usage* 2_extract_SVS2_snow.py [-h] [-cf CONFIGFILE] [-d DIST_CRIT]
                             [-exp LIST_EXP [LIST_EXP ...]]
                             [-var LIST_VAR [LIST_VAR ...]] [-elev_4near]

*Arguments*

  -cf, --configfile
                        File containing experiments info


  -d, --dist_crit
                        Critical distance in km used to remove stations from
                        the analysis
  -exp, --list_exp
                        List of experiments to evaluated (ID defined in the config file)

  -var, --list_var
                        List of variables to extract

  -elev_4near           Select the grid point with the smallest elevation
                        difference among the 4 nearest grid points. Otherwise,
                        the nearest grid point is used

*Example*: 
`python 2_extract_SVS2_snow.py -cf ../examples/config_svs2_era5l.py -d 3 -exp SVS2 -var SDA  -elev_4near`

**3_extract_era5_snow.py**

* Extract the ERA5-Land simulated times series of snow variables at the position of the stations listed in the file `snow_data.nc` obtained from `1_prep_snow_data.py`. 
* The requested snow variables need to be provided as input to the extraction script


*Usage* 3_extract_era5_snow.py [-h] [-cf CONFIGFILE] [-d DIST_CRIT]
                             [-exp LIST_EXP [LIST_EXP ...]]
                             [-var LIST_VAR [LIST_VAR ...]] [-elev_4near]
                             [-b DATE_BEG] [-e DATE_END]

*Arguments*

  -cf, --configfile
                        File containing experiments info

  -d, --dist_crit
                        Critical distance in km used to remove stations from
                        the analysis
  -exp, --list_exp
                        List of experiments to evaluated (ID defined in the config file)

  -var, --list_var
                        List of variables to extract

  -elev_4near           Select the grid point with the smallest elevation
                        difference among the 4 nearest grid points. Otherwise,
                        the nearest grid point is used

  -b,           Beginning date for extraction, format YYYYMMDD

  -e,            End date for extraction,, format YYYYMMDD


*Example*: 
`python 3_extract_era5_snow.py -cf ../examples/config_svs2_era5l.py -d 3 -exp ERA5L -var SMA -d 20141001 -e 20160901`
