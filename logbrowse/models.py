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

import datetime, calendar, scipy, flyingrhino, pandas
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import connection as dbconn
from django.db import transaction
from af_utils import dt2jsts, utc, cross
from pymavlink import mavutil
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
    
    def sensor_plot_pandas(self, msg_field):
        thrindex=MavDatum.objects.filter(msgField='ThrIn').values_list('message_id',flat=True)
        thr=MavDatum.objects.filter(msgField='ThrIn').values_list('value',flat=True)
        return pandas.Series(thr, index=thrindex)
    
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
        elif 'Mot1' in self.messageFieldsRecorded:
            #probably because it is a dataflash log, not a tlog
            right_yax='Mot1'
            left_yax='Mot2'            
        elif 'roll_sensor' in self.messageFieldsRecorded:
            right_yax='roll_sensor'
            left_yax='pitch_sensor'
        return {"labels":[right_yax,left_yax],
                "data":"[[%s],[%s]]"%(self.sensor_plot_data(right_yax),self.sensor_plot_data(left_yax))}
    
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
    
    def detectTakeoffs(self, thr_threshold=300):
        #Only for dflog now
        takeoffs=cross(self.sensor_plot_pandas('ThrIn'), cross=thr_threshold, direction='rising')
        for takeoffTime in takeoffs:
            newFE=FlightEvent(flight=self,
                              eventType='TAKEOFF',
                              automatically_detected=True,
                              timestamp=takeoffTime.astype(str),
                              comments='Throttle crossing %s detected' % thr_threshold
                              )
            newFE.save()        

    def detectLandings(self, thr_threshold=300):
        #Only for dflog now
        landings=cross(self.sensor_plot_pandas('ThrIn'), cross=thr_threshold, direction='falling')
        for landingTime in landings:
            newFE=FlightEvent(flight=self,
                              eventType='LANDING',
                              automatically_detected=True, 
                              timestamp=landingTime.astype(str),
                              comments='Throttle crossing 300 detected' % thr_threshold
                              )
            newFE.save()
    
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
        #need to make this happen only on first save
        "Overridden save reading in log" + (self.logfile.name or '(no name)')
        self.read_log()
        #from logbrowse import importLog
        #importLog.readInLog(settings.MEDIA_ROOT + self.logfile.name, gpstime=gpstime)
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.slug])
    
    class Meta:
        ordering = ['comments','slug']
    
    def read_log(self, logfile_path=None):
        if not logfile_path:
            logfile_path=self.logfile.name
        if not self.is_tlog:
            #flyingrhino can't do tlogs yet. We assume it's a dataflash log if it's not a tlog.
            fr_flight=flyingrhino.flight(settings.MEDIA_ROOT + logfile_path)
            cursor=dbconn.cursor()
            transaction.enter_transaction_management()
            fr_flight.to_afterflight_sql(dbconn=dbconn.connection,close_when_done=False)
            transaction.commit()
        else:
            self.read_tlog()
            pass
        #Do automatic processing
        self.detectTakeoffs()
        self.detectLandings()

    def read_tlog(self):
        mlog = mavutil.mavlink_connection(self.logfile.name)
        mavData=[]
        mavMessages=[]
        while True:
            m=mlog.recv_msg()
            if not m:
                break
            if 'PARAM' in m._type:
                continue
            timestamp=datetime.datetime.fromtimestamp(m._timestamp, utc)
            mavMessages.append(MavMessage(msgType=m._type, timestamp=timestamp, flight=self))
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
        #Can't get bulk_create to work here because you end up with blank message_id s on the mavData TODO
        MavMessage.objects.bulk_create(mavMessages)
        MavDatum.objects.bulk_create(mavData)
    
class FlightVideo(models.Model):
    flight=models.ForeignKey('Flight')
    #In seconds
    delayVsLogstart=models.FloatField(default=0)
    onboard=models.BooleanField(blank=True, default=True)
    url=models.URLField(blank=True, null=True)
    videoFile=models.FileField(blank=True, null=True, upload_to='video')
    
    @property
    def startTime(self):
        if self.delayVsLogstart:
            return self.flight.startTime+datetime.timedelta(seconds=self.delayVsLogstart)
        else:
            return None
    #For youtube videos, we don't store the endtime. Instead, get it from javascript at runtime.
    
    @property
    def startTimeJS(self):
        return dt2jsts(self.startTime)
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.flight.slug])

class MavMessage(models.Model):
    msgType=models.CharField(max_length=40, choices=MSG_TYPES)
    timestamp=models.DateTimeField(db_index=True, primary_key=True)
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
    
