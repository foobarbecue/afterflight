   #Copyright 2013 Aaron Curtis

   #Licensed under the Apache License, Version 2.0 (the "License");
   #you may not use this file except in compliance with the License.
   #You may obtain a copy of the License at

       #http://www.apache.org/licenses/LICENSE-2.0

   #Unless required by applicable law or agreed to in writing, software
   #distributed under the License is distributed on an "AS IS" BASIS,
   #WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   #See the License for the specific language governing permissions and
   #limitations under the License.

'''
Reads a .tlog using pymavlink into the afterflight database
todo: get_or_creates should be checking MAV id
'''
import sys, os, re
from datetime import datetime
from django.conf import settings
# allow import from where mavlink.py is
sys.path.append(settings.PYMAVLINK_PATH)
import mavutil
import dflogs
from logbrowse.models import Flight, MavMessage, MavDatum
from django.contrib.auth.models import User
from django.db import transaction
from django.template.defaultfilters import slugify


def readInLog(filepath):
    if filepath.endswith('.log'):
        return readInDfLog(filepath)
    elif filepath.endswith('.tlog'):
        return readInTLog(filepath)
    
def readInDfLog(filepath,dataType='all',startTime=startTime, useGpsTime=True, frame='octa'):
    df_GPS_fields=['time','sats','lat','lon','sensor_alt','gps_alt','ground_speed','ground_course']
    df_RAW_fields=['gyro_x','gyro_y','gyro_z','accel_x','accel_y','accel_z']
    newFlight, created=Flight.objects.get_or_create(logfile=filepath)
    logFile=open(logFilePath,'r')
    #should maybe rewrite this using a class for each row type?
    for logLine in logFile:
        logLine=logLine.split(',')
        if logLine[0]=='GPS':    
            timestamp=datetime.timedelta(milliseconds=int(logLine[1]))+startTime
            newMessage=MavMessage(msgType='df_GPS', timestamp=timestamp, flight=newFlight)
            for x in range(len(df_GPS_fields)):
                newDatum=MavDatum(msgField='df_%s' % df_GPS_fields[x],value=logLine[x+1],message=newMessage)
            
        elif logLine[0]=='MOT':
            if timestamp: #We are using the timestamp from the GPS packet, because both happen at 10hz
                newMessage=MavMessage(msgType='df_MOT', timestamp=timestamp, flight=newFlight)
                for x in range(1,9): #hardcoded for octocopter, TODO generalize for n motors
                    newDatum=MavDatum(msgField='motor %s' % x,value=logLine[x],message=newMessage)
                    newDatum.save()
                timestamp=None
            else continue #we haven't had a gps timestamp yet
            
        elif logLine[0]=='RAW':
            #Unlike the timestamped GPS messages, which happen at 10hz, RAW messages come in at 50hz
            if timestamp50:
                timestamp50=timestamp50+timedelta(milliseconds=20)
            else:
                timestamp50=timestamp #set it to the GPS timestamp. This is a few milliseconds wrong! TODO
            newMessage=MavMessage(msgType='df_RAW', timestamp=timestamp50, flight=newFlight)
            for x in range(len(df_RAW_fields)):
                newDatum=MavDatum(msgField='%s' % df_RAW_fields[x],value=logLine[x],message=newMessage)
    
    return newFlight

def readInTLog(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    newFlight, created=Flight.objects.get_or_create(logfile=filepath)
    if created:
        filename=re.match(r'.*/(.*)$',newFlight.logfile.name).groups()[0]
        newFlight.slug=slugify(filename)
        print "slug is %s" % newFlight.slug
        newFlight.save()
        while True:
            try:
                m=mlog.recv_msg()
                #Importing flight parameters into the database is not implemented yet,
                #so we skip those messages.
                if 'PARAM' in m._type:
                    continue
                timestamp=datetime.fromtimestamp(m._timestamp)
                newMessage=MavMessage(msgType=m._type, timestamp=timestamp, flight=newFlight)
                newMessage.save()
                m=m.to_dict()
                for key, item in m.items():
                    if key!='mavpackettype':
                        try:
                            value=float(item)
                        except ValueError:
                            print "non-number value in %s" % m
                            continue
                        newDatum=MavDatum(msgField=key,value=value,message=newMessage)
                        newDatum.save()
            except AttributeError:
                newFlight.save()
                return newFlight
    else:
        print "already imported %s" % newFlight.logfile.name
        return newFlight

def readInDirectory(log_dir_path):
    log_filenames=os.listdir(log_dir_path)
    for log_filename in log_filenames:
        if log_filename.endswith('.tlog'):
            print 'reading %s' % log_filename
            readInLog(os.path.join(log_dir_path, log_filename))
