# This file contains the variables needed by the different scripts
# No modifications are required by the user

# Dictionary that describes the association between observed and simulated variables
dic_var = {'SMA':'snw','SDA':'snd','SML':'snw', 'SMH':'snw','SNDP':'snd', 'SVDP':'snd','SNDN':'den','SVDN':'den','DNA':'den'}

# Dictionary containing maximal values applied in range thresholding to remove unrealistic data
dic_fac_max = {'SMA':5000.,'SMH':5000.,'SML':5000.,'SDA':6.,'SNDP':6., 'SVDP':6.,'DNA':900,'SNDN':900,'SVDN':900}

# Dictionary containing the variables units used when generating the graphics
dic_var_units={'SMA':'kg m$^{-2}$','SMH':'kg m$^{-2}$','SDA':'m','SML':'kg m$^{-2}$','SNDP':'m','SVDP':'m','DNA':'kg m$^{-3}$','SNDN':'kg m$^{-3}$','SVDN':'kg m$^{-3}$'}

# Dictionary containing the variables names and the associated title used when generating the graphics
dic_varname={'SMA':'SWE','SDA':'Snow Depth','SML':'SWE Open', 'SMH':'SWE Forest','SNDP':'Snow Depth Open', 'SVDP':'Snow Depth Forest','SNDN':'Snow Density Open','SVDN':'Snow Density Forest','DNA':'Snow Density '}

# Dictionary containing the correspondance between variable in the open and variable in the forest
dic_vgh={'SML':'SMH','SMA':'SMH','SNDP':'SVDP','SDA':'SVDP'}

#Dictionary used to inform the plotting of scores for distinct tile of SVS and SVS2
dic_tile = {'SMA':{'open':'SML','forest':'SMH'}}
dic_style_tile = {'open':'--','forest':'-.'}

# Dictionary containing domains names and associated abbreviations
dic_reg = {'NB':'NB','SNT':'USA West','BC':'BC','AB':'AB','NWT':'NWT','YUK':'YUK','ONR_OPG':'ON','CBC':'Coastal CAN','IBC':'Interior CAN','RBC':'Rockies CAN','CUS':'Coastal US','IUS':'Interior US','RUS':'Rockies US','AlaskaplusCanadianArctic':'AA','BritishColumbia2':'WC', 'AlbertaSaskatchewan':'AS', 'CanadaEast':'EastCan','UnitedStatesOfAmericaWest':'WU','UnitedStatesOfAmericaEast':'EU','mtn_1':'Alaska','mtn_2':'Appalach.','mtn_3':'Brooks','mtn_4':'Cascades','mtn_5':'Coast','mtn_6':'Great Basin','mtn_7':'Mackenzie','mtn_8':'Rockies Can.','mtn_9':'Sierra Nevada','mtn_10':'Rockies US','mtn_11':'Torngat','CanadaWest':'WestCan', \
'eco_1':'Arctic Cordillera','eco_2':'Tundra','eco_3':'Taiga','eco_4':'Hudson Plain','eco_5':'N. For.','eco_6':'N.W. For. Mtns','eco_7':'W. Coast For.','eco_8':'E. Tempe. For.','eco_10':'N. Am. Desert','eco_9':'Great Plains','eco_11':'Medit. California','eco_12':'S. semi-arid Highlands','eco_13':'Temperate Sierras',\
'Pacific_North_West_CLIM':'Bk_PacificNW','North_Rockies_CLIM':'Bk_NRockies','Mt_West_CLIM':'Bk_Mt_West',\
'Central_CLIM':'Bk_Central','Great_Lakes_CLIM':'Bk_GreatLakes','Boreal_CLIM':'Bk_Boreal','East_CLIM':'Bk_East','Prairie_CLIM':'Bk_Prairie', \
'Great_Basin_CLIM':'Bk_GreatBasin','West_Boreal_CLIM':'Bk_WestBoreal','East_Boreal_CLIM':'Bk_EastBoreal','Arctic_Land_CLIM':'Bk_ArcticLand','Desert_CLIM':'Bk_Desert', \
'Pacific_South_West_CLIM':'Bk_PacificSW',\
'Arctic_plus_CLIM':'Bk_ArcticPlus','Central_Tundra_CLIM':'Bk_CentralTundra','East_Taiga_CLIM':'Bk_EastTaiga','East_Tundra_CLIM':'Bk_EastTundra',\
'North_Atlantic_CLIM':'Bk_NorthAtlantic','North_Plains_CLIM':'Bk_NorthPlains','West_Taiga_CLIM':'Bk_WestTaiga','West_Tundra_CLIM':'Bk_WestTundra','Taigas_CLIM':'Bk_Taigas',\
'HRDPS_National':'HRDPS_Nat','NorthAmericaPlus':'NorAmPlus', \
'Pac_CAN':'Pac_CAN','Int_CAN':'Int_CAN','Roc_CAN':'Roc_CAN', \
'Pac_USA':'Pac_USA','Int_USA':'Int_USA','Roc_USA':'Roc_USA', \
'Canada':'Canada','OntarioQuebec':'OntarioQuebec','Prairies':'Prairies','All':'All', \
'GLS':'GLS','YUK':'YUK','SKA':'SKA','MCK':'MCK','GSL':'GSL','CHU':'CHU','FRA':'FRA','NEL':'NEL',\
'SNX23_BCEF':'SNX23_BCEF','SNX23_CPCR':'SNX23_CPCR','SNX23_FLCF':'SNX23_FLCF','SNX23_UKT':'SNX23_UKT','SNX23_ACP':'SNX23_ACP',\
'FMO':'FMO','BJA':'BJA','UMQ':'UMQ','WHU':'WHU','KUJ':'KUJ','RES':'RES','CAB':'CAB', \
}

# Dictionary containg the names of the scores used for each figure
dic_score_title={'bias':'Bias','rmse':'RMSE', 'medae':'Med. Abs. Error','nse':'NSE','pbias':'PBIAS','cor':'Corr. coeff.','stde':'Std Dev. Error','moymod':'Mean','nrmse':'nRMSE','kge09':'KGE-09','fbi':'FBI','hss':'HSS','kge12':'KGE-12','ss':'Spread-Skill', 'crps':'CRPS', 'crps_pot':'Potential CRPS', 'crps_rel': 'CRPS Reliability', 'rbias':'Relative Bias','beta':'beta KGE','gamma':'gamma KGE','ets':'ETS'}

#Dictionary containing the information relative to the snow databases
dic_snow_data={
    'CANSWE':{'type':'snow','path':'/fs/site7/eccc/crd/cps/data/CanSWE/CanSWE_2025/Updated_Data_ECCC/ECCC_CanSWE-CanEEN_1928-2025_v8.nc'},
}

# Add black list of stations
station_black_list=['BCE-4A34P','BCE-4A35P','BCE-1D18P','BCE-1C14P','UU-FT_FtrRdg','UU-FT_PlFrst','UU-MC-FisRdgFrst','UU-MC-VVFrst','UU-MC-UpFrst','UU-MC-FisSFFrst','UU-MC-FisN','UU-MC-FisS','UU-MC-FisRdgTp','AVCAN_CAA-ITPITP_WX_PLOT_RMR','AVCAN_LAST_FRONTIER_HSBELL_2_LDG','AVCAN_ASTER_LAKE','AVCAN_BURSTALL_PASS','Coos_Bay_8_SW']
