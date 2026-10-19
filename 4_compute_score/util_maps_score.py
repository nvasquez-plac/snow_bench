import pdb
import numpy as np 
import datetime as dt 
import matplotlib as mpl 
mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap, maskoceans
import pandas as pd
import util_score as util
import geopandas as gpd
import os,sys
import base64
import branca.colormap as branca_colormap
from folium import plugins
import folium
from folium import Tooltip
from PIL import Image
import io
import matplotlib.cm as cm  # For colormap

#import palettable as pal

from palettable.scientific.diverging import Vik_5
from palettable.scientific.diverging import Vik_5_r
#from palettable.scientific.sequential import Batlow_5_r
#from palettable.scientific.sequential import Davos_5_r


def get_fig_shape(nexp):
  if(nexp<3):
    ncol=nexp+1
    nrow=1
  elif(nexp==3):  
    ncol=2
    nrow=2
  elif(nexp==4):  
    ncol=3
    nrow=2
  elif(nexp==5):  
    ncol=3
    nrow=2
  return([nrow,ncol]) 

def limit_domain(reg):
# Define lat/lon limits for the 
    if(reg=='South_Ontario'):
        return([41.0,47.0,-84.0,-74.0])
    elif(reg=='North_Ontario'):
        return([45,52.0,-95.0,-80.0])
    elif(reg=='BC'):
        return([47.5,58.0,-132,-114])
    elif(reg=='South_BC'):
        return([45.3,55.25,-129.0,-111.5])
    elif(reg=='Wash_State'):
        return([45.5,49.5,-124.5,-119.0])
    elif(reg=='Vancouver'):
        return([48.25,51.5,-126.5,-119.0])
    elif(reg=='Rockies'):
        return([48.5,52.5,-119,-112.5])
    elif(reg=='Ontario'):
        return([38,57.0,-98.0,-74.0])
    elif(reg=='OnQc'):
        return([38,60.0,-98.0,-60.0])
    elif(reg=='WestCan'):
        return([47.5,72.0,-145,-95])
    elif(reg=='EastCan'):
        return([38,65.0,-98.0,-52.0])
    elif(reg=='WestUS'):
        return([30,49.5,-130,-95])


def limit_domain2(reg):
    if(reg=='NorAm'):
      return([6500000,6000000,58.5,-100])
    if(reg=='WestUS'):
      return([2000000,2000000,41.5,-115])
    if(reg=='WestCan'):
      return([4000000,2500000,60,-122])
    if(reg=='EastCan'):
      return([1900000,1700000,48,-75])
    if(reg=='NorAm2'):
      return([7500000,7300000,52,-100])


def limit_domain3(reg,xgeo,X):

    if(hasattr(X,'dic_shp')):
        dic_shp = X.dic_shp
        dir_shp = X.dir_shp
    else:
        dic_shp = {}
        dir_shp = None

    list_shp= [key for key in dic_shp]  

    if(reg=='All'):
        lats=xgeo.lat.values[:,:]
        lons=xgeo.lon.values[:,:]-360.0

    elif(reg in list_shp): # Domain defined using shapefiles provided by the users   
        # Path to the corresponding shapefile 
        fic_shp = dir_shp+'/'+dic_shp[reg]['id']+'.shp'
        domain_shp = gpd.read_file(fic_shp).to_crs(4326)
        bnd=domain_shp['geometry'].bounds
        max_lat= bnd.maxy
        if isinstance(max_lat, pd.Series):
            max_lat = float(max_lat.iloc[0])
        min_lat= bnd.miny
        if isinstance(min_lat, pd.Series):
            min_lat = float(min_lat.iloc[0])
        max_lon= bnd.maxx
        if isinstance(max_lon, pd.Series):
            max_lon = float(max_lon.iloc[0])
        min_lon= bnd.minx
        if isinstance(min_lon, pd.Series):
            min_lon = float(min_lon.iloc[0])
    else:
        lats,lons,poly = util.emetDomain(reg)

    delta_lat = 0.05*(np.max(lats)-np.min(lats))
    delta_lon = 0.05*(np.max(lons)-np.min(lons))

    return([np.min(lats)-delta_lat,np.max(lats)+delta_lat,np.min(lons)-delta_lon,np.max(lons)+delta_lon])


