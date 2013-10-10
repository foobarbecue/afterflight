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
"""
High-level data retrieval from the Flight model. Most of these could be methods on the
Flight model, but cacheops doesn't work with instance methods so we do the cacheable 
stuff here. Some of these are then wrapped by flight instance methods so they are easy 
to use in templates. TODO better solution. 
"""

from cacheops import cached
#not using 'from logbrowse.models import MavDatum' because of circular dependency
import logbrowse
from af_utils import dt2jsts
import scipy, pandas, pdb

@cached()
def initial_plot(flight):
    #first we try to plot 
    #right_yax='Mot 1'
    #left_yax='Mot 2'
    if flight.is_tlog:
        right_yax='throttle'
        left_yax='servo3_raw'
    else:
        msg_fields=message_fields_recorded(flight)
        #pdb.set_trace()
        if 'Mot 1' in msg_fields:
            #probably because it is a dataflash log, not a tlog
            right_yax='Mot 1'
            left_yax='Mot 2'
        elif 'Mot1' in msg_fields:
            #probably because it is a dataflash log, not a tlog
            right_yax='Mot1'
            left_yax='Mot2'            
        elif 'roll_sensor' in msg_fields:
            right_yax='roll_sensor'
            left_yax='pitch_sensor'
    return {"labels":[right_yax,left_yax],
            "data":"[[%s],[%s]]"%(flight.sensor_plot_data(right_yax),flight.sensor_plot_data(left_yax))}

@cached()    
def message_fields_recorded(flight):
    return logbrowse.models.MavDatum.objects.filter(message__flight=flight).values('msgField').order_by('msgField').distinct().values_list('msgField',flat=True)

@cached()
def message_types_recorded(flight):
    return logbrowse.models.MavDatum.objects.filter(message__flight=flight).values_list('message__msgType',flat=True).order_by('message__msgType').distinct()

@cached()
def count_messages_by_type(flight):
    msgTypeCounts=[None]*len(flight.message_types_recorded)
    x=0
    for msgType in flight.message_types_recorded:
        msgTypeCounts[x]=flight.mavmessage_set.filter(msgType=msgType).count()
        x+=1
    return zip(flight.message_types_recorded, msgTypeCounts)

@cached()
def lat_lons_JSON(flight):
    return scipy.array([flight.lons(), flight.lats()]).transpose().tolist()

@cached()
def gps_timestamps(flight):
    #unfortunately the timestamps end up with L for 'long' in the JS unless we remove them here.
    #Actually, could probably do the multiplication by 1000 to convert to JS timestamp on the client side.
    #return str(longTstamps).replace('L','')
    return [dt2jsts(timestamp) for timestamp in flight.gps_times()]

def gps_times(flight):
    return logbrowse.models.MavMessage.objects.filter(flight=flight,msgType__in=['GLOBAL_POSITION_INT','df_GPS','GPS']).order_by('timestamp').values_list('timestamp',flat=True)

@cached()
def sensor_plot_data(flight, msg_field):
    dataQ=logbrowse.models.MavDatum.objects.filter(message__flight=flight, msgField=msg_field)
    vals=dataQ.values_list('message__timestamp','value')
    return ','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in vals])

@cached()
def sensor_plot_pandas(flight, msg_field):
    thrindex=logbrowse.models.MavDatum.objects.filter(message__flight=flight, msgField=msg_field).values_list('message_id',flat=True)
    thr=logbrowse.models.MavDatum.objects.filter(message__flight=flight, msgField=msg_field).values_list('value',flat=True)
    return pandas.Series(thr, index=thrindex)

def length_str(flight):
#     try:
        flt_length=flight.end_time() - flight.start_time()
        return str(flt_length)[:7]
#     except:
#         return None

@cached()
def start_time(flight):
    try:
        return flight.mavmessage_set.exclude(msgType='BAD_DATA').order_by('timestamp')[0].timestamp
    except IndexError:
        pass

@cached()
def end_time(flight):
    #if self.mavmessage_set.exclude(msgType='BAD_DATA').exists():
    try:
        return flight.mavmessage_set.exclude(msgType='BAD_DATA').latest('timestamp').timestamp
    except IndexError:
        pass

def invalidate_caches(flight):
    flight_funcs=[initial_plot,
                  message_fields_recorded,
                  message_types_recorded,
                  count_messages_by_type,
                  lat_lons_JSON,
                  gps_timestamps,
                  sensor_plot_data,
                  sensor_plot_pandas,
                  start_time,
                  end_time]
    for fn in flight_funcs:
        fn.invalidate(flight)

    