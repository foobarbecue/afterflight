'''
Reads a .tlog using pymavlink into the afterflight database
'''

# allow import from where mavlink.py is
import sys
from datetime import datetime
from django.conf import settings
sys.path.append(settings.PYMAVLINK_PATH)
import mavutil
from logbrowse.models import Flight, MavMessage, MavDatum

def readInLog(filepath):
    mlog = mavutil.mavlink_connection(filepath)
    newFlight=Flight(logfile=filepath)

    m=mlog.recv_msg()
    timestamp=datetime.fromtimestamp(m._timestamp)
    newMessage=MavMessage(msgType=m._type, timestamp=timestamp)
    newMessage.save()
    m=m.to_dict()
    print m
    for key, item in m.items():
        if key!='mavpackettype':
            newDatum=MavDatum(msgField=key,value=item,message=newMessage)
            newDatum.save()

