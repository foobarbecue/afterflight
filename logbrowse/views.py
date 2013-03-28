from django.utils import simplejson
from models import Flight, FlightVideo
from django.shortcuts import render_to_response
import calendar
from utils import dt2jsts
# Create your views here.
def flightDetail(request, slug):
    flight=Flight.objects.get(slug=slug)
    timelineEventList=[]
    heartbeats=flight.mavmessage_set.filter(msgType='HEARTBEAT')
    for heartbeat in heartbeats:
        try:
            timelineEventList.append(
                {"start":dt2jsts(heartbeat.timestamp),
                "content":"HB",
                "group":"Heartbeat"})
        except AttributeError:
            pass        
    return render_to_response('flight_detail.html',{
        'timeline_data':simplejson.dumps(timelineEventList),
        'object':flight})

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

def chapTimelineFormatFlights(request):
    timelineEventList=[]
    for flight in Flight.objects.all():
        #optimize this later-- should be single db transaction
        try:
            timelineEventList.append(
                {"start":flight.startTime.isoformat(),
                "end":flight.startTime.isoformat(),
                "content":"<a href=%s>%s</a>" % (flight.get_absolute_url(), flight.id),
                "group":"flight"
                })
        except AttributeError:
            pass

    for video in FlightVideo.objects.all():
        vidDescription="<a href=%s>" % video.url
        if video.onboard:
            vidDescription+="Start of onboard video"
        else:
            vidDescription+="Start of offboard video"
        vidDescription+="</a>"
        try:
            timelineEventList.append(
                {"start":dt2jsts(video.startTime),
                "content":vidDescription,
                "group":"video"})
        except AttributeError:
            pass
   
    return render_to_response('chaptimeline.html',
        {
        'object_list':Flight.objects.all(),
        'timeline_data': simplejson.dumps(timelineEventList)
        })