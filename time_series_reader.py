#!/usr/bin/env python3

# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 15:28:50 2019

@author: moparthys
to compile fortran code, mk_fortran.f90:
try first this
f2py -c mk_fortran.f90 -m mankendall_fortran_repeat_exp2 --fcompiler=gfortran

if not try this
LDFLAGS=-shared f2py -c mk_fortran.f90 -m mankendall_fortran_repeat_exp2 --fcompiler=gfortran

dimensions of 4 regions of MSG-Disk

  Character(Len=4), Dimension(1:4) :: zone = (/ 'Euro', 'NAfr', 'SAfr', 'SAme' /)
  Integer,          Dimension(1:4) :: xmin = (/  1550 ,  1240 ,  2140 ,    40  /)
  Integer,          Dimension(1:4) :: xmax = (/  3250 ,  3450 ,  3350 ,   740  /)
  Integer,          Dimension(1:4) :: ymin = (/    50 ,   700 ,  1850 ,  1460  /)
  Integer,          Dimension(1:4) :: ymax = (/   700 ,  1850 ,  3040 ,  2970  /)
"""

from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import h5py
from netCDF4 import Dataset
import sys
from os import getpid
import re
import glob
import traceback
from timeit import default_timer as timer
from generic import binned_statistic_dd
import pathlib


class TimeSeriesExtractor():
    def __init__(self, start, end, product, chunks, output_path='./output_timeseries/'):
        self.dseries = pd.date_range(start, end, freq='D')
        self.product = product
        self.chunks = chunks
        self.output_path = output_path
        
        pathlib.Path(self.output_path+'/'+self.product).mkdir(parents=True, exist_ok=True)

    def get_lw_mask(self):
        """Get the MSG disk land mask (0: see, 1: land, 2: outside space, 3: river/lake)"""
        hlw = h5py.File('./input_ancillary/HDF5_LSASAF_USGS-IGBP_LWMASK_MSG-Disk_201610171300','r')
        self.lwmsk = hlw['LWMASK'][self.chunks.global_limits('slice')]
        hlw.close()
    
    def get_file_paths(self, key):
        series = self.dseries

        if self.product=='albedo':
    
            if key=='icare':
    
                # ICARE: 2005-01-01 -> 2016-09-18 (~2005-2016)
                root_dssf = '/cnrm/vegeo/SAT/DATA/AERUS_GEO/Albedo_v104'
                file_paths_root = [root_dssf+'/'+str('{:04}'.format(d.year))+'/' for d in series]
                file_pattern = 'SEV_AERUS-ALBEDO-D3_{}_V1-04.h5'
                file_paths_one = [file_pattern.format(d.strftime('%Y-%m-%d')) for d in series]     
                file_paths_final = [file_paths_root[f]+file_paths_one[f] for f in range(len(file_paths_one))]
        
            elif key=='mdal':
                # MDAL: 2004-01-19 -> 2015-12-31 (~2004-2015)
                root_dssf = '/cnrm/vegeo/SAT/DATA/MSG/Reprocessed-on-2017/MDAL'
                file_paths_root = [root_dssf+'/'+str('{:04}'.format(d.year))+'/'+str('{:02}'.format(d.month))+'/'+str('{:02}'.format(d.day))+'/' for d in series]
                file_pattern = 'HDF5_LSASAF_MSG_ALBEDO_MSG-Disk_{}0000'
                file_paths_one = [file_pattern.format(d.strftime('%Y%m%d')) for d in series]     
                file_paths_final = [file_paths_root[f]+file_paths_one[f] for f in range(len(file_paths_one))]
       
            elif key=='mdal_nrt':
                # MDAL_NRT: 2015-11-11 -> today (~2016-today)
                root_dssf = '/cnrm/vegeo/SAT/DATA/MSG/NRT-Operational/AL2'
                file_paths_root_one = root_dssf+'/'+'AL2-{}/'
                #file_pattern = 'HDF5_LSASAF_MSG_ALBEDO_MSG-Disk_{}0000.h5' # 2015 -> 2018
                file_pattern = 'HDF5_LSASAF_MSG_ALBEDO_MSG-Disk_{}0000' # 2019 -> 2020
                file_paths_one = [file_paths_root_one.format(d.strftime('%Y%m%d')) for d in series]     
                file_paths_two = [file_pattern.format(d.strftime('%Y%m%d')) for d in series]     
                file_paths_final = [file_paths_one[f]+file_paths_two[f] for f in range(len(file_paths_one))]
       
        elif self.product=='dssf':
            
            if key=='mdal_nrt':
            
                root_dir='/cnrm/vegeo/SAT/DATA/MSG/NRT-Operational/DSSF/'
                file_paths_root=[root_dir+'DSSF-'+str('{:04}'.format(d.year))+str('{:02}'.format(d.month))+str('{:02}'.format(d.day))+'/' for d in s]
                file_pattern='HDF5_LSASAF_MSG_DSSF_MSG-Disk_{}.h5'
                file_paths_one=[file_pattern.format(d.strftime('%Y%m%d%H%M')) for d in s]
                file_paths_final=[file_paths_root[f]+file_paths_one[f] for f in range(len(file_paths_one))]
    
        elif self.product=='lai':
    
            if key=='mdal':
    
                root_dir = '/cnrm/vegeo/SAT/DATA/MSG_LAI_DAILY_CDR/'
                #file_pattern = 'HDF5_LSASAF_MSG_LAI-D10_MSG-Disk_{}0000'
                file_pattern = 'HDF5_LSASAF_MSG_LAI_MSG-Disk_{}0000'
                file_paths_one = [file_pattern.format(d.strftime('%Y%m%d')) for d in series]
                file_paths_final = [root_dssf+file_paths_one[f] for f in range(len(file_paths_one))]
    
        return file_paths_final 

    def get_product_files(self, key='default'):
        self.product_files = {} 
    
        if self.product=='albedo':
            if key=='default':
                self.product_files['mdal'] = self.get_file_paths('mdal')
                self.product_files['mdal_nrt'] = self.get_file_paths('mdal_nrt')
    
        if self.product=='lai':
            if key=='default': 
                self.product_files['mdal'] = self.get_file_paths('mdal')
    
        if self.product=='dssf':
            if key=='default': 
                self.product_files['mdal_nrt'] = self.get_file_paths('mdal_nrt')
    
    def extract_valid_albedo(self, file_name,row0,row1,col0,col1):
        """Shortcut function to extract valid albedo data"""
        ## Extract data zone
        try:
            fh5 = h5py.File(file_name,'r')
        except Exception:
            traceback.print_exc()
            print ('File not found, moving to next file, assigning NaN to extacted pixel.')
            return None
    
        albedo = fh5['AL-BB-DH'][row0:row1,col0:col1] # array of int
        zage = fh5['Z_Age'][row0:row1,col0:col1]
        fh5.close()
        
        ## remove invalid data
        albedo = np.where(albedo==-1, np.nan, albedo/10000.)            
        albedo = np.where(zage>0, np.nan, albedo)
        
        return albedo
    
    def extract_albedo(self, chunk, date, dateindex):
        files = {}
        files['mdal_nrt'] = self.product_files['mdal_nrt'][dateindex]
        files['mdal'] = self.product_files['mdal'][dateindex]
        
        ## Reading MDAL albedo
        if date.year>=2016:
            file_mdal = files['mdal_nrt']
            if date.year<=2018:
                file_mdal += '.h5'
        else:   
            file_mdal = files['mdal']
        print(file_mdal)
        albedo = self.extract_valid_albedo(file_mdal, *chunk.global_lim)
        
        ## If error in reading, go to the next iteration
        if albedo is None:
            return None
    
        return albedo
    
    def write_ts_chunk(self, chunk, tseries):
        """Write time series of the data for each master iteration"""
        write_file = self.output_path+self.product+'/store_time_series_'+'_'.join([str(i) for i in chunk.global_lim])+'.nc'
    
        nc_iter = Dataset(write_file, 'w', format='NETCDF4')
        
        nc_iter.createDimension('x', tseries.shape[0])
        nc_iter.createDimension('y', tseries.shape[1])
        nc_iter.createDimension('z', tseries.shape[2])
        
        var1 = nc_iter.createVariable('time_series_chunk', np.float, ('x','y','z'), zlib=True)
        nc_iter.variables['time_series_chunk'][:] = tseries
            
        nc_iter.close()
    
        print(">>> Data chunk written to:", write_file)
    
    def run(self):
        self.get_lw_mask()
        self.get_product_files()
        
        for chunk in self.chunks.list:
            t0 = timer()
            print('***', 'Row/Col_SIZE=({},{})'.format(*chunk.dim), 'GLOBAL_LOCATION=[{}:{},{}:{}]'.format(*chunk.global_lim))
           
            ## Initialize an array series with nan
            tseries = np.full([len(self.dseries), *chunk.dim], np.nan)
            print(tseries.shape)
    
    
            ## Initialize an array to store histogram stats
            nbins = 100
            res_h = np.zeros((len(self.dseries), nbins))
            
            ## Create the chunk mask
            lwmsk_chunk = self.lwmsk[chunk.local_slice]
            ocean = np.where(lwmsk_chunk==0)
            land = np.where(lwmsk_chunk==1)
    
    
            for dateindex,date in enumerate(self.dseries):
    
                result = self.extract_albedo(chunk, date, dateindex)
                  
                if result is not None:
                    ## Fill series 
                    tseries[dateindex,:] = result
             
                    ## Fill histogram
                    h = np.histogram(result, bins=np.linspace(0.,1.,nbins+1))[0]
                    #res_h[dateindex] = np.log10(h) # w/o scaling
                    #res_h[dateindex] = np.log10(h/(np.count_nonzero(~np.isnan(net_albedo)))) # scale by total nb of not nan
                    res_h[dateindex] = np.log10(h/h.max()) # scale by max
    
                else:
                    continue
    
            ## Generate and save histogram
            fig = plt.figure()
            ax = fig.add_subplot(111)
            #res_h[res_h==0.0] = np.nan
            ax.imshow(res_h.T, aspect='auto', origin='lower', extent=(0,len(self.dseries),0,1))
            ax.grid()
            ax.set_xlabel('date')
            ax.set_ylabel('albedo')
            plt.savefig('res_hist.png')
    
    
            print(timer()-t0)
    
            self.write_ts_chunk(chunk, tseries)
   
            del tseries       
    

