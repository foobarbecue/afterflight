'''
Reads a .tlog using pymavlink into the afterflight database
todo: get_or_creates should be checking MAV id
'''
import sys, os
from datetime import datetime
from django.conf import settings
# allow import from where mavlink.py is
sys.path.append(settings.PYMAVLINK_PATH)
import mavutil
from logbrowse.models import Flight, MavMessage, MavDatum
from django.contrib.auth.models import User
from django.db import transaction

def readInLog(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    newFlight, created=Flight.objects.get_or_create(logfile=filepath)
    while created:
        try:
            m=mlog.recv_msg()
            #Importing flight parameters into the database is not implemented yet,
            #so we skip those messages.
            if 'PARAM' in m._type:
                continue
            timestamp=datetime.fromtimestamp(m._timestamp)
            newMessage=MavMessage(msgType=m._type, timestamp=timestamp)
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

def readInDirectory(log_dir_path):
    log_filenames=os.listdir(log_dir_path)
    for log_filename in log_filenames:
        if '.tlog' in log_filename:
            print 'reading %s' % log_filename
            readInLog(os.path.join(log_dir_path, log_filename))
