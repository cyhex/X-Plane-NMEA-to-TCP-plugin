"""
PI_XTCPgps.py version 0.1 beta 1
copyright (c) 2009 Timor at cyhex; released under GPL 2.0 or later

XTCPgps is a plugin for X-Plane. Based on Ed Park's XMAPgps, It sends these NMEA sentences
over a TCP connection to mapping software: GPRMC, GPGGA, dummy GPGSA.

Demonstrated to work with XCsoar 6.1 running on a Android 2.2 and 
with XCsoar running on a Linux desktop.  

Alex Ferrer 2014: added LXWP0 NMEA sentence so Xsoar (for use with Xcsoar condor driver) 
                  can take advantage of vario, IAS and Wind info
"""

from XPLMProcessing import *
from XPLMDataAccess import *
from XPLMUtilities import *

#import math
from datetime import date
import time
import sys
import threading
import socket
import os

OutputFile = open(os.path.join(XPLMGetSystemPath(),'Resources','plugins','PythonScripts','XTCPgps.txt'), 'w')

def cksum(sentence):
    """calculates checksum for NMEA sentences"""
    i = 0
    cksum = 0
    senlen = len(sentence)
    while i < senlen:
        cksum = cksum^ord(sentence[i:i+1])
        i = i+1
    cksum = hex(cksum)[2:]
    return cksum


class SocketPlugin(object):
    #Edit here, yout host and port
    HOST = ('192.168.1.45',4353)
    connected = False
    
    def __init__(self):
        self.connect()
        
    
    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.s.connect(self.HOST)
            self.connected = True
        except Exception, e:
            OutputFile.write(" Can not connect to NMEA Client on %s:%s %s \n" % (self.HOST[0],self.HOST[1], e))
            OutputFile.flush()
            self.connected = False
        
        
        
               
            
                
    def write(self,data):
        if not self.connected:
            self.connect()
                
        try:
            self.s.send(data)
        except:
            self.connected = False
            self.s.close()
            
        
    
class PythonInterface:
        def XPluginStart(self):
            self.Name = "XTCPgps"
            self.Sig =  "Timor.Python.XTCPgps"
            self.Desc = "A plugin to send NMEA sentences to mapping software over TCP."
    
            # For possible debugging use:
            # Open a file to write to, located in the same directory as this plugin.
            self.OutputFile = OutputFile
            self.LineCount = 0
            self.ser = SocketPlugin()
            
            
            # test if self.ser is writable
            test_thread = threading.Thread(target=self.ser.write, args=("HELLO?",))
            before_count = threading.activeCount()
            test_thread.start()
            time.sleep(0.1)
            after_count = threading.activeCount()
            self.CannotWrite = after_count - before_count
    
            self.OutputFile.write(str(before_count) + '  ' + str(after_count) + '  ' + str(self.CannotWrite) + '\n')
            self.LineCount = self.LineCount + 1
    
            # Locate data references for all communicated variables.
    
            # time and date
            self.drZulu_time = XPLMFindDataRef("sim/time/zulu_time_sec")
            self.drDate      = XPLMFindDataRef("sim/time/local_date_days")
            # probably ok to set fixed date from system, not x-plane
            self.n_date = date.today().strftime("%d%m%y")
    
            # ground speed
            self.drVgnd_kts = XPLMFindDataRef("sim/flightmodel/position/groundspeed")
    
            # magnetic heading and variation
            self.drHding_mag = XPLMFindDataRef("sim/flightmodel/position/magpsi")
            self.drMag_var   = XPLMFindDataRef("sim/flightmodel/position/magnetic_variation")
    
            # latitude, longitude, and altitude
            self.drLat_deg = XPLMFindDataRef("sim/flightmodel/position/latitude")
            self.drLon_deg = XPLMFindDataRef("sim/flightmodel/position/longitude")
            self.drAlt_ind = XPLMFindDataRef("sim/flightmodel/position/elevation")

            # indicated airspeed  
            self.drIAS_ind = XPLMFindDataRef("sim/flightmodel/position/indicated_airspeed")

            # wind vector currently acting on the plane in KTS
            self.drWind_dir   = XPLMFindDataRef("sim/cockpit2/gauges/indicators/wind_heading_deg_mag")
            self.drWind_speed = XPLMFindDataRef("sim/cockpit2/gauges/indicators/wind_speed_kts")

            # barometric pressure
            self.drBaro_alt = XPLMFindDataRef("sim/flightmodel/misc/h_ind")
            self.drVario_fpm  = XPLMFindDataRef("sim/cockpit2/gauges/indicators/total_energy_fpm")
    
            # Register our callback for once per 1-second.  Positive intervals
            # are in seconds, negative are the negative of sim frames.  Zero
            # registers but does not schedule a callback for time.
            self.FlightLoopCB = self.FlightLoopCallback
            XPLMRegisterFlightLoopCallback(self, self.FlightLoopCB, 1.0, 0)
            return self.Name, self.Sig, self.Desc

        def XPluginStop(self):
            # Unregister the callback.
            XPLMUnregisterFlightLoopCallback(self, self.FlightLoopCB, 0)
            self.OutputFile.close()

        def XPluginEnable(self):
            return 1

        def XPluginDisable(self):
            pass

        def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
            pass

        def FlightLoopCallback(self, elapsedMe, elapsedSim, counter, refcon):
    
            if self.CannotWrite:
    
                return 10.0
    
    #        self.where = 1
    #        self.OutputFile.write('where?  ' + str(self.where) + '  ' + str(time.clock()) + '\n')
    #            self.LineCount = self.LineCount + 1
    
            # Get current values for communicated variables.
            self.Zulu_time = XPLMGetDataf(self.drZulu_time)  # sec since midnight
            self.Lat_deg = XPLMGetDatad(self.drLat_deg)
            self.Lon_deg = XPLMGetDatad(self.drLon_deg)
            self.Vgnd_kts = XPLMGetDataf(self.drVgnd_kts)*1.943  # m/sec -> kts
            self.Hding_mag = XPLMGetDataf(self.drHding_mag)
            self.Mag_var = XPLMGetDataf(self.drMag_var)
            self.Alt_ind = XPLMGetDatad(self.drAlt_ind)
            
            # get values for LXWP0
            self.IAS      = XPLMGetDataf(self.drIAS_ind)*1.852     # kias -> kph
            self.Baro_Alt = XPLMGetDataf(self.drBaro_alt)*0.3048   # feet-> meter  
            self.Vario    = XPLMGetDataf(self.drVario_fpm)*0.00508 # fpm -> m/s
            self.Wind_Dir = XPLMGetDataf(self.drWind_dir)
            self.Wind_Speed = XPLMGetDataf(self.drWind_speed)*1.852  # kias -> kph
    
            # put in nmea format (matches x-plane | equipment | nmea serial feed)
            # time ssss.ssss since midnight --> hhmmss
            hh  = int(self.Zulu_time/3600)
            mm = int(self.Zulu_time/60) - 60*hh
            ss = int(round(self.Zulu_time,0)) - 3600*hh - 60*mm
            n_time = str(hh).zfill(2)    \
                   + str(mm).zfill(2)    \
                   + str(ss).zfill(2) + '.00'
    
            # lat and lon +/- ddd.dddd --> dddmm.mmm,h
            h = 'N'
            if self.Lat_deg < 0:
                h = 'S'
            self.Lat_deg = abs(self.Lat_deg)
            ddd = int(self.Lat_deg)
            mmm = 60*(self.Lat_deg - ddd)
            n_lat = str(ddd).zfill(2)        \
                          + ('%.4f' % mmm).zfill(7) + ','    \
                          + h
    
            h = 'E'
            if self.Lon_deg < 0:
                h = 'W'
            self.Lon_deg = abs(self.Lon_deg)
            ddd = int(self.Lon_deg)
            mmm = 60*(self.Lon_deg - ddd)
            n_lon = str(ddd).zfill(3)        \
                          + ('%.4f' % mmm).zfill(7) + ','    \
                          + h
    
            # speed and heading may need some padding
            n_speed = ('%.1f' % self.Vgnd_kts).zfill(5)
            # heading mag --> true
            n_heading = '%.1f' % (self.Hding_mag - self.Mag_var)
    
            # date set once above 
    
            # magnetic variation +/- dd.dddd --> ddd.d,h
            h = 'W'
            if self.Mag_var < 0:
                h = 'E'
            self.Mag_var = abs(self.Mag_var)
            ddd = '%.1f' % self.Mag_var
            n_magvar = str(ddd)    + ','    \
                     + h
    
            # altitude meters
            n_alt = '%.1f' % self.Alt_ind
    
            # construct the nmea gprmc sentence
            gprmc = 'GPRMC'        + ','    \
                  + n_time        + ','    \
                  + 'A'        + ','    \
                  + n_lat        + ','    \
                  + n_lon        + ','    \
                  + n_speed        + ','    \
                  + n_heading    + ','    \
                  + self.n_date    + ','    \
                  + n_magvar
    
            # append check sum and inital $
            cks = cksum(gprmc)
            gprmc = '$' + gprmc + '*' + cks + '\r\n'
    
            # construct the nmea gpgga sentence
            gpgga = 'GPGGA'        + ','    \
                  + n_time        + ','    \
                  + n_lat        + ','    \
                  + n_lon        + ',1,04,0.0,'    \
                  + n_alt        + ',M,,,,'
    
            # append check sum and inital $
            cks = cksum(gpgga)
            gpgga = '$' + gpgga + '*' + cks + '\r\n'
    
            # pocketfms requires gpgsa sentence;
            # this one (constant) is what x-plane equipment setting sends.
            gpgsa = "$GPGSA,A,3,13,20,31,,,,,,,,,,02.2,02.2,*1e\r\n"
      
    # ----------------- 
            # alexferrer: add ias and pressure data so xcsoar can work the vario
            # construct the nmea lwxp0 sentence
            '''
                $LXWP0,Y,222.3,1665.5,1.71,,,,,,239,174,10.1 
                0 loger_stored (Y/N) 
                1 IAS (kph) 
                2 baroaltitude (m) 
                3 vario (m/s) 
                4-8 unknown 
                9 heading of plane 
                10 windcourse (deg) 
                11 windspeed (kph) 
            '''
            n_logger  = 'Y'       # logger stored
            n_ias     = ('%.1f' % self.IAS).zfill(5)        # kph
            n_baroalt = '%.1f' % self.Baro_Alt               # m
            n_vario   = '%.1f' % self.Vario                 # m/s
            n_dummy   = ',,,,,,'                            # unknown
                                                            # airplane heading
            n_winddir = '%.1f' %self.Wind_Dir               # wind direction deg
            n_windspd = ('%.1f' % self.Wind_Speed).zfill(5) # kph
                
            lxwp0 = 'LXWP0'    + ','    \
                  + n_logger   + ','    \
                  + n_ias      + ','    \
                  + n_baroalt  + ','    \
                  + n_vario    + ','    \
                  + n_dummy    + ','    \
                  + n_heading  + ','    \
                  + n_winddir  + ','    \
                  + n_windspd
    
            # append check sum and inital $
            cks = cksum(lxwp0)
            lxwp0 = '$' + lxwp0 + '*' + cks + '\r\n'  
    # -------------------    
    # -------------- test only ---------------------- 
            #print "NMEA> " ,  lxwp0 , n_windspd #gprmc, gpgga, gpgsa,
    
    #        serial write at 4800 baud can take .3 sec, so put in own thread;
            write_thread = threading.Thread(target=self.ser.write, args=(gprmc + gpgga + gpgsa + lxwp0,))
            write_thread.start()
    
    #        self.where = 5
    #        self.OutputFile.write('where?  ' + str(self.where) + '  ' + str(time.clock()) + '\n')
    #            self.LineCount = self.LineCount + 1
    
            # Return s.s to indicate that we want to be called again in s.s seconds.
            return 1.0
