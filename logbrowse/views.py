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

try:
    import ujson as json
    print 'imported ujson'
except:
    print 'could not find ujson'
    from django.utils import simplejson as json


from models import Flight, FlightVideo, MavDatum, FlightEvent
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.views.generic.edit import CreateView
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import datetime, fltdata
from af_utils import dt2jsts
from django.core.cache import cache
# Create your views here.

def upload_progress(request):
    """
    AJAX view adapted from django-progressbarupload

    Return the upload progress and total length values
    """
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    if 'logfilename' in request.GET:
        logfilename = request.GET['logfilename']
    elif 'logfilename' in request.META:
        logfilename = request.META['logfilename']
    cache_key = "%s_%s" % (request.META['REMOTE_ADDR'], progress_id)
    data = cache.get(cache_key)
    if not data:
        data = cache.get(logfilename.replace(' ','_'))
    return HttpResponse(json.dumps(data))
    

class FlightForm(ModelForm):
    class Meta:
        fields = ('logfile','comments')
        model = Flight        

class FlightCreate(CreateView):
    model = Flight
    form_class = FlightForm
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(FlightCreate, self).dispatch(*args, **kwargs)
    
    def form_valid(self, form):
        form.instance.pilot = self.request.user
        form.instance.orig_logfile_name = form.instance.logfile.name
        form.instance.logfile.name = slugify(form.instance.logfile.name.split('/')[-1])
        #TODO: take out the slugfield entirely? It's the same as logfile.name...
        form.instance.slug = form.instance.logfile.name
        return super(FlightCreate, self).form_valid(form)

class VideoForm(ModelForm):
    def __init__(self, *args, **kwargs):
        #have to get rid of the user because super doesn't expect it
        user = kwargs.pop('current_user')
        super(VideoForm, self).__init__(*args, **kwargs)
        self.fields['flight'].queryset=Flight.objects.filter(pilot=user)
    
    class Meta:
        model = FlightVideo
        exclude = ('created_by',)

class VideoCreate(CreateView):
    form_class = VideoForm
    #seems like you shouldn't have to specify this a second time.
    #See https://docs.djangoproject.com/en/1.5/topics/class-based-views/generic-editing/#models-and-request-user
    model = FlightVideo

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(VideoCreate, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        #Make sure the user is not trying to attach a video to someone else's flight
        if form.instance.flight.pilot == self.request.user:
            return super(VideoCreate, self).form_valid(form)
        else:
            raise PermissionDenied
    
    #The purpose of this is to pass the user to the ModelForm and filter the flight choices by user
    def get_form_kwargs(self):
        kwargs = super(VideoCreate, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs        

def changeVidStartTime(request, vid_id):
    vid = get_object_or_404(FlightVideo, pk=vid_id)
    try:
        vid.delayVsLogstart = request.POST['delayVsLogstart']
        vid.save()
        return HttpResponseRedirect(vid.flight.get_absolute_url())
    except:
        return HttpResponseBadRequest('Invalid input for delayVsLogstart')

def flight_detail(request, slug):
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
        start_time=dt2jsts(flight.start_time()+datetime.timedelta(seconds=video.delayVsLogstart))
        timelineDictForVid={"start":start_time,"group":"Video","editable":True}
        if video.onboard:
            timelineDictForVid['content']='Start of onboard video ' 
        else:
            timelineDictForVid['content']='Start of offboard video ' + video.url
        timelineDictForVid['vidUrl']=video.url
        timelineDictForVid['pk']=video.pk  
        timelineEventList.append(timelineDictForVid)

    #add start and end of log
    if flight.is_tlog:
        log_type='Mavlink telemetry log'
    else:
        log_type='APM dataflash log'
    timelineEventList.append({'start':dt2jsts(flight.start_time()),
                              'end':dt2jsts(flight.end_time()),
                              'group':'Logs',
                              'content':'%s %s' % (log_type, flight.logfile.name)})
    

    for evt in flight.flightevent_set.all():
        print evt
        timelineDictForEvt={"start":dt2jsts(evt.timestamp), "content":evt.get_eventType_display(), "comment":evt.comment}
        timelineDictForEvt['group']='Flight events'
        timelineDictForEvt['pk']=evt.pk
        #timelineDictForEvt['detectionMethod']=evt.detection_method
        
        #Text that explains how the event was created and link to confirm it if it was automatic
        if evt.automatically_detected:
            timelineDictForEvt['className']='autodetected'
            timelineDictForEvt['confirmed']='false'
        else:
            timelineDictForEvt['confirmed']='true'
        timelineEventList.append(timelineDictForEvt)

    return render(request, 'flight_detail.html',{
        'timeline_data':json.dumps(timelineEventList),
        'initial_plot':fltdata.initial_plot(flight),
        'object':flight})

@csrf_exempt
def edit_flightevent(request):
    #TODO check it's actually POST etc
    pk=request.POST.get('pk')
    action=request.POST.get('action')
    if action == 'changeVidDelay':
        flightvid=FlightVideo.objects.get(pk=pk)
        if request.user == flightvid.flight.pilot:
            flightvid.delayVsLogstart=float(request.POST.get('vidDelay'))/1000
            flightvid.save()
            return HttpResponse(str(flightvid.start_time_js))
        else:
            return HttpResponseForbidden('This user does not own this FlightEvent')        

    else:
        flightevent=FlightEvent.objects.get(pk=pk)
        if request.user == flightevent.flight.pilot:
            if action == 'confirm':
                flightevent.confirm()
                return HttpResponse('confirmed')
            elif action == 'unconfirm':
                flightevent.unconfirm() 
                return HttpResponse('unconfirmed')
            elif action == 'delete':
                flightevent.delete() 
                return HttpResponse('deleted')
        else:
            return HttpResponseForbidden('This user does not own this FlightEvent')

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
        
class LogUploadForm(ModelForm):
    class Meta:
        model = Flight

def flightIndex(request, pilot=None):
    if pilot:
        flights=Flight.objects.filter(pilot__username=pilot)
    else:
        flights=Flight.objects.all()
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
    for flight in flights:
        #optimize this later-- should be single db transaction
        try:
            timelineEventList.append(
                {"start":flight.start_time().isoformat(),
                "end":flight.start_time().isoformat(),
                "content":"<a href=%s logpk=%s>%s</a>" % (flight.get_absolute_url(), flight.pk, flight.pk),
                "group":"flight",
                "test":"test"
                })
        except AttributeError:
            pass
        # Get the last GPS coordinate for each flight to add to the flight index map.
        # We use the last one because it's more likely to be a better fix that the first.
        try:
            lat=MavDatum.objects.filter(msgField__in=['lat','Lat'], message__flight=flight).latest().value
            lon=MavDatum.objects.filter(msgField__in=['lon','Long','Lng'], message__flight=flight).latest().value
            if lon != 0 and lat != 0: #TODO should actually check the GPS_STATUS messages to throw away points where there is no fix
                if flight.is_tlog:
                    lat=lat/1e7
                    lon=lon/1e7
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
                {"start":dt2jsts(video.start_time),
                "content":vidDescription,
                "group":"video"})
        except AttributeError:
            pass
    
    return render(request,
        'flight_list.html',
        {
        'object_list':flights,
        'timeline_data': json.dumps(timelineEventList),
        'flightStartLocs': json.dumps(flightStartLocsJSON)
        })