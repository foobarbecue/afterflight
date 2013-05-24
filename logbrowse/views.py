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

from django.utils import simplejson
from models import Flight, FlightVideo, MavDatum
from django.shortcuts import render_to_response
from django.http import HttpResponse
import calendar, datetime, json
from utils import dt2jsts
# Create your views here.
def flightDetail(request, slug):
    print 'loading' + slug
    flight=Flight.objects.get(slug=slug)
    timelineEventList=[]
    heartbeats=flight.mavmessage_set.filter(msgType='HEARTBEAT')
    
    #Timeline data construction
    for heartbeat in heartbeats:
        try:
            timelineEventList.append(
                {"start":dt2jsts(heartbeat.timestamp),
                "content":"HB",
                "group":"Heartbeat"})
        except AttributeError:
            pass
    for video in flight.flightvideo_set.all():
        startTime=dt2jsts(flight.startTime+datetime.timedelta(seconds=video.delayVsLogstart))
        timelineDictForVid={"start":startTime,"group":"Video"}
        if video.onboard:
            timelineDictForVid['content']='Onboard video start'
        else:
            timelineDictForVid['content']='Offboard video start'
        timelineEventList.append(timelineDictForVid)

    for evt in flight.flightevent_set.all():
        print evt
        timelineDictForEvt={"start":dt2jsts(evt.timestamp), "content":evt.get_eventType_display() + evt.comment}
        if evt.automatically_detected:
            timelineDictForEvt['group']='Flight events'
        else:
            timelineDictForEvt['group']='Annotations'
        timelineEventList.append(timelineDictForEvt)

    return render_to_response('flight_detail.html',{
        'timeline_data':simplejson.dumps(timelineEventList),
        'initial_plot':flight.initial_plot(),
        'object':flight})

def plotDataJSON(request):
    right_axis_msgfield=request.GET.get('right_axis')
    left_axis_msgfield=request.GET.get('left_axis')
    flight=request.GET.get('flight')
    
    rdataQuery=MavDatum.objects.filter(message__flight__slug=flight, msgField=right_axis_msgfield)
    right_axis_data=rdataQuery.values_list('message__timestamp','value')
    
    ldataQuery=MavDatum.objects.filter(message__flight__slug=flight, msgField=left_axis_msgfield)
    left_axis_data=ldataQuery.values_list('message__timestamp','value')
    
    right_axis_data= '['+','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in right_axis_data])+']'
    left_axis_data= '['+','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in left_axis_data])+']'
    data='[%s,%s]' % (right_axis_data,left_axis_data)
    return HttpResponse(data, content_type='application/json')
        
def timegliderFormatFlights(request):
    flightList=[]
    for flight in Flight.objects.all():
        #optimize this later-- should be single db transaction
        flightList.append(
            {"id":flight.pk,
            "title":flight.slug,
            "startdate":dt2jsts(flight.startTime),
            "enddate":dt2jsts(flight.endTime)})
    #add the timeline header information
    flightListWheader={
        'id':'flight_timeline',
        'title':'flight_timeline',
        'events':flightList[0:3]
        }
    return render_to_response('timeline.html',{'timeline_data': simplejson.dumps([flightListWheader,])})

def flightIndex(request):
    timelineEventList=[]
    flightStartLocs=[]
    flightStartLocsJSON = {
        "type": "FeatureCollection", 
        "features": [
        {
            "type": "Feature", 
            "geometry":
                {
                    "type": "MultiPoint", 
                    "coordinates": flightStartLocs
                },
        },]
    };
    for flight in Flight.objects.all():
        #optimize this later-- should be single db transaction
        try:
            timelineEventList.append(
                {"start":flight.startTime.isoformat(),
                "end":flight.startTime.isoformat(),
                "content":"<a href=%s logpk=%s>%s</a>" % (flight.get_absolute_url(), flight.id, flight.id),
                "group":"flight",
                "test":"test"
                })
        except AttributeError:
            pass
        # Get the last GPS coordinate for each flight to add to the flight index map.
        # We use the last one because it's more likely to be a better fix that the first.
        try:
            latestGPSmsg=flight.mavmessage_set.filter(msgType__in=["GLOBAL_POSITION_INT","GPS_RAW_INT","df_GPS"]).latest()
            lat=latestGPSmsg.mavdatum_set.get(msgField__in=['lat','Lat']).value/1e7
            lon=latestGPSmsg.mavdatum_set.get(msgField__in=['lon','Long']).value/1e7
            if lon != 0 and lat != 0: #TODO should actually check the GPS_STATUS messages to throw away points where there is no fix
                flightStartLocsJSON['features'].append(
                    {
                    "type":"Feature",
                    "geometry":{
                            "type":"Point",
                            "coordinates":[lon,lat]
                        },
                     "properties":{"number":unicode(flight.pk),"name":unicode(flight),"slug":flight.slug}
                     })

            
        #should be except DoesNotExist, find where to import that from
        except:
            pass

    

    for video in FlightVideo.objects.all():
        vidDescription="<a href=%s>" % video.url
        #if video.onboard:
            #vidDescription+="Start of onboard video"
        #else:
            #vidDescription+="Start of offboard video"
        vidDescription+="</a>"
        try:
            timelineEventList.append(
                {"start":dt2jsts(video.startTime),
                "content":vidDescription,
                "group":"video"})
        except AttributeError:
            pass
   
    return render_to_response('flight_list.html',
        {
        'object_list':Flight.objects.all(),
        'timeline_data': simplejson.dumps(timelineEventList),
        'flightStartLocs': simplejson.dumps(flightStartLocsJSON)
        })