import time, scipy
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
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
    video=models.URLField(blank=True, null=True)
    battery=models.ForeignKey('Battery',blank=True, null=True, )
    airframe=models.ForeignKey('Airframe', blank=True, null=True)
    slug=models.SlugField()

    def thrData(self):
        vltDataQ=MavDatum.objects.filter(message__flight=self, msgField='throttle')
        vltVals=vltDataQ.values_list('message__timestamp','value')
        return vltVals

    def thrDataFlot(self):
        vltDataQ=MavDatum.objects.filter(message__flight=self, msgField='throttle')
        vltVals=vltDataQ.values_list('message__timestamp','value')
        return ','.join([r'[%.1f,%.1f]' % (time.mktime(timestamp.timetuple())*1000,value) for timestamp, value in self.thrData()])
        
    def battVltsData(self):
        vltDataQ=MavDatum.objects.filter(message__flight=self, msgField='voltage_battery')
        vltVals=vltDataQ.values_list('message__timestamp','value')
        return vltVals

    def battVltsDataFlot(self):
        return ','.join([r'[%.1f,%.1f]' % (time.mktime(timestamp.timetuple())*1000,value) for timestamp, value in self.battVltsData()])

    def lats(self):
        lats=MavDatum.objects.filter(message__flight=self, msgField='lat')
        return scipy.array(lats.values_list('value', flat=True))/10000000
        
    def lons(self):
        lons=MavDatum.objects.filter(message__flight=self, msgField='lon')
        return scipy.array(lons.values_list('value', flat=True))/10000000

    def latLonsFlot(self):
        return ','.join([r'[%.1f,%.1f]' % latLon for latLon in zip(self.lats(), self.lons())])

    @property
    def latLonsJSON(self):
        return scipy.array([self.lons(), self.lats()]).transpose().tolist()
    
    @property
    def gpsTimes(self):
        return MavMessage.objects.filter(flight=self,msgType='GPS_RAW_INT').values_list('timestamp',flat=True)
    
    @property
    def startTime(self):
        if self.mavmessage_set.exists():
            return self.mavmessage_set.order_by('timestamp')[0].timestamp
    
    @property
    def endTime(self):
        if self.mavmessage_set.exists():
            return self.mavmessage_set.order_by('-timestamp')[0].timestamp
    
    @property
    def gpsTimestamps(self):
        return [time.mktime(timestamp.timetuple())*1000 for timestamp in self.gpsTimes]
        
    @property
    def messageTypesRecorded(self):
        return MavDatum.objects.filter(message__flight=self).values_list('message__msgType',flat=True).distinct()
    
    @property
    def messageFieldsRecorded(self):
        return MavDatum.objects.filter(message__flight=self).values('msgField').distinct()
    
    @property
    def length(self):
        return self.endTime - self.startTime
    
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
    
    def get_absolute_url(self):
        return reverse('flights', args=[self.slug])
    
    class Meta:
        ordering = ['slug']

class FlightVideo(models.Model):
    flight=models.ForeignKey('Flight')
    delayVsLogstart=models.DateTimeField(blank=True, null=True)
    onboard=models.BooleanField(blank=True, default=True)
    url=models.URLField(blank=True, null=True)
    videoFile=models.FileField(blank=True, null=True, upload_to='video')

class MavMessage(models.Model):
    msgType=models.CharField(max_length=40, choices=MSG_TYPES)
    timestamp=models.DateTimeField()
    flight=models.ForeignKey('Flight')

    def __unicode__(self):
        return "%s on %s" % (self.msgType, self.timestamp)
    
class MavDatum(models.Model):
    message=models.ForeignKey('MavMessage')
    msgField=models.CharField(max_length=40)
    value=models.FloatField()

    def epoch_timestamp(self):
        return time.mktime(self.message.timestamp.timetuple())*1000

    def __unicode__(self):
        return "%s on %s" % (self.msgField, self.message.timestamp)
    
class Battery(models.Model):
    cells=models.IntegerField(blank=True, null=True)
    capacity=models.IntegerField(blank=True, null=True)
    currentRating=models.IntegerField(blank=True, null=True)
    mfgSerNum=models.CharField(blank=True, null=True,max_length=40)
    persSerNum=models.CharField(max_length=40, primary_key=True)

class Airframe(models.Model):
    mfg=models.CharField(blank=True, null=True, max_length=40)
    partModel=models.CharField(blank=True, null=True, max_length=40)
    mfgSerNum=models.CharField(blank=True, null=True,max_length=40)
    persSerNum=models.CharField(max_length=40)
