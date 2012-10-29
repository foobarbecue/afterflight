'''
Reads a .tlog using pymavlink into the afterflight database
todo: get_or_creates should be checking MAV id
'''
import sys
from datetime import datetime
from django.conf import settings
# allow import from where mavlink.py is
sys.path.append(settings.PYMAVLINK_PATH)
import mavutil
from logbrowse.models import Flight, MavMessage, MavDatum
from django.contrib.auth.models import User

def readInLog(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    newFlight, created=Flight.objects.get_or_create(logfile=filepath)
    while True:
        try:
            m=mlog.recv_msg()
            #Importing flight parameters into the database is not implemented yet,
            #so we skip those messages.
            if 'PARAM' in m._type:
                continue
            timestamp=datetime.fromtimestamp(m._timestamp)
            newMessage, created=MavMessage.objects.get_or_create(msgType=m._type, timestamp=timestamp)
            #If this message is already in the database
            if not created:
                continue
            newMessage.save()
            m=m.to_dict()
            for key, item in m.items():
                if key!='mavpackettype':
                    newDatum=MavDatum(msgField=key,value=item,message=newMessage)
                    newDatum.save()
        except AttributeError:
            newFlight.save()
            continue
    return newFlight
