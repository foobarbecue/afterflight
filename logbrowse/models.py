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

import calendar, scipy, flyingrhino
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import connection as dbconn
from django.db import transaction
from datetime import timedelta
from af_utils import dt2jsts
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

class Flight(models.Model):
    pilot=models.ForeignKey(User,blank=True, null=True)
    logfile=models.FileField(blank=True, null=True, upload_to='logs')
    start=models.DateTimeField(blank=True, null=True)
    comments=models.TextField(blank=True, null=True)
    #payload=models.TextField(blank=True, null=True)
    video=models.URLField(blank=True, null=True)
    battery=models.ForeignKey('Battery',blank=True, null=True, )
    airframe=models.ForeignKey('Airframe', blank=True, null=True)
    slug=models.SlugField(primary_key=True)

    def thrData(self):
        vltDataQ=MavDatum.objects.filter(message__flight=self, msgField='throttle')
        vltVals=vltDataQ.values_list('message__timestamp','value')
        return vltVals

    def thrDataFlot(self):
        return ','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in self.thrData()])
        
    def battVltsData(self):
        vltDataQ=MavDatum.objects.filter(message__flight=self, msgField='voltage_battery')
        vltVals=vltDataQ.values_list('message__timestamp','value')
        return vltVals

    def battVltsDataFlot(self):
        return ','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in self.battVltsData()])
    
    def sensor_plot_data(self, msg_field):
        dataQ=MavDatum.objects.filter(message__flight=self, msgField=msg_field)
        vals=dataQ.values_list('message__timestamp','value')
        return ','.join([r'[%.1f,%.1f]' % (dt2jsts(timestamp),value) for timestamp, value in vals])
    
    @property
    def is_tlog(self):
        return 'tlog' in self.slug
    
    def initial_plot(self):
        #first we try to plot 
        #right_yax='Mot 1'
        #left_yax='Mot 2'
        if self.is_tlog:
            right_yax='throttle'
            left_yax='servo3_raw'
            #return {"labels":['Battery voltage (mv)','Throttle (pwm)'],
                    #"data":"[[%s],[%s]]"%(self.battVltsDataFlot(),self.thrDataFlot())}
        elif 'Mot 1' in self.messageFieldsRecorded:
            #probably because it is a dataflash log, not a tlog
            right_yax='Mot 1'
            left_yax='Mot 2'
        elif 'roll_sensor' in self.messageFieldsRecorded:
            right_yax='roll_sensor'
            left_yax='pitch_sensor'
        return {"labels":[right_yax,left_yax],
                "data":"[[%s],[%s]]"%(self.sensor_plot_data(right_yax),self.sensor_plot_data(left_yax))}
    
    def lats(self):
        # The 'order_by' should be unnecessary, since it's already in the model's Meta, but seems only to work this way. *might be fixed now TODO
        lats=MavDatum.objects.filter(message__flight=self, msgField__in=['lat','df_lat','Lat'], message__msgType__in=['GLOBAL_POSITION_INT','df_GPS']).order_by('message__timestamp')
        return scipy.array(lats.values_list('value', flat=True))/1e7
        
    def lons(self):
        lons=MavDatum.objects.filter(message__flight=self, msgField__in=['lon','df_lon','Long'], message__msgType__in=['GLOBAL_POSITION_INT','df_GPS']).order_by('message__timestamp')
        
        return scipy.array(lons.values_list('value', flat=True))/1e7

    def latLonsFlot(self):
        return ','.join([r'[%.1f,%.1f]' % latLon for latLon in zip(self.lats(), self.lons())])

    @property
    def latLonsJSON(self):
        return scipy.array([self.lons(), self.lats()]).transpose().tolist()
    
    @property
    def gpsTimes(self):
        return MavMessage.objects.filter(flight=self,msgType__in=['GLOBAL_POSITION_INT','df_GPS']).order_by('timestamp').values_list('timestamp',flat=True)
    
    @property
    def startTime(self):
        #if self.mavmessage_set.exclude(msgType='BAD_DATA').exists():
        try:
            return self.mavmessage_set.exclude(msgType='BAD_DATA').order_by('timestamp')[0].timestamp
        except IndexError:
            pass
    
    @property
    def endTime(self):
        #if self.mavmessage_set.exclude(msgType='BAD_DATA').exists():
        try:
            return self.mavmessage_set.exclude(msgType='BAD_DATA').latest('timestamp').timestamp
        except IndexError:
            pass
    
    @property
    def gpsTimestamps(self):
        longTstamps=[dt2jsts(timestamp) for timestamp in self.gpsTimes]
        #unfortunately the timestamps end up with L for 'long' in the JS unless we remove them here.
        #Actually, could probably do the multiplication by 1000 to convert to JS timestamp on the client side.
        #return str(longTstamps).replace('L','')
        return [dt2jsts(timestamp) for timestamp in self.gpsTimes]
        
    @property
    def messageTypesRecorded(self):
        return MavDatum.objects.filter(message__flight=self).values_list('message__msgType',flat=True).order_by('message__msgType').distinct()
    
    @property
    def messageFieldsRecorded(self):
        return MavDatum.objects.filter(message__flight=self).values('msgField').order_by('msgField').distinct().values_list('msgField',flat=True)
    
    @property
    def length(self):
        return (self.endTime - self.startTime)
    
    def lengthStr(self):
        return str(self.length)[:7]
    
    def countMessagesByType(self):
        msgTypeCounts=[None]*len(self.messageTypesRecorded)
        x=0
        for msgType in self.messageTypesRecorded:
            msgTypeCounts[x]=self.mavmessage_set.filter(msgType=msgType).count()
            x+=1
        return zip(self.messageTypesRecorded, msgTypeCounts)
    
    def throttleData(self):
        pass
        #return (timestamps, voltages)

    def __unicode__(self):
        return self.slug

    #for msgField in messageFieldsRecorded:
        #self.__dict__['%sJSON' % msgField]=lambda: MavDatum.objects.filter(message__flight=self, msgField=msgField).values_list('message__timestamp','value')
    
    #overwritten save method to import the logfile if this is a new instance
    def save(self, gpstime=True, *args, **kwargs):
        super(Flight, self).save(*args, **kwargs)
        from logbrowse import importLog
        importLog.readInLog(settings.MEDIA_ROOT + self.logfile.name, gpstime=gpstime)
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.slug])
    
    class Meta:
        ordering = ['comments','slug']
    
    def read_dflog(self, logfile_path=None):
        if not logfile_path:
            logfile_path=self.logfile.name
        fr_flight=flyingrhino.flight(logfile_path)
        cursor=dbconn.cursor()
        transaction.enter_transaction_management()
        fr_flight.to_afterflight_sql(dbconn=dbconn)
        transaction.commit()

