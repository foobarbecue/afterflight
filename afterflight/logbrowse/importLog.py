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
THIS IS DEPRECATED. MOVING TO USING flyingrhino FOR IMPORT / EXPORT
Reads a .tlog using pymavlink into the afterflight database
todo: get_or_creates should be checking MAV id
'''
import sys, os, re
from datetime import datetime, timedelta
from django.conf import settings
from pymavlink import mavutil
import xml.etree.ElementTree as et
from logbrowse.models import Flight, MavMessage, MavDatum, FlightEvent
from django.contrib.auth.models import User
from django.db import transaction, reset_queries
from django.template.defaultfilters import slugify


def readInLog(filepath, **kwargs):
    print "Importing " + filepath
    if filepath.endswith('.log'):        
        return readInDfLog(filepath, **kwargs)
    elif filepath.endswith('.tlog'):
        return readInTLog(filepath, **kwargs)
    
def readInDfLog(filepath, startdate=None, **kwargs):
    #TODO expand this to deal with the new self-describing log format
    if not startdate:
        startdate=datetime.strptime(filepath.split('/')[-1][:10],'%Y-%m-%d')
    readInDfLogOldFormat(filepath=filepath, startdate=startdate, xml_format_file='dataflashlog.xml', **kwargs)

def readInDfLogOldFormat(filepath, startdate, xml_format_file='dataflashlog.xml', gpstime=True, **kwargs):
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
    if created:
        filename=re.match(r'.*/(.*)$',newFlight.logfile.name).groups()[0]
        newFlight.slug=slugify(filename)
        newFlight.save(**kwargs)
        logFile=open(filepath,'r')
        prev_timestamp={}
        
        if gpstime:
            #throw away data until we have a timestamp TODO deal with when gps logging is off...
            for log_line in logFile:
                if log_line.startswith('GPS'):
                    #set all of the cur_timestamps to the first GPS point TODO we are throwing this point away right now
                    log_line=log_line.split(',')
                    cur_timestamp=timedelta(milliseconds=int(log_line[1]))+startdate
                    for df_msg_type in time_dict:
                        time_dict[df_msg_type]['cur_timestamp']=cur_timestamp
                    break
                else:
                    continue
        else:
            for df_msg_type in time_dict:
                time_dict[df_msg_type]['cur_timestamp']=startdate

        
        for log_line in logFile:
            try:
                log_line=log_line.split(',')
                df_msg_type=log_line[0]
                if df_msg_type not in df_msg_types:
                    if df_msg_type.startswith('MOD'):
                        #Create a new event, using the latest GPS timestamp for the event timestamp
                        new_event=FlightEvent(timestamp=time_dict['GPS']['cur_timestamp'],eventType='MODE',comment=log_line[1],flight=newFlight,automatically_detected=True)
                        new_event.save()
                    elif df_msg_type.startswith('.'): #not sure why there are some lines that are just period.
                        pass
                    #else:
                        #print '%s not a known message type, skipping.'%df_msg_type
                    continue
                #update the time
                cur_time=time_dict[df_msg_type]['cur_timestamp']+time_dict[df_msg_type]['lag']
                time_dict[df_msg_type]['cur_timestamp']=cur_time

                if df_msg_type.startswith('GPS'):
                    #We need to multiply the lat and lon by 1e7 so they match the float-format GPS values from the .tlogs
                    log_line[3]=float(log_line[3])*1e7
                    log_line[4]=float(log_line[4])*1e7
                
                #Create a MavMessage for the row
                new_message=MavMessage(msgType='df_'+df_msg_type, timestamp=time_dict[log_line[0]]['cur_timestamp'], flight=newFlight)
                new_message.save()

                #Create MavDatums for each cell
                for x in range(len(log_line)-1):
                    #check for log lines that are longer than they are supposed to be acc to the schema
                    if x>(len(df_msg_types[df_msg_type])-1):
                        #print "Extra value in %s" % log_line
                        continue
                    new_datum=MavDatum(msgField=df_msg_types[df_msg_type][x],value=log_line[x+1],message=new_message)
                    #if df_msg_type.startswith('GPS'):
                        #pdb.set_trace()
                    new_datum.save()
            except:
                print "problem with %s" % log_line
                    
    return newFlight

def readInTLog(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    newFlight, created=Flight.objects.get_or_create(logfile__icontains=filepath.split('/')[-1])
    if created or (newFlight.mavmessage_set.count() == 0):
        filename=re.match(r'.*/(.*)$',newFlight.logfile.name).groups()[0]
        newFlight.slug=slugify(filename)
        mavMessages=[]
        mavData=[]
        while True:
            try:
                m=mlog.recv_msg()
                #Importing flight parameters into the database is not implemented yet,
                #so we skip those messages.
                if 'PARAM' in m._type:
                    continue
                timestamp=datetime.fromtimestamp(m._timestamp)
                newMessage=MavMessage(msgType=m._type, timestamp=timestamp, flight=newFlight)
                #mavMessages.append(newMessage)
                newMessage.save()
                m=m.to_dict()
                for key, item in m.items():
                    if key!='mavpackettype':
                        try:
                            value=float(item)
                        except ValueError:
                            #print "non-number value in %s" % m
                            continue
                        newDatum=MavDatum(msgField=key,value=value,message=newMessage)
                        mavData.append(newDatum)
            #end of logfile triggers an AttributeError. A more robust way of detecting this would be better. TODO
            except AttributeError:
                #Can't get bulk_create to work here because you end up with blank message_id s on the mavData TODO
                #res=MavMessage.objects.bulk_create(mavMessages)
                MavDatum.objects.bulk_create(mavData)
                return newFlight
    else:
        print "already imported %s" % newFlight.logfile.name
        return newFlight

def readInDirectory(log_dir_path, **kwargs):
    # kwargs is just for gpstime for now
    log_filenames=os.listdir(log_dir_path)
    for log_filename in log_filenames:
        readInLog(os.path.join(log_dir_path, log_filename), **kwargs)
        reset_queries()

