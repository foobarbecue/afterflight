import time, scipy
from django.db import models
from django.contrib.auth.models import User
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
    def gpsTimestamps(self):
        times=MavMessage.objects.filter(flight=self,msgType='GPS_RAW_INT').values_list('timestamp',flat=True)
        return [time.mktime(timestamp.timetuple())*1000 for timestamp in times]
        
    @property
    def messageTypesRecorded(self):
        return MavDatum.objects.filter(message__flight=self).values('message__msgType').distinct()

    def throttleData(self):
        pass
        #return (timestamps, voltages)

    def __unicode__(self):
        return self.slug

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
