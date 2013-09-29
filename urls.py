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

from django.conf.urls import patterns, include, url
#from django.views.generic.list_detail import *
from django.views.generic import TemplateView
from django.contrib import admin
from logbrowse.models import Flight
from logbrowse.views import *
import settings
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'afterflight2.views.home', name='home'),
    # url(r'^afterflight2/', include('afterflight2.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    #url(r'^flight/(?P<slug>.+)/$',object_detail,{'queryset':Flight.objects.all()}, name='flights'),
    url(r'^flight/(?P<slug>.+)/$',flight_detail, name='flights'),
    url(r'^pilot/(?P<pilot>.+)/$',flightIndex, name='flightsForPilot'),
    url(r'^data$',plotDataJSON, name='flights'),
    url(r'^/?$',flightIndex, name='timeline'),
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^about/', direct_to_template, {'template':'about.html'}),
    url(r'^about', TemplateView.as_view(template_name='about.html')),
    url(r'^upload_progress$', upload_progress, name="upload_progress"),
    url(r'^upload', FlightCreate.as_view(), name='flight_create'),
    url(r'^add_video', VideoCreate.as_view(), name='video_create'),
    url(r'^edit_fe', edit_flightevent, name='edit_flightevent'),
    (r'^accounts/', include('allauth.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^(media)/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT, 'show_indexes':True
        }),
    )
    urlpatterns += patterns('django.contrib.staticfiles.views',
        url(r'^static/(?P<path>.*)$', 'serve'),
    )    