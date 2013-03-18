from django.utils import simplejson
from models import Flight
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