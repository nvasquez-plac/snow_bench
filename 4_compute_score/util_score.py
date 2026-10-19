import numpy as np
import rpnpy.librmn.all as rmn
import matplotlib.path as mplPath
import pdb
import fstd2nc
import xarray as xr
import datetime as dt 
import calendar
import matplotlib
import pandas as pd
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import geopandas as gpd
import sys
from scipy.stats import rankdata  as rank
import re
import cartopy
import cartopy.mpl.geoaxes
import cartopy.feature as cfeature
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import shutil
import rasterio
from rasterio.transform import rowcol
import rioxarray as rxr
from pyproj import Transformer,geod
from rasterio.windows import from_bounds

class ForkedPdb(pdb.Pdb):
    """A Pdb subclass that may be used from a forked multiprocessing child"""
    def interaction(self, *args, **kwargs):
        _stdin = sys.stdin
        try:
            sys.stdin = open('/dev/stdin')  # Or 'con' on Windows, or similar
            pdb.Pdb.interaction(self, *args, **kwargs)
        finally:
            sys.stdin = _stdin


def plot_station_timeseries(args_tuple):
    """
    Function to plot time series for a single station - designed for parallel execution
    """
    (sta, var, reg, res_fin, cfg_exp, list_exp, date_beg, date_end, 
     ladd_vgh, max_alti, lcheck_alti, ref_exp_alti, lalti_ok, 
     dic_var, dic_varname, dic_units, 
     dic_vgh, dir_sto_reg) = args_tuple
    
    # Create a feature for States/Admin 1 regions at 1:50m from Natural Earth
    states_provinces = cfeature.NaturalEarthFeature(
            category='cultural',
            name='admin_1_states_provinces_lines',
            scale='50m',
            facecolor='none')
    
    #try:
    alt_sta = res_fin['elevation'].loc[dict(station_id=sta)].values
    #ForkedPdb().set_trace()
    lat_sta = round(res_fin['lat'].loc[dict(station_id=sta)].values.item(),4)
    lon_sta = round(res_fin['lon'].loc[dict(station_id=sta)].values.item(),4)


    lalti = []

    for iexp, exp in enumerate(list_exp):
        alt_mod = res_fin['Elevation_'+exp].loc[dict(station_id=sta)].values
        lalti.append(alt_mod)

    print(f"Processing station {sta}, alt_sta: {alt_sta}, lalti: {lalti}")
    
    if lcheck_alti == False or (lcheck_alti and any(lalti_ok)):
        # Extract observations
        obs = res_fin[dic_var[var]].loc[dict(time=slice(date_beg,date_end),station_id=sta)]
        mask_obs = np.isnan(obs)
        mask_ok = ~mask_obs
                    
        if np.sum(mask_ok.values) > 0:  # Generate figure if enough observations are available
            fig = plt.figure(figsize=(8,5))
            plt.subplots_adjust(wspace=0., hspace=0.)
            ax1 = fig.add_subplot(1,1,1)
            plt.grid()
            
            # Plot observed values
            ax1.plot(obs.time.values, obs.values, 's', label='Obs.', color='black')

            # Add inset showing station location
            axins = inset_axes(ax1, width="40%", height="40%", loc=3,
                axes_class=cartopy.mpl.geoaxes.GeoAxes,
                axes_kwargs=dict(projection=cartopy.crs.PlateCarree()),
                bbox_to_anchor=(1.0,1-0.35,0.8,0.8), bbox_transform=ax1.transAxes)                    
            axins.set_extent([-167, -50, 25, 75])
            axins.add_feature(cartopy.feature.COASTLINE)
            axins.add_feature(cartopy.feature.BORDERS)
            axins.add_feature(states_provinces, edgecolor='gray')
            lon = res_fin['lon'].loc[dict(station_id=sta)].values.item(0)
            lat = res_fin['lat'].loc[dict(station_id=sta)].values.item(0)
            axins.scatter(lon, lat, color='red', s=20, transform=cartopy.crs.PlateCarree())

            ax1.set_ylabel(dic_varname[var]+' ('+dic_units[var]+')', fontsize=12)
            plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
            max_var = np.nanmax(obs.values)

            if lcheck_alti:
                if ref_exp_alti:
                    tt_elev = ref_exp_alti[0]
                else:
                    tt_elev = 'Separated exp'
            else:
                tt_elev = 'None'                     

            ax1.text(1.02, 0.98, 'Lat: '+str(lat_sta)+' Lon: '+str(lon_sta), {'fontsize':8,'color':'black','style':'italic'}, 
                    horizontalalignment='left', verticalalignment='center', transform=ax1.transAxes)
            ax1.text(1.02, 0.38, 'Elevation reference: '+tt_elev, {'fontsize':8,'color':'black','style':'italic'}, 
                    horizontalalignment='left', verticalalignment='center', transform=ax1.transAxes)
            ax1.text(1.02, 0.34, 'Elevation max dif.: '+str(max_alti)+' m', {'fontsize':8,'color':'black','style':'italic'}, 
                    horizontalalignment='left', verticalalignment='center', transform=ax1.transAxes)   
            ax1.text(1.02, 0.3, 'Elev. sta. '+str(round(alt_sta.item(0),1))+' m', {'fontsize':8,'color':'black','style':'italic'}, 
                    horizontalalignment='left', verticalalignment='center', transform=ax1.transAxes) 

            ss = 0
            iexp_plot = 0

            # Loop over experiments
            for iexp, exp in enumerate(list_exp):
                if lalti_ok[iexp]:  # Experiment meets elevation criteria
                    name_var = var+'_'+exp
                    mod = res_fin[name_var].loc[dict(time=slice(date_beg,date_end),station_id=sta)]
                    mask_mod = ~np.isnan(mod)
                    
                    ss = ss + np.sum(mask_mod.values)

                    if np.sum(mask_mod.values) > 0:
                        max_var = np.maximum(max_var, np.nanmax(mod.values))
                        

                        ax1.plot(mod.time.values, mod.values, '-', 
                                   label=exp, color=cfg_exp[exp]['col'], linewidth=2.0)

                        if ladd_vgh and var in list(dic_vgh.keys()):
                            var_vgh = dic_vgh[var]
                            name_var_vgh = var_vgh+'_'+exp
                            mod_vgh = res_fin[name_var_vgh].loc[dict(time=slice(date_beg,date_end),station_id=sta)]*dic_fac_mod[var]
                            mask_mod_vgh = ~np.isnan(mod_vgh)
                            ax1.plot(mod.time[mask_mod_vgh].values, mod_vgh[mask_mod_vgh].values, '--', 
                                     label=exp+' Forest', color=cfg_exp[exp]['col'], linewidth=2.0)

                        ax1.set_ylim([0, 1.1*max_var])
                        ax1.legend(loc='upper left', ncol=1, borderpad=0.2, markerscale=1, 
                                 labelspacing=0.05, borderaxespad=0.1, fontsize=11, 
                                 bbox_to_anchor=(1.02, 0.7))
                        
                        type_sta = res_fin['type_mes'].loc[dict(station_id=sta)].values
                        if type_sta > 1:
                            tt = 'Auto.'
                        else:
                            tt = 'Man'
                        fig.suptitle(dic_varname[var]+' Station '+sta+' ('+tt+')')

                        ax1.text(1.02, 0.26-iexp_plot*0.04, 'Elev. '+exp+' '+str(round(lalti[iexp].item(0),1))+' m',
                               {'fontsize':8,'color':cfg_exp[exp]['col'],'style':'italic'}, 
                               horizontalalignment='left', verticalalignment='center', transform=ax1.transAxes)  
                        iexp_plot = iexp_plot + 1

            if ss > 10.:
                fig_name = dir_sto_reg+'/'+var+'_'+sta+'_'+date_beg+'_'+date_end+'.png'
                plt.savefig(fig_name, format="png", bbox_inches='tight', dpi=200)
                plt.close()
                return f"Successfully created {fig_name}"
            else:
                plt.close()
                return f"Skipped {sta} - insufficient data (ss={ss})"
        else:
            return f"Skipped {sta} - no valid observations"
    else:
        return f"Skipped {sta} - elevation criteria not met"
            
    #except Exception as e:
    #    return f"Error processing station {sta}: {str(e)}"

def find_sta(domain,da,X):

# Add to the input data array da a mask to determine if the stations in da belong to a given Emet domain
      if(hasattr(X,'dic_shp')):
          dic_shp = X.dic_shp
          dir_shp = X.dir_shp
      else:
          dic_shp = {}
          dir_shp = None

      list_shp= [key for key in dic_shp]

      if(domain=='All'): 
         inside = np.full((len(da.lat.values)), True)

      elif(domain in list_shp): # Domain defined using shapefiles provided by the users
         # Path to the corresponding shapefile 
         fic_shp = dir_shp+'/'+dic_shp[domain]['id']+'.shp'
         domain_shp = gpd.read_file(fic_shp).to_crs(4326)

         # Prepare dataframe containing stations information
         data = da[['lon', 'lat', 'station_name']].to_dataframe().reset_index()

         # Generate geodataframe to extract stations located within the shapefile
         df_station = gpd.GeoDataFrame(
           data=data[['station_id', 'station_name', 'lon', 'lat']],
           geometry=gpd.points_from_xy(x=data['lon'], y=data['lat']),
           crs='epsg:4326')

         # Get the station contained in the shapefiles
         df_station_clip = gpd.sjoin(df_station, domain_shp, predicate = 'within')

         # Get array of boolean 
         inside = da.station_id.isin(df_station_clip).values

      else: # Emet domains

         lats,lons,poly = emetDomain(domain)
         path           = mplPath.Path(poly)
         #points = zip(da.lat.values,da.lon.values)
         points = np.transpose(np.vstack([da.lat.values,da.lon.values]))
         inside = path.contains_points(points)

      # Create mask containing the location of the stations
      da['mask_'+domain]=xr.DataArray(inside,dims='station_id')


def gen_date(freq,da,db,de):

    list_beg  = []
    list_end  = []
    list_mid  = []

    daw = da.copy()
    # Normalize time
    daw['time'] = daw.indexes['time'].normalize()
    if(freq=='day'):
       date_ext1= dt.datetime.strptime(db,"%Y%m%d")
       date_ext2= dt.datetime.strptime(de,"%Y%m%d")
       list_beg = pd.date_range(date_ext1,date_ext2)
       list_mid = list_beg
       list_end = list_beg+np.timedelta64(1,'D')

    elif(freq in ['period','accu','melt']):
       date_ext1= dt.datetime.strptime(db,"%Y%m%d")
       date_ext2= dt.datetime.strptime(de,"%Y%m%d")
       date_ext2 = date_ext2+dt.timedelta(days=1)
       list_beg.append(date_ext1)
       list_end.append(date_ext2)
       date_mid = date_ext1+ (date_ext2-date_ext1)/2
       list_mid.append(date_mid)

    elif(freq=='month'):  
       # Get list of months between the two dates
       daterange = pd.date_range(db,de, freq='1M')
       for dd in daterange:
            date_ext1= dt.datetime(dd.year,dd.month,1,0)
            list_beg.append(date_ext1)
            list_mid.append(date_ext1)
            list_end.append(dd.to_pydatetime()+dt.timedelta(days=1))
       # Add the last month:
       date_ext1 = dd.to_pydatetime()+dt.timedelta(days=1)
       list_beg.append(date_ext1)
       list_mid.append(date_ext1)
       days_in_month = calendar.monthrange(date_ext1.year, date_ext1.month)[1]
       date_ext2= dt.datetime(date_ext1.year,date_ext1.month,days_in_month,0)+dt.timedelta(days=1)
       list_end.append(date_ext2)


    elif(freq=='bi-month'):   

       daterange = pd.date_range(db,de, freq='SMS')
       for dd in daterange:
            date_ref = dd.to_pydatetime()
            list_mid.append(date_ref)
            date_ext1 = date_ref-dt.timedelta(days=6)
            date_ext2 = date_ref+dt.timedelta(days=6)
            list_beg.append(date_ext1)
            list_end.append(date_ext2)

    return(list_beg, list_end, list_mid)

def compute_score(sco,obs,mod):

    if(sco =='bias'):
        sol = np.nanmean(mod - obs)
    elif(sco=='mae' or sco=='crps'): #crps for deterministic runs is the mean absolute error (MAE)
        sol = np.nanmean(np.abs(mod-obs))
    elif(sco=='medae'):
        sol = np.percentile(np.abs(mod-obs),50)
    elif(sco=='stde'):
        bias = np.nanmean(mod) -np.nanmean(obs)
        rmse2 = np.nanmean( (mod-obs)**2.)
        sol = np.nanmean(np.sqrt(rmse2-bias**2.))        
    elif(sco=='rmse'):
        sol = np.sqrt(np.nanmean( (mod-obs)**2.))
    elif(sco=='nrmse'):
        obs_mean = np.nanmean(obs)
        #don't want to divide by 0 or we get inf
        if obs_mean == 0:
            obs_mean = np.nan
        sol = np.sqrt(np.nanmean( (mod-obs)**2.))/ obs_mean
    elif(sco=='nse'):
        sol = nse = 1-(sum(pow((mod-obs),2))/sum(pow((obs-np.mean(obs)),2)))
    elif(sco=='pbias'):
        if(sum(obs)>0):
            sol = 100.0*sum(mod-obs)/sum(obs)
        else:
            sol = np.nan
    elif(sco=='cor'):
        sol = np.corrcoef(obs,mod)[0,1]
    elif(sco=='det'):
        mm = np.nanmean(obs)
        ss_tot = np.sum((obs-mm)**2.)
        ss_res = np.sum((obs-mod)**2.)
        sol= 1.0- ss_res/ss_tot
    elif(sco=='nobs'):
        sol = len(obs)
    elif(sco=='moyobs'):
        sol = np.nanmean(obs)
    elif(sco=='moymod'):
        sol = np.nanmean(mod)
    elif(sco=='kge09'):
        sol = kge09(mod,obs)
    elif(sco=='kge12'):
        sol = kge12(mod,obs)
    elif(sco=='alpha'):
        sol = alpha(mod,obs)
    elif(sco=='gamma'):
        sol = gamma(mod,obs)
    elif(sco=='beta'):
        sol = beta(mod,obs)
    elif(sco=='wass_dis'):
        sol = cdf_distance(obs,mod,1)
    elif(sco=='energy_dis'):
        sol = cdf_distance(obs,mod,2)
        
    return(sol)


# Function useful to derive KGE and its component
def beta(sim,obs): 
   return  np.mean(sim)/np.mean(obs) 

def alpha(sim,obs):    
  return np.std(sim)/np.std(obs) 

def gamma(sim,obs):    
  return (np.mean(obs)*np.std(sim))/(np.mean(sim)*np.std(obs)) 

def kge09(sim,obs):    
  pearson =  np.corrcoef(sim,obs)[0,1]
  return 1.-np.sqrt( (pearson-1.)**2. + (beta(sim,obs)-1.)**2. + (alpha(sim,obs)-1.)**2.) 

def kge12(sim,obs): 
  pearson =  np.corrcoef(sim,obs)[0,1]   
  return 1.-np.sqrt( (pearson-1.)**2. + (beta(sim,obs)-1.)**2. + (gamma(sim,obs)-1.)**2.)


def plot_histo(list_score,rest,var,X2,X,fig_name,per):

    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Get units
    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'nrmse':'-'}

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')


    plot_lines = []
    nreg= len(rest.domain.values)
    nscore = len(list_score)

    fig, ax = plt.subplots(nscore, 1, sharex='col',figsize=(1.25*nreg,nscore*8/3.))
    fig.suptitle(dic_var[var]+' '+per,y=0.95)
    plt.subplots_adjust( wspace=0.,hspace=0.15)

    nexp=len(rest.exp)

    for iscore,score in enumerate(list_score):

         # Define maximal and minimal value when computing the scores
         max_t = limits[var]['max_g'][score]
         min_t = limits[var]['min_g'][score]

         name_reg  = []
         ind = 0
         if(nexp>5):
           w = 0.15
         else:
           w = 0.2
         ax.ravel()[iscore].set_xticks(np.arange(-0.5,nreg ,1))
         ax.ravel()[iscore].grid(zorder=0)
         ax.ravel()[iscore].set_axisbelow(True)

         for ireg,reg in enumerate(rest.domain.values):

             for iexp,exp in enumerate(rest.exp):
                val = rest[score].loc[dict(exp=exp,domain=reg)]
                bb1 = ax.ravel()[iscore].bar(ireg-w + iexp*w, val,width=0.95*w,color=cfg_exp[str(exp.values)]['col'],label = exp.values)

                if(iscore==0 and iexp==0):
                      nob = rest['nobs'].loc[dict(exp=exp,domain=reg)]
                      if(np.isnan(nob)):
                           nob =0
                      ax.ravel()[iscore].text(ireg,max_t+0.03*(max_t-min_t), int(nob),{'fontsize':8,'color':'black','style':'italic'},horizontalalignment='center',verticalalignment='center')
                   
                if iscore==0 and ireg==0:
                   plot_lines.append(bb1)
             name_reg.append(dic_reg[reg])
             #name_reg.append(reg)

         ax.ravel()[iscore].set_xlim(-0.5,  nreg-0.5 )
         ax.ravel()[iscore].set_ylabel(dic_title[score]+' ('+units[score]+')',fontsize=12)
         ax.ravel()[iscore].set_xticks(np.arange(0,nreg ,1))
         ax.ravel()[iscore].set_xticklabels(name_reg,rotation=45,ha='right',fontsize = 11)
         ax.ravel()[iscore].set_ylim(min_t, max_t)


    lgd=ax.ravel()[0].legend([plot_lines[i] for i in np.arange(0,len(rest.exp.values))],rest.exp.values,loc='upper left',ncol=3,borderaxespad=0.1,borderpad=0.2)#

    plt.savefig(fig_name,format="png",bbox_inches='tight')
    plt.clf()

def plot_histo_comb(list_score,res_man,res_auto,var,X2,X,fig_name,per,lsuper):

# Plot barplot showing results for manual and automatic stations


    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Get units
    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'nrmse':'-','kge12':'-','beta':'-','gamma':'-'}

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')


    plot_lines = []
    nreg_man= len(res_man.domain.values)
    nreg_auto= len(res_auto.domain.values)
    nreg = nreg_man+nreg_auto
    nscore = len(list_score)

    if(nscore>4):
        sys.exit('Maximal number of 4 scores reached. Please reduce the number of score on the figure with option comb')

    dic_fig={'sup_title':{2:1.02,3:0.98,4:0.95},
             'fig_bot':{2:0.12,3:0.08,4:0.07},
              'loc_leg':{2:0.98,3:0.95,4:0.93}}

    res_all={}
    res_all['man'] = res_man
    res_all['auto'] = res_auto
    nreg_all={}
    nreg_all['man'] = nreg_man
    nreg_all['auto'] = nreg_auto

    if(lsuper):
       list_type = ['man']
    else:
       list_type = ['man','auto']

    nexp = len(res_all['man'].exp)

    ncol = len(list_type)
 
    fig, ax = plt.subplots(nscore, ncol, sharex='col',figsize=(0.8*ncol*nreg,nscore*8/3.))
    fig.suptitle(dic_var[var]+': '+per,y=dic_fig['sup_title'][nscore],fontweight="bold")
    if(lsuper):
        fig.supxlabel('Number of manual/automatic stations are shown above the 1st image. \n Scores for manual (automatic) stations are shown with colors (hatches).',fontstyle="italic",fontsize=9)
    else:
        fig.supxlabel('Number of stations are shown above the top graphs',fontstyle="italic",fontsize=10)
    plt.subplots_adjust( wspace=0.05,hspace=0.15)

    for itype,tt in enumerate(list_type): 

      for iscore,score in enumerate(list_score):
 

        # Define maximal and minimal value when computing the scores
         max_t = limits[var]['max_g'][score]
         min_t = limits[var]['min_g'][score]  


         iplot = iscore*ncol+itype
         name_reg  = []
         ind = 0
         #w = 0.25
         if(nexp>5):
             w = 0.12
         else:
             w = 0.17
         ax.ravel()[iplot].set_xticks(np.arange(-0.5,nreg_all[tt] ,1))
         ax.ravel()[iplot].grid(zorder=0)
         ax.ravel()[iplot].set_axisbelow(True)

         for ireg,reg in enumerate(res_all[tt].domain.values):

             for iexp,exp in enumerate(res_all[tt].exp):
                val = res_all[tt][score].loc[dict(exp=exp,domain=reg)]
                bb1 = ax.ravel()[iplot].bar(ireg-w/2*nexp +w/2.+ iexp*w, val,width=0.95*w,color=cfg_exp[str(exp.values)]['col'],label = exp.values)#,edgecolor='k')

                if(lsuper):
                     if(reg in res_all['auto'].domain):
                        val2 = res_all['auto'][score].loc[dict(exp=exp,domain=reg)]
                        bb2 = ax.ravel()[iplot].bar(ireg-w/2*nexp+w/2.  + iexp*w, val2,width=0.95*w,fill=False,hatch='///',label = exp.values)

                if(iscore==0 and iexp==0):
                      nob = res_all[tt]['nobs'].loc[dict(exp=exp,domain=reg)]
                      if(np.isnan(nob.values[0])):
                          nob.values[:] =0
                      txt = add_comma(int(nob.values[0]))#str(int(nob))
                      if(lsuper):
                          if(reg in res_all['auto'].domain):
                             nob2 = res_all['auto']['nobs'].loc[dict(exp=exp,domain=reg)]
                             if(np.isnan(nob2)): nob2 =0
                             txt = str(int(nob))+'/'+str(int(nob2))

                      ax.ravel()[iplot].text(ireg,max_t+0.03*(max_t-min_t), txt,{'fontsize':8,'color':'black','style':'italic'},horizontalalignment='center',verticalalignment='center')
                   
                if iscore==0 and ireg==0:
                    plot_lines.append(bb1)

             try:
                 name_reg.append(dic_reg[reg])
             except: # If using a shapefile, the name of the reg might not be in the config file
                 name_reg.append(reg)

         ax.ravel()[iplot].set_xlim(-0.5,  nreg_all[tt]-0.5 )
         if(itype==0):
           ax.ravel()[iplot].set_ylabel(dic_title[score]+' ('+units[score]+')',fontsize=12)
         else:
           ax.ravel()[iplot].set_yticklabels([])
         if(iscore==0 and  (not lsuper)):
           if(itype==0):
             ax.ravel()[iplot].set_title('Manual measurements',y=1.04)
           else:
             ax.ravel()[iplot].set_title('Automatic stations',y=1.04)
         ax.ravel()[iplot].set_xticks(np.arange(0,nreg_all[tt] ,1))
         ax.ravel()[iplot].set_xticklabels(name_reg,rotation=0,ha='center',fontsize = 11)
         #ax.ravel()[iplot].set_xticklabels(name_reg,rotation=45,ha='right',fontsize = 11)
         ladd_color =False
         if(ladd_color):
            for ireg,reg in enumerate(res_all[tt].domain.values):
               cmap = matplotlib.cm.get_cmap('Paired')
               norm = matplotlib.colors.Normalize(vmin=1, vmax=12)
               palette = plt.cm.Paired
               print(ireg)
               plt.gca().get_xticklabels()[ireg].set_color(cmap(norm(ireg+1)))

         ax.ravel()[iplot].set_ylim(min_t, max_t)

         if(iplot==0):
            fig.legend([plot_lines[i] for i in np.arange(0,len(res_all[tt].exp.values))],res_all[tt].exp.values,loc='upper center',bbox_to_anchor=(0.5, dic_fig['loc_leg'][nscore]),ncol=len(res_all[tt].exp.values),borderaxespad=0.1,fontsize=10,shadow=True)
            fig.subplots_adjust(bottom=dic_fig['fig_bot'][nscore])   


    plt.savefig(fig_name,format="png",bbox_inches='tight',dpi=300)
    plt.clf()



def add_comma(number):
    return ("{:,}".format(number))


def get_date_accu(var_obs,sta,date_beg,date_end,var,type_mes):

    yy = pd.to_datetime(var_obs.time.values[0]).year

    if(np.sum(~np.isnan(var_obs.values))==0.):
        print('No observation to determine lenght of the accu. season', sta.values)
        date_beg_ext = dt.datetime(yy,11,1)
        date_end_ext = dt.datetime(yy+1,3,1)
    else:
        if(type_mes in [0,1,7]):
            date_beg_ext = dt.datetime(yy,11,1)   # Set default date for manual stations
        else: 
            date_beg_ext = find_date_start(var_obs,yy,var)  # Dynamic data selection for automatic stations

        date_end_ext = find_date_max(var_obs,var)#+dt.timedelta(days=3)

    return(date_beg_ext,date_end_ext)

def get_date_melt(var_obs,sta,date_beg,date_end,var,type_mes):

    yy = pd.to_datetime(var_obs.time.values[0]).year

    if(np.sum(~np.isnan(var_obs.values))==0.):
        print('No observation to determine lenght of the melt. season', sta.values)
        date_beg_ext = dt.datetime(yy+1,3,1)
        date_end_ext = dt.datetime(yy+1,6,30)
    else:
        date_beg_ext =  util.find_date_max(swe_obs) # Date of maximum SWE

        if(type_mes in [0,1,7]):
            date_end_ext = dt.datetime(yy+1,6,30)   # Set default date for manual stations (June 30 th)
        else: 
            date_end_ext = find_date_end(var_obs,yy,var)  # Dynamic data selection for automatic stations

    return(date_beg_ext,date_end_ext)


def find_date_start(var_obs,yy,var):

    dic_th = {'snw':100,'snd':0.4}
    # Determine valid date for var_obs
    mask_val = ~np.isnan(var_obs.values)
    # Extract valid SWE
    var_obs_val = var_obs[mask_val]
    # Get corresponding hour
    date_ini = var_obs_val.time[0].values
    hour = pd.to_datetime(date_ini).hour

    # Get max SWE
    max_var_obs = np.nanmax(var_obs.values)

    if(max_var_obs>dic_th[var]): # take 1st date of continuous snow cover
      date_cen = dt.datetime(yy+1,1,15,hour)
      date_cur = date_cen
      var_obs_ref = var_obs.sel(time=date_cur).values
      date_ref = date_cur
      while(date_cur>pd.to_datetime(var_obs.time.values[0])):
        var_obs_cur = var_obs.sel(time=date_cur).values
        if(np.isnan(var_obs_ref) & ~np.isnan(var_obs_cur)):
           var_obs_ref=var_obs_cur
        if(var_obs_cur < var_obs_ref):
           date_ref= date_cur
           var_obs_ref = var_obs_cur
        date_cur = date_cur - dt.timedelta(hours=24)

    else: # For shallow and intermittent snowpack : use 1 day with snow since 1st November. 
       date_cen = dt.datetime(yy,11,1,hour)
       date_cur = date_cen

       date_ref=date_cur

       while(date_cur< pd.to_datetime(dt.datetime(yy,1,1,hour))):
           var_obs_cur = var_obs.sel(time=date_cur).values
           if(var_obs_cur>0.):
              date_ref= date_cur
              break
           date_cur = date_cur + dt.timedelta(hours=24)

    return(date_ref)

def find_date_end(swe,yy,var):

    dic_th = {'snw':100,'snd':0.4}
    
    # Determine valid date for swe
    mask_val = ~np.isnan(swe.values)
    # Extract valid SWE
    swe_val = swe[mask_val]
    # Get corresponding hour
    date_ini = swe_val.time[0].values
    hour = pd.to_datetime(date_ini).hour
    
    # Get max SWE
    max_swe = np.nanmax(swe.values)

    if(max_swe>dic_th[var]): # take last date of continuous snow cover
      date_cen = find_date_max(swe)
      date_cur = date_cen
      swe_ref = swe.sel(time=date_cur).values
      date_ref = date_cur
      while(date_cur<=pd.to_datetime(swe.time.values[-1])):
        swe_cur = swe.sel(time=date_cur).values
        if(np.isnan(swe_ref) & ~np.isnan(swe_cur)):
           swe_ref=swe_cur
        if(swe_cur < swe_ref):
           date_ref= date_cur
           swe_ref = swe_cur
        date_cur = date_cur + dt.timedelta(hours=24)

    else: # For shallow and intermittent snowpack : last day with snow since 1st April. 
       date_cen = dt.datetime(yy+1,6,1,hour)
       date_cur = date_cen

       date_max = find_date_max(swe)

       while(date_cur> date_max):
           swe_cur = swe.sel(time=date_cur).values
           if(swe_cur>0.):
              date_ref= date_cur
              break
           date_cur = date_cur - dt.timedelta(hours=24)

    return(date_ref)


def find_date_max(var_obs,var):
    val_max = var_obs.where(var_obs==var_obs.max(),drop=True).squeeze()
    if hasattr(val_max.time.values, "__len__"):
       date_last_max = pd.to_datetime(val_max.time.values[-1])
    else:
       date_last_max = pd.to_datetime(val_max.time.values)
    return(date_last_max)


def list_empty_stations(res):

    # Get list of stations
    sta_id = res.station_id.values.tolist()

    list_var = res['variable']

    # List of stations to drop
    list_drop = []
    for sta in sta_id:
        ll_mod=[]
        ll_obs=[]

        for var in list_var:
            # Check if moymod is set to nan for all experiments and all time period
            mod = res['moymod'].loc[dict(station_id=sta,variable=var)].values
            lmod = np.isnan(mod).all()
            ll_mod.append(lmod)

            # Check if moyobs is set to nan for all experiments and all time period
            obs = res['moyobs'].loc[dict(station_id=sta,variable=var)].values
            lobs = np.isnan(obs).all()
            ll_obs.append(lobs)

        if(False in ll_mod and False in ll_obs):
            print('keep',sta)
        else: 
            list_drop.append(sta)

    return(list_drop)

def list_empty_stations_all(res,list_exp,list_var):

    # Get list of stations
    sta_id = res.station_id.values.tolist()

    # List of stations to drop
    list_drop = []
    for sta in sta_id:
        ll_var=[]
        for var in list_var: 
            for exp in list_exp:
                name_var = var+'_'+exp
                mod = res[name_var].loc[dict(station_id=sta)].values[:,]
                ll_var.append(np.isnan(mod).all())

        if(all(ll_var)):
            list_drop.append(sta)

    return(list_drop)


def plot_boxplot_reg_comb(list_score,list_reg,type_sta,res,var,X,X2,fig_name,per,nobs_min,type_plot,exp_ref):

    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Get units
    units=give_units(var,X2,type_plot)

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')

    nscore = len(list_score)
    nreg = len(list_reg)

    list_exp = res.exp.values.tolist()
    if(type_plot in ['dif','dif_rel']):
        list_exp.remove(exp_ref)
    nexp=len(list_exp)

    if(nscore>4):
        sys.exit('Maximal number of 4 scores reached. Please reduce the number of score on the figure with option comb')

    dic_fig={'sup_title':{1:1.2,2:1.03,3:0.98,4:0.95},
            'fig_bot':{1:0.15,2:0.12,3:0.08,4:0.07},
            'loc_leg':{1:1.12,2:0.99,3:0.95,4:0.93}}    

    dc_w = {1:0.25,2:0.25,3:0.17,4:0.17,5:0.12}

    if(nexp>5):
        sys.exit('Maximal number of 4 experiments reached. Please reduce the number of experiments on the figure')
   
    if(type_sta=='comb'):
        ncol=2
        list_type = ['manual','auto']
    else:
        ncol=1
        list_type = [type_sta]

    #Reduce time dimension
    res = res.isel(time=0)   

    if(nreg<4):
        fig, ax = plt.subplots(nscore, ncol, sharex='col',figsize=(1.6*nreg*ncol,nscore*8/3.),squeeze=False)
    else:
        fig, ax = plt.subplots(nscore, ncol, sharex='col',figsize=(0.6*nreg*ncol,nscore*8/3.),squeeze=False)

    ax = np.atleast_1d(ax)

    title = dic_var[var]+': '+per
    fig.suptitle(get_suptitle(type_plot,title,exp_ref),y=dic_fig['sup_title'][nscore],fontweight="bold",fontsize=11)

    #if(ncol==2):
    #    fig.supxlabel('Number of stations are shown above the top graphs',fontstyle="italic",fontsize=10)    
    plt.subplots_adjust( wspace=0.05,hspace=0.15)
    plot_lines = []

    for itype,tt in enumerate(list_type):

        for iscore,sco in enumerate(list_score):

            # Define maximal and minimal value when computing the scores
            max_g,min_g = get_limits(type_plot, sco,limits[var]) 

            if(ncol==2):
                iplot = iscore*2+itype
            else:
                iplot = iscore 
            print(sco,iplot)
            cp_reg = 0
            name_reg  = []

            ind = 0  
            w = get_width(nexp)

            ax.ravel()[iplot].set_xticks(np.arange(-0.5,nreg ,1))
            ax.ravel()[iplot].grid(zorder=0)
            ax.ravel()[iplot].set_axisbelow(True)            

            for ireg,reg in enumerate(list_reg):
                mask_ref=res['mask_'+reg].values

                if(tt=='manual'):
                    mask_sta = (res['type_mes'].values<=1)
                elif(tt=='auto'):
                    mask_sta = (res['type_mes'].values>1)
                elif(tt=='all'): # Select all stations
                    mask_sta = (res['type_mes'].values>-10)
                    
                mask_ref =  mask_ref & mask_sta

               # for iexp,exp in enumerate(res.exp.values):
                for iexp,exp in enumerate(list_exp):                    
                    iplot2=0
                    mask_nobs = res['nobs'].loc[(dict(exp=exp))].values >nobs_min

                    mask_ref_exp =  mask_ref & mask_nobs

                    var_sel = get_var_boxplot(res,sco,exp,exp_ref,type_plot,mask_ref_exp)

                    #var_sel = res[sco].loc[(dict(exp=exp))].values[mask_ref_exp]
                    mask_mod = np.isnan(var_sel)
                    var_sel = var_sel[~mask_mod] 

                    nexp_plot = 0
                    if(len(var_sel)> 5): 

                        if(iexp==0 and iscore==0):
                            ax.ravel()[iplot].text(ireg, max_g+(0.04)*(max_g-min_g), int(len(var_sel)),{'fontsize':9,'color':'k','style':'italic'},horizontalalignment='center',verticalalignment='center')
                        nexp_plot = nexp_plot+1
                        #bb1 = ax.ravel()[iplot].boxplot(var_sel,positions = [cp_reg/2.-w*nexp/2. + w/2+ iexp*w], widths = 0.95*w,patch_artist=True,whis=[10,90],showfliers=False,showmeans=False,meanprops={'markeredgecolor':'black','markerfacecolor':'grey'})
                        bb1 = ax.ravel()[iplot].boxplot(var_sel,positions = [ireg-w/2*nexp +w/2.+ iexp*w], widths = 0.95*w,patch_artist=True,whis=[10,90],showfliers=False,showmeans=False,meanprops={'markeredgecolor':'black','markerfacecolor':'grey'})
                        set_whis(bb1,cfg_exp[exp]['col'],'green')

                        iplot2=iplot2+1


                        if iplot2==1:
                            plot_lines.append(bb1["boxes"][0])

                    iplot2=iplot2+1


                #if(nexp_plot>0):
                    #cp_reg = cp_reg+1
                name_reg.append(dic_reg[reg])

            ax.ravel()[iplot].set_xlim(-0.5,  nreg-0.5 )
            if(itype==0):
                ax.ravel()[iplot].set_ylabel(get_ylab_boxplot(type_plot,dic_title, units, sco),fontsize=13)
            else:
                ax.ravel()[iplot].set_yticklabels([])

            if(ncol==2):
                if(iscore==0):
                    if(itype==0):
                        ax.ravel()[iplot].set_title('Manual snow course',y=1.04)
                    else:
                        ax.ravel()[iplot].set_title('Automatic stations',y=1.04)
            else:
                if(iscore==0):
                    if(type_sta=='manual'):
                        tt = 'Manual snow course'
                    elif(type_sta=='auto'):
                        tt = 'Automatic stations'
                    else:
                        tt = 'Manual + automatic measurements'
                    ax.ravel()[iplot].set_title(tt,y=1.04)

            ax.ravel()[iplot].set_xticks(np.arange(0,nreg ,1))
            if(ncol==2):
                ax.ravel()[iplot].set_xticklabels(name_reg,rotation=45,ha='center',fontsize = 9)        
            else:
                ax.ravel()[iplot].set_xticklabels(name_reg,rotation=45,ha='right',fontsize = 11)        

            ax.ravel()[iplot].set_ylim(min_g,max_g)
            #ax.ravel()[iplot].grid()

            if(iplot==0):
                fig.legend([plot_lines[i] for i in np.arange(0,len(list_exp))],list_exp,loc='upper center',bbox_to_anchor=(0.5, dic_fig['loc_leg'][nscore]),ncol=len(res.exp.values),borderaxespad=0.1,fontsize=10,shadow=True)
                fig.subplots_adjust(bottom=dic_fig['fig_bot'][nscore])

    plt.savefig(fig_name,format="png",bbox_inches='tight',dpi=300)
    plt.clf()


def plot_boxplot_comb(list_score,list_reg,type_sta,res,var,X,X2,fig_name,per,nobs_min,type_cat,reg_sel,type_plot,exp_ref,ladd_nsta):

    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Get units
    units=give_units(var,X2,type_plot)

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')

    list_score_routine=list_score.copy()
    if(ladd_nsta):
        list_score_routine.append('nsta')

    nscore = len(list_score_routine)
    nreg = len(list_reg)

    list_exp = res.exp.values.tolist()
    if(type_plot in ['dif','dif_rel']):
        list_exp.remove(exp_ref)
    nexp=len(list_exp)
    
    if(nscore>4):
        sys.exit('Maximal number of 4 scores reached. Please reduce the number of score on the figure with option comb')

    dic_fig={'sup_title':{1:1.2,2:1.03,3:0.98,4:0.95},
            'fig_bot':{1:0.15,2:0.12,3:0.08,4:0.07},
            'loc_leg':{1:1.12,2:0.99,3:0.95,4:0.93}}
    

    #Reduce time dimension
    res = res.isel(time=0)   

    fig, ax = plt.subplots(nscore, 2, sharex='col',figsize=(1.6*nreg*2.,nscore*8/3.))
    title = dic_var[var]+': '+per
    fig.suptitle(get_suptitle(type_plot,title,exp_ref),y=dic_fig['sup_title'][nscore],fontweight="bold") 
    if(not ladd_nsta):
        fig.supxlabel('Number of stations are shown above the top graphs',fontstyle="italic",fontsize=10)    
    plt.subplots_adjust( wspace=0.05,hspace=0.15)
    plot_lines = []

    list_type = ['man','auto']


    for itype,tt in enumerate(list_type):

        for iscore,sco in enumerate(list_score_routine):

            # Define maximal and minimal value when computing the scores
            max_g,min_g = get_limits(type_plot, sco,limits[var]) 

            iplot = iscore*2+itype
            print(sco,iplot)
            cp_reg = 0
            name_reg  = []

            ind = 0  
            if(nexp>5):
                w = 0.12
            else:
                w = 0.17            
            ax.ravel()[iplot].set_xticks(np.arange(-0.5,nreg ,1))
            ax.ravel()[iplot].grid(zorder=0)
            ax.ravel()[iplot].set_axisbelow(True)            

            for ireg,reg in enumerate(list_reg):

                #for iexp,exp in enumerate(res.exp.values):
                for iexp,exp in enumerate(list_exp):
                    iplot2=0

                    # Select reference mask based on type of category
                    mask_ref=get_mask_ref(res,reg,type_cat,exp)

                    # Add regional selection for certain category
                    if(type_cat in ['alti','cfia','tpi']):
                        mask_reg = res['mask_'+reg_sel].values
                        mask_ref = mask_ref & mask_reg

                    # Select as a function of measurement type
                    if(tt=='man'):
                        mask_sta = (res['type_mes'].values<=1)
                    else:
                        mask_sta = (res['type_mes'].values>1)
                    mask_ref =  mask_ref & mask_sta

                    mask_nobs = res['nobs'].loc[(dict(exp=exp))].values >nobs_min

                    mask_ref_exp =  mask_ref & mask_nobs

                    var_sel = get_var_boxplot(res,sco,exp,exp_ref,type_plot,mask_ref_exp)

                    mask_mod = np.isnan(var_sel)
                    var_sel = var_sel[~mask_mod]

                    nexp_plot = 0
                    if(len(var_sel)> 5): 

                        if(iexp==0 and iscore==0 and not ladd_nsta):
                            ax.ravel()[iplot].text(ireg, max_g+(0.04)*(max_g-min_g), int(len(var_sel)),{'fontsize':9,'color':'k','style':'italic'},horizontalalignment='center',verticalalignment='center')
                        nexp_plot = nexp_plot+1
                        if(sco=='nsta'):
                            bb2 = ax.ravel()[iplot].bar(ireg-w/2*nexp +w/2.+ iexp*w, len(var_sel),width=0.95*w,color=cfg_exp[exp]['col'],label = exp)
                        else:
                            bb1 = ax.ravel()[iplot].boxplot(var_sel,positions = [ireg-w/2*nexp +w/2.+ iexp*w], widths = 0.95*w,patch_artist=True,whis=[10,90],showfliers=False,showmeans=False,meanprops={'markeredgecolor':'black','markerfacecolor':'grey'})
                            set_whis(bb1,cfg_exp[exp]['col'],'green')

                        iplot2=iplot2+1


                        if iplot2==1:
                            plot_lines.append(bb1["boxes"][0])

                    iplot2=iplot2+1

                if(type_cat=='reg'):
                    name_reg.append(dic_reg[reg])
                elif(type_cat in ['alti','cfia','tpi']):
                    name_reg.append(get_name(reg,type_cat))
                    
            ax.ravel()[iplot].set_xlim(-0.5,  nreg-0.5 )
            if(itype==0):
                ax.ravel()[iplot].set_ylabel(get_ylab_boxplot(type_plot,dic_title, units, sco),fontsize=13)
            else:
                ax.ravel()[iplot].set_yticklabels([])

            if(iscore==0):
                if(itype==0):
                    ax.ravel()[iplot].set_title('Manual snow course',y=1.04)
                else:
                    ax.ravel()[iplot].set_title('Automatic stations',y=1.04)

            ax.ravel()[iplot].set_xticks(np.arange(0,nreg ,1))
            ax.ravel()[iplot].set_xticklabels(name_reg,rotation=0,ha='center',fontsize = 11)            
            ax.ravel()[iplot].set_ylim(min_g,max_g)

            if(iplot==0):
                fig.legend([plot_lines[i] for i in np.arange(0,len(list_exp))],list_exp,loc='upper center',bbox_to_anchor=(0.5, dic_fig['loc_leg'][nscore]),ncol=len(list_exp),borderaxespad=0.1,fontsize=10,shadow=True)
                fig.subplots_adjust(bottom=dic_fig['fig_bot'][nscore])

    plt.savefig(fig_name,format="png",bbox_inches='tight',dpi=300)
    plt.clf()




def give_units(var,X2,type_plot):
    dic_units = X2.dic_var_units
    uu = dic_units[var]
    if(type_plot=='dif_rel'):
        uu='%'
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'kge12':'-','kge09':'-','moymod':uu,'nrmse':'-', 'ss':'-','rbias':'-','crps':uu, 'crps_pot':uu, 'crps_rel':uu,'nrmse':'-'}
    return(units)

def get_ylab_boxplot(type_plot,dic_title,units,sco):
    if(sco=='nsta'):
        return('Number of stations')
    else:
        ylab = dic_title[sco]+' ('+units[sco]+')'
        if(type_plot=='val'):
            return(ylab) 
        elif(type_plot in ['dif','dif_rel']):
            return('Changes in '+ylab)

def get_suptitle(type_plot,title,exp_ref):  
    if(type_plot=='val'):
        return(title) 
    elif(type_plot in ['dif','dif_rel']):
        return('Changes comp. to '+exp_ref+' for '+title)

def get_var_boxplot(res,sco,exp,exp_ref,type_plot,mask_ref_exp): 

    if(sco=='nsta'):
        var_sel = res['rmse'].loc[(dict(exp=exp_ref))].values[mask_ref_exp]

    else:

        if(type_plot=='val'):
            var_sel = res[sco].loc[(dict(exp=exp))].values[mask_ref_exp]

        elif(type_plot=='dif'):
            sco_comp = res[sco].loc[(dict(exp=exp))].values[mask_ref_exp]
            sco_ref = res[sco].loc[(dict(exp=exp_ref))].values[mask_ref_exp]
            var_sel = sco_comp - sco_ref

        elif(type_plot=='dif_rel'):
            sco_comp = res[sco].loc[(dict(exp=exp))].values[mask_ref_exp]
            sco_ref = res[sco].loc[(dict(exp=exp_ref))].values[mask_ref_exp]
            sco_norm = res['rmse'].loc[(dict(exp=exp_ref))].values[mask_ref_exp]

            if(sco=='bias'):
                var_sel = - (np.abs(sco_comp)-np.abs(sco_ref))/np.abs(sco_norm) *100. 
            elif(sco=='cor'):
                var_sel = (sco_comp-sco_ref)/(1 - sco_ref)*100.
            else: 
                var_sel = -(sco_comp-sco_ref)/sco_ref *100.  
                    
    return(var_sel)

def get_name(reg, type_cat): 

    if(type_cat in ['alti','tpi']):
        name_reg = reg[0]+'m-'+reg[1]+'m'
    elif(type_cat=='cfia'):
        name_reg = reg[0]+'-'+reg[1]

    return(name_reg)

def get_mask_ref(res, reg, type_cat,exp): 

    if(type_cat=='reg'):
        mask_ref=res['mask_'+reg].values
    elif(type_cat=='alti'):
        alti_min = int(reg[0])
        alti_max = int(reg[1])
        mask_ref=np.logical_and(res.elevation.values > alti_min,res.elevation.values <= alti_max)
    elif(type_cat=='cfia'):
        cfia_min = float(reg[0])
        cfia_max = float(reg[1])
        mask_ref=np.logical_and(res['CFIA_'+exp].values > cfia_min,res['CFIA_'+exp].values <= cfia_max)
    elif(type_cat=='tpi'):
        tpi_min = float(reg[0])
        tpi_max = float(reg[1])
        mask_ref=np.logical_and(res.tpi.values > tpi_min,res.tpi.values <= tpi_max)

    return(mask_ref)

def get_limits(type_plot, sco,limits): 
        # Define maximal and minimal value when computing the score
        if(sco=='nsta'):
            max_g = 200
            min_g = 0
        else: 
            if(type_plot == 'val'): 
                max_g = limits['max_g'][sco]
                min_g = limits['min_g'][sco]         
            elif(type_plot == 'dif'): 
                max_g = limits['max_g'][sco]
                min_g = -1.0 * max_g
            elif(type_plot == 'dif_rel'):
                max_g =100
                min_g = -100

        return(max_g,min_g)


def get_col(val,val_max):
    if(np.abs(val)<val_max/1.5):
        return('black')
    else:
        return('lightgrey')

def get_width(nexp):
   if(nexp<4):
      w = 0.25
   else:
      w = (1-0.1)/nexp

   return(w)

def set_whis(box,col1,col2):

   for patch in box['boxes']:
      patch.set(facecolor=col1)

   for whisker in box['whiskers']:
 #   whisker.set(color='#7570b3', linewidth=1.5)
      whisker.set(color='k',linewidth=1.)
  #    whisker.set(color=col2,linewidth=1.)

## change color and linewidth of the caps
   for cap in box['caps']:
#    cap.set(color='#7570b3', linewidth=1.5)
      cap.set( linewidth=1.)

 ## change color and linewidth of the medians
   for median in box['medians']:
     median.set( color= 'k',linewidth=1.)
     #median.set( color= col2,linewidth=1.)
  
   for bx in box['boxes']:
    # change outline color
    bx.set(  linewidth=1.5)


def plot_score_card(list_score,res_man,res_auto,var,X,X2,fig_name,exp_ref, exp_comp, per):

# Plot score card summarizing comparison between 2 experiments including res for manual and automatic stations


    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Minimal number of obs. to plot change in scores
    dic_nobs_min={'man':20,'auto':200}

    # Get units
    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'nrmse':'-'}

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')

    # List of domain with available scores
    #list_reg_all =  np.union1d(res_man.domain.values, res_auto.domain.values)
    list_reg_all = list(reversed(dict.fromkeys([*res_man.domain.values, *res_auto.domain.values])))
    nreg = len(list_reg_all)

    nscore = len(list_score)

    res_all={}
    res_all['man'] = res_man
    res_all['auto'] = res_auto
    list_type = ['man','auto']

    # Table containing the scores to be shown
    tab_score = np.zeros((nreg,nscore*2))

    list_xlabel=[]

    for ireg, reg in enumerate(list_reg_all):
       for iscore,score in enumerate(list_score):
          for it, tt in enumerate(list_type):

             tab_score[ireg,iscore*2+it] = np.nan # Default value

             if(reg in res_all[tt].domain):
               nobs = res_all[tt]['nobs'].loc[dict(domain=reg,exp=exp_ref)]
               sco_norm = res_all[tt]['rmse'].loc[dict(domain=reg,exp=exp_ref)]
               sco_ref = res_all[tt][score].loc[dict(domain=reg,exp=exp_ref)]
               sco_comp = res_all[tt][score].loc[dict(domain=reg,exp=exp_comp)]
               if(score=='bias' or score=='pbias'):
                 comp = - (np.abs(sco_comp)-np.abs(sco_ref))/np.abs(sco_norm) *100. 
                # pdb.set_trace()
               else: 
                 comp = -(sco_comp-sco_ref)/sco_norm *100.

               if(nobs>dic_nobs_min[tt]):  
                  tab_score[ireg,iscore*2+it] = comp

             if(ireg==0):
                list_xlabel.append(tt)

    plot_lines = []
    fig, ax = plt.subplots(1, 1 ,figsize=(2*nscore,0.8*nreg))

    data = np.ma.masked_invalid(tab_score)

    max_val = max(5,min(25,round(np.max(np.abs(data)))))

    c = ax.pcolor(data,cmap='RdBu_r', vmin=-1*max_val, vmax=max_val) 
    ax.patch.set(hatch='x', edgecolor='black')
    cbar= fig.colorbar(c)
    cbar.set_label('Performance change in %',fontsize=10)

    ax.set_yticks(np.arange(0.5,nreg ,1))
    ax.set_yticklabels(list_reg_all,rotation=0,fontsize = 9)
    ax.set_xticks(np.arange(0.5,nscore*2 ,1))
    ax.set_xticklabels(list_xlabel,rotation=45,ha='center',fontsize = 9)

    plt.vlines(np.arange(2,nscore*2,2),ymin=0,ymax=nreg,linewidth=3)

    for ii in np.arange(0,nscore*2 ,1):
      for jj in np.arange(0,nreg ,1):
          if(~np.isnan(tab_score[jj,ii])):
             #plt.text(ii+0.5,jj+0.5,"%.1f" % tab_score[jj,ii],fontsize = 9,ha='center',va='center',color=get_col(tab_score[jj,ii],10))
             plt.text(ii+0.5,jj+0.5,"%.1f" % tab_score[jj,ii],fontsize = 9,ha='center',va='center',color=get_col(tab_score[jj,ii],25))

    for ii,score in enumerate(list_score):
          plt.text(ii*2+1,nreg+0.2,dic_title[score],fontsize = 9,ha='center',va='center')
         
    ax.set_title('Score Card - '+dic_var[var]+' - '+exp_comp+' vs. '+exp_ref+' - '+per,y=1.06)

    plt.savefig(fig_name,format="png",bbox_inches='tight',dpi=300)
    plt.clf()


def plot_score(score,sco,reg,list_exp,var,dir_ref,tsta,X2,X,freq,suffix,ladd_nobs,limit_graph,list_tile):

    nexp = len(list_exp)
    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits
    dic_tile = X2.dic_tile
    style = X2.dic_style_tile
    
    # Get units
    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'kge12':'-','kge09':'-','moymod':uu,'nrmse':'-', 'ss':'-','rbias':'-','crps':uu, 'crps_pot':uu, 'crps_rel':uu,'nrmse':'-'}

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')

    if sco in ['rmse','medae','stde']:
        loc_leg = 'upper left'
    else:
        loc_leg = 'best'

    fig=plt.figure(figsize=(8,5))
    plt.subplots_adjust( wspace=0.,hspace=0.05)
    ax1=fig.add_subplot(1,1,1)
    
    plt.grid()

    if sco=='bias' or sco=='pbias':
        ax1.axhline(0,linewidth=1.5)
    elif sco=='rbias' or sco=='ss':
        ax1.axhline(1,linewidth=1.5, color='black', linestyle='-')

    # Determine maximum value 
    max_sco = 0.   
    for ii,exp in enumerate(list_exp):
        max_sco = np.maximum(max_sco,np.nanmax(np.abs(score[sco].loc[(dict(variable=var,domain=reg,exp=exp))].values)))
    if(np.isnan(max_sco)):
       return                # Exit function if no data are present
    
    max_t = limits[var]['max_g'][sco]
    min_t = limits[var]['min_g'][sco]

    if(limit_graph=='auto'):
        if(sco=='bias'):
            min_t = -1.1*max_sco
            max_t = 1.1*max_sco
        elif(sco in ['rmse','medae','stde','moymod','ss','rbias','crps', 'crps_pot','crps_rel', 'nrmse']):
            max_t = 1.1*max_sco

    for ii,exp in enumerate(list_exp):
        if(freq in ['month','bi-month']):
           ax1.plot(score.time,score[sco].loc[(dict(variable=var,domain=reg,exp=exp))],marker='s',color = cfg_exp[exp]['col'],linestyle='-',label=exp)
        else:
           ax1.plot(score.time,score[sco].loc[(dict(variable=var,domain=reg,exp=exp))],color = cfg_exp[exp]['col'],linewidth=2,label=exp)
           # Add score for different tile if asked by user
           if(len(list_tile)> 0):
               if(var in dic_tile.keys()):
                   for tile in list_tile:
                       vv = dic_tile[var][tile]
                       ax1.plot(score.time,score[sco].loc[(dict(variable=vv,domain=reg,exp=exp))],color = '#ef8a62',linewidth=2,label=exp+' '+tile,linestyle=style[tile])

        
        if(freq!='day'):
            for jj,dd in enumerate(score.time.values):
                nob = score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))].values[jj]
                if(np.isnan(nob)):
                    nob =0
                plt.text(dd, max_t+(0.015+(0.04*ii))*(max_t-min_t), int(nob),{'fontsize':8,'color':cfg_exp[exp]['col'],'style':'italic'},horizontalalignment='center',verticalalignment='center')
            if(sco=='moymod' and ii==0):
                ll=ax1.plot(score.time,score['moyobs'].loc[(dict(variable=var,domain=reg,exp=exp))],color = 'black',marker='s',linestyle='-',label='Obs.',zorder=10)
        else:

            if(ii==0 and ladd_nobs):
                ax2 = ax1.twinx()
                max_obs = score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))].max(skipna=True)
                ax2.plot(score.time,score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))],color = 'black',linewidth=1)
                
                ax2.set_ylim([0,1.06*max_obs])
                ax2.set_ylabel('Number of observations',fontsize = 12)  

            if(sco=='moymod' and ii==0):
                ll=ax1.plot(score.time,score['moyobs'].loc[(dict(variable=var,domain=reg,exp=exp))],color = 'black',linewidth=2,label='Obs.',zorder=1)

    ax1.set_ylabel(dic_title[sco]+' ('+units[sco]+')',fontsize = 12)
    ax1.set_ylim([min_t,max_t])
    if (sco=='moymod'):
        nleg=len(list_exp)+1
    else:
        nleg=len(list_exp)

    if(len(list_tile)> 0):
        if(var in dic_tile.keys()):
            nleg = nleg + len(list_tile)

    if(freq!='day'):
        ax1.legend(loc=loc_leg,ncol=nleg,borderpad=0.2,markerscale=1,labelspacing=0.05,borderaxespad=0.1,fontsize=10)
    else:
       ax1.legend(loc='center',ncol=nleg,borderpad=0.2,markerscale=1,labelspacing=0.05,borderaxespad=0.1,fontsize=10,bbox_to_anchor=(0.5, 1.06))

    fig.suptitle(dic_var[var]+' '+dic_title[sco]+' '+reg,y=1.0)
    fig.autofmt_xdate()
    ax1.set_xlim([score.time.values[0]-np.timedelta64(2,'D'),score.time.values[-1]+np.timedelta64(2,'D')])
    
    nameexp_str  = "_".join(list_exp)

    fig_name = dir_ref+'/'+sco+'_'+var+'_'+nameexp_str+'_'+reg+'_'+tsta+'_'+suffix+'.png'

    plt.savefig(fig_name,format="png",bbox_inches='tight',dpi=300)
    plt.clf()


def plot_score_multi_reg(score,sco,var,dir_ref,tsta,X2,X,freq,list_reg,suffix):

    list_exp = score.exp.values
    nexp = len(list_exp)
    dic_title=X2.dic_score_title
    dic_var=X2.dic_varname
    dic_reg = X2.dic_reg
    dic_units = X2.dic_var_units
    cfg_exp = X.cfg_exp
    limits = X.dic_limits

    # Get units
    uu = dic_units[var]
    units={'bias':uu,'rmse':uu,'medae':uu,'nse':'-','pbias':'%','cor':'-','stde':uu,'moymod':uu, 'ss':'-'}

    if(var not in limits.keys()):
        print('The maximal and minimal values for the variable '+var+' are not defined')

    if sco in ['rmse','medae','stde']:
        loc_leg = 'upper left'
    else:
        loc_leg = 'best'

    nreg = len(list_reg)
    ncol=2
    if(nreg>2):
         nrow = (nreg+1)/2
    else:
         nrow = 1
    nrow=int(nrow)
    fig, ax = plt.subplots(nrow, ncol, sharex='col',figsize=(8*ncol,5*nrow))
  #  fig.suptitle(dic_var[var]+': '+per,y=0.98,fontweight="bold")
    plt.subplots_adjust( wspace=0.25,hspace=0.15)

    for ireg,reg in enumerate(list_reg):
      ax.ravel()[ireg].grid()
      if sco=='bias' or sco=='pbias':
        ax.ravel()[ireg].axhline(0,linewidth=1.5)

      # Determine maximum value 
      max_sco = 0.   
      for ii,exp in enumerate(list_exp):
        max_sco = np.maximum(max_sco,np.nanmax(np.abs(score[sco].loc[(dict(variable=var,domain=reg,exp=exp))].values)))
      if(np.isnan(max_sco)):
         return                # Exit function if no data are present

      # Define maximal and minimal value when computing the scores
      max_t = limits[var]['max_g'][sco]
      min_t = limits[var]['min_g'][sco]
     
      pl=[]
      
      for ii,exp in enumerate(list_exp):

        if(freq!='day'):
          for jj,dd in enumerate(score.time.values):
            nob = score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))].values[jj]
            if(np.isnan(nob)):
                nob =0
            ax.ravel()[ireg].text(dd, 0.98*max_t-(0.015+(0.04*ii))*(max_t-min_t), int(nob),{'fontsize':8,'color':cfg_exp[exp]['col'],'style':'italic'},horizontalalignment='center',verticalalignment='center',)
        else:
           if(ii==0):
            if(sco!='moymod'):
              ax2 = ax.ravel()[ireg].twinx()
              max_obs = np.nanmax(score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))].values[:])
              ax2.plot(score.time,score['nobs'].loc[(dict(variable=var,domain=reg,exp=exp))],color = 'black',linewidth=1,zorder=10,linestyle='dashed')
              ax2.set_ylim([0,1.06*max_obs])
              ax2.set_ylabel('Number of observations',fontsize = 12) 
 
        if(freq in ['month','bi-month']):
           ll=ax.ravel()[ireg].plot(score.time,score[sco].loc[(dict(variable=var,domain=reg,exp=exp))],marker='s',color = cfg_exp[exp]['col'],linestyle='None',label=exp)
        else:
           ll=ax.ravel()[ireg].plot(score.time,score[sco].loc[(dict(variable=var,domain=reg,exp=exp))],color = cfg_exp[exp]['col'],linewidth=2,label=exp,zorder=1)
           if(sco=='moymod' and ii==0):
               ll=ax.ravel()[ireg].plot(score.time,score['moyobs'].loc[(dict(variable=var,domain=reg,exp=exp))],color = 'black',linewidth=2,label='Obs.',zorder=1)
        if(ireg==0):
            pl.append(ll) 

      ax.ravel()[ireg].set_ylabel(dic_title[sco]+' ('+units[sco]+')',fontsize = 12)  
      ax.ravel()[ireg].set_ylim([min_t,max_t])
      ax.ravel()[ireg].set_title('Region: '+dic_reg[reg],fontsize = 14)

      fig.suptitle(dic_var[var]+' - Time series of '+dic_title[sco],y=0.97,fontweight="bold",fontsize = 14)
      fig.autofmt_xdate()
      ax.ravel()[ireg].set_xlim([score.time.values[0]-np.timedelta64(2,'D'),score.time.values[-1]+np.timedelta64(2,'D')])
      if(sco=='moymod'):
          ncol_leg = len(list_exp)+1
      else:
          ncol_leg = len(list_exp)

      ax.ravel()[ireg].legend(loc='best',ncol=ncol_leg,borderpad=0.2,markerscale=1,labelspacing=0.05,borderaxespad=0.1,fontsize=11)#,bbox_to_anchor=(1.07, 1.15))

    fig_name = dir_ref+'/'+sco+'_'+var+'_multidomain_'+tsta+'_'+suffix+'.png'
    plt.savefig(fig_name,format="png",bbox_inches='tight')
    plt.clf()


def add_tpi(ds,dtpi):

    file_elev = '/fs/site7/eccc/cmd/cmd_shared/slib800/geo/GMTED2010/products/mean/mn75_grd.tif'
    elev = rxr.open_rasterio(file_elev, masked=True).squeeze()
    #transformer = Transformer.from_crs("EPSG:4326", elev.rio.crs, always_xy=True)

    list_sta = ds.station_id.values.tolist()

    stations=[]

    for sta in list_sta:

        lat = ds['lat'].loc[ds.station_id ==sta].values.item()
        lon = ds['lon'].loc[ds.station_id ==sta].values.item()
        alti = ds['elevation'].loc[ds.station_id ==sta].values.item()
        sid = ds['station_id'].loc[ds.station_id ==sta].values.item()

        stations.append({"name":sid,"lon":lon,"lat":lat,'elev':alti})

    results = compute_tpi(elev, stations, radius_m=dtpi*1000.)
    #print(results)

    tpi_list=[tt['tpi'] for tt in results]
    ds['tpi']=xr.DataArray(tpi_list,dims='station_id')

    #sid='BCE-2A27'
    #mm = [tt['name']=='BCE-2A27' for tt in results]
    #results[mm.index(True)]


def compute_tpi(elev, stations, radius_m):
    """
    Compute TPI for a list of stations.

    Parameters:
        elev      : xarray.DataArray - elevation data loaded with rioxarray
        stations  : list of dicts with keys 'name', 'lon', 'lat'
        radius_m  : float - radius in metres

    Returns:
        list of dicts with keys 'name', 'tpi', 'elev', 'mean_elev'
    """
    results = []

    transformer = Transformer.from_crs("EPSG:4326", elev.rio.crs, always_xy=True)
    pixel_size_x = abs(float(elev.x[1] - elev.x[0]))
    pixel_size_y = abs(float(elev.y[1] - elev.y[0]))

    for stn in stations:

        lon, lat = stn["lon"], stn["lat"]

        # Local azimuthal equidistant projection centred on the station
        # distances from centre are accurate in metres in all directions
        aeqd = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m"
        to_aeqd = Transformer.from_crs("EPSG:4326", aeqd, always_xy=True)
        to_wgs84 = Transformer.from_crs(aeqd, "EPSG:4326", always_xy=True)


         # Convert radius_m to degrees by projecting a bounding box corner
        lon_e, _ = to_wgs84.transform( radius_m, 0)
        _, lat_n = to_wgs84.transform(0,  radius_m)
        _, lat_s = to_wgs84.transform(0, -radius_m)
        lon_w, _ = to_wgs84.transform(-radius_m, 0)

        radius_deg_x = abs(lon_e - lon)
        radius_deg_y = max(abs(lat_n - lat), abs(lat_s - lat))

        # Clip patch in WGS84
        patch_da = elev.sel(x=slice(lon - radius_deg_x, lon + radius_deg_x),y=slice(lat + radius_deg_y, lat - radius_deg_y))  # top-down
        patch = patch_da.values.astype(np.float32)


        # Centre pixel
        col_c = int(np.argmin(np.abs(patch_da.x.values - lon)))
        row_c = int(np.argmin(np.abs(patch_da.y.values - lat)))

        # Reproject all pixel coords to AEQD → distances in metres
        lons_grid, lats_grid = np.meshgrid(patch_da.x.values, patch_da.y.values)
        x_m, y_m = to_aeqd.transform(lons_grid, lats_grid)
        dist_m = np.sqrt(x_m**2 + y_m**2)

        # TPI
        centre_elev = patch[row_c, col_c]
        neighbourhood = np.where(dist_m <= radius_m, patch, np.nan)
        neighbourhood[row_c, col_c] = np.nan

        mean_elev = np.nanmean(neighbourhood)
        tpi = centre_elev - mean_elev

        results.append({
            "name": stn["name"],
            "tpi": float(tpi),
            "elev": float(centre_elev),
            "mean_elev": float(mean_elev)
        })        


    return results


def emetDomain(name):
    if name == 'AlaskaplusCanadianArctic':
        coord = ((58,-170),(58,-141),(58,-122.65),(58,-97.5),(58,-50),(90,-50),(90,-170))
    elif name   == 'AlbertaSaskatchewan':
        coord = ((58,-122.65),(53.93,-119.14),(48.98,-111.93),(49.02,-97.5),(58,-97.5))
    elif name == 'BritishColumbia2':
        coord = ((48.67,-129.95),(48.18,-122.83),(48.99,-122.52),(48.98,-111.93),(53.93,-119.14),(58,-122.65),(58,-141.09))
    elif name == 'Canada':
        coord = ((48.67,-129.95),(48.18,-122.83),(48.99,-122.52),(48.98,-111.93),(49.02,-95.01),(48.5,-94.04),(47.94,-91.41), \
                 (47.94,-89.3),(48.28,-88.44),(46.68,-84.88),(44.95,-82.4),(43.61,-82.18),(41.88,-83.17),(41.7,-82.35), \
                 (42.92,-78.75),(43.45,-79.21),(43.75,-76.68),(44.98,-74.75),(45.01,-70.88),(47.29,-69.35),(47.17,-67.9), \
                 (45.93,-67.98),(42.76,-66.27),(45,-50),(73.6,-63.19),(77.56,-76.38),(83.24,-55.99),(83.24,-87.45),(71.54,-141.06), \
                 (57.47,-141.09))
    elif name == 'CanadaEast':
        coord = ((48.98,-97.5),(49.02,-95.01),(48.5,-94.04),(47.94,-91.41),(47.94,-89.3),(48.28,-88.44),(46.68,-84.88), \
                 (44.95,-82.4),(43.61,-82.18),(41.88,-83.17),(41.7,-82.35),(42.92,-78.75),(43.45,-79.21),(43.75,-76.68), \
                 (44.98,-74.75),(45.01,-70.88),(47.29,-69.35),(47.17,-67.9),(45.93,-67.98),(42.76,-66.27),(45,-50), \
                 (58,-50),(58,-97.5))
    elif name == 'CanadaWest':
        coord = ((48.67,-129.95),(48.18,-122.83),(48.99,-122.52),(48.98,-111.93),(49.02,-97.5),(58,-97.5),(58,-141.09))
    elif name == 'CanadianArctic':
        coord = ((58,-141),(58,-50),(90,-50),(90,-141))
    elif name == 'GreatLakesWatersheds':
        coord = ((40.3996734619141,-84.4644012451172),(40.3998107910156,-84.4871292114258),(40.4000625610352,-84.4904251098633), \
                 (40.400577545166,-84.4933471679688),(40.4019355773926,-84.4978942871094),(41.3868598941689,-87.4282608028936), \
                 (41.387577056736,-87.4295806883979),(41.3884696959199,-87.4307861324739),(41.3902664181608,-87.4329452518218), \
                 (46.8414115905762,-93.1713790893555),(46.8439292907715,-93.1733551025391),(46.8450088500977,-93.1741409301758), \
                 (46.8506736755371,-93.1766510009766),(46.8511238098145,-93.1767883300781),(46.9364204406738,-93.1970367431641), \
                 (47.1507911682129,-93.2052001953125),(47.1526794433594,-93.205207824707),(47.1539421081543,-93.205078125), \
                 (47.1567306518555,-93.2040328979492),(47.1682586669922,-93.1984100341797),(47.171142578125,-93.1967010498047), \
                 (47.1810531616211,-93.1905364990234),(47.458869934082,-92.9884490966797),(49.96484375,-89.99609375), \
                 (50.39453125,-89.28125),(50.734375,-88.7109375),(50.73828125,-88.42578125),(50.73828125,-88.3828125), \
                 (49.609375,-85.5390625),(47.3554687502827,-79.8671874998031),(44.0141830444336,-74.6891174316406), \
                 (43.9594383239746,-74.6161727905273),(43.957088470459,-74.6136932373047),(43.9563598632813,-74.6130752563477), \
                 (43.7368621826172,-74.5177536010742),(43.6615753173828,-74.4993743896484),(43.6587867736816,-74.499397277832), \
                 (43.6577072143555,-74.4996490478516),(43.657169342041,-74.5000305175781),(42.3495941162109,-76.3157653808594), \
                 (42.2699508666992,-76.5061721801758),(42.2684478759766,-76.5108642578125),(41.8462867736816,-77.8365631103516), \
                 (40.9722213745117,-81.2614364624023),(40.5986824035645,-83.2250137329102),(40.4269485473633,-84.2626647949219), \
                 (40.422004699707,-84.2935104370117),(40.408763885498,-84.3834686279297),(40.4076232910156,-84.3927001953125), \
                 (40.3999633789063,-84.4612121582031),(40.3996734619141,-84.4644012451172))
    elif name == 'Maritimes':
        coord = ((49.56,-74),(55.13,-54.9),(45.29,-50.33),(40.63,-66.8))
    elif name == 'Prairies':
        coord = ((48.76,-119.92),(48.76,-93.28),(60.94,-89.51),(60.94,-120.36))
    elif name == 'NorthAmericaPlus':
        coord = ((25,-170),(25,-40),(85,-40),(85,-170)) 
    elif name == 'NorthAmericaPlus_ESSD_Gonzalo':
        coord = ((29,-130),(29,-66),(76,-66),(76,-130))
    elif name == 'OntarioQuebec':
        coord = ((48,-96.01),(40.12,-82.74),(44.03,-70.26),(49.68,-63.49),(57.99,-63.23),(57.99,-96.01))
    elif name == 'UnitedStatesOfAmerica':
        coord = ((48.67,-129.95),(48.18,-122.83),(48.99,-122.52),(48.98,-111.93),(49.02,-95.01),(48.5,-94.04),(47.94,-91.41), \
                 (47.94,-89.3),(48.28,-88.44),(46.68,-84.88),(44.95,-82.4),(43.61,-82.18),(41.88,-83.17),(41.7,-82.35), \
                 (42.92,-78.75),(43.45,-79.21),(43.75,-76.68),(44.98,-74.75),(45.01,-70.88),(47.29,-69.35),(47.17,-67.9), \
                 (45.93,-67.98),(42.76,-66.27),(45,-50),(25,-70),(25,-130))
    elif name == 'UnitedStatesOfAmericaEast':
        coord = ((48.98,-97.5),(49.02,-95.01),(48.5,-94.04),(47.94,-91.41),(47.94,-89.3),(48.28,-88.44),(46.68,-84.88),(44.95,-82.4), \
                 (43.61,-82.18),(41.88,-83.17),(41.7,-82.35),(42.92,-78.75),(43.45,-79.21),(43.75,-76.68),(44.98,-74.75), \
                 (45.01,-70.88),(47.29,-69.35),(47.17,-67.9),(45.93,-67.98),(42.76,-66.27),(45,-50),(25,-50),(25,-97.5))
    elif name == 'UnitedStatesOfAmericaWest':
        coord = ((48.67,-130),(48.18,-122.83),(48.99,-122.52),(48.98,-111.93),(49.02,-97.5),(25,-97.5),(25,-130))
    elif name == 'Appalachia_CLIM':
        coord =  ((42.5,-80.5),(42.5,-78.5),(42,-78.5),(42,-78),(41.5,-78),(41.5,-77.5),(41,-77.5),(41,-78),(41,-78.5),(39.5,-78.5),(39.5,-79),(38.5,-79),(38.5,-79.5),(38,-79.5),(38,-80),(37.5,-80),(37.5,-80.5),(37,-80.5),(37,-81),(36.5,-81),(36.5,-81.5),(36,-81.5),(36,-82),(35.5,-82),(35.5,-82.5),(35,-82.5),(35,-83),(34.5,-83),(34.5,-83.5),(34,-83.5),(34,-85),(35,-85),(35,-85.5),(35.5,-85.5),(35.5,-86),(36,-86),(36,-87),(36.5,-87),(36.5,-87.5),(37,-87.5),(37,-88.5),(37.5,-88.5),(37.5,-88),(38,-88),(38,-87.5),(38.5,-87.5),(38.5,-87),(39,-87),(39,-86.5),(40.5,-86.5),(40.5,-83.5),(40.5,-83),(41,-83),(41,-82.5),(41,-82),(41.5,-82),(41.5,-81),(41.5,-80.5),(42.5,-80.5))
    elif name == 'Mt_West_CLIM':
        coord = ((56,-125),(56,-122.5),(55.5,-122.5),(55.5,-121),(55,-121),(55,-120.5),(54.5,-120.5),(54.5,-119.5),(54,-119.5),(54,-118),\
                (53.5,-118),(53.5,-117),(53,-117),(53,-116.5),(52.5,-116.5),(52.5,-115.5),(52,-115.5),(52,-115),(51.5,-115),(51.5,-114.5),(50.5,-114.5),\
                (50.5,-114),(49.5,-114),(49.5,-113),(49,-113),(49,-112.5),(48,-112.5),(48,-112),(47.5,-112),(47.5,-110.5),(47,-110.5),(47,-110),(46.5,-110),\
                (46.5,-109.5),(46,-109.5),(46,-109),(45.5,-109),(45.5,-108.5),(45,-108.5),(45,-108),(44.5,-108),(44.5,-107.5),(44,-107.5),(44,-107),\
                (43,-107),(43,-106.5),(42.5,-106.5),(42.5,-106),(42,-106),(42,-105),(41,-105),(41,-104.5),(38,-104.5),(38,-104),(37.5,-104),(37.5,-103.5),\
                (35.5,-103.5),(35.5,-104),(35,-104),(35,-104.5),(34.5,-104.5),(34.5,-105),(34,-105),(34,-105.5),(33,-105.5),(33,-108.5),(33.5,-108.5),\
                (33.5,-109),(34,-109),(34,-109.5),(34.5,-109.5),(34.5,-110.5),(35,-110.5),(35,-111),(35.5,-111),(35.5,-111.5),(36,-111.5),(36,-112),\
                (36.5,-112),(36.5,-118.5),(37,-118.5),(37,-119),(37.5,-119),(37.5,-119.5),(38,-119.5),(38,-120),(38.5,-120),(38.5,-120.5),(39,-120.5),\
                (39,-121),(39.5,-121),(39.5,-121.5),(40,-121.5),(40,-122),(45.5,-122),(45.5,-121.5),(47,-121.5),(47,-121),(48,-121),(48,-120.5),\
                (49.5,-120.5),(49.5,-121.5),(50,-121.5),(50,-122),(51,-122),(51,-122.5),(51.5,-122.5),(51.5,-123),(52,-123),(52,-123.5),(52.5,-123.5),\
                (52.5,-124),(53,-124),(53,-124.5),(53.5,-124.5),(53.5,-125),(54,-125),(54,-125.5),(54.5,-125.5),(54.5,-126.5),(55,-126.5),(55,-126),\
                (55,-125.5),(55.5,-125.5),(55.5,-125),(56,-125))
    elif name == 'Pacific_North_West_CLIM':
         coord = ((60,-138.5),(60,-137),(59.5,-137),(59.5,-136),(60,-136),(60,-135),(59.5,-135),(59.5,-134),(59,-134),(59,-133.5),(58.5,-133.5),(58.5,-133),\
                 (58,-133),(58,-132),(57.5,-132),(57.5,-131.5),(57,-131.5),(57,-130.5),(56.5,-130.5),(56.5,-129.5),(56,-129.5),(56,-128.5),(55.5,-128.5),\
                 (55.5,-128),(55,-128),(55,-126.5),(54.5,-126.5),(54.5,-125.5),(54,-125.5),(54,-125),(53.5,-125),(53.5,-124.5),(53,-124.5),(53,-124),\
                 (52.5,-124),(52.5,-123.5),(52,-123.5),(52,-123),(51.5,-123),(51.5,-122.5),(51,-122.5),(51,-122),(50,-122),(50,-121.5),(49.5,-121.5),\
                 (49.5,-120.5),(48,-120.5),(48,-121),(47,-121),(47,-121.5),(45.5,-121.5),(45.5,-122),(40.5,-122),(40.5,-122.5),(40.5,-123),(40,-123),\
                 (40,-123.5),(39.5,-123.5),(39.5,-124),(39,-124),(39,-124.5),(39.5,-124.5),(39.5,-125),(42,-125),(42,-125.5),(43,-125.5),(43,-125),\
                 (47.5,-125),(47.5,-125.5),(48.5,-125.5),(48.5,-126.5),(49,-126.5),(49,-127),(49.5,-127),(49.5,-128),(50,-128),(50,-129),(51,-129),\
                 (51,-128.5),(51.5,-128.5),(51.5,-129),(52,-129),(52,-129.5),(52.5,-129.5),(52.5,-130),(53,-130),(53,-131),(53.5,-131),(53.5,-131.5),\
                 (55,-131.5),(55,-132.5),(54.5,-132.5),(54.5,-132),(53,-132),(53,-131.5),(52.5,-131.5),(52.5,-131),(52,-131),(52,-131.5),(52,-132.5),\
                 (52.5,-132.5),(52.5,-133.5),(53.5,-133.5),(53.5,-134),(54.5,-134),(54.5,-133.5),(55,-133.5),(55,-134.5),(56,-134.5),(56,-135.5),\
                 (56.5,-135.5),(56.5,-136),(57,-136),(57,-137),(58,-137),(58,-138.5),(60,-138.5))
    elif name == 'North_Rockies_CLIM':
         coord =((56,-125),(56,-122.5),(55.5,-122.5),(55.5,-121),(55,-121),(55,-120.5),(54.5,-120.5),(54.5,-119.5),(54,-119.5),(54,-118),(53.5,-118),\
                 (53.5,-117),(53,-117),(53,-116.5),(52.5,-116.5),(52.5,-115.5),(52,-115.5),(52,-115),(51.5,-115),(51.5,-114.5),(50.5,-114.5),(50.5,-114),\
                 (49.5,-114),(49.5,-113),(49,-113),(49,-112.5),(48,-112.5),(48,-112),(47.5,-112),(47.5,-110.5),(47,-110.5),(47,-110),(46.5,-110),(46.5,-109.5),\
                 (46,-109.5),(46,-109),(45.5,-109),(45.5,-108.5),(45,-108.5),(45,-108),(44.5,-108),(44.5,-107.5),(44,-107.5),(44,-107),(43.5,-107),(43.5,-107.5),\
                 (43.5,-108),(43,-108),(43,-108.5),(42.5,-108.5),(42.5,-109),(42,-109),(42,-109.5),(42,-111),(41.5,-111),(41.5,-113),(42,-113),(42,-114),\
                 (42.5,-114),(42.5,-114.5),(43,-114.5),(43,-116),(43.5,-116),(43.5,-116.5),(44.5,-116.5),(44.5,-117),(49,-117),(49,-117.5),(49.5,-117.5), \
                 (49.5,-118),(50,-118),(50,-118.5),(50.5,-118.5),(50.5,-119),(51,-119),(51,-120),(51.5,-120),(51.5,-121),(52,-121),(52,-121.5),(52.5,-121.5),\
                 (52.5,-122),(53.5,-122),(53.5,-123),(54,-123),(54,-125.5),(54.5,-125.5),(54.5,-126.5),(55,-126.5),(55,-126),(55,-125.5),(55.5,-125.5),(55.5,-125),(56,-125))
    elif name == 'NorthAmericaEast':
        coord = ((25,-97.5),(25,-50),(85,-50),(85,-97.5)) 
    elif name == 'NorthAmericaWest':
        coord = ((25,-145),(25,-97.5),(85,-97.5),(85,-145))
    elif name == 'Great_Lakes_CLIM':
        coord = ((49,-89.5),(49,-87),(48.5,-87),(48.5,-86.5),(48,-86.5),(48,-85.5),(47.5,-85.5),(47.5,-85),(47,-85),(47,-84.5),(46.5,-84.5),\
                (46.5,-81.5),(46,-81.5),(46,-80.5),(45.5,-80.5),(45.5,-77.5),(46,-77.5),(46,-74.5),(46,-74),(46.5,-74),(46.5,-72.5),(45.5,-72.5),\
                (45.5,-73),(45.5,-73.5),(45,-73.5),(45,-74),(45,-75.5),(44.5,-75.5),(44.5,-76),(44,-76),(44,-76.5),(43,-76.5),(43,-77),(43,-79),\
                (42.5,-79),(42.5,-79.5),(42.5,-80.5),(41.5,-80.5),(41.5,-81),(41.5,-82),(41,-82),(41,-82.5),(41,-83),(40.5,-83),(40.5,-87.5),\
                (41,-87.5),(41,-88.5),(41.5,-88.5),(41.5,-89),(44,-89),(44,-89.5),(45,-89.5),(45,-90),(45.5,-90),(45.5,-90.5),(46,-90.5),(46,-92.5), \
                (47.5,-92.5),(47.5,-92),(48,-92),(48,-91),(48,-90.5),(48.5,-90.5),(48.5,-90),(48.5,-89.5),(49,-89.5))
    elif name == 'SouthOntario':   
        coord = ((41.3,-84),(44,-72),(46.2,-72),(48.6,-79),(48.6,-84))
    #elif name == 'Arctic_All_CLIM':
    #    coord = ((70,-105),(70,-87.5),(69.5,-87.5),(69.5,-78),(69,-78),(69,-74),(68.5,-74),(68.5,-69.5),(68,-69.5),(68,-65.5),(67.5,-65.5),(67.5,-62.5),(67,-62.5),(67,-58.5),(66.5,-58.5),(66.5,-56.5),(66,-56.5),(66,-54.5),(65.5,-54.5),(65.5,-53),(65,-53),(65,-52),(64.5,-52),(64.5,-51),(64,-51),(64,-49.5),(63.5,-49.5),(63.5,-49),(63,-49),(63,-48),(62.5,-48),(62.5,-47),(62,-47),(62,-46),(61.5,-46),(61.5,-45.5),(61,-45.5),(61,-45),(60.5,-45),(60.5,-43.5),(60,-43.5),(60,-43),(59.5,-43),(59.5,-42.5),(59,-42.5),(59,-41.5),(58.5,-41.5),(58.5,-41),(57.5,-41),(57.5,-41.5),(57.5,-42),(57,-42),(57,-42.5),(56.5,-42.5),(56.5,-43),(56,-43),(56,-43.5),(56,-44),(55.5,-44),(55.5,-44.5),(55,-44.5),(55,-45),(54.5,-45),(54.5,-45.5),(54.5,-46),(54,-46),(54,-46.5),(53.5,-46.5),(53.5,-47),(53,-47),(53,-47.5),(53,-48),(52,-48),(52,-48.5),(51.5,-48.5),(51.5,-49),(51.5,-49.5),(51,-49.5),(51,-50),(50.5,-50),(50.5,-50.5),(49.5,-50.5),(49.5,-51),(49.5,-51.5),(49,-51.5),(49,-52),(48,-52),(48,-52.5),(47.5,-52.5),(47.5,-53),(48.5,-53),(48.5,-54),(49.5,-54),(49.5,-55.5),(50,-55.5),(50,-56.5),(51,-56.5),(51,-56),(53,-56),(53,-56.5),(53.5,-56.5),(53.5,-57.5),(54,-57.5),(54,-58),(54.5,-58),(54.5,-58.5),(54,-58.5),(54,-59),(54,-60),(53.5,-60),(53.5,-60.5),(53.5,-61),(53,-61),(53,-61.5),(53,-63),(52.5,-63),(52.5,-63.5),(52.5,-66),(52,-66),(52,-75),(52.5,-75),(52.5,-79.5),(51.5,-79.5),(51.5,-81),(52,-81),(52,-81.5),(53.5,-81.5),(53.5,-82.5),(54.5,-82.5),(54.5,-83),(55,-83),(55,-84.5),(55.5,-84.5),(55.5,-86.5),(56,-86.5),(56,-88),(56.5,-88),(56.5,-88.5),(57,-88.5),(57,-91.5),(57.5,-91.5),(57.5,-93),(58,-93),(58,-93.5),(58.5,-93.5),(58.5,-94.5),(59,-94.5),(59,-95),(58.5,-95),(58.5,-95.5),(58.5,-96),(58,-96),(58,-108),(58.5,-108),(58.5,-116),(59,-116),(59,-119),(59.5,-119),(59.5,-123),(60,-123),(60,-128.5),(60.5,-128.5),(60.5,-132.5),(61,-132.5),(61,-134.5),(60.5,-134.5),(60.5,-135),(60,-135),(60,-135.5),(60,-136),(59.5,-136),(59.5,-137),(60,-137),(60,-138.5),(58.5,-138.5),(58.5,-139),(59,-139),(59,-140.5),(59.5,-140.5),(59.5,-145.5),(60,-145.5),(60,-147.5),(59.5,-147.5),(59.5,-150.5),(60,-150.5),(60,-150),(60.5,-150),(60.5,-149.5),(60.5,-149),(61,-149),(61,-148.5),(61.5,-148.5),(61.5,-148),(62,-148),(62,-147),(62,-146.5),(62.5,-146.5),(62.5,-146),(63,-146),(63,-145),(63,-144.5),(63.5,-144.5),(63.5,-144),(64,-144),(64,-143),(64,-142.5),(64.5,-142.5),(64.5,-141.5),(64.5,-141),(65,-141),(65,-139),(65,-138.5),(65.5,-138.5),(65.5,-137),(65.5,-136.5),(66,-136.5),(66,-135.5),(66,-135),(66.5,-135),(66.5,-132.5),(66.5,-132),(67,-132),(67,-130.5),(67,-130),(67.5,-130),(67.5,-127.5),(67.5,-127),(68,-127),(68,-123.5),(68,-123),(68.5,-123),(68.5,-119),(68.5,-118.5),(69,-118.5),(69,-115),(69,-114.5),(69.5,-114.5),(69.5,-105.5),(69.5,-105),(70,-105))
    elif name == 'Arctic_Land_CLIM':   
        coord = ((68.5,-73),(68.5,-69.5),(68,-69.5),(68,-65.5),(67.5,-65.5),(67.5,-62.5),(65.5,-62.5),(65.5,-63),(65.5,-65.5),(64,-65.5),(64,-65),\
                (63,-65),(63,-65.5),(62.5,-65.5),(62.5,-66),(62.5,-66.5),(62,-66.5),(62,-69.5),(62.5,-69.5),(62.5,-71.5),(63,-71.5),(63,-72),(63.5,-72),\
                (63.5,-73),(64,-73),(64,-74.5),(64.5,-74.5),(64.5,-75),(66.5,-75),(66.5,-73.5),(66.5,-73),(68.5,-73),(70,-105),(70,-87.5),(69.5,-87.5),\
                (69.5,-82.5),(67,-82.5),(67,-83),(67,-83.5),(66.5,-83.5),(66.5,-84),(66.5,-84.5),(65,-84.5),(65,-83),(64,-83),(64,-83.5),(64,-84.5),\
                (63.5,-84.5),(63.5,-86.5),(64,-86.5),(64,-87),(64.5,-87),(64.5,-88.5),(64,-88.5),(64,-89),(64,-90),(63.5,-90),(63.5,-90.5),(63.5,-91),\
                (63,-91),(63,-91.5),(62.5,-91.5),(62.5,-92),(62.5,-92.5),(62,-92.5),(62,-93),(62,-93.5),(61.5,-93.5),(61.5,-94),(61,-94),(61,-94.5),\
                (60.5,-94.5),(60.5,-95),(58.5,-95),(58.5,-95.5),(58.5,-96),(58,-96),(58,-108),(58.5,-108),(58.5,-116),(59,-116),(59,-119),(59.5,-119),\
                (59.5,-123),(60,-123),(60,-128.5),(60.5,-128.5),(60.5,-132.5),(61,-132.5),(61,-134.5),(60.5,-134.5),(60.5,-135),(60,-135),(60,-135.5),\
                (60,-136),(59.5,-136),(59.5,-137),(60,-137),(60,-138.5),(58.5,-138.5),(58.5,-139),(59,-139),(59,-140.5),(59.5,-140.5),(59.5,-145.5),\
                (60,-145.5),(60,-147.5),(59.5,-147.5),(59.5,-150.5),(60,-150.5),(60,-150),(60.5,-150),(60.5,-149.5),(60.5,-149),(61,-149),(61,-148.5),\
                (61.5,-148.5),(61.5,-148),(62,-148),(62,-147),(62,-146.5),(62.5,-146.5),(62.5,-146),(63,-146),(63,-145),(63,-144.5),(63.5,-144.5),\
                (63.5,-144),(64,-144),(64,-143),(64,-142.5),(64.5,-142.5),(64.5,-141.5),(64.5,-141),(65,-141),(65,-139),(65,-138.5),(65.5,-138.5),\
                (65.5,-137),(65.5,-136.5),(66,-136.5),(66,-135.5),(66,-135),(66.5,-135),(66.5,-132.5),(66.5,-132),(67,-132),(67,-130.5),(67,-130),\
                (67.5,-130),(67.5,-127.5),(67.5,-127),(68,-127),(68,-123.5),(68,-123),(68.5,-123),(68.5,-119),(68.5,-118.5),(69,-118.5),(69,-115),\
                (69,-114.5),(69.5,-114.5),(69.5,-105.5),(69.5,-105),(70,-105),(68.5,-73),(62.5,-78.5),(62.5,-73.5),(62,-73.5),(62,-72.5),(61.5,-72.5),\
                (61.5,-71.5),(61,-71.5),(61,-70),(59,-70),(59,-68.5),(58.5,-68.5),(58.5,-67),(59,-67),(59,-66.5),(59,-66),(60,-66),(60,-64.5),(59.5,-64.5),\
                (59.5,-64),(59,-64),(59,-63.5),(58.5,-63.5),(58.5,-63),(58,-63),(58,-62.5),(57.5,-62.5),(57.5,-62),(56.5,-62),(56.5,-61.5),(56,-61.5),\
                (56,-61),(55.5,-61),(55.5,-60),(55,-60),(55,-58.5),(54,-58.5),(54,-59),(54,-60),(53.5,-60),(53.5,-60.5),(53.5,-61),(53,-61),(53,-61.5),\
                (53,-63),(52.5,-63),(52.5,-63.5),(52.5,-66),(52,-66),(52,-75),(52.5,-75),(52.5,-79.5),(54,-79.5),(54,-80),(55,-80),(55,-79.5),(55,-79),\
                (55.5,-79),(55.5,-78.5),(55.5,-78),(56,-78),(56,-77.5),(56,-77),(57.5,-77),(57.5,-77.5),(58,-77.5),(58,-78),(58.5,-78),(58.5,-78.5),\
                (59.5,-78.5),(59.5,-78),(60.5,-78),(60.5,-78.5),(62.5,-78.5),(68.5,-73))
    elif name == 'Arctic_plus_CLIM':
        coord = ((81.972431,-100.546875),(83.811024,-75.761719),(82.994132,-59.150391),(82.402423,-59.0625),(81.910828,-62.226563),(81.160996,-64.863281),\
                (79.171335,-71.982422),(77.542096,-75.234375),(75.140778,-74.53125),(66.93006,-57.65625),(61.100789,-56.074219),(48,-52),(48,-52.5),(47.5,-52.5),\
                (47.5,-53),(48.5,-53),(48.5,-54),(49.5,-54),(49.5,-55.5),(50,-55.5),(50,-56.5),(51,-56.5),(51,-56),(53,-56),(53,-56.5),(53.5,-56.5),(53.5,-57.5),\
                (54,-57.5),(54,-58),(54.5,-58),(54.5,-58.5),(54,-58.5),(54,-59),(54,-60),(53.5,-60),(53.5,-60.5),(53.5,-61),(53,-61),(53,-61.5),(53,-63),\
                (52.5,-63),(52.5,-63.5),(52.5,-66),(52,-66),(52,-75),(52.5,-75),(52.5,-79.5),(51.5,-79.5),(51.5,-81),(52,-81),(52,-81.5),(53.5,-81.5),\
                (53.5,-82.5),(54.5,-82.5),(54.5,-83),(55,-83),(55,-84.5),(55.5,-84.5),(55.5,-86.5),(56,-86.5),(56,-88),(56.5,-88),(56.5,-88.5),(57,-88.5),\
                (57,-91.5),(57.5,-91.5),(57.5,-93),(58,-93),(58,-93.5),(58.5,-93.5),(58.5,-94.5),(59,-94.5),(59,-95),(58.5,-95),(58.5,-95.5),(58.5,-96),\
                (58,-96),(58,-108),(58.5,-108),(58.5,-116),(59,-116),(59,-119),(59.5,-119),(59.5,-123),(60,-123),(60,-128.5),(60.5,-128.5),(60.5,-132.5),\
                (61,-132.5),(61,-134.5),(60.5,-134.5),(60.5,-135),(60,-135),(60,-135.5),(60,-136),(59.5,-136),(59.5,-137),(60,-137),(60,-138.5),(58.5,-138.5),\
                (58.5,-139),(59,-139),(59,-140.5),(59.5,-140.5),(59.5,-145.5),(60,-145.5),(60,-147.5),(59.5,-147.5),(55.103516,-154.555664),(53.540307,-163.168945),\
                (50.233152,-174.375),(51.781436,-189.755859),(57.727619,-184.394531),(64.960766,-170.419922),(67.272043,-166.904297),(69.687618,-170.771484),\
                (72.475276,-157.851563),(71.80141,-145.283203),(71.773941,-131.791992),(77.878814,-124.980469))
    elif name == 'Boreal_CLIM':   
        coord = ((61,-134.5),(61,-132.5),(60.5,-132.5),(60.5,-128.5),(60,-128.5),(60,-123),(59.5,-123),(59.5,-119),(59,-119),(59,-116),(58.5,-116),\
                (58.5,-108),(58,-108),(58,-96),(58.5,-96),(58.5,-95.5),(58.5,-95),(59,-95),(59,-94.5),(58.5,-94.5),(58.5,-93.5),(58,-93.5),(58,-93),\
                (57.5,-93),(57.5,-91.5),(57,-91.5),(57,-88.5),(56.5,-88.5),(56.5,-88),(56,-88),(56,-86.5),(55.5,-86.5),(55.5,-84.5),(55,-84.5),(55,-83),\
                (54.5,-83),(54.5,-82.5),(53.5,-82.5),(53.5,-81.5),(52,-81.5),(52,-81),(51.5,-81),(51.5,-79.5),(52.5,-79.5),(52.5,-75),(52,-75),(52,-66),\
                (52.5,-66),(52.5,-63.5),(52.5,-63),(53,-63),(53,-61.5),(53,-61),(53.5,-61),(53.5,-60.5),(53.5,-60),(54,-60),(54,-59),(54,-58.5),\
                (54.5,-58.5),(54.5,-58),(54,-58),(54,-57.5),(53.5,-57.5),(53.5,-56.5),(53,-56.5),(53,-56),(51,-56),(51,-56.5),(50,-56.5),(50,-55.5),\
                (49.5,-55.5),(49.5,-54),(48.5,-54),(48.5,-53),(46.5,-53),(46.5,-53.5),(46.5,-56.5),(47.5,-56.5),(47.5,-60.5),(48,-60.5),(48,-60),\
                (48.5,-60),(48.5,-59.5),(49,-59.5),(49,-59),(50,-59),(50,-58.5),(50.5,-58.5),(50.5,-58),(51,-58),(51,-59),(50.5,-59),(50.5,-59.5),\
                (50,-59.5),(50,-60),(50,-62),(49.5,-62),(49.5,-61.5),(49,-61.5),(49,-62),(49,-64.5),(49.5,-64.5),(49.5,-69),(49,-69),(49,-69.5),\
                (48.5,-69.5),(48.5,-70),(48,-70),(48,-70.5),(47.5,-70.5),(47.5,-71),(47,-71),(47,-71.5),(46.5,-71.5),(46.5,-72),(46.5,-74),(46,-74),\
                (46,-74.5),(46,-77.5),(45.5,-77.5),(45.5,-80.5),(46,-80.5),(46,-81.5),(46.5,-81.5),(46.5,-84.5),(47,-84.5),(47,-85),(47.5,-85),\
                (47.5,-85.5),(48,-85.5),(48,-86.5),(48.5,-86.5),(48.5,-87),(49,-87),(49,-89.5),(48.5,-89.5),(48.5,-90),(48.5,-90.5),(48,-90.5),(48,-91),\
                (48,-92),(47.5,-92),(47.5,-93),(48,-93),(48,-93.5),(48.5,-93.5),(48.5,-94.5),(49,-94.5),(49,-95),(49.5,-95),(49.5,-96),(50,-96),\
                (50,-97),(50.5,-97),(50.5,-98.5),(51,-98.5),(51,-99.5),(51.5,-99.5),(51.5,-101.5),(52,-101.5),(52,-102),(52.5,-102),(52.5,-103),\
                (53,-103),(53,-104.5),(53.5,-104.5),(53.5,-114.5),(53,-114.5),(53,-117),(53.5,-117),(53.5,-118),(54,-118),(54,-119.5),(54.5,-119.5),\
                (54.5,-120.5),(55,-120.5),(55,-121),(55.5,-121),(55.5,-122.5),(56,-122.5),(56,-125),(55.5,-125),(55.5,-125.5),(55,-125.5),(55,-128),\
                (55.5,-128),(55.5,-128.5),(56,-128.5),(56,-129.5),(56.5,-129.5),(56.5,-130.5),(57,-130.5),(57,-131.5),(57.5,-131.5),(57.5,-132),(58,-132),\
                (58,-133),(58.5,-133),(58.5,-133.5),(59,-133.5),(59,-134),(59.5,-134),(59.5,-135),(60.5,-135),(60.5,-134.5),(61,-134.5))
    elif name == 'Central_CLIM':   
        coord = ((53.5,-114.5),(53.5,-104.5),(53,-104.5),(53,-103),(52.5,-103),(52.5,-102),(52,-102),(52,-101.5),(51.5,-101.5),(51.5,-99.5),(51,-99.5),\
                (51,-98.5),(50.5,-98.5),(50.5,-97),(50,-97),(50,-96),(49.5,-96),(49.5,-95),(49,-95),(49,-94.5),(48.5,-94.5),(48.5,-93.5),(48,-93.5),\
                (48,-93),(47.5,-93),(47.5,-92.5),(46,-92.5),(46,-90.5),(45.5,-90.5),(45.5,-90),(45,-90),(45,-89.5),(44,-89.5),(44,-89),(41.5,-89),\
                (41.5,-88.5),(41,-88.5),(41,-87.5),(40.5,-87.5),(40.5,-86.5),(39,-86.5),(39,-87),(38.5,-87),(38.5,-87.5),(38,-87.5),(38,-88),(37.5,-88),\
                (37.5,-88.5),(37,-88.5),(37,-89.5),(37.5,-89.5),(37.5,-90.5),(38,-90.5),(38,-91.5),(38.5,-91.5),(38.5,-93.5),(38,-93.5),(38,-94),\
                (38,-94.5),(37.5,-94.5),(37.5,-95),(37,-95),(37,-95.5),(32.5,-95.5),(32.5,-95),(31.5,-95),(31.5,-95.5),(30.5,-95.5),(30.5,-96),\
                (28,-96),(28,-96.5),(28,-97),(27.5,-97),(27.5,-97.5),(27,-97.5),(27,-98.5),(28,-98.5),(28,-99),(29,-99),(29,-100.5),(29.5,-100.5),\
                (29.5,-101.5),(30,-101.5),(30,-102),(31,-102),(31,-102.5),(32.5,-102.5),(32.5,-103.5),(34,-103.5),(34,-104),(35.5,-104),(35.5,-103.5),\
                (37.5,-103.5),(37.5,-104),(38,-104),(38,-104.5),(41,-104.5),(41,-105),(42,-105),(42,-106),(42.5,-106),(42.5,-106.5),(43,-106.5),(43,-107),\
                (44,-107),(44,-107.5),(44.5,-107.5),(44.5,-108),(45,-108),(45,-108.5),(45.5,-108.5),(45.5,-109),(46,-109),(46,-109.5),(46.5,-109.5),\
                (46.5,-110),(47,-110),(47,-110.5),(47.5,-110.5),(47.5,-112),(48,-112),(48,-112.5),(49,-112.5),(49,-113),(49.5,-113),(49.5,-114),\
                (50.5,-114),(50.5,-114.5),(51.5,-114.5),(51.5,-115),(52,-115),(52,-115.5),(52.5,-115.5),(52.5,-116.5),(53,-116.5),(53,-115),(53,-114.5),\
                (53.5,-114.5))
    elif name == 'Central_Tundra_CLIM':   
        coord = ((70,-105),(70,-87.5),(69.5,-87.5),(69.5,-82.5),(67,-82.5),(67,-83),(67,-83.5),(66.5,-83.5),(66.5,-84),(66.5,-84.5),(65,-84.5),(65,-83),\
                (64,-83),(64,-83.5),(64,-84.5),(63.5,-84.5),(63.5,-86.5),(64,-86.5),(64,-87),(64.5,-87),(64.5,-88.5),(64,-88.5),(64,-89),(64,-90),
                (63.5,-90),(63.5,-90.5),(63.5,-91),(63,-91),(63,-91.5),(62.5,-91.5),(62.5,-92),(62.5,-92.5),(62,-92.5),(62,-93),(62,-93.5),(61.5,-93.5),\
                (61.5,-94),(61,-94),(61,-94.5),(60.5,-94.5),(60.5,-95.5),(61,-95.5),(61,-96),(62,-96),(62,-96.5),(63,-96.5),(63,-97),(63.5,-97),\
                (63.5,-97.5),(64,-97.5),(64,-101),(64.5,-101),(64.5,-105.5),(65,-105.5),(65,-115.5),(65.5,-115.5),(65.5,-116.5),(66,-116.5),(66,-117.5),\
                (66.5,-117.5),(66.5,-118.5),(67,-118.5),(67,-120),(67.5,-120),(67.5,-122),(68,-122),(68,-123),(68.5,-123),(68.5,-119),(68.5,-118.5),\
                (69,-118.5),(69,-115),(69,-114.5),(69.5,-114.5),(69.5,-105.5),(69.5,-105),(70,-105)) 
    elif name == 'Desert_CLIM':   
        coord = ((37,-112),(37,-111.5),(35.5,-111.5),(35.5,-111),(35,-111),(35,-110.5),(34.5,-110.5),(34.5,-109),(34,-109),(34,-108.5),(33.5,-108.5),\
                (33.5,-107.5),(33,-107.5),(33,-105.5),(34,-105.5),(34,-105),(34.5,-105),(34.5,-104.5),(35,-104.5),(35,-104),(34,-104),(34,-103.5),\
                (32.5,-103.5),(32.5,-102.5),(31,-102.5),(31,-102),(30,-102),(30,-101.5),(29.5,-101.5),(29.5,-100.5),(29,-100.5),(29,-99),(28,-99),\
                (28,-98.5),(27.5,-98.5),(27.5,-98),(27,-98),(27,-97.5),(26,-97.5),(26,-97),(25.5,-97),(25.5,-97.5),(25.5,-104),(25,-104),(25,-104.5),\
                (25,-108),(24.5,-108),(24.5,-108.5),(24,-108.5),(24,-112),(24.5,-112),(24.5,-112.5),(25,-112.5),(25,-113),(26,-113),(26,-113.5),\
                (26.5,-113.5),(26.5,-114),(27,-114),(27,-114.5),(27.5,-114.5),(27.5,-115),(31,-115),(31,-115.5),(31.5,-115.5),(31.5,-116),(32,-116),\
                (32,-116.5),(34.5,-116.5),(34.5,-117),(35.5,-117),(35.5,-117.5),(36,-117.5),(36,-118),(36.5,-118),(36.5,-112.5),(36.5,-112),(37,-112))
    elif name == 'East_CLIM':   
        coord = ((49.5,-69),(49.5,-64.5),(49,-64.5),(49,-64),(48.5,-64),(48.5,-64.5),(48,-64.5),(48,-65),(47,-65),(47,-60.5),(46.5,-60.5),(46.5,-60),\
                (45.5,-60),(45.5,-60.5),(45.5,-61),(45,-61),(45,-61.5),(45,-62),(44.5,-62),(44.5,-62.5),(44.5,-64),(44,-64),(44,-64.5),(43.5,-64.5),\
                (43.5,-65),(43.5,-65.5),(43,-65.5),(43,-66.5),(43.5,-66.5),(43.5,-67),(44.5,-67),(44.5,-67.5),(44,-67.5),(44,-68),(44,-69),(43.5,-69),\
                (43.5,-69.5),(43.5,-70.5),(42.5,-70.5),(42.5,-70),(41,-70),(41,-70.5),(41,-72),(40.5,-72),(40.5,-72.5),(40.5,-74),(39.5,-74),(39.5,-74.5),\
                (39,-74.5),(39,-75),(38,-75),(38,-75.5),(37,-75.5),(37,-76),(36,-76),(36,-75.5),(35,-75.5),(35,-76),(34.5,-76),(34.5,-76.5),(34.5,-77.5),\
                (34,-77.5),(34,-78),(33.5,-78),(33.5,-78.5),(34,-78.5),(34,-79),(34.5,-79),(34.5,-79.5),(35,-79.5),(35,-80),(34.5,-80),(34.5,-80.5),\
                (34,-80.5),(34,-81),(33.5,-81),(33.5,-81.5),(33,-81.5),(33,-82),(32.5,-82),(32.5,-84),(33.5,-84),(33.5,-84.5),(34,-84.5),(34,-85),\
                (35,-85),(35,-85.5),(35.5,-85.5),(35.5,-86),(36,-86),(36,-87),(36.5,-87),(36.5,-87.5),(37,-87.5),(37,-88.5),(37.5,-88.5),(37.5,-88),\
                (38,-88),(38,-87.5),(38.5,-87.5),(38.5,-87),(39,-87),(39,-86.5),(40.5,-86.5),(40.5,-83.5),(40.5,-83),(41,-83),(41,-82.5),(41,-82),\
                (41.5,-82),(41.5,-81),(41.5,-80.5),(42.5,-80.5),(42.5,-79.5),(42.5,-79),(43,-79),(43,-77),(43,-76.5),(44,-76.5),(44,-76),(44.5,-76),\
                (44.5,-75.5),(45,-75.5),(45,-74),(45,-73.5),(45.5,-73.5),(45.5,-73),(45.5,-72.5),(46.5,-72.5),(46.5,-72),(46.5,-71.5),(47,-71.5),(47,-71),\
                (47.5,-71),(47.5,-70.5),(48,-70.5),(48,-70),(48.5,-70),(48.5,-69.5),(49,-69.5),(49,-69),(49.5,-69))
    elif name == 'East_Taiga_CLIM':   
        coord = ((59,-71.5),(59,-68.5),(58.5,-68.5),(58.5,-67),(59,-67),(59,-66),(58,-66),(58,-65.5),(57.5,-65.5),(57.5,-65),(57,-65),(57,-64.5),\
                (56.5,-64.5),(56.5,-63.5),(57,-63.5),(57,-63),(57,-62.5),(57.5,-62.5),(57.5,-62),(56.5,-62),(56.5,-61.5),(56,-61.5),(56,-61),(55.5,-61),\
                (55.5,-60),(55,-60),(55,-58.5),(54,-58.5),(54,-59),(54,-60),(53.5,-60),(53.5,-60.5),(53.5,-61),(53,-61),(53,-61.5),(53,-63),(52.5,-63),\
                (52.5,-63.5),(52.5,-66),(52,-66),(52,-75),(52.5,-75),(52.5,-79.5),(54,-79.5),(54,-80),(55,-80),(55,-79.5),(55,-79),(55.5,-79),(55.5,-78.5),\
                (55.5,-78),(56,-78),(56,-77.5),(56,-77),(57.5,-77),(57.5,-76.5),(58,-76.5),(58,-74),(58,-73.5),(58.5,-73.5),(58.5,-72),(58.5,-71.5),(59,-71.5)) 
    elif name == 'East_Tundra_CLIM':   
        coord = ((68.5,-73),(68.5,-69.5),(68,-69.5),(68,-65.5),(67.5,-65.5),(67.5,-62.5),(65.5,-62.5),(65.5,-63),(65.5,-65.5),(64,-65.5),(64,-65),(63,-65),\
                (63,-65.5),(62.5,-65.5),(62.5,-66),(62.5,-66.5),(62,-66.5),(62,-69.5),(62.5,-69.5),(62.5,-71.5),(63,-71.5),(63,-72),(63.5,-72),(63.5,-73),\
                (64,-73),(64,-74.5),(64.5,-74.5),(64.5,-75),(66.5,-75),(66.5,-73.5),(66.5,-73),(68.5,-73),(62.5,-78.5),(62.5,-73.5),(62,-73.5),(62,-72.5),\
                (61.5,-72.5),(61.5,-71.5),(61,-71.5),(61,-70),(59,-70),(59,-70.5),(59,-71.5),(58.5,-71.5),(58.5,-72),(58.5,-73.5),(58,-73.5),(58,-74),\
                (58,-76.5),(57.5,-76.5),(57.5,-77.5),(58,-77.5),(58,-78),(58.5,-78),(58.5,-78.5),(59.5,-78.5),(59.5,-78),(60.5,-78),(60.5,-78.5),(62.5,-78.5),\
                (68.5,-73),(60,-66),(60,-64.5),(59.5,-64.5),(59.5,-64),(59,-64),(59,-63.5),(58.5,-63.5),(58.5,-63),(58,-63),(58,-62.5),(57,-62.5),(57,-63),\
                (57,-63.5),(56.5,-63.5),(56.5,-64.5),(57,-64.5),(57,-65),(57.5,-65),(57.5,-65.5),(58,-65.5),(58,-66),(60,-66),(68.5,-73)) 
    elif name == 'Pacific_South_West_CLIM':   
        coord = ((40.5,-123),(40.5,-122),(40,-122),(40,-121.5),(39.5,-121.5),(39.5,-121),(39,-121),(39,-120.5),(38.5,-120.5),(38.5,-120),(38,-120),\
                (38,-119.5),(37.5,-119.5),(37.5,-119),(37,-119),(37,-118.5),(36.5,-118.5),(36.5,-118),(36,-118),(36,-117.5),(35.5,-117.5),(35.5,-117),\
                (34.5,-117),(34.5,-116.5),(32,-116.5),(32,-116),(31.5,-116),(31.5,-115.5),(31,-115.5),(31,-115),(28.5,-115),(28.5,-115.5),(29,-115.5),\
                (29,-116),(29.5,-116),(29.5,-116.5),(30,-116.5),(30,-117),(31,-117),(31,-117.5),(31.5,-117.5),(31.5,-118),(32,-118),(32,-118.5),\
                (32.5,-118.5),(32.5,-119.5),(33,-119.5),(33,-120.5),(33.5,-120.5),(33.5,-121),(34,-121),(34,-121.5),(35,-121.5),(35,-122),(35.5,-122),\
                (35.5,-122.5),(36,-122.5),(36,-123),(37,-123),(37,-123.5),(37.5,-123.5),(37.5,-124),(38,-124),(38,-124.5),(39,-124.5),(39,-124),\
                (39.5,-124),(39.5,-123.5),(40,-123.5),(40,-123),(40.5,-123))
    elif name == 'North_Atlantic_CLIM':   
        coord = ((49.5,-69),(49.5,-64.5),(49,-64.5),(49,-64),(48.5,-64),(48.5,-64.5),(48,-64.5),(48,-65),(47,-65),(47,-60.5),(46.5,-60.5),(46.5,-60),\
                (45.5,-60),(45.5,-60.5),(45.5,-61),(45,-61),(45,-61.5),(45,-62),(44.5,-62),(44.5,-62.5),(44.5,-64),(44,-64),(44,-64.5),(43.5,-64.5),\
                (43.5,-65),(43.5,-65.5),(43,-65.5),(43,-66.5),(43.5,-66.5),(43.5,-67),(44.5,-67),(44.5,-67.5),(44,-67.5),(44,-68),(44,-69),(43.5,-69),\
                (43.5,-69.5),(43.5,-70.5),(42.5,-70.5),(42.5,-70),(41,-70),(41,-70.5),(41,-72),(40.5,-72),(40.5,-76),(41,-76),(41,-77.5),(41.5,-77.5),\
                (41.5,-78),(42,-78),(42,-78.5),(42.5,-78.5),(42.5,-79),(43,-79),(43,-77),(43,-76.5),(44,-76.5),(44,-76),(44.5,-76),(44.5,-75.5),\
                (45,-75.5),(45,-74),(45,-73.5),(45.5,-73.5),(45.5,-73),(45.5,-72.5),(46.5,-72.5),(46.5,-72),(46.5,-71.5),(47,-71.5),(47,-71),(47.5,-71),\
                (47.5,-70.5),(48,-70.5),(48,-70),(48.5,-70),(48.5,-69.5),(49,-69.5),(49,-69),(49.5,-69)) 
    elif name == 'North_Plains_CLIM':   
        coord = ((53.5,-114.5),(53.5,-104.5),(53,-104.5),(53,-103),(52.5,-103),(52.5,-102),(52,-102),(52,-101.5),(51.5,-101.5),(51.5,-99.5),(51,-99.5),\
                (51,-98.5),(50.5,-98.5),(50.5,-97),(50,-97),(50,-96),(49.5,-96),(49.5,-95),(49,-95),(49,-94.5),(48.5,-94.5),(48.5,-95),(48.5,-95.5),\
                (48,-95.5),(48,-96),(47,-96),(47,-96.5),(46,-96.5),(46,-97),(45.5,-97),(45.5,-97.5),(44.5,-97.5),(44.5,-98),(41.5,-98),(41.5,-105),\
                (42,-105),(42,-106),(42.5,-106),(42.5,-106.5),(43,-106.5),(43,-107),(44,-107),(44,-107.5),(44.5,-107.5),(44.5,-108),(45,-108),(45,-108.5),\
                (45.5,-108.5),(45.5,-109),(46,-109),(46,-109.5),(46.5,-109.5),(46.5,-110),(47,-110),(47,-110.5),(47.5,-110.5),(47.5,-112),(48,-112),\
                (48,-112.5),(49,-112.5),(49,-113),(49.5,-113),(49.5,-114),(50.5,-114),(50.5,-114.5),(51.5,-114.5),(51.5,-115),(52,-115),(52,-115.5),\
                (52.5,-115.5),(52.5,-116.5),(53,-116.5),(53,-115),(53,-114.5),(53.5,-114.5)) 
    elif name == 'Prairie_CLIM': 
        coord = ((48.5,-95.5),(48.5,-93.5),(48,-93.5),(48,-93),(47.5,-93),(47.5,-92.5),(46,-92.5),(46,-90.5),(45.5,-90.5),(45.5,-90),(45,-90),(45,-89.5),\
                (44,-89.5),(44,-89),(41.5,-89),(41.5,-88.5),(41,-88.5),(41,-87.5),(40.5,-87.5),(40.5,-86.5),(39,-86.5),(39,-87),(38.5,-87),(38.5,-87.5),\
                (38,-87.5),(38,-88),(37.5,-88),(37.5,-88.5),(37,-88.5),(37,-89.5),(37.5,-89.5),(37.5,-90.5),(38,-90.5),(38,-91.5),(38.5,-91.5),(38.5,-93.5),\
                (38,-93.5),(38,-94),(38,-94.5),(37.5,-94.5),(37.5,-95),(37,-95),(37,-96.5),(37.5,-96.5),(37.5,-97),(39.5,-97),(39.5,-97.5),(40.5,-97.5),\
                (40.5,-98),(44.5,-98),(44.5,-97.5),(45.5,-97.5),(45.5,-97),(46,-97),(46,-96.5),(47,-96.5),(47,-96),(48,-96),(48,-95.5),(48.5,-95.5))
    elif name == 'Great_Basin_CLIM':
        coord = ((54,-125),(54,-122.5),(53.5,-122.5),(53.5,-122),(52.5,-122),(52.5,-121.5),(52,-121.5),(52,-121),(51.5,-121),(51.5,-120),(51,-120),(51,-119),\
                (50.5,-119),(50.5,-118.5),(50,-118.5),(50,-118),(49.5,-118),(49.5,-117.5),(49,-117.5),(49,-117),(44.5,-117),(44.5,-116.5),(43.5,-116.5),\
                (43.5,-116),(43,-116),(43,-114.5),(42.5,-114.5),(42.5,-114),(42,-114),(42,-113),(41.5,-113),(41.5,-112.5),(39.5,-112.5),(39.5,-113),\
                (38.5,-113),(38.5,-113.5),(37.5,-113.5),(37.5,-114),(36.5,-114),(36.5,-118.5),(37,-118.5),(37,-119),(37.5,-119),(37.5,-119.5), \
                (38,-119.5),(38,-120),(38.5,-120),(38.5,-120.5),(39,-120.5),(39,-121),(39.5,-121),(39.5,-121.5),(40,-121.5),(40,-122),(45.5,-122),\
                (45.5,-121.5),(47,-121.5),(47,-121),(48,-121),(48,-120.5),(49.5,-120.5),(49.5,-121.5),(50,-121.5),(50,-122),(51,-122),(51,-122.5),\
                (51.5,-122.5),(51.5,-123),(52,-123),(52,-123.5),(52.5,-123.5),(52.5,-124),(53,-124),(53,-124.5),(53.5,-124.5),(53.5,-125),(54,-125)) 
    elif name == 'West_Boreal_CLIM':
        coord = ((61,-134.5),(61,-132.5),(60.5,-132.5),(60.5,-128.5),(60,-128.5),(60,-123),(59.5,-123),(59.5,-119),(59,-119),(59,-116),(58.5,-116),\
                (58.5,-108),(58,-108),(58,-96.5),(57.5,-96.5),(57.5,-97),(56.5,-97),(56.5,-97.5),(56,-97.5),(56,-98),(55.5,-98),(55.5,-98.5),(55,-98.5),\
                (55,-99),(54.5,-99),(54.5,-99.5),(54,-99.5),(54,-100),(53,-100),(53,-100.5),(52.5,-100.5),(52.5,-101),(52,-101),(52,-102),(52.5,-102),\
                (52.5,-103),(53,-103),(53,-104.5),(53.5,-104.5),(53.5,-114.5),(53,-114.5),(53,-117),(53.5,-117),(53.5,-118),(54,-118),(54,-119.5),\
                (54.5,-119.5),(54.5,-120.5),(55,-120.5),(55,-121),(55.5,-121),(55.5,-122.5),(56,-122.5),(56,-125),(55.5,-125),(55.5,-125.5),\
                (55,-125.5),(55,-128),(55.5,-128),(55.5,-128.5),(56,-128.5),(56,-129.5),(56.5,-129.5),(56.5,-130.5),(57,-130.5),(57,-131.5),\
                (57.5,-131.5),(57.5,-132),(58,-132),(58,-133),(58.5,-133),(58.5,-133.5),(59,-133.5),(59,-134),(59.5,-134),(59.5,-135),(60.5,-135),\
                (60.5,-134.5),(61,-134.5))     
    elif name == 'East_Boreal_CLIM':
        coord = ((59,-95),(59,-94.5),(58.5,-94.5),(58.5,-93.5),(58,-93.5),(58,-93),(57.5,-93),(57.5,-91.5),(57,-91.5),(57,-88.5),(56.5,-88.5), \
                (56.5,-88),(56,-88),(56,-86.5),(55.5,-86.5),(55.5,-84.5),(55,-84.5),(55,-83),(54.5,-83),(54.5,-82.5),(53.5,-82.5),(53.5,-81.5),\
                (52,-81.5),(52,-81),(51.5,-81),(51.5,-79.5),(52.5,-79.5),(52.5,-75),(52,-75),(52,-66),(52.5,-66),(52.5,-63.5),(52.5,-63),(53,-63),\
                (53,-61.5),(53,-61),(53.5,-61),(53.5,-60.5),(53.5,-60),(54,-60),(54,-59),(54,-58.5),(54.5,-58.5),(54.5,-58),(54,-58),(54,-57.5),\
                (53.5,-57.5),(53.5,-56.5),(53,-56.5),(53,-56),(51,-56),(51,-56.5),(50,-56.5),(50,-55.5),(49.5,-55.5),(49.5,-54),(48.5,-54),(48.5,-53),\
                (46.5,-53),(46.5,-53.5),(46.5,-56.5),(47.5,-56.5),(47.5,-60.5),(48,-60.5),(48,-60),(48.5,-60),(48.5,-59.5),(49,-59.5),(49,-59),\
                (50,-59),(50,-58.5),(50.5,-58.5),(50.5,-58),(51,-58),(51,-59),(50.5,-59),(50.5,-59.5),(50,-59.5),(50,-60),(50,-62),(49.5,-62),\
                (49.5,-61.5),(49,-61.5),(49,-62),(49,-64.5),(49.5,-64.5),(49.5,-69),(49,-69),(49,-69.5),(48.5,-69.5),(48.5,-70),(48,-70),(48,-70.5),\
                (47.5,-70.5),(47.5,-71),(47,-71),(47,-71.5),(46.5,-71.5),(46.5,-72),(46.5,-74),(46,-74),(46,-74.5),(46,-77.5),(45.5,-77.5),(45.5,-80.5),\
                (46,-80.5),(46,-81.5),(46.5,-81.5),(46.5,-84.5),(47,-84.5),(47,-85),(47.5,-85),(47.5,-85.5),(48,-85.5),(48,-86.5),(48.5,-86.5),\
                (48.5,-87),(49,-87),(49,-89.5),(48.5,-89.5),(48.5,-90),(48.5,-90.5),(48,-90.5),(48,-91),(48,-92),(47.5,-92),(47.5,-93),(48,-93),\
                (48,-93.5),(48.5,-93.5),(48.5,-94.5),(49,-94.5),(49,-95),(49.5,-95),(49.5,-96),(50,-96),(50,-97),(50.5,-97),(50.5,-98.5),(51,-98.5),\
                (51,-99.5),(51.5,-99.5),(51.5,-101.5),(52,-101.5),(52,-101),(52.5,-101),(52.5,-100.5),(53,-100.5),(53,-100),(54,-100),(54,-99.5),\
                (54.5,-99.5),(54.5,-99),(55,-99),(55,-98.5),(55.5,-98.5),(55.5,-98),(56,-98),(56,-97.5),(56.5,-97.5),(56.5,-97),(57.5,-97),\
                (57.5,-96.5),(58,-96.5),(58,-96),(58.5,-96),(58.5,-95.5),(58.5,-95),(59,-95))      
    elif name == 'West_Taiga_CLIM':
        coord = ((68,-127),(68,-122),(67.5,-122),(67.5,-120),(67,-120),(67,-118.5),(66.5,-118.5),(66.5,-117.5),(66,-117.5),(66,-116.5),(65.5,-116.5),\
                (65.5,-115.5),(65,-115.5),(65,-105.5),(64.5,-105.5),(64.5,-101),(64,-101),(64,-97.5),(63.5,-97.5),(63.5,-97),(63,-97),(63,-96.5),\
                (62,-96.5),(62,-96),(61,-96),(61,-95.5),(60.5,-95.5),(60.5,-95),(58.5,-95),(58.5,-95.5),(58.5,-96),(58,-96),(58,-108),(58.5,-108),\
                (58.5,-116),(59,-116),(59,-119),(59.5,-119),(59.5,-123),(60,-123),(60,-127),(61,-127),(61,-126.5),(61.5,-126.5),(61.5,-126),(63,-126),\
                (63,-126.5),(63.5,-126.5),(63.5,-127),(64,-127),(64,-127.5),(64.5,-127.5),(64.5,-128),(65,-128),(65,-130),(65.5,-130),(65.5,-132),\
                (67,-132),(67,-130.5),(67,-130),(67.5,-130),(67.5,-127.5),(67.5,-127),(68,-127)) 
    elif name == 'West_Tundra_CLIM':
        coord = ((66.5,-135),(66.5,-132),(65.5,-132),(65.5,-130),(65,-130),(65,-128),(64.5,-128),(64.5,-127.5),(64,-127.5),(64,-127),(63.5,-127),\
                (63.5,-126.5),(63,-126.5),(63,-126),(61.5,-126),(61.5,-126.5),(61,-126.5),(61,-127),(60,-127),(60,-128.5),(60.5,-128.5),(60.5,-132.5),\
                (61,-132.5),(61,-134.5),(60.5,-134.5),(60.5,-135),(60,-135),(60,-135.5),(60,-136),(59.5,-136),(59.5,-137),(60,-137),(60,-138.5),\
                (58.5,-138.5),(58.5,-139),(59,-139),(59,-140.5),(59.5,-140.5),(59.5,-145.5),(60,-145.5),(60,-147.5),(59.5,-147.5),(59.5,-150.5),\
                (60,-150.5),(60,-150),(60.5,-150),(60.5,-149.5),(60.5,-149),(61,-149),(61,-148.5),(61.5,-148.5),(61.5,-148),(62,-148),(62,-147),\
                (62,-146.5),(62.5,-146.5),(62.5,-146),(63,-146),(63,-145),(63,-144.5),(63.5,-144.5),(63.5,-144),(64,-144),(64,-143),(64,-142.5),\
                (64.5,-142.5),(64.5,-141.5),(64.5,-141),(65,-141),(65,-139),(65,-138.5),(65.5,-138.5),(65.5,-137),(65.5,-136.5),(66,-136.5),\
                (66,-135.5),(66,-135),(66.5,-135)) 
    elif name == 'Taigas_CLIM':
        coord = ((59,-71.5),(59,-68.5),(58.5,-68.5),(58.5,-67),(59,-67),(59,-66),(58,-66),(58,-65.5),(57.5,-65.5),(57.5,-65),(57,-65),(57,-64.5),\
                (56.5,-64.5),(56.5,-63.5),(57,-63.5),(57,-63),(57,-62.5),(57.5,-62.5),(57.5,-62),(56.5,-62),(56.5,-61.5),(56,-61.5),(56,-61),\
                (55.5,-61),(55.5,-60),(55,-60),(55,-58.5),(54,-58.5),(54,-59),(54,-60),(53.5,-60),(53.5,-60.5),(53.5,-61),(53,-61),(53,-61.5),\
                (53,-63),(52.5,-63),(52.5,-63.5),(52.5,-66),(52,-66),(52,-75),(52.5,-75),(52.5,-79.5),(54,-79.5),(54,-80),(55,-80),(55,-79.5),\
                (55,-79),(55.5,-79),(55.5,-78.5),(55.5,-78),(56,-78),(56,-77.5),(56,-77),(57.5,-77),(57.5,-76.5),(58,-76.5),(58,-74),(58,-73.5),\
                (58.5,-73.5),(58.5,-72),(58.5,-71.5),(59,-71.5),(68,-127),(68,-122),(67.5,-122),(67.5,-120),(67,-120),(67,-118.5),(66.5,-118.5),\
                (66.5,-117.5),(66,-117.5),(66,-116.5),(65.5,-116.5),(65.5,-115.5),(65,-115.5),(65,-105.5),(64.5,-105.5),(64.5,-101),(64,-101),\
                (64,-97.5),(63.5,-97.5),(63.5,-97),(63,-97),(63,-96.5),(62,-96.5),(62,-96),(61,-96),(61,-95.5),(60.5,-95.5),(60.5,-95),(58.5,-95),\
                (58.5,-95.5),(58.5,-96),(58,-96),(58,-108),(58.5,-108),(58.5,-116),(59,-116),(59,-119),(59.5,-119),(59.5,-123),(60,-123),(60,-127),\
                (61,-127),(61,-126.5),(61.5,-126.5),(61.5,-126),(63,-126),(63,-126.5),(63.5,-126.5),(63.5,-127),(64,-127),(64,-127.5),(64.5,-127.5),\
                (64.5,-128),(65,-128),(65,-130),(65.5,-130),(65.5,-132),(67,-132),(67,-130.5),(67,-130),(67.5,-130),(67.5,-127.5),(67.5,-127),(68,-127),(59,-71.5)) 
    elif name == 'SAR-NIF_Can':
        coord = ((48.5,-131),(57.5,-131),(57.5,-110),(48.5,-110))
    elif name == 'SAR-NIF_US':
        coord = ((41.5,-125),(49.2,-125),(49.2,-108),(41.5,-108))
    elif name == 'HRDPS_National':
        coord= (66.60,-153.20),(70.25,-129.80),(70.30,-99.80),(64.90,-69.70),\
                (55.4,-50.00),(47.80,-40.40),(27.00,-67.00),(34.40,-78.00),\
                (40.40,-100.00),(41.30,-120.00),(39.50,-133.70)
    elif name == 'GLS':
       coord = (52.3522, -70.65), (52.0572, -70.6501), (51.7715, -70.4262), (51.3398, -70.3559), (50.8728, -70.3127), (50.3722, -70.313), (49.974, -70.4253),\
               (49.6873, -70.6508), (49.4281, -70.8483), (49.09, -70.6751), (48.7533, -70.7168), (48.7533, -70.421), (48.8658, -70.0228), (48.6406, -69.7263),\
               (48.6405, -69.4267), (48.3053, -69.3685), (48.0791, -69.6791), (47.7429, -69.8748), (47.5168, -70.1725), (47.2924, -70.4708), (47.0629, -70.7634),\
               (47.1725, -70.5331), (47.4008, -70.2305), (47.6266, -69.8898), (47.8957, -69.6341), (48.078, -69.2689), (47.8543, -69.1835), (47.458, -69.3005),\
               (47.1801, -69.5543), (46.9765, -69.8643), (46.7297, -70.1382), (46.3931, -70.3127), (46.1663, -70.242), (45.8002, -70.3127), (45.5143, -70.5387),\
               (45.2674, -70.5959), (45.1556, -70.7782), (45.1915, -71.1006), (45.1553, -71.3699), (44.9387, -71.6702), (44.7051, -71.9541), (44.4535, -72.2253),\
               (44.0554, -72.339), (44.0302, -72.8243), (43.708, -72.7877), (43.3556, -72.7312), (43.2431, -73.1295), (43.3556, -73.5304), (43.3941, -73.7992),\
               (43.7929, -73.6873), (44.0301, -73.9507), (43.8289, -74.2507), (43.5805, -74.5312), (43.3566, -74.8266), (43.2436, -75.2257), (43.4322, -75.4878),\
               (43.0327, -75.3754), (42.8577, -75.7127), (42.7932, -75.9452), (42.4998, -76.1628), (42.2315, -76.4159), (42.2536, -76.7254), (42.2311, -77.0019),\
               (42.3436, -77.1893), (42.5682, -77.4781), (42.3433, -77.764), (42.1337, -77.6252), (41.7809, -77.7827), (42.0058, -78.0782), (42.2313, -78.3741),\
               (42.2313, -78.6704), (42.3433, -79.0697), (42.2318, -79.4707), (42.1186, -79.8691), (41.8935, -80.1683), (41.6686, -80.467), (41.4437, -80.7662),\
               (41.2191, -81.054), (41.0912, -81.2253), (40.9696, -81.4496), (40.9943, -81.7246), (40.983, -82.0129), (40.9097, -82.2388), (40.8805, -82.6549),\
               (40.6564, -82.7939), (40.6567, -83.093), (40.5441, -83.4932), (40.5756, -83.8139), (40.4315, -84.1927), (40.4316, -84.4921), (40.5447, -84.8924),\
               (40.7692, -85.1931), (41.2004, -85.2746), (41.3312, -85.6567), (41.3313, -85.957), (41.5577, -86.2573), (41.6355, -86.6257), (41.4597, -86.963),\
               (41.3314, -87.3481), (41.3314, -87.6496), (41.6458, -87.8618), (41.9487, -87.8619), (42.3499, -87.9745), (42.7509, -88.0867), (43.1307, -88.2203),\
               (43.469, -88.395), (43.693, -88.6944), (43.5806, -89.0944), (43.4686, -89.4947), (43.7131, -89.7746), (44.113, -89.6613), (44.3998, -89.4372),\
               (44.8169, -89.3428), (45.1541, -89.158), (45.2808, -89.2103), (45.6793, -89.0998), (45.9757, -89.0997), (46.1671, -89.2048), (46.1181, -89.5496),\
               (46.2795, -89.8996), (46.167, -90.298), (46.1671, -90.7987), (46.1674, -91.2993), (46.3814, -91.5754), (46.3921, -91.8839), (46.2796, -92.283),\
               (46.3941, -92.6823), (46.6172, -92.7559), (46.7294, -93.155), (47.0321, -93.1497), (47.3291, -93.1496), (47.5161, -92.8149), (47.559, -92.4754),\
               (47.8528, -92.3335), (47.7411, -91.9347), (47.5793, -91.5755), (47.6287, -91.24), (47.9224, -91.012), (48.1059, -90.6748), (48.3034, -90.3515), \
               (48.304, -90.3735), (48.6366, -90.5622), (48.8657, -90.495), (48.8498, -90.0016), (48.8667, -90.0764), (49.1266, -90.3373), (49.4232, -90.3373),\
               (49.7655, -90.1686), (49.9904, -90.097), (50.2152, -89.8), (50.3271, -89.4009), (50.5273, -89.0986), (50.7773, -88.8164), (50.7676, -88.319),\
               (50.5522, -88.0173), (50.4401, -87.6181), (50.2342, -87.3004), (49.9355, -87.3006), (49.8626, -87.0773), (49.4635, -87.1885), (49.315, -87.263),\
               (49.189, -87.0721), (49.4882, -86.8494), (49.6737, -86.5121), (49.6701, -86.1754), (49.6525, -85.8936), (49.6529, -85.5949), (49.348, -85.3888),\
               (49.0906, -85.3467), (48.9878, -84.9378), (48.754, -84.7761), (48.5401, -84.8247), (48.7532, -84.5161), (48.6408, -84.1168), (48.4335, -83.8128),\
               (48.3032, -83.6562), (48.0785, -83.8085), (48.0784, -83.5116), (47.8534, -83.4398), (47.634, -83.1378), (47.4604, -82.8003), (47.6269, -82.5601),\
               (47.5161, -82.1613), (47.5161, -81.8639), (47.4019, -81.4649), (47.5735, -81.3372), (47.8535, -81.0946), (48.1581, -80.8863), (48.3027, -80.509),\
               (48.3033, -80.0083), (48.4158, -79.6088), (48.3124, -79.2004), (48.6405, -79.0234), (48.5421, -78.6372), (48.7524, -78.3364), (48.4156, -78.15),\
               (48.1915, -78.3), (47.9659, -78.0141), (48.0784, -77.6147), (47.9654, -77.2152), (47.998, -76.9497), (48.1717, -76.6108), (48.1382, -76.163),\
               (48.3004, -75.9249), (48.1516, -75.7119), (48.4374, -75.4872), (48.7532, -75.2808), (49.0322, -75.037), (49.179, -74.7012), (48.9782, -74.3898),\
               (49.2038, -74.3958), (49.5405, -74.3684), (49.8315, -74.1369), (50.1022, -73.8761), (50.4257, -73.6855), (50.665, -73.3945), (50.7777, -72.996),\
               (50.8028, -72.6753), (51.0023, -72.4038), (51.2195, -72.1052), (51.4524, -71.8123), (51.8133, -71.6623), (52.0148, -71.3433), (52.2398, -71.0476), (52.3522, -70.65)
    elif name == 'YUK':
         coord = ((69.0923, -143.3813), (68.7584, -143.325), (68.8673, -143.0275), (68.9236, -142.5783), (68.8111, -142.2886), (68.6423, -141.9473), (68.5053, -141.6373),\
                 (68.5861, -141.3153), (68.6216, -140.8498), (68.6985, -140.4163), (68.6985, -140.0178), (68.6423, -139.6708), (68.5861, -139.2211), (68.5861, -138.8227), (68.5298, -138.4753), (68.3048, -138.1894),\
                 (68.1361, -137.8417), (68.2486, -137.4439), (68.2698, -137.0251), (68.0359, -136.7438), (67.7981, -136.4711), (67.5738, -136.1756), (67.2733, -136.0688), (67.0303, -136.1251), (66.7397, -136.0129),\
                 (66.4491, -136.0167), (66.1682, -136.2509), (66.0554, -136.6493), (66.0327, -137.0252), (65.9429, -137.3437), (65.8304, -137.7421), (65.7179, -138.1405), (65.6153, -138.5438), (65.4929, -138.8285),\
                 (65.4929, -139.226), (65.3808, -139.6237), (65.3698, -140.0063), (65.0994, -139.8004), (65.0155, -139.5564), (64.8386, -139.2188), (64.7615, -138.8939), (64.4805, -138.6563), (64.5964, -138.2625),\
                 (64.5253, -137.9252), (64.368, -137.5725), (64.3118, -137.227), (64.3118, -136.8296), (64.368, -136.3804), (64.3118, -135.9313), (64.4804, -135.5901), (64.593, -135.2962), (64.5368, -134.8471),\
                 (64.4805, -134.3979), (64.4805, -134.1041), (64.593, -133.7067), (64.4243, -133.4738), (64.3747, -133.0312), (64.2751, -132.7499), (64.3118, -132.3848), (64.1993, -131.9875), (64.2769, -131.6251),\
                 (64.368, -131.249), (64.2554, -130.9598), (64.0828, -130.7283), (63.9743, -130.4374), (63.7912, -130.2189), (63.6369, -130.0883), (63.412, -129.8511), (63.2994, -129.9642), (62.9761, -129.8813),\
                 (62.7931, -129.5543), (62.5117, -129.3256), (62.2253, -129.2063), (62.0623, -129.4494), (62.006, -129.7949), (61.9497, -130.1361), (61.6913, -130.0501), (61.6123, -130.3775), (61.3946, -130.556),\
                 (61.2749, -130.8529), (61.2748, -131.2503), (61.2186, -131.5958), (60.9937, -131.8809), (60.8593, -131.7374), (60.7123, -131.4134), (60.6545, -131.0682), (60.4875, -130.9531), (60.4468, -131.2874),\
                 (60.2624, -131.2685), (60.2624, -130.871), (60.0938, -130.8122), (59.9466, -130.6125), (59.5493, -130.6125), (59.3626, -130.3774), (59.1939, -130.7186), (59.0252, -131.0553), (58.969, -131.5044),\
                 (59.0774, -131.9062), (59.3064, -132.1919), (59.4751, -132.5331), (59.4026, -132.7501), (59.3626, -133.1121), (59.1939, -133.4581), (59.0815, -133.8561), (59.0662, -134.2687), (59.2385, -134.6062),\
                 (59.419, -134.9311), (59.6491, -135.1103), (59.7563, -135.5099), (59.8126, -135.8554), (59.7563, -136.1965), (60.0002, -136.4625), (60.3458, -136.5187), (60.7123, -136.4832), (60.825, -136.6143),\
                 (61.0521, -136.9075), (61.331, -136.6744), (61.4998, -136.9292), (61.6685, -137.275), (61.6123, -137.6209), (61.5562, -137.9665), (61.3939, -137.8688), (61.2171, -138.0938), (60.8813, -138.1645),\
                 (60.825, -138.5097), (60.5998, -138.6304), (60.4312, -138.9149), (60.5999, -139.26), (60.7124, -139.6572), (60.8772, -139.8937), (61.0499, -140.2349), (61.1734, -140.6249), (61.2748, -141.0288),\
                 (61.3873, -141.4258), (61.3311, -141.7708), (61.6122, -141.9507), (61.7569, -142.2562), (61.8934, -141.9913), (62.1184, -141.7021), (62.4506, -141.5226), (62.5116, -141.1782), (62.5683, -140.7286),\
                 (62.6247, -140.4177), (62.8197, -140.6249), (62.9972, -140.8499), (63.0183, -141.2268), (63.1308, -141.5171), (63.1271, -141.9187), (63.412, -142.1442), (63.412, -142.542), (63.477, -142.987),\
                 (63.6931, -143.1431), (63.8229, -143.4374), (63.862, -143.7959), (64.2288, -143.7187), (64.4805, -143.6765), (64.5782, -144.0562), (64.9194, -144.1123), (65.0993, -144.1052), (65.0959, -144.5062),\
                 (65.0992, -144.9003), (65.043, -145.3498), (65.153, -145.7386), (65.2118, -145.9724), (65.3805, -146.0938), (65.3685, -146.4751), (65.268, -146.885), (65.2572, -147.3751), (65.2118, -147.8354),\
                 (65.324, -147.9685), (65.6052, -147.8407), (65.8304, -147.8699), (65.7774, -148.1107), (65.8305, -148.5596), (65.7742, -149.0094), (65.8307, -149.4591), (65.9419, -149.7138), (66.2797, -149.757),\
                 (66.506, -149.7848), (66.8975, -149.6752), (67.0675, -149.3296), (67.2363, -149.3206), (67.4613, -149.0351), (67.7426, -148.8684), (67.7426, -149.1624), (67.799, -149.5036), (68.0799, -149.5131),\
                 (68.2487, -149.2756), (68.1924, -148.9301), (68.3049, -148.5328), (68.386, -148.1626), (68.4174, -147.7383), (68.6423, -147.4535), (68.5861, -147.0045), (68.6986, -146.6116), (68.6986, -146.2144),\
                 (68.6986, -145.8169), (68.8541, -145.4623), (68.9236, -145.0222), (68.9236, -144.6249), (69.0361, -144.3312), (69.0923, -143.8822), (69.0923, -143.3813))
    elif name == 'SKA':
         coord = ((57.3008, -127.6875), (57.1028, -127.5751), (56.8508, -127.5254), (56.761, -127.3499), (56.8437, -127.1323), (56.7384, -126.9316), (56.8508, -126.7334), (56.7384, -126.5352), (56.7384, -126.2337), \
                 (56.5492, -126.1126), (56.2888, -126.1625), (56.2888, -126.464), (56.1982, -126.6751), (56.0, -126.5627), (55.9144, -126.7876), (55.7262, -126.6649), (55.6306, -126.4501), (55.5012, -126.2688),\
                 (55.2763, -126.183), (55.0514, -126.097), (54.9502, -125.8876), (54.7515, -125.7752), (54.6015, -125.6139), (54.6015, -125.3124), (54.6016, -125.0108), (54.6015, -124.7093), (54.3771, -124.6862),\
                 (54.3766, -124.5377), (54.1784, -124.4255), (54.1519, -124.7094), (54.2644, -124.9076), (54.1519, -125.1062), (54.1519, -125.4077), (54.2644, -125.6061), (54.294, -125.887), (54.2707, -126.0001),\
                 (54.0722, -125.8879), (54.1022, -126.1123), (54.0395, -126.2609), (54.1519, -126.4595), (54.066, -126.6755), (54.0395, -126.9596), (53.927, -127.1581), (53.7081, -127.246), (53.702, -127.5452), \
                 (53.5896, -127.7435), (53.7021, -127.9417), (53.8267, -128.1351), (54.1274, -128.1371), (54.2219, -128.1374), (54.2645, -128.3965), (54.2645, -128.698), (54.1905, -128.9251), (53.992, -129.0376),\
                 (53.927, -129.283), (54.0463, -129.4787), (54.2418, -129.5998), (54.442, -129.7124), (54.7138, -129.6736), (54.8295, -129.4874), (54.9388, -129.2859), (55.0514, -129.088), (55.1636, -128.8897),\
                 (55.1639, -128.5882), (55.3522, -128.4748), (55.4375, -128.2498), (55.6141, -128.3844), (55.6151, -128.686), (55.8089, -128.8122), (56.008, -128.6998), (56.1759, -128.5479), (56.2871, -128.3493),\
                 (56.3868, -128.3624), (56.5135, -128.1787), (56.6261, -128.0602), (56.636, -128.3578), (56.7386, -128.5598), (56.909, -128.7), (57.107, -128.8124), (57.1883, -128.5832), (57.1657, -128.4745),\
                 (57.1883, -128.1869), (57.3006, -127.989), (57.3008, -127.6875))
    elif name == 'MCK':
         coord = ((68.8285, -134.325), (68.7704, -133.9061), (68.5463, -133.6026), (68.5301, -133.1053), (68.1101, -132.9815), (68.097, -132.6984), (68.11, -132.4121), (68.097, -132.1008), (67.8718, -131.8001),\
                 (67.7596, -131.3994), (67.7592, -130.8993), (67.6472, -130.4994), (67.5344, -130.1003), (67.3995, -129.7143), (67.1974, -129.4148), (67.1963, -129.116), (67.4222, -128.8287), (67.4221, -128.3286),\
                 (67.4052, -128.0218), (67.3652, -127.5756), (67.0848, -127.5575), (67.0848, -127.2585), (67.1138, -126.7871), (67.0953, -126.4504), (67.0333, -126.0008), (66.8603, -125.6627), (66.7475, -125.2637),\
                 (66.6351, -124.8644), (66.635, -124.3643), (66.6333, -124.0657), (66.5224, -123.6666), (66.6359, -123.7816), (66.9724, -123.7564), (66.86, -123.3571), (66.7476, -122.9586), (66.9248, -122.6244),\
                 (67.1091, -122.7359), (67.4223, -122.5282), (67.3098, -122.1297), (67.3099, -121.6296), (67.4655, -121.2748), (67.6474, -120.9462), (67.8723, -120.6609), (67.9848, -120.2631), (68.0971, -119.8656),\
                 (67.8722, -119.5706), (67.5583, -119.3628), (67.5349, -118.8859), (67.6464, -118.4877), (67.5349, -118.0894), (67.4378, -117.6754), (67.3099, -117.2922), (67.0856, -117.2317), (66.9726, -117.2714),\
                 (67.085, -116.8735), (66.7747, -116.6627), (66.6351, -116.2907), (66.618, -115.9855), (66.5799, -115.5381), (66.2999, -115.327), (66.0729, -115.4631), (65.9604, -115.0648), (65.6421, -115.0889),\
                 (65.4589, -114.9752), (65.1735, -114.7502), (64.9482, -114.6901), (64.8435, -114.2998), (65.1731, -114.1089), (65.0607, -113.7108), (64.9734, -113.2878), (65.173, -113.0168), (64.8399, -112.8373),\
                 (64.8353, -112.537), (64.6107, -112.2411), (64.4983, -111.8431), (64.4983, -111.343), (64.3859, -110.9448), (64.3859, -110.4447), (64.4983, -110.0464), (64.6108, -109.6483), (64.6128, -109.3503),\
                 (64.4283, -109.013), (64.4983, -108.6564), (64.3858, -108.2576), (64.6108, -107.9606), (64.5104, -107.5503), (64.3856, -107.164), (64.1412, -106.8769), (63.8241, -107.0692), (63.4563, -107.2129),\
                 (63.2565, -107.3365), (63.1487, -106.9367), (63.1382, -106.6503), (62.7394, -106.5384), (62.4753, -106.7953), (62.2496, -107.0924), (62.1363, -106.7098), (61.7992, -106.7501), (61.9111, -106.3516),\
                 (61.7663, -105.976), (61.3679, -105.8628), (61.0128, -105.8041), (60.7875, -106.1006), (60.7596, -106.4247), (60.675, -106.7952), (60.3568, -106.9877), (60.3371, -106.7215), (60.4456, -106.3243),\
                 (60.4494, -106.027), (60.4394, -105.5305), (60.519, -105.2994), (60.5337, -104.851), (60.4495, -104.6375), (60.3371, -104.2391), (60.2247, -103.8409), (60.2695, -103.5004), (59.9733, -103.5011),\
                 (59.7739, -103.1883), (59.4937, -102.938), (59.2086, -102.7127), (58.988, -103.0125), (58.6516, -103.1854), (58.5382, -103.5833), (58.3133, -103.8801), (58.087, -104.1752), (57.7907, -104.4007),\
                 (57.6809, -104.7369), (57.6385, -105.0655), (57.6386, -105.3609), (57.4145, -105.656), (57.2223, -105.9758), (57.0761, -106.3496), (57.0761, -106.8497), (57.1114, -107.3243), (56.8679, -107.4391),\
                 (56.7387, -107.8294), (56.8512, -108.2275), (56.8512, -108.5238), (56.7168, -108.9003), (56.5138, -109.2182), (56.6264, -109.6163), (56.4131, -109.9164), (56.2287, -110.0255), (55.9331, -109.8014),\
                 (55.6479, -110.0257), (55.4554, -110.1379), (55.1707, -110.3539), (55.1643, -110.6507), (55.2766, -111.048), (55.0937, -111.1502), (54.7991, -111.3752), (54.7143, -111.8003), (54.7143, -112.3004),\
                 (54.5264, -112.6131), (54.2645, -112.8703), (54.2843, -113.176), (54.152, -113.5624), (53.933, -113.8593), (53.8146, -114.2546), (53.6878, -114.6377), (53.4031, -114.8629), (53.1089, -115.0877),\
                 (52.9148, -115.4124), (53.0273, -115.8094), (52.9148, -116.2061), (52.8024, -116.6027), (52.914, -116.9999), (52.6318, -117.2251), (52.2356, -117.1126), (52.1275, -117.5131), (52.2494, -117.8999),\
                 (52.4294, -118.0124), (52.4649, -118.2699), (52.79, -118.4624), (53.0273, -118.7342), (53.1397, -119.1305), (53.2522, -119.5269), (53.4771, -119.8198), (53.702, -119.8876), (53.927, -120.1716),\
                 (54.0396, -120.5682), (54.3768, -120.7489), (54.4725, -121.1624), (54.3769, -121.5426), (54.3768, -122.0427), (54.2646, -122.4398), (54.1538, -122.8367), (54.5456, -122.9624), (54.6018, -123.1998),\
                 (54.7143, -123.5968), (54.9392, -123.8813), (54.9392, -124.3813), (55.0516, -124.7783), (55.0241, -125.0998), (55.1641, -125.4692), (55.389, -125.7532), (55.6604, -125.9999), (55.9444, -126.2249),\
                 (56.0638, -126.6148), (56.3962, -126.7777), (56.4011, -126.2794), (56.6261, -126.4456), (56.6262, -126.7384), (56.6372, -127.2341), (56.6262, -127.5313), (56.9878, -127.6874), (57.3843, -127.5747),\
                 (57.6381, -127.3018), (57.6302, -127.006), (57.8631, -126.9411), (57.7508, -127.2552), (58.0613, -127.4624), (58.3131, -127.7197), (58.3343, -128.0254), (58.2665, -128.2502), (58.0882, -128.5807), \
                 (58.2006, -128.9773), (58.3121, -129.3749), (58.3803, -129.5999), (58.4256, -129.8482), (58.5079, -130.2749), (58.4634, -130.6123), (58.8602, -130.7249), (59.1001, -130.4467), (59.4376, -130.4999),\
                 (59.7218, -130.7249), (59.8876, -130.8434), (60.1125, -131.1276), (60.3492, -131.3999), (60.5623, -131.104), (60.5798, -131.287), (60.7516, -131.6249), (60.8998, -131.9859), (61.1245, -131.8705),\
                 (61.3972, -131.6249), (61.4602, -131.3873), (61.4619, -131.0949), (61.4618, -130.8018), (61.6869, -130.5175), (61.9118, -130.4491), (62.0243, -130.0525), (62.1367, -129.8717), (62.2475, -129.4746),\
                 (62.433, -129.3749), (62.6992, -129.618), (63.0105, -129.8246), (63.1491, -129.9795), (63.4841, -129.9374), (63.599, -130.3228), (63.8366, -130.6107), (64.0076, -130.9499), (64.2737, -131.1929),\
                 (64.1613, -131.5895), (64.1615, -131.8827), (64.1613, -132.3828), (64.1614, -132.6756), (64.2737, -133.0721), (64.3862, -133.4686), (64.4986, -133.8653), (64.2738, -134.1583), (64.3862, -134.5549),\
                 (64.4987, -134.9516), (64.497, -135.4501), (64.2737, -135.745), (64.2738, -136.2451), (64.2738, -136.7452), (64.2737, -137.2452), (64.328, -137.6999), (64.4986, -138.0384), (64.4477, -138.4876), \
                 (64.5049, -138.825), (64.7236, -139.1155), (64.8361, -139.5121), (64.9487, -139.9088), (65.1735, -139.9771), (65.5106, -139.9661), (65.5446, -139.4999), (65.6119, -139.2717), (65.6231, -138.9829),\
                 (65.7347, -138.5858), (65.7997, -138.1496), (65.9597, -137.791), (65.9604, -137.4961), (66.0729, -137.0984), (66.1854, -136.7008), (66.2976, -136.3033), (66.5231, -136.0155), (66.8602, -136.0525),\
                 (67.1047, -136.2374), (67.4225, -136.0359), (67.5349, -135.6381), (67.6464, -135.2388), (68.0776, -135.1688), (68.5777, -135.1688), (68.8285, -134.8251), (68.8285, -134.325))
    elif name == 'GSL':
         coord = ((51.5451, -56.0813), (51.35, -56.1401), (51.0875, -56.4194), (50.8386, -56.588), (50.644, -56.5876), (50.3992, -56.869), (50.1392, -57.1409), (49.9615, -57.3757), (49.8014, -57.3478), \
                 (49.7443, -56.9908), (49.4639, -56.8585), (49.4076, -56.5001), (49.2409, -56.4752), (48.9584, -56.7247), (48.7895, -57.0828), (48.7247, -57.4314), (48.452, -57.573), (48.2833, -57.8184),\
                 (48.058, -58.0934), (47.8623, -57.769), (47.665, -58.101), (47.6637, -58.3894), (47.6082, -58.7663), (47.5705, -59.2449), (47.9084, -59.4543), (48.1141, -59.1187), (48.3374, -58.7612),\
                 (48.5106, -58.7017), (48.619, -58.7195), (48.9884, -58.5553), (49.1262, -58.2729), (49.2393, -58.2479), (49.5755, -58.0924), (49.8006, -57.8861), (50.139, -57.6576), (50.516, -57.4782),\
                 (50.7387, -57.3705), (50.8684, -57.0809), (51.1531, -56.8099), (51.4309, -56.5112), (51.5451, -56.0813), (53.176, -69.5813), (53.1197, -69.2311), (52.8693, -69.1877), (52.5956, -69.356),\
                 (52.7823, -69.0191), (52.677, -68.6249), (52.6497, -68.2315), (52.6135, -67.9688), (52.6704, -67.7136), (53.0063, -67.662), (52.8947, -67.368), (52.8063, -67.0501), (52.7661, -66.7684), \
                 (52.9527, -66.5437), (52.9313, -66.2626), (52.8008, -66.3189), (52.563, -66.3751), (52.2689, -66.3757), (52.2761, -66.1912), (52.1635, -65.8971), (52.0511, -65.608), (51.9413, -65.3063),\
                 (51.811, -65.1379), (51.8033, -64.744), (51.6574, -64.4832), (51.982, -64.4062), (52.1636, -64.1813), (52.4577, -64.1811), (52.7823, -64.0992), (52.8385, -63.7489), (52.9507, -63.4501),\
                 (52.8381, -63.1555), (52.8385, -62.7535), (52.9163, -62.4939), (52.7822, -62.1182), (52.6688, -61.7154), (52.5573, -61.3126), (52.3885, -60.96), (52.3326, -60.5432), (52.4619, -60.4127),\
                 (52.5534, -60.127), (52.726, -59.7763), (52.6696, -59.425), (52.5573, -59.1246), (52.501, -58.7732), (52.6695, -58.5346), (52.6341, -58.1627), (52.4946, -57.8811), (52.3322, -57.6427),\
                 (52.0793, -57.4309), (52.1635, -56.9997), (52.2753, -56.7091), (52.2177, -56.3563), (52.107, -55.9531), (51.8413, -56.0267), (51.7047, -56.4201), (51.4923, -56.7621), (51.3769, -57.0753),\
                 (51.4333, -57.4622), (51.3292, -57.8858), (51.2137, -58.2967), (51.0951, -58.6486), (50.8525, -58.9505), (50.6209, -59.2313), (50.6166, -59.402), (50.4207, -59.7628), (50.2117, -59.977),\
                 (50.1978, -60.3954), (50.1953, -60.8985), (50.1433, -61.3053), (50.0886, -61.7602), (50.1986, -62.2006), (50.2538, -62.6706), (50.2573, -63.045), (50.2138, -63.5025), (50.2843, -63.9546),\
                 (50.2819, -64.3988), (50.2522, -64.8371), (50.2626, -65.2542), (50.252, -65.6617), (50.1614, -66.0979), (50.2517, -66.4667), (49.9962, -66.7754), (49.7761, -67.1085), (49.4102, -67.256), \
                 (49.2958, -67.6737), (49.2292, -68.1195), (49.0727, -68.2856), (48.9461, -68.6267), (48.7339, -68.9759), (48.4727, -69.2473), (48.3397, -69.5479), (48.4401, -69.8623), (48.7331, -70.0885),\
                 (48.6212, -70.4901), (48.7889, -70.8019), (49.1, -70.8186), (49.3894, -71.0434), (49.7452, -70.8794), (49.9139, -70.5277), (50.1392, -70.5051), (50.5133, -70.4247), (50.9149, -70.4249),\
                 (51.2639, -70.3698), (51.5029, -70.5374), (51.7139, -70.728), (52.0346, -70.7062), (52.3273, -70.5913), (52.5089, -70.2562), (52.8384, -70.1743), (53.0635, -69.8752), (53.176, -69.5813),\
                 (51.5451, -56.0813), (49.2392, -65.25), (49.1825, -64.7915), (49.0218, -64.4063), (48.7897, -64.2828), (48.7329, -64.2814), (48.453, -64.219), (48.3403, -64.6356), (48.1381, -64.9696), \
                 (48.0019, -65.3748), (48.1149, -65.8011), (48.1045, -66.1495), (48.0012, -66.251), (47.9108, -65.8133), (47.7124, -65.5513), (47.8301, -65.1294), (47.7251, -64.7458), (47.7836, -64.5383),\
                 (47.5359, -64.8594), (47.2155, -65.0855), (47.0661, -65.1353), (46.9384, -64.8569), (46.6468, -64.6972), (46.3112, -64.5157), (46.189, -64.0858), (46.0457, -63.8162), (45.9454, -63.7946),\
                 (45.8914, -63.3992), (45.8028, -63.0466), (45.726, -62.6644), (45.7433, -62.3075), (45.9194, -61.9413), (45.6397, -61.6864), (45.5276, -61.4741), (45.4157, -61.7825), (45.37, -62.0457),\
                 (45.4932, -62.3244), (45.3439, -62.4371), (45.3589, -62.8282), (45.5276, -63.1848), (45.5275, -63.5885), (45.5275, -63.9931), (45.8095, -64.0142), (46.036, -64.3187), (46.1076, -64.6835),\
                 (46.226, -65.0807), (46.4709, -65.361), (46.4158, -65.7006), (46.3348, -66.0385), (46.1463, -66.3831), (46.3712, -66.6771), (46.4586, -67.106), (46.4844, -67.3777), (46.7078, -67.315),\
                 (46.8975, -66.9935), (47.1019, -66.7846), (47.2708, -66.8839), (47.4959, -66.9545), (47.479, -67.2748), (47.3835, -67.5608), (47.3556, -67.8933), (47.6581, -68.1186), (47.8333, -68.2393),\
                 (48.0583, -68.4232), (47.9855, -68.7935), (47.7233, -69.0244), (47.7008, -69.3002), (47.8165, -69.5242), (48.1107, -69.2876), (48.3206, -68.9615), (48.4515, -68.5708), (48.6597, -68.2267), \
                 (48.7883, -67.8187), (48.9014, -67.3949), (49.0247, -66.9932), (49.1266, -66.5739), (49.2388, -66.1602), (49.2952, -65.705), (49.2392, -65.25), (51.5451, -56.0813), (49.9692, -64.0125),\
                 (49.8574, -63.5911), (49.8011, -63.1258), (49.6883, -62.7059), (49.5142, -62.3326), (49.3602, -61.9317), (49.0766, -61.6667), (49.0705, -62.179), (49.1278, -62.634), (49.1963, -63.1052),\
                 (49.3523, -63.5056), (49.5952, -63.8339), (49.7454, -64.2375), (49.9127, -64.4863), (49.9692, -64.0125), (51.5451, -56.0813), (47.0458, -64.0125), (46.7478, -64.0479), (46.5396, -63.6951),\
                 (46.5382, -63.3598), (46.4029, -62.9978), (46.4793, -62.5846), (46.4821, -62.0814), (46.3169, -62.2698), (46.046, -62.4478), (45.9299, -62.8519), (46.1883, -63.1678), (46.1893, -63.5058),\
                 (46.3749, -63.8919), (46.5959, -64.1262), (46.7961, -64.3485), (47.0458, -64.0125), (51.5451, -56.0813), (46.9895, -60.4125), (46.6927, -60.3563), (46.3166, -60.5248), (46.3084, -60.1653),\
                 (46.0914, -59.903), (45.9412, -60.3011), (46.0906, -60.5507), (46.0646, -60.692), (45.9433, -61.0282), (45.865, -61.3102), (45.9685, -61.5358), (46.3107, -61.3038), (46.601, -61.0312),\
                 (46.8856, -60.7494), (46.9895, -60.4125), (51.5451, -56.0813))
    elif name == 'CHU':
         coord = ((59.5499, -102.15), (59.2502, -101.9254), (59.2492, -101.6995), (59.2125, -101.3624), (58.8757, -101.3256), (58.7625, -101.2345), (58.5586, -100.9129), (58.2011, -100.8544), \
                 (57.9591, -100.9128), (57.6371, -100.7195), (57.4128, -100.6439), (57.3005, -100.2422), (57.473, -99.8992), (57.6621, -99.5621), (57.8612, -99.2482), (57.8628, -98.9465), \
                 (57.8628, -98.4433), (57.9753, -98.0408), (57.9753, -97.7392), (57.8868, -97.313), (57.8213, -96.8637), (57.9751, -96.6303), (57.9746, -96.1271), (58.0866, -95.9224),\
                 (58.3042, -95.6138), (58.4245, -95.2076), (58.5364, -94.7965), (58.6517, -94.3772), (58.5567, -94.0585), (58.0535, -94.0516), (57.6421, -94.1636), (57.4143, -94.4708), \
                 (57.3003, -94.8148), (57.0765, -94.7162), (56.8515, -95.021), (56.7763, -95.3985), (56.6372, -95.6325), (56.569, -96.0755), (56.4017, -96.4241), (56.2892, -96.8284),\
                 (56.3211, -97.3109), (56.4015, -97.735), (56.4015, -98.2383), (56.3999, -98.5845), (56.1334, -98.7756), (55.8463, -99.0099), (55.7269, -99.4106), (55.5026, -99.7123),\
                 (55.5018, -100.0141), (55.5478, -100.3509), (55.3702, -100.6879), (55.1644, -100.9968), (54.9394, -101.0735), (54.8399, -101.4714), (54.827, -101.7773), (54.827, -102.2806),\
                 (55.1459, -102.4872), (55.2768, -102.8597), (55.4997, -103.1622), (55.3271, -103.5008), (55.1392, -103.3879), (55.0518, -103.8143), (54.9393, -104.2158), (55.0443, -104.6247),\
                 (54.7594, -104.8503), (54.3583, -104.7377), (54.0395, -104.9322), (54.0398, -105.2306), (54.0396, -105.5291), (53.747, -105.5255), (53.7026, -105.7893), (53.8146, -106.1903),\
                 (53.8146, -106.6936), (53.5849, -106.7627), (53.5108, -106.9882), (53.3643, -107.2856), (53.1393, -107.4376), (53.1006, -107.7748), (53.2859, -108.112), (53.5838, -108.1123),\
                 (53.6469, -108.5622), (53.6942, -108.5627), (53.6707, -108.8998), (53.7339, -109.3494), (53.9271, -109.67), (53.8147, -110.0708), (54.0395, -110.3591), (53.9971, -110.6997),\
                 (53.9271, -111.058), (53.9271, -111.3561), (54.152, -111.6543), (54.1595, -112.1549), (54.2646, -112.5581), (54.2926, -112.8369), (54.6932, -112.7248), (54.8264, -112.3449),\
                 (54.8264, -111.8417), (54.9386, -111.4409), (55.1729, -111.3685), (55.3888, -111.0799), (55.297, -110.6998), (55.3883, -110.2787), (55.5455, -110.3622), (55.8373, -110.1223),\
                 (56.0296, -110.0248), (56.3289, -110.2498), (56.616, -110.0193), (56.7383, -109.6215), (56.6258, -109.2203), (56.8507, -108.9208), (56.9632, -108.5194), (56.9632, -108.2201),\
                 (56.8507, -107.8187), (57.0956, -107.5497), (57.2993, -107.2307), (57.1882, -106.8294), (57.1882, -106.3261), (57.4129, -106.0273), (57.637, -105.7285), (57.7505, -105.3275),\
                 (57.7761, -104.8497), (57.8501, -104.622), (58.0877, -104.3271), (58.3476, -104.0621), (58.5377, -103.7281), (58.7113, -103.3869), (59.099, -103.2514), (59.2124, -102.8501),\
                 (59.4375, -102.5509), (59.5499, -102.15))       
    elif name == 'NEL':
         coord = ((57.1866, -93.0375), (56.9714, -92.7034), (56.6283, -92.8842), (56.5151, -93.2931), (56.3034, -93.6092), (56.1776, -94.0105), (55.9531, -94.3158), (55.9519, -94.8168), (55.9519, -95.3179),\
                 (55.8707, -95.7396), (55.8393, -96.221), (55.7258, -96.217), (55.6907, -95.7393), (55.3895, -95.9639), (55.2114, -96.3012), (55.1645, -96.7672), (55.051, -96.7828), (55.0197, -96.3019),\
                 (54.7147, -96.5222), (54.49, -96.8242), (54.2265, -97.0882), (54.0502, -97.4255), (53.9264, -97.0353), (53.9236, -96.7342), (53.8129, -96.3335), (53.6594, -95.9636), (53.4695, -95.6345), \
                 (53.1402, -95.5922), (52.9141, -95.5843), (52.6894, -95.2848), (52.5, -94.9505), (52.4645, -94.4845), (52.4297, -94.1615), (52.3132, -93.8253), (52.1272, -93.499), (52.2396, -93.0993),\
                 (52.1272, -92.6995), (52.0645, -92.2505), (51.7666, -92.2503), (51.4529, -92.4481), (51.3398, -92.5532), (51.3234, -92.248), (51.1603, -91.9129), (51.0025, -92.0087), (51.0025, -91.7108),\
                 (50.8899, -91.3113), (50.5535, -91.1253), (50.5525, -90.8282), (50.419, -90.4503), (50.1214, -90.4503), (49.8243, -90.4505), (49.4281, -90.5598), (49.241, -90.2254), (48.9782, -89.9764),\
                 (48.7538, -89.871), (48.7537, -90.1675), (48.7467, -90.4592), (48.4159, -90.2724), (48.1922, -90.0249), (48.079, -90.4236), (47.8543, -90.7202), (47.6374, -91.0198), (47.4512, -91.3505), \
                 (47.4286, -91.799), (47.7258, -92.0247), (47.5169, -92.3065), (47.5166, -92.6033), (47.4047, -93.0024), (47.6291, -93.2998), (47.4178, -93.6024), (47.4637, -94.0495), (47.6489, -94.3859),\
                 (47.6291, -94.6939), (47.5174, -95.0932), (47.312, -95.1765), (47.0147, -95.4005), (46.7289, -95.3888), (46.3921, -95.372), (46.1675, -95.4446), (46.2737, -95.8497), (45.9874, -95.8503),\
                 (45.6048, -95.9799), (45.4128, -96.3011), (45.5334, -96.6372), (45.6064, -97.0669), (45.788, -97.3128), (45.8297, -97.6506), (46.0158, -97.9871), (46.4152, -98.0997), (46.6169, -98.185), \
                 (46.8869, -98.4369), (47.1793, -98.6672), (47.5831, -98.7747), (47.7416, -99.1281), (47.7416, -99.6291), (47.5174, -99.9261), (47.4041, -100.3247), (47.6291, -100.6109), (47.7427, -101.0095), \
                 (47.7417, -101.3055), (47.9904, -101.5866), (48.1919, -101.8974), (48.4695, -102.1496), (48.6412, -102.489), (48.6915, -102.8254), (48.7335, -103.1627), (48.7325, -103.4998), (48.9157, -103.8371),\
                 (49.1006, -104.1694), (49.316, -104.4685), (49.455, -104.8493), (49.7658, -105.0499), (49.766, -105.3452), (49.9908, -105.6308), (50.2157, -105.9264), (50.2158, -106.222),\
                 (50.421, -106.5373), (50.5531, -106.916), (50.4611, -107.3259), (50.2782, -107.4378), (49.9915, -107.6799), (49.7659, -107.9749), (49.618, -108.3376), (49.4291, -108.6583), \
                 (49.7064, -108.8999), (49.9905, -108.6643), (50.103, -108.2662), (50.3275, -107.971), (50.5398, -107.8873), (50.4409, -108.2725), (50.5531, -108.6709), (50.6657, -109.0692),\
                 (50.8905, -109.3649), (50.8638, -109.6873), (50.6658, -109.9564), (50.3378, -109.9179), (50.2157, -110.3125), (49.878, -110.2396), (49.5409, -110.2177), (49.4284, -110.6156), (49.4284, -111.1166),\
                 (49.4284, -111.6177), (49.4284, -112.1187), (49.5409, -112.5167), (49.2035, -112.6895), (48.9787, -112.9838), (48.7721, -113.2876), (48.5286, -113.5631), (48.7481, -113.8409), (48.8202, -114.0749),\
                 (49.091, -114.3141), (49.3161, -114.6079), (49.6926, -114.7499), (50.1034, -114.8405), (50.4406, -115.0215), (50.4525, -115.3101), (50.7365, -115.5374), (51.0029, -115.7896), (51.211, -116.0999),\
                 (51.4527, -116.3678), (51.6765, -116.6624), (51.7902, -117.0588), (52.0389, -117.3373), (52.3525, -117.3086), (52.8021, -117.2977), (53.0271, -117.0128), (52.9146, -116.6153), (53.0271, -116.2177),\
                 (53.1395, -115.82), (53.1375, -115.5247), (53.2519, -115.1272), (53.6103, -114.9748), (53.8143, -114.6586), (53.9267, -114.2602), (54.1392, -113.9598), (54.2641, -113.5661), (54.488, -113.2703),\
                 (54.4109, -112.8377), (54.489, -112.4735), (54.376, -112.0753), (54.2641, -111.6769), (54.2641, -111.381), (54.0867, -111.0378), (54.1516, -110.6868), (54.1516, -110.3911), (54.1516, -110.0953),\
                 (53.9267, -109.8094), (53.9775, -109.4628), (53.8142, -109.1149), (53.7018, -108.7165), (53.9267, -108.4306), (53.7018, -108.3599), (53.5893, -107.9615), (53.3557, -107.8941), (53.1395, -107.5953),\
                 (52.803, -107.4633), (52.8281, -107.7759), (52.6896, -107.8425), (52.681, -107.5431), (52.6422, -107.212), (52.8361, -107.0993), (53.0282, -107.4196), (53.3149, -107.4372), (53.5884, -107.1906),\
                 (53.6082, -106.8753), (53.8668, -106.8746), (53.9267, -106.4236), (53.9265, -105.9226), (53.8265, -105.7463), (54.1516, -105.5645), (54.1836, -105.2997), (54.1609, -104.9627), (54.5308, -104.8498),\
                 (54.9284, -104.957), (55.1636, -104.6627), (55.0513, -104.2634), (55.1637, -103.8638), (55.312, -103.7246), (55.5011, -103.3903), (55.5423, -103.0506), (55.3886, -102.6915), (55.1923, -102.3753),\
                 (55.1636, -102.1163), (54.9394, -102.2579), (54.9387, -101.767), (55.0419, -101.3698), (55.0512, -101.0675), (55.2963, -100.7997), (55.6135, -100.6043), (55.7258, -100.2041), (55.7259, -99.9046),\
                 (55.7957, -99.6741), (55.9508, -99.3047), (56.1757, -99.017), (56.4004, -98.9425), (56.3077, -98.7726), (56.5132, -98.4677), (56.5132, -97.9667), (56.5131, -97.4656), (56.4006, -97.0645), (56.513, -96.6633),\
                 (56.5381, -96.187), (56.7379, -95.873), (56.8922, -95.5117), (56.9604, -95.2685), (57.0752, -94.8668), (57.1876, -94.4653), (57.0688, -94.2578), (57.0461, -93.9327), (57.1869, -93.5385), (57.1866, -93.0375))
    elif name == 'Quebec_HQ':
        coord = ((45,-79),(45,-62),(56,-62),(56,-79))
    elif name == 'SNX23_BCEF':
        coord = ((64.65,-148.45),(64.77,-148.45),(64.77,-148.2),(64.65,-148.2)) 
    elif name == 'SNX23_FLCF':
        coord = ((64.85,-147.85),(64.95,-147.85),(64.95,-147.6),(64.85,-147.6)) 
    elif name == 'SNX23_CPCR':
        coord = ((65.1,-147.7),(65.2,-147.7),(65.2,-147.4),(65.1,-147.4)) 
    elif name == 'SNX23_UKT':
        coord = ((68.4,-149.7),(68.7,-149.7),(68.7,-149.2),(68.4,-149.2)) 
    elif name == 'SNX23_ACP':
        coord = ((69.9,-149.),(70.2,-149.),(68.7,-148.5),(70.2,-148.5))
    elif name == 'FMO':
        coord = ((47.26,-71.25),(47.36,-71.25),(47.36,-71.0),(47.26,-71.0))   
    elif name == 'BJA':
        coord = ((53.60,-76.20),(53.75,-76.20),(53.75,-75.85),(53.60,-75.85))   
    elif name == 'KUJ':
        coord = ((55.10,-77.9),(55.30,-77.9),(55.30,-77.50),(55.10,-77.50)) 
    elif name == 'UMQ':
        coord = ((56.45,-76.70),(56.65,-76.70),(56.65,-76.30),(56.45,-76.30)) 
    elif name == 'WHU':
        coord = ((82.9,-75.0),(83.2,-75.0),(83.2,-73.0),(82.9,-73.0)) 
    elif name == 'RES':
        coord = ((74.5,-96.0),(75.0,-96.0),(75.0,-94.0),(74.5,-94.0)) 
    elif name == 'CAB':
        coord = ((69.03,-105.3),(69.2,-105.3),(69.2,-104.3),(69.03,-104.3)) 
    elif name == 'CAB':
        coord = ((69.03,-105.3),(69.2,-105.3),(69.2,-104.3),(69.03,-104.3)) 
    elif name == 'Appalachia-MidAtlantic_CLIM':
        coord = ((41.000000,-76.000000),(40.500000,-76.000000),(40.500000,-74.000000),(39.500000,-74.000000),(39.500000,-74.500000),(39.000000,-74.500000),(39.000000,-75.000000),(38.000000,-75.000000),(38.000000,-75.500000),(37.000000,-75.500000),(37.000000,-76.000000),(36.000000,-76.000000),(36.000000,-75.500000),(35.000000,-75.500000),(35.000000,-76.000000),(34.500000,-76.000000),(34.500000,-76.500000),(34.500000,-77.500000),(34.000000,-77.500000),(34.000000,-78.000000),(33.500000,-78.000000),(33.500000,-78.500000),(34.000000,-78.500000),(34.000000,-79.000000),(34.500000,-79.000000),(34.500000,-79.500000),(35.000000,-79.500000),(35.000000,-80.000000),(34.500000,-80.000000),(34.500000,-80.500000),(34.000000,-80.500000),(34.000000,-81.000000),(33.500000,-81.000000),(33.500000,-81.500000),(33.000000,-81.500000),(33.000000,-82.000000),(32.500000,-82.000000),(32.500000,-84.000000),(33.500000,-84.000000),(33.500000,-84.500000),(34.000000,-84.500000),(34.000000,-85.000000),(35.000000,-85.000000),(35.000000,-85.500000),(35.500000,-85.500000),(35.500000,-86.000000),(36.000000,-86.000000),(36.000000,-87.000000),(36.500000,-87.000000),(36.500000,-87.500000),(37.000000,-87.500000),(37.000000,-88.500000),(37.500000,-88.500000),(37.500000,-88.000000),(38.000000,-88.000000),(38.000000,-87.500000),(38.500000,-87.500000),(38.500000,-87.000000),(39.000000,-87.000000),(39.000000,-86.500000),(40.500000,-86.500000),(40.500000,-83.500000),(40.500000,-83.000000),(41.000000,-83.000000),(41.000000,-82.500000),(41.000000,-82.000000),(41.500000,-82.000000),(41.500000,-81.000000),(41.500000,-80.500000),(42.500000,-80.500000),(42.500000,-78.500000),(42.000000,-78.500000),(42.000000,-78.000000),(41.500000,-78.000000),(41.500000,-77.500000),(41.000000,-77.500000))
    elif name == 'Central-South_Plains_CLIM':
        coord = ((37.500000,-96.500000),(37.000000,-96.500000),(37.000000,-95.500000),(32.500000,-95.500000),(32.500000,-95.000000),(31.500000,-95.000000),(31.500000,-95.500000),(30.500000,-95.500000),(30.500000,-96.000000),(28.000000,-96.000000),(28.000000,-96.500000),(28.000000,-97.000000),(27.500000,-97.000000),(27.500000,-97.500000),(27.000000,-97.500000),(27.000000,-98.500000),(28.000000,-98.500000),(28.000000,-99.000000),(29.000000,-99.000000),(29.000000,-100.500000),(29.500000,-100.500000),(29.500000,-101.500000),(30.000000,-101.500000),(30.000000,-102.000000),(31.000000,-102.000000),(31.000000,-102.500000),(32.500000,-102.500000),(32.500000,-103.500000),(34.000000,-103.500000),(34.000000,-104.000000),(35.500000,-104.000000),(35.500000,-103.500000),(37.500000,-103.500000),(37.500000,-104.000000),(38.000000,-104.000000),(38.000000,-104.500000),(41.000000,-104.500000),(41.000000,-105.000000),(41.500000,-105.000000),(41.500000,-98.000000),(40.500000,-98.000000),(40.500000,-97.500000),(39.500000,-97.500000),(39.500000,-97.000000),(37.500000,-97.000000))
    elif name == 'North_Mt_West_CLIM':
        coord = ((56,-125),(56,-122.5),(55.5,-122.5),(55.5,-121),(55,-121),(55,-120.5),(54.5,-120.5),(54.5,-119.5),(54,-119.5),(54,-118),(53.5,-118),(53.5,-117),(53,-117),(53,-116.5),(52.5,-116.5),(52.5,-115.5),(52,-115.5),(52,-115),(51.5,-115),(51.5,-114.5),(50.5,-114.5),(50.5,-114),(49.5,-114),(49.5,-113),(49,-113),(49,-112.5),(48,-112.5),(48,-112),(47.5,-112),(47.5,-110.5),(47,-110.5),(47,-110),(46.5,-110),(46.5,-109.5),(46,-109.5),(46,-109),(45.5,-109),(45.5,-108.5),(45,-108.5),(45,-109),(45,-109.5),(42.5,-109.5),(42.5,-110.5),(42.5,-111),(42.5,-111.5),(43,-111.5),(43.5,-111.5),(44,-111.5),(44.5,-111.5),(44.5,-112),(44.5,-112.5),(44,-112.5),(44,-113),(43.5,-113),(43.5,-113.5),(43.5,-114),(43.5,-114.5),(43.5,-115),(43.5,-115.5),(43.5,-116),(44,-116),(44,-116.5),(44.5,-116.5),(44.5,-117),(44.5,-117.5),(44,-117.5),(44,-118),(44,-118.5),(43.5,-118.5),(43.5,-119),(43.5,-119.5),(43.5,-120),(43.5,-120.5),(43.5,-121),(43,-121),(43,-122),(45.5,-122),(45.5,-121.5),(47,-121.5),(47,-121),(48,-121),(48,-120.5),(49.5,-120.5),(49.5,-121.5),(50,-121.5),(50,-122),(51,-122),(51,-122.5),(51.5,-122.5),(51.5,-123),(52,-123),(52,-123.5),(52.5,-123.5),(52.5,-124),(53,-124),(53,-124.5),(53.5,-124.5),(53.5,-125),(54,-125),(54,-125.5),(54.5,-125.5),(54.5,-126.5),(55,-126.5),(55,-126),(55,-125.5),(55.5,-125.5),(55.5,-125),(56,-125))
    elif name == 'South_Mt_West_CLIM':
        coord = ((45,-108.5),(45,-108),(44.5,-108),(44.5,-107.5),(44,-107.5),(44,-107),(43,-107),(43,-106.5),(42.5,-106.5),(42.5,-106),(42,-106),(42,-105),(41,-105),(41,-104.5),(38,-104.5),(38,-104),(37.5,-104),(37.5,-103.5),(35.5,-103.5),(35.5,-104),(35,-104),(35,-104.5),(34.5,-104.5),(34.5,-105),(34,-105),(34,-105.5),(33,-105.5),(33,-108.5),(33.5,-108.5),(33.5,-109),(34,-109),(34,-109.5),(34.5,-109.5),(34.5,-110.5),(35,-110.5),(35,-111),(35.5,-111),(35.5,-111.5),(36,-111.5),(36,-112),(36.5,-112),(36.5,-118.5),(37,-118.5),(37,-119),(37.5,-119),(37.5,-119.5),(38,-119.5),(38,-120),(38.5,-120),(38.5,-120.5),(39,-120.5),(39,-121),(39.5,-121),(39.5,-121.5),(40,-121.5),(40,-122),(43,-122),(43,-121),(43.5,-121),(43.5,-120.5),(43.5,-120),(43.5,-119.5),(43.5,-119),(43.5,-118.5),(44,-118.5),(44,-118),(44,-117.5),(44.5,-117.5),(44.5,-117),(44.5,-116.5),(44,-116.5),(44,-116),(43.5,-116),(43.5,-115.5),(43.5,-115),(43.5,-114.5),(43.5,-114),(43.5,-113.5),(43.5,-113),(44,-113),(44,-112.5),(44.5,-112.5),(44.5,-112),(44.5,-111.5),(44,-111.5),(43.5,-111.5),(43,-111.5),(42.5,-111.5),(42.5,-111),(42.5,-110.5),(42.5,-109.5),(45,-109.5),(45,-109),(45,-108.5))
    elif name == 'South_CLIM':
        coord = ((38.5,-93.5),(38.5,-91.5),(38,-91.5),(38,-90.5),(37.5,-90.5),(37.5,-89.5),(37,-89.5),(37,-87.5),(36.5,-87.5),(36.5,-87),(36,-87),(36,-86),(35.5,-86),(35.5,-85.5),(35,-85.5),(35,-85),(34,-85),(34,-84.5),(33.5,-84.5),(33.5,-84),(32.5,-84),(32.5,-82),(33,-82),(33,-81.5),(33.5,-81.5),(33.5,-81),(34,-81),(34,-80.5),(34.5,-80.5),(34.5,-80),(35,-80),(35,-79.5),(34.5,-79.5),(34.5,-79),(34,-79),(34,-78.5),(33.5,-78.5),(33.5,-79),(33,-79),(33,-79.5),(32.5,-79.5),(32.5,-80),(32,-80),(32,-80.5),(32,-81),(31,-81),(31,-81.5),(29.5,-81.5),(29.5,-81),(29,-81),(29,-80.5),(27.5,-80.5),(27.5,-80),(25,-80),(25,-80.5),(24.5,-80.5),(24.5,-82),(25.5,-82),(25.5,-82.5),(26,-82.5),(26,-83),(27,-83),(27,-83.5),(29,-83.5),(29,-84),(29.5,-84),(29.5,-85),(29,-85),(29,-86),(29.5,-86),(29.5,-86.5),(30,-86.5),(30,-89),(28.5,-89),(28.5,-89.5),(28.5,-91.5),(29,-91.5),(29,-93.5),(29.5,-93.5),(29.5,-94),(29,-94),(29,-94.5),(29,-95),(28.5,-95),(28.5,-96),(30.5,-96),(30.5,-95.5),(31.5,-95.5),(31.5,-95),(32.5,-95),(32.5,-95.5),(37,-95.5),(37,-95),(37.5,-95),(37.5,-94.5),(38,-94.5),(38,-94),(38,-93.5),(38.5,-93.5))
    else:
        raise rmn.FSTDError("Domain "+name+" not found (check in util_score.py)")

    poly  = np.array(coord)
    lats  = poly[:,0]
    lons  = poly[:,1]
    return (lats, lons, poly) 