def limit_domain4(reg,xgeo,X):


    if(hasattr(X,'dic_shp')):
        dic_shp = X.dic_shp
        dir_shp = X.dir_shp
    else:
        dic_shp = {}
        dir_shp = None
    list_shp= [key for key in dic_shp]          

    if(reg=='All'):
        lats=xgeo.lat.values[:,:]
        lons=xgeo.lon.values[:,:]-360.0
        max_lat= np.max(lats)
        min_lat= np.min(lats)
        max_lon= np.max(lons)
        min_lon= np.min(lons)
        
    elif(reg in list_shp): # Domain defined using shapefiles provided by the users   
        # Path to the corresponding shapefile 
        fic_shp = dir_shp+'/'+dic_shp[reg]['id']+'.shp'
        domain_shp = gpd.read_file(fic_shp).to_crs(4326)
        bnd=domain_shp['geometry'].bounds
        max_lat= bnd.maxy
        if isinstance(max_lat, pd.Series):
            max_lat = float(max_lat.iloc[0])
        min_lat= bnd.miny
        if isinstance(min_lat, pd.Series):
            min_lat = float(min_lat.iloc[0])
        max_lon= bnd.maxx
        if isinstance(max_lon, pd.Series):
            max_lon = float(max_lon.iloc[0])
        min_lon= bnd.minx
        if isinstance(min_lon, pd.Series):
            min_lon = float(min_lon.iloc[0])
    

    else:
        lats,lons,poly = util.emetDomain(reg)
        max_lat= np.max(lats)
        min_lat= np.min(lats)
        max_lon= np.max(lons)
        min_lon= np.min(lons)


    lat0 = (max_lat+min_lat)/2.
    lon0 = (max_lon+min_lon)/2.

    dlat= max_lat-min_lat

    height = 1.1* get_distance(max_lat,lon0,min_lat,lon0)*1000.
    width = get_distance(min_lat,max_lon,min_lat,min_lon)*1000.

    return([width,height,lat0,lon0,dlat])


def calc_poly(reg,xgeo,X):
    if(hasattr(X,'dic_shp')):
        dic_shp = X.dic_shp
        dir_shp = X.dir_shp
    else:
        dic_shp = {}
        dir_shp = None
    list_shp= [key for key in dic_shp]          
        
    if(reg in list_shp): # Domain defined using shapefiles provided by the users   
        # Path to the corresponding shapefile 
        fic_shp = dir_shp+'/'+dic_shp[reg]['id']+'.shp'
        domain_shp = gpd.read_file(fic_shp).to_crs(4326)
        poly = domain_shp.geometry.iloc[0].exterior.coords[:]
        # Filter out tuples with more than two elements
        poly = [coord[:2] for coord in poly if len(coord) >= 2] 
        lons, lats = zip(*poly)

    else:
        lats,lons,poly = util.emetDomain(reg)
        lats = np.append(lats, lats[0])
        lons = np.append(lons, lons[0])
    
    return([lats,lons])


def get_distance(lat1,lon1,lat2,lon2): 
    from math import sin, cos, sqrt, atan2, radians

    # Approximate radius of earth in km
    R = 6371.0
    
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance
    #print("Result: ", distance)
    #print("Should be: ", 278.546, "km")


def add_fig_score(ax,reg,var,res,score,exp,t_mes,plot_type,xgeo,var_geo,ladd_elev,lplot_cbar,X,X2,nobs_min,ladd_poly,**exp_ref):    


    lim_dom = limit_domain4(reg,xgeo,X)
    

    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    limits = X.dic_limits    

    if(plot_type == 'val_score'): 
        # Get units
      uu = dic_units[var]
      units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'ss':'-','crps':uu,'crps_rel':uu,'crps_pot':uu,'crpss':'-','rbias':'-'}
      min_g = limits[var]['min_g']
      max_g  = limits[var]['max_g']

    elif(plot_type == 'comp_ref'):  
      min_g = {'bias':-100,'rmse':-50,'medae':0,'nse':-1,'pbias':-50,'cor':-1,'stde':0,'nrmse':0,'kge09':0,'ss':0,'crps':0,'crpss':-1,'rbias':0}
      max_g = {'bias':100,'rmse':50,'medae':100,'nse':1,'pbias':50,'cor':1,'stde':200,'nrmse':2,'kge09':1,'ss':2,'crps':4,'crpss':1,'rbias':10}
      uu = '%'
      units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'ss':'%','crps':uu,'crps_pot':uu,'crps_rel':uu,'crpss':'-','rbias':'-'}


    if(plot_type == 'val_score'): 
      cmap = plt.cm.YlGnBu
      if score in ['bias','pbias','kge09','ss']:
        #cmap = plt.cm.RdYlBu
        cmap = plt.cm.RdBu
        #cmap = plt.cm.seismic_r
      if score in ['rmse','nrmse','stde','crps',]:
        cmap = plt.cm.YlGnBu

    elif(plot_type == 'comp_ref'): 
        #cmap  =  Vik_5_r.mpl_colormap
        cmap = plt.cm.RdBu_r
    
    if(plot_type == 'val_score'):   
        mod = res[score].loc[(dict(variable=var,exp=exp))].values[:,0]

        #val = np.percentile(np.abs(mod[~np.isnan(mod)]),95)
        #if(score in ['bias','pbias']):
        #     min_g[score] = -1.0*val
        #if(score in ['pbias','bias','rmse']):    
        #     max_g[score] = val

    elif(plot_type == 'comp_ref'):  
         sco_ref = res[score].loc[dict(variable=var,exp=exp_ref['exp_ref'])].values[:,0]
         sco_comp = res[score].loc[dict(variable=var,exp=exp)].values[:,0]

         if(score=='bias'):
             sco_norm = res['rmse'].loc[dict(variable=var,exp=exp_ref['exp_ref'])].values[:,0]
             mod = - (np.abs(sco_comp)-np.abs(sco_ref))/np.abs(sco_norm) *100. 
         elif(score=='pbias'):
             mod = - (np.abs(sco_comp)-np.abs(sco_ref))
         elif(score=='crps'):
             # As defind in Sec. 3.2 of https://tc.copernicus.org/articles/16/1281/2022/
             mod = [0] * len(sco_ref)
             for i in range(len(sco_comp)):
                 if sco_comp[i] < sco_ref[i]:
                     mod[i] = 1 - (sco_comp[i]/sco_ref[i])
                 else:
                     mod[i] = (sco_ref[i]/sco_comp[i]) - 1  
             mod = np.array(mod)
         elif(score=='ss'):
             #absolute difference each score is from 1 (ideal score)
             abs_diff_ref = abs(1-sco_ref)
             abs_diff_comp = abs(1-sco_comp)
             #Percent change in absolute difference to 1
             mod = -(abs_diff_comp-abs_diff_ref)/abs_diff_ref *100. 
         else: 
             mod = -(sco_comp-sco_ref)/sco_ref *100. 
         
         val = min(np.percentile(np.abs(mod[~np.isnan(mod)]),95),100.)
         min_g[score] = -1.0*val
         max_g[score] = val
             
    nobs = res['nobs'].loc[dict(variable=var,exp=exp)].values[:,0]

    # Select only stations with a minimum number of valid observations
    mask_sel_obs = nobs>= nobs_min

    mask_mod = ~np.isnan(mod)
    #val = mod[~mask_mod]
    lat_val = res['lat'].values
    lon_val = res['lon'].values

    mask_man = (res['type_mes'].values<=1)
    mask_auto = (res['type_mes'].values>1)

    mask_auto_ok = mask_auto & mask_mod & mask_sel_obs
    mask_man_ok = mask_man & mask_mod & mask_sel_obs


    #m = Basemap(llcrnrlat=lim_dom[0], urcrnrlat=lim_dom[1],\
    #    llcrnrlon=lim_dom[2], urcrnrlon=lim_dom[3],projection='lcc',lat_1=45.,lat_2=55,lon_0= (lim_dom[2]+lim_dom[3])/2, resolution='h',ax=ax)

    #print(lim_dom[2])
    #m = Basemap(width=lim_dom[0],height=lim_dom[1],projection='lcc',\
    #        resolution='l',lat_1=45.,lat_2=55,lat_0=lim_dom[2],lon_0=lim_dom[3],ax=ax, rsphere = 6370997)    

    #m = Basemap(width=lim_dom[0],height=lim_dom[1],projection='lcc',\
    #        resolution='l',lat_1=lim_dom[2]-lim_dom[4]/2.,lat_2=lim_dom[2]+lim_dom[4]/2.,lat_0=lim_dom[2],lon_0=lim_dom[3],ax=ax, rsphere = 6370997)      

    m = Basemap(width=lim_dom[0],height=lim_dom[1],projection='lcc',area_thresh=5000.,\
            resolution='h',lat_1=lim_dom[2]-lim_dom[4]/2.,lat_2=lim_dom[2]+lim_dom[4]/2.,lat_0=lim_dom[2],lon_0=lim_dom[3],ax=ax, rsphere = 6370997)      


    #m = Basemap(width=lim_dom[0],height=lim_dom[1],projection='lcc',\
    #    resolution='l',lat_1=lim_dom[2],lat_2=lim_dom[2],lat_0=lim_dom[2],lon_0=lim_dom[3],ax=ax, rsphere = 6370997)


    # Create a polygon for regions
    if(ladd_poly):
        
        lats, lons = calc_poly(reg,xgeo,X)
        x, y = m(lons, lats)
        m.plot(x, y, linestyle='-', linewidth='0.75', color='darkblue')

    if(ladd_elev):   
        xpt, ypt = m(xgeo.lon.values-360.0, xgeo.lat.values) 
        palette = plt.cm.gray_r
        #zs = xgeo[var_geo].values[0,:,:]
        #pdb.set_trace()
        lev2 = np.arange(0,3500,50)
        norm = mpl.colors.BoundaryNorm(lev2, palette.N)
        PLOT = m.contourf(xpt, ypt,  xgeo[var_geo].values[0,:,:], cmap=palette, norm=norm, levels = lev2, extend='both', antialiased=True,alpha=1)
        PLOT = m.contourf(xpt, ypt,  xgeo[var_geo].values[0,:,:], cmap=palette, norm=norm, levels = lev2, extend='both', antialiased=True,alpha=1)
    else:
        m.fillcontinents(color='lightgrey',lake_color='white')
    m.drawcoastlines(color='#555555', linewidth=0.5)
    m.drawcountries(linewidth=0.5, color='#555555')
    m.drawstates(linewidth=0.5, color='#555555')
   # m.drawrivers(color='b')   

    if(t_mes == 'all' or t_mes=='auto'): 
       xsta,ysta = m(lon_val[mask_auto_ok], lat_val[mask_auto_ok])
       mmb = m.scatter(xsta,ysta, marker='o',c = mod[mask_auto_ok], cmap=cmap,vmin = min_g[score], vmax=max_g[score],s=15,zorder=10,edgecolor='black',linewidth=0.4)

    if(t_mes == 'all' or t_mes=='manual'):
       xsta,ysta = m(lon_val[mask_man_ok], lat_val[mask_man_ok])
       mmb = m.scatter(xsta,ysta, marker='s',c = mod[mask_man_ok], cmap=cmap,vmin = min_g[score], vmax=max_g[score],s=15,zorder=10,edgecolor='black',linewidth=0.35)
    
    if(lplot_cbar): 
       cbar = m.colorbar(mmb, location='bottom', pad='5%',extend='both')
   # cbar = m.colorbar(mmb, location='bottom',extend='both')
       if(plot_type == 'val_score'):  
          cbar.set_label(dic_title[score]+' ('+units[score]+')',size=10 )
       elif(plot_type == 'comp_ref'): 
          cbar.set_label('Change in '+dic_title[score]+' ('+units[score]+')',size=10 )
          if(score=='crps'):
              cbar.set_label('CRPSS',size=10 )
          elif(score=='ss'):
              cbar.set_label('Change in Absolute Difference from 1 ('+units[score]+')',size=10)
    
    if(plot_type == 'val_score'):  
        titre = dic_title[score]+' '+dic_var[var]+' '+exp+' (sta. '+t_mes+')'
    elif(plot_type == 'comp_ref'):  
        if score=='crps':
            titre = 'CRPSS '+dic_var[var]+' of '+exp+' and '+exp_ref['exp_ref']+' (sta. '+t_mes+')'
        else:
            titre = 'Perf. change in '+dic_title[score]+' '+dic_var[var]+' '+exp+'-'+exp_ref['exp_ref']+' (sta. '+t_mes+')'
        

    ax.set_title(titre,size=8)


def add_fig_best(ax,reg,var,res,score,list_exp,t_mes,xgeo,cfg_exp):   

    lim_dom = limit_domain2(reg)

    mod_exp= {}
    for exp in list_exp: 
         if(score in ['pbias','bias']):
             mod_exp[exp] = np.abs(res[score].loc[(dict(variable=var,exp=exp))].values)
         else:
             mod_exp[exp] = res[score].loc[(dict(variable=var,exp=exp))].values


    nobs = res['nobs'].loc[dict(variable=var,exp=list_exp[0])].values
    mask_sel_obs = nobs> 5

    mask_mod = ~np.isnan(mod_exp[list_exp[0]])

    #val = mod[~mask_mod]
    lat_val = res['lat'].values
    lon_val = res['lon'].values

    mask_man = (res['type_mes'].values<=1)
    mask_auto = (res['type_mes'].values>1)

    mask_auto_ok = mask_auto & mask_mod & mask_sel_obs
    mask_man_ok = mask_man & mask_mod & mask_sel_obs



    all_score = pd.DataFrame.from_dict(mod_exp)
    best_exp=all_score.idxmin(axis=1)


    m = Basemap(width=lim_dom[0],height=lim_dom[1],projection='lcc',
             resolution='l',lat_1=45.,lat_2=55,lat_0=lim_dom[2],lon_0=lim_dom[3],ax=ax)


    if(reg != 'NorAm2'): 
        m.drawcoastlines(color='#555555', linewidth=0.75)
        m.drawcountries(linewidth=0.5, color='#555555')
        m.drawstates(linewidth=0.5, color='#555555')
   # m.drawrivers(color='b')   
        xpt, ypt = m(xgeo.lon.values-360.0, xgeo.lat.values) 
        palette = plt.cm.gray_r
        lev2 = np.arange(0,3500,200)
        norm = mpl.colors.BoundaryNorm(lev2, palette.N)
        PLOT = m.contourf(xpt, ypt,  xgeo.MF.values[0,:,:], cmap=palette, norm=norm, levels = lev2, extend='both', antialiased=True,alpha=1)
    else:
        m.drawlsmask(resolution='l')

    lat_sel = res['lat'].values
    lon_sel = res['lon'].values
    for iexp,exp in enumerate(list_exp):
        mask_exp = (best_exp==exp)

        if(t_mes == 'all' or t_mes=='man'): 
           lon_exp = lon_sel[mask_exp & mask_man_ok ]
           lat_exp = lat_sel[mask_exp & mask_man_ok]
           xsta,ysta = m(lon_exp, lat_exp)
           mmb = m.scatter(xsta,ysta, marker='s',facecolor=cfg_exp[exp]['col'],s=13,zorder=10,edgecolor='black',label=exp,linewidth=0.5)

        if(t_mes == 'all' or t_mes=='auto'): 
           lon_exp = lon_sel[mask_exp & mask_auto_ok ]
           lat_exp = lat_sel[mask_exp & mask_auto_ok]
           xsta,ysta = m(lon_exp, lat_exp)
           mmb = m.scatter(xsta,ysta, marker='o',facecolor=cfg_exp[exp]['col'],s=13,zorder=10,edgecolor='black',label=exp,linewidth=0.5)


    ax.legend(loc='lower left',ncol=3,fontsize=8)
    ax.set_title('Best experiment')
    #plt.title('Best experiment')



def generate_interactive_map(reg,var,res,score,xgeo,X,X2,exp_ref,exp,date_beg,date_end,dir_series,map_name):

    dic_score_title=X2.dic_score_title
    dic_varname=X2.dic_varname
    dic_units = X2.dic_var_units

    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'ss':'-','crps':uu,'crps_rel':uu,'crps_pot':uu,'crpss':'-','rbias':'-'}    

    # Add mask that determines the location of the stations within the region of interest
    util.find_sta(reg,res,X)

    # Extract list of stations to be selected and keep only these stations. 
    mask_sel = res['mask_'+reg]
    list_sta = res.station_id.values[mask_sel]
    res_reg=res.where(res.station_id.isin(list_sta),drop=True)

    # Extract limit of the domain for folium
    lim_dom = limit_domain4(reg,xgeo,X)

    # Extract limit of the domain for folium
    bound_dom = limit_domain3(reg,xgeo,X)
    bound_folium = [[bound_dom[0],bound_dom[2] ], [bound_dom[1],bound_dom[3]] ]

    # Suffix in html path
    suff = X.dir_html.split('public_html')[1]
    user = os.environ['USER']

    # Import scores and convert to a geopandas object    
    df = res_reg.to_dataframe().reset_index()
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")

    # Compute scores to be used as color for the marker on the map

    sco_ref = res_reg[score].loc[dict(variable=var,exp=exp_ref)]
    sco_comp = res_reg[score].loc[dict(variable=var,exp=exp)]

    if(score=='bias'):
        sco_norm = res_reg['rmse'].loc[dict(variable=var,exp=exp_ref)]
        mod = - (np.abs(sco_comp)-np.abs(sco_ref))/np.abs(sco_norm) *100.
    elif(score=='pbias'):
        mod = - (np.abs(sco_comp)-np.abs(sco_ref))
    elif(score=='crps'):
        mod = [0] * len(sco_ref)
        for i in range(len(sco_comp)):
            if sco_comp[i] < sco_ref[i]:
                mod[i] = 1 - (sco_comp[i]/sco_ref[i])
            else:
                mod[i] = (sco_ref[i]/sco_comp[i]) - 1  
        mod = np.array(mod)
    elif(score=='ss'):
        #absolute difference each score is from 1 (ideal score)
        abs_diff_ref = abs(1-sco_ref)
        abs_diff_comp = abs(1-sco_comp)
        #Percent change in absolute difference to 1
        mod = -(abs_diff_comp-abs_diff_ref)/abs_diff_ref *100. 
    else: 
        mod = -(sco_comp-sco_ref)/sco_ref *100. 
  
         
    # Determine limit for colormap
    val = min(np.percentile(np.abs(mod.values[~np.isnan(mod.values[:])]),95),100.)
    min_g = -1.0*val
    max_g = val
        
    # Make sure the time series png's are in the netcdf and vice versa:
    clipped_df_var = gdf[gdf['variable'] == var].dropna()

    # Add points with popups that display images
    unique_ids = clipped_df_var['station_id'].unique()


    locations = []
    for id in unique_ids:
        lat = res_reg['lat'].loc[dict(station_id=id)].values.item(0)
        lon = res_reg['lon'].loc[dict(station_id=id)].values.item(0)
        name = res_reg['station_name'].loc[dict(station_id=id)].values.item(0)
        type_sta = res_reg['type_mes'].loc[dict(station_id=id)].values.item(0)

        image_url = 'https://goc-dx-u3.science.gc.ca/~'+f'{user}/'+f'{suff}/series/'+f'{reg}/'+f'{var}_{id}_{date_beg}_{date_end}.png'


        locations.append(
                    {"lat": lat,
                "lon": lon,
                "name": name,
                "type": type_sta,
                "id":id,
                "image": os.path.join(dir_series,reg,'{}_{}_{}_{}.png'.format(var, id, date_beg, date_end)),
                "image_url":image_url})


    # Create folium map
    m = folium.Map(location=[lim_dom[2], lim_dom[3]], zoom_start=5,prefer_canvas=True,tiles=None)

    # Add title using HTML
    title_html = f'''
            <h3 align="center" style="font-size:20px"><b>Change in {dic_score_title[score]} for {dic_varname[var]} between {exp} and {exp_ref} </b></h3>
            '''
    m.get_root().html.add_child(folium.Element(title_html))


    # Create a coolwarm colormap using branca
    colormap = branca_colormap.LinearColormap(
        colors=[cm.coolwarm(i) for i in range(256)],
        vmin=-50,
        vmax=50
    )
    custom_ticks = [-50,-40,-30,-20,-10,0,10,20,30,40,50]  # Define your desired tick positions
    colormap = colormap.to_step(len(custom_ticks))  # Discretize the colormap to match the ticks
    colormap.caption = "Performance Change in "+dic_score_title[score]+" (%)"  # Set title for the colorbar
    colormap.tick_labels = custom_ticks  # Assign custom tick labels  

    colormap.add_to(m) 

    m.get_root().html.add_child(folium.Element(f'''
    <style>
        .legend {{
            font-size: 16px !important;
            line-height: 1.5 !important;
        }}
        .legend .colorbar {{
            width: 250px !important;
            height: 30px !important;
            margin-bottom: 30px !important;  /* Add space below the colorbar */
        }}
        .legend .colorbar-label {{
            font-size: 18px !important;
            font-weight: bold !important;
            margin-top: 300px !important;  /* Add space above the label */
        }}
        .legend .colorbar-ticks {{
            font-size: 14px !important;
        }}
    </style>
    '''))  

    for loc in locations:

        # Select color corresponding to relative change in score
        color = colormap(mod.loc[dict(station_id=loc['id'])].values.item(0))  

        html = f"""
            <div>
            <img src="{loc['image_url']}" width="900"  loading="lazy" />
        </div>
        """      

        # Create an iframe for the popup
        iframe = folium.IFrame(html, width=900, height=550)
        popup = folium.Popup(iframe, max_width=8000, close_on_click=True) 


        sc1 = round(sco_ref.loc[dict(station_id=loc['id'])].values.item(0),2)
        sc2=  round(sco_comp.loc[dict(station_id=loc['id'])].values.item(0),2)
        pf =  round(mod.loc[dict(station_id=loc['id'])].values.item(0),2)  

        tooltip_text = f"""
         <b>{loc['name']}</b><br>
         {dic_score_title[score]} {exp_ref}: {sc1} {units[score]} <br>
         {dic_score_title[score]} {exp}: {sc2} {units[score]}<br>
         Perf change: <b>{pf} % </b><br>
        <i>Click for time series</i>
        """     

        # Use Tooltip class for additional options
        tooltip = Tooltip(
            tooltip_text,
            sticky=True,  # Keeps tooltip visible when cursor moves slightly
            direction='bottom',  # Forces tooltip to appear below the marker
            style="font-size: 16px;"  # Additional CSS styling
        )   


        if(loc['type']<=1.): 
            # Add square for manual stations 
            folium.Marker(
                location=[loc["lat"], loc["lon"]],
                icon=folium.DivIcon(
                #html='<div style="width: 15px; height: 15px; background-color: #3388ff; border: 1px solid #0066cc;"></div>',
                html=f'<div style="width: 13px; height: 13px; background-color: {color}; border: 1px solid black;"></div>',
                icon_size=(13, 13),
                icon_anchor=(7, 7)),
                popup=popup,
                tooltip=tooltip,
            ).add_to(m)
        else: #Add circle for automatic stations 
            # Add CircleMarker as a small dot
            folium.CircleMarker(
                location=[loc["lat"], loc["lon"]],
                radius=7,  # Small dot size
                weight=1,  # Width of the edge (stroke)
                color="black",  # Outline color
                fill=True,
                fill_color=color,  # Fill color
                fill_opacity=1.0,  # Opacity of the fill
                popup=popup,
                tooltip=tooltip
            ).add_to(m)  

    folium.TileLayer('openstreetmap').add_to(m)

    # Add Google Satellite tile layer
    google_satellite_tiles = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    folium.TileLayer(
        tiles=google_satellite_tiles,
        attr="Google Satellite",
        name="Google Satellite",
        overlay=False,  # Background layer
        control=True  # Include in LayerControl
    ).add_to(m)            

    # Add other tile layers if desired (e.g., terrain, hybrid)
    google_terrain_tiles = "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
    folium.TileLayer(
        tiles=google_terrain_tiles,
        attr="Google Terrain",
        name="Google Terrain",
        overlay=False,
        control=True
    ).add_to(m)

    #folium.TileLayer('cartodbdark_matter').add_to(m) 
    # Add the default tile layer (e.g., OpenStreetMap)
    #folium.TileLayer('openstreetmap').add_to(m)

    # Add a Layer Control to toggle between tile layers
    folium.LayerControl().add_to(m)

    # Adjust the map to fit all markers
    m.fit_bounds(bound_folium)

    m.save(map_name)