class FlightVideo(models.Model):
    flight=models.ForeignKey('Flight')
    #In seconds
    delayVsLogstart=models.FloatField(blank=True, null=True)
    onboard=models.BooleanField(blank=True, default=True)
    url=models.URLField(blank=True, null=True)
    videoFile=models.FileField(blank=True, null=True, upload_to='video')
    
    @property
    def startTime(self):
        return self.flight.startTime+timedelta(seconds=self.delayVsLogstart)
    #For youtube videos, we don't store the endtime. Instead, get it from javascript at runtime.
    
    @property
    def startTimeJS(self):
        return dt2jsts(self.startTime)

class MavMessage(models.Model):
    msgType=models.CharField(max_length=40, choices=MSG_TYPES)
    timestamp=models.IntegerField(db_index=True, primary_key=True)
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
    message=models.ForeignKey('MavMessage',db_column='timestamp')
    msgField=models.CharField(max_length=40)
    value=models.FloatField()
    timestamp=models.IntegerField()

    def epoch_timestamp(self):
        return calendar.gmtime(self.message.timestamp.timetuple())*1000

    def __unicode__(self):
        return "%s on %s" % (self.msgField, self.message.timestamp)
        
    class Meta:
        get_latest_by=['message__timestamp']
        ordering = ['message']
    
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
    
