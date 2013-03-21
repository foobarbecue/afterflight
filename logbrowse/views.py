from django.utils import simplejson
from models import Flight, FlightVideo
from django.shortcuts import render_to_response

# Create your views here.
def voltThrPlot(flight):
    return render_to_response('voltPlot.html',{'flight':flight})

def timegliderFormatFlights(throwaway):
    flightList=[]
    for flight in Flight.objects.all():
        #optimize this later-- should be single db transaction
        flightList.append(
            {"id":flight.pk,
            "title":flight.slug,
            "startdate":unicode(flight.startTime),
            "enddate":unicode(flight.endTime)})
    #add the timeline header information
    flightListWheader={
        'id':'flight_timeline',
        'title':'flight_timeline',
        'events':flightList[0:3]
        }
    return render_to_response('timeline.html',{'timeline_data': simplejson.dumps([flightListWheader,])})

def chapTimelineFormatFlights(throwaway):
    timelineEventList=[]
    for flight in Flight.objects.all():
        #optimize this later-- should be single db transaction
        try:
            timelineEventList.append(
                {"start":flight.startTime.isoformat(),
                "end":flight.endTime.isoformat(),
                "content":"<a href=%s>%s</a>" % (flight.get_absolute_url(), flight.id),
                "group":"flight"})
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
                {"start":video.flight.startTime+video.delayVsLogstart.isoformat(),
                "content":vidDescription,
                "group":"flight"})
        except AttributeError:
            pass
   
    return render_to_response('chaptimeline.html',
        {
        'object_list':Flight.objects.all(),
        'timeline_data': simplejson.dumps(timelineEventList)
        })