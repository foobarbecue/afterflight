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

import datetime, scipy, flyingrhino
from logbrowse import fltdata
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadhandler import StopUpload
from django.db import connection as dbconn
from django.db import transaction
from af_utils import dt2jsts, utc, cross
from pymavlink import mavutil
from cacheops import cached
from django.core.cache import cache
# Create your models here.

MSG_TYPES=(('SYS_STATUS','SYS_STATUS'),
('MEMINFO','MEMINFO'),
('MISSION_CURRENT','MISSION_CURRENT'),
('GPS_RAW_INT','GPS_RAW_INT'),
('NAV_CONTROLLER_OUTPUT','NAV_CONTROLLER_OUTPUT'),
('RAW_IMU','RAW_IMU'),
('SCALED_PRESSURE','SCALED_PRESSURE'),
('SENSOR_OFFSETS','SENSOR_OFFSETS'),
('SERVO_OUTPUT_RAW','SERVO_OUTPUT_RAW'),
('RC_CHANNELS_RAW','RC_CHANNELS_RAW'),
('AHRS','AHRS'),
('HWSTATUS','HWSTATUS'),
('ATTITUDE','ATTITUDE'),
('VFR_HUD','VFR_HUD'),
('HEARTBEAT','HEARTBEAT'),
('PARAM_REQUEST_LIST','PARAM_REQUEST_LIST'),
('PARAM_VALUE','PARAM_VALUE'),
('REQUEST_DATA_STREAM','REQUEST_DATA_STREAM'),
('STATUSTEXT','STATUSTEXT'),
('GPS_STATUS','GPS_STATUS'))

class NoDuplicateFileStorage(FileSystemStorage):
    """
    This exists to handle the case of trying to upload the same file twice.
    By default, django adds a _1 counter to the filename, but we want to 
    cancel the upload.
    """
    def _save(self, name, content):
        if self.exists(name):
            raise StopUpload('File already exists', connection_reset=True)
        return super(OverwriteStorage, self)._save(name, content)

class Flight(models.Model):
    pilot=models.ForeignKey(User,blank=True, null=True)
    #Doing this this way doesn't quite work yet. Causes TypeError. TODO
    #logfile=models.FileField(blank=True, null=True, upload_to='logs', storage=NoDuplicateFileStorage)
    logfile=models.FileField(blank=True, null=True, upload_to='logs')
    start=models.DateTimeField(blank=True, null=True)
    comments=models.TextField(blank=True, null=True)
    #payload=models.TextField(blank=True, null=True)
    video=models.URLField(blank=True, null=True)
    battery=models.ForeignKey('Battery',blank=True, null=True, )
    airframe=models.ForeignKey('Airframe', blank=True, null=True)
    orig_logfile_name=models.TextField(blank=True, null=True)
    slug=models.SlugField(primary_key=True)
    
    def initial_plot(self):
        return fltdata.initial_plot(self)
    
    def sensor_plot_data(self, msg_field):
        return fltdata.sensor_plot_data(self, msg_field)
    
    def sensor_plot_pandas(self, msg_field):
        return fltdata.sensor_plot_pandas(self, msg_field)
    
    @property
    def is_tlog(self):
        return 'tlog' in self.slug
    
    def lats(self):
        # The 'order_by' should be unnecessary, since it's already in the model's Meta, but seems only to work this way. *might be fixed now TODO
        lats=MavDatum.objects.filter(message__flight=self, msgField__in=['lat','Lat'], message__msgType__in=['GLOBAL_POSITION_INT','GPS']).order_by('message__timestamp')
        lats=scipy.array(lats.values_list('value', flat=True))
        if self.is_tlog:
            lats=lats/1e7
        return lats
    
    def lons(self):
        lons=MavDatum.objects.filter(message__flight=self, msgField__in=['lon','Lng','Long'], message__msgType__in=['GLOBAL_POSITION_INT','GPS']).order_by('message__timestamp')
        lons=scipy.array(lons.values_list('value', flat=True))
        if self.is_tlog:
            lons=lons/1e7        
        return lons

    @property
    def lat_lons_JSON(self):
        return fltdata.lat_lons_JSON(self)
    
    def gps_times(self):
        return fltdata.gps_times(self)
    
    
    def start_time(self):
        return fltdata.start_time(self)
    
    def start_time_js(self):
        return dt2jsts(self.start_time())
    
    def end_time(self):
        return fltdata.end_time(self)
    
    def gps_timestamps(self):
        return fltdata.gps_timestamps(self)

    def length_str(self):
        return fltdata.length_str(self)

    def message_fields_recorded(self):
        return fltdata.message_fields_recorded(self)
        
    def message_types_recorded(self):
        return fltdata.message_types_recorded(self)
    
    def count_messages_by_type(self):
        return fltdata.count_messages_by_type(self)
    
    def detect_takeoffs(self, thr_threshold=300):
        #Only for dflog now
        takeoffs=cross(self.sensor_plot_pandas('ThrIn'), cross=thr_threshold, direction='rising')
        for takeoffTime in takeoffs:
            newFE=FlightEvent(flight=self,
                              eventType='TAKEOFF',
                              automatically_detected=True,
                              detection_method='crossing %s' % 300,
                              timestamp=takeoffTime.astype(str),
                              comment='Throttle crossing %s detected' % thr_threshold
                              )
            newFE.save()        

    def detect_landings(self, thr_threshold=300):
        #Only for dflog now
        landings=cross(self.sensor_plot_pandas('ThrIn'), cross=thr_threshold, direction='falling')
        for landingTime in landings:
            newFE=FlightEvent(flight=self,
                              eventType='LANDING',
                              automatically_detected=True, 
                              detection_method='crossing %s' % 300,
                              timestamp=landingTime.astype(str),
                              comment='Throttle crossing %s detected' % thr_threshold
                              )
            newFE.save()

    def __unicode__(self):
        return self.slug
    
    #overwritten save method to import the logfile if this is a new instance
    def save(self, gpstime=True, *args, **kwargs):
        super(Flight, self).save(*args, **kwargs)
        #need to make this happen only on first save
        "Overridden save reading in log" + (self.logfile.name or '(no name)')
        self.read_log()
        self.invalidate_caches()
        #from logbrowse import importLog
        #importLog.readInLog(settings.MEDIA_ROOT + self.logfile.name, gpstime=gpstime)
    
    def invalidate_caches(self):
        fltdata.invalidate_caches(self)
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.slug])
    
    class Meta:
        ordering = ['comments','slug']
    
    def read_log(self, logfile_path=None):
        if not logfile_path:
            logfile_path=self.logfile.path
        if not self.is_tlog:
            #flyingrhino can't do tlogs yet. We assume it's a dataflash log if it's not a tlog.
            fr_flight=flyingrhino.flight(logfile_path, messaging=self.set_processing_state)
            self.set_processing_state('Dataflash log loaded into memory, inserting into database')
            cursor=dbconn.cursor()
            transaction.enter_transaction_management()
            fr_flight.to_afterflight_sql(dbconn=dbconn.connection,close_when_done=False)
            transaction.commit()
            self.set_processing_state('Dataflash log inserted into database', length=10, uploaded=10)
        else:
            self.read_tlog()
            pass
        #Do automatic processing
        self.detect_takeoffs()
        self.detect_landings()

    def read_tlog(self):
        mlog = mavutil.mavlink_connection(self.logfile.path)
        mavData=[]
        mavMessages=[]
        ts=None
        prev_timestamp=None
        orig_dup=None
        while True:
            m=mlog.recv_msg()
            if not m:
                #We have hit the end of the logfile
                break
            if 'PARAM' in m.get_type():
                continue
            try:
                #Ugly hack because the DB can't deal with duplicate timestamps because we
                #are using timestamp as the primary key on message
                if m._timestamp==prev_timestamp or m._timestamp==orig_dup:
                    #The new timestamp is the same as the last message, so add a millisecond.
                    if not orig_dup:
                        orig_dup=m._timestamp
                    ts=prev_timestamp+0.000001
                else:
                    ts=m._timestamp
                    orig_dup=None
                timestamp=datetime.datetime.fromtimestamp(ts, utc)
                prev_timestamp=ts
            except: 
                print "bad timestamp on %s " % m
                break
            mavMessages.append(MavMessage(msgType=m.get_type(), timestamp=timestamp, flight=self))
            m=m.to_dict()
            for key, item in m.items():
                if key!='mavpackettype':
                    try:
                        value=float(item)
                    except ValueError:
                        #print "non-number value in %s" % m
                        continue
                    newDatum=MavDatum(msgField=key,value=value,message_id=timestamp)
                    mavData.append(newDatum)
        self.set_processing_state('Inserting telemetry log messages into database')
        MavMessage.objects.bulk_create(mavMessages)
        self.set_processing_state('Inserting telemetry log data into database')
        MavDatum.objects.bulk_create(mavData)
        self.set_processing_state('Waiting for db transaction to finish and refreshing page')
    
    def set_processing_state(self, processing_state, length=100, uploaded=50):
        print processing_state
        self.progress_cache_key = self.orig_logfile_name.replace(' ','_')
        cache.set(self.progress_cache_key, {
            'length': length,
            'uploaded': uploaded,
            'message': processing_state
        })
        return self.progress_cache_key

    def get_processing_state(self):
        return cache.get(self.orig_logfile_name.replace(' ','_'))

class FlightVideo(models.Model):
    flight=models.ForeignKey('Flight')
    #In seconds
    delayVsLogstart=models.FloatField(default=0)
    onboard=models.BooleanField(blank=True, default=True)
    url=models.URLField(blank=True, null=True)
    videoFile=models.FileField(blank=True, null=True, upload_to='video')
    
    def start_time(self):
        return self.flight.start_time()+datetime.timedelta(seconds=self.delayVsLogstart)
        #For youtube videos, we don't store the endtime. Instead, get it from javascript at runtime.
    
    @property
    def start_time_js(self):
        return dt2jsts(self.start_time())
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.flight.slug])

class MavMessage(models.Model):
    msgType=models.CharField(max_length=40, choices=MSG_TYPES)
    timestamp=models.DateTimeField(db_index=True, primary_key=True)
    orig_linenum=models.DateTimeField(null=True,blank=True)
    flight=models.ForeignKey('Flight')

    def __unicode__(self):
        return "%s on %s" % (self.msgType, self.timestamp)
    
    class Meta:
        get_latest_by='timestamp'
        ordering = ['timestamp']
    
class MavDatum(models.Model):
    #Use timestamp as the reference to the mavmessage -- it's the primary key on mavmessage
#     TODO: can we have joint primary key using message and msgfield?
    rowid=models.IntegerField(primary_key=True)
    message=models.ForeignKey('MavMessage',null=True,db_column='timestamp')
    msgField=models.CharField(max_length=40)
    value=models.FloatField()

    def __unicode__(self):
        return "%s on %s" % (self.msgField, self.message.timestamp)
        
    class Meta:
        get_latest_by='message'
    
class Battery(models.Model):
    cells=models.IntegerField(blank=True, null=True)
    capacity=models.IntegerField(blank=True, null=True)
    currentRating=models.IntegerField(blank=True, null=True)
    mfgSerNum=models.CharField(blank=True, null=True,max_length=40)
    persSerNum=models.CharField(max_length=40, primary_key=True)
    mass=models.IntegerField(blank=True, null=True,max_length=40)
    mfg=models.CharField(blank=True, null=True,max_length=40)
    
    def __unicode__(self):
        return '%s (%ss %sc)' % (self.persSerNum, self.cells, self.capacity)

class Airframe(models.Model):
    mfg=models.CharField(blank=True, null=True, max_length=40)
    partModel=models.CharField(blank=True, null=True, max_length=40)
    mfgSerNum=models.CharField(blank=True, null=True,max_length=40)
    persSerNum=models.CharField(max_length=40)
    
    def __unicode__(self):
        return self.mfg + ' ' + self.partModel

class FlightEvent(models.Model):
    EVENT_TYPES=(
        ('TAKEOFF','Takeoff'),
        ('LANDING','Landing'),
        ('CRASH','Hard landing'),
        ('FLIP','Flip'),
        ('MODE','Mode change')
    )
    flight=models.ForeignKey(Flight)
    eventType=models.CharField(blank=True, null=True, max_length=40, choices=EVENT_TYPES)
    comment=models.TextField()
    automatically_detected=models.BooleanField(default=False)
    timestamp=models.DateTimeField()
    detection_method=models.CharField(blank=True, null=True, max_length=200)
    
    def confirm(self):
        """Human-verify this event after automatic detection"""
        self.automatically_detected=False
        self.save()
    
    def unconfirm(self):
        """Human-invalidate this event after automatic detection"""
        self.automatically_detected=True
        self.save()