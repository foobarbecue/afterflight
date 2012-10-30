from django.conf.urls import patterns, include, url
from django.views.generic.list_detail import *
from django.contrib import admin
from logbrowse.models import Flight
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'afterflight2.views.home', name='home'),
    # url(r'^afterflight2/', include('afterflight2.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^flight/(?P<slug>.+)/$',object_detail,{'queryset':Flight.objects.all()}),
    url(r'^flight/$',object_list,{'queryset':Flight.objects.all()}),
    url(r'^admin/', include(admin.site.urls)),
)
