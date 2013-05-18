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
from datetime import datetime, timedelta
from django.conf import settings
# allow import from where mavlink.py is
sys.path.append(settings.PYMAVLINK_PATH)
import mavutil
import xml.etree.ElementTree as et
from logbrowse.models import Flight, MavMessage, MavDatum
from django.contrib.auth.models import User
from django.db import transaction
from django.template.defaultfilters import slugify

@transaction.commit_on_success
def readInLog(filepath):
    if filepath.endswith('.log'):
        return readInDfLog(filepath)
    elif filepath.endswith('.tlog'):
        return readInTLog(filepath)
    
def readInDfLog(filepath, startdate, xml_format_file='dataflashlog.xml'):
    
    #Read in the dataflash log format and put it in a dictionary df_msg_types
    with open(xml_format_file,'r') as df_log_format_file:    
        df_log_xml=et.parse(df_log_format_file).getroot()
        APM=df_log_xml.find('APM')
        AC2=df_log_xml.find('AC2')
    df_msg_types={}
    for field_type in (AC2.getchildren()+APM.getchildren()):
        df_msg_types[field_type.tag]=[dtype.text for dtype in field_type.getchildren()]
    
    #create a dictionary to keep track of last timestamp for each message field, and the lags
    #format {'PM':{'lag':datetime.timedelta, 'curtime':datetime.datetime}}
    time_dict={}
    #setup lags
    for df_msg_type in df_msg_types.keys():
        time_dict[df_msg_type]={'lag':timedelta(milliseconds=100),'cur_timestamp':None}
        #Unlike the timestamped GPS messages, which happen at 10hz, RAW messages come in at 50hz
    time_dict['RAW']['lag']=timedelta(milliseconds=20)
    
    newFlight, created=Flight.objects.get_or_create(logfile=filepath)
    filename=re.match(r'.*/(.*)$',newFlight.logfile.name).groups()[0]
    newFlight.slug=slugify(filename)
    newFlight.save()
    logFile=open(filepath,'r')
    prev_timestamp={}
    
    #throw away data until we have a timestamp
    for log_line in logFile:
        if log_line.startswith('GPS'):
            break
        else:
            continue
    #set all of the cur_timestamps to the first GPS point TODO we are throwing this point away right now
    log_line=log_line.split(',')
    cur_timestamp=timedelta(milliseconds=int(log_line[1]))+startdate
    for df_msg_type in time_dict:
        time_dict[df_msg_type]['cur_timestamp']=cur_timestamp
    
    for log_line in logFile:
        log_line=log_line.split(',')
        df_msg_type=log_line[0]
        if df_msg_type not in df_msg_types:
            print '%s not a known message type, skipping.'%df_msg_type
            continue
        #update the time
        cur_time=time_dict[df_msg_type]['cur_timestamp']+time_dict[df_msg_type]['lag']
        time_dict[df_msg_type]['cur_timestamp']=cur_time
        
        #Create a MavMessage for the row
        new_message=MavMessage(msgType=df_msg_type, timestamp=time_dict[log_line[0]]['cur_timestamp'], flight=newFlight)
        new_message.save()

        #Create MavDatums for each cell
        for x in range(len(log_line)-1):
            if df_msg_type=='GPS':
                #We need to multiply the lat and lon by 1e7 so they match the float-format GPS values from the .tlogs
                log_line[2]=float(log_line[2])*1e7
                log_line[3]=float(log_line[3])*1e7
            #check for log lines that are longer than they are supposed to be acc to the schema
            if x>(len(df_msg_types[df_msg_type])-1):
                #print "Extra value in %s" % log_line
                continue
            new_datum=MavDatum(msgField=df_msg_types[df_msg_type][x],value=log_line[x+1],message=new_message)
            new_datum.save()
        
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
