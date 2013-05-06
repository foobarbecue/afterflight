from pylab import *
import pandas, cv, os, pdb, shutil

logFilePath="/home/aaron/arducopter/binary/MissionPlanner/logs/2012-07-09 10-02 6.log"
startTime=datetime.datetime(2012,07,9)
logSampleLag={'MOTORS':datetime.timedelta(milliseconds=100)}
#dfFormat is a dict of dataflash log parameters. Values are a list of fields and the logging frequency in milliseconds.
dfFormat={'MOT':motlist=['MOT%s'%x for x in range(1,9)],
         'RAW':['gyro_x','gyro_y','gyro_z','accel_x','accel_y','accel_z'],
         'INAV':['baro_alt','inertial_nav_alt','baro_rate','inertial_nav_alt_rate','accel_corr_x','accel_corr_y','accel_corr_z','inav_accel_corr_z','gps_lat_diff','gps_lon_diff','inav_Lat','inav_lon','inav_lat_vel','inav_lon_vel'],
         'ITERM':[],
         'GPS':['time','sats','lat','lon','sensor_alt','gps_alt','ground_speed','ground_course']}

def loadDataFromLog(logFilePath=logFilePath,dataType='all',startTime=startTime, useGpsTime=True, frame='octa'):
    """
    Reads in a APM Mission Planner .log file, returning it as a pandas DataFrame

    Given the path to a log file produced by the ArduPilotMega Mission Planner,
    returns a :class:`pandas.DataFrame`.

    If argument useGpsTime is True, then the DataFrame will have a time index
    constructed from GPS data. All data that cannot be directly associated with
    a GPS timestamp is discarded. In this case startTime should be midnight GMT
    on the day of the flight, because the logged GPS timestamps only contain
    milliseconds since midnight GMT.

    If useGpsTime is False, timestamps are calculated using the logging frequncies
    as stated at http://code.google.com/p/ardupilot-mega/wiki/Datalogging.

    Either way, the time index starts at argument startTime. If you are using GPS
    timestamps, startTime should be the beginning of the day on which the log was
    collected, because the log data only contains GPS milliseconds since midnight
    GMT.
    """
    if frame=='quad':
      logData={'timestamp':[],'motors_out':np.empty(dtype='int32', shape=(0,4))}
    if frame=='octa':
      logData={'timestamp':[],'motors_out':np.empty(dtype='int32', shape=(0,8))}
    logFile=open(logFilePath,'r')
    timestampIsCurrent=False
    for logLine in logFile:
        if dataType=='all':
            if useGpsTime:
                if logLine.startswith('GPS'):
                    logLine=logLine.split(',')
                    logData['timestamp'].append(datetime.timedelta(milliseconds=int(logLine[1]))+startTime)
                    timestampIsCurrent=True
                elif logLine.startswith('MOT'):
                    if timestampIsCurrent:
                        logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
                        #Throw away data until we get another timestamp (might want to write linear interp in here)
                        timestampIsCurrent=False
                elif logLine.startswith('GPS'):
                    if timestampIsCurrent:
                        logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
                        timestampIsCurrent=False
                elif logLine.startswith('RAW'):
                    if timestampIsCurrent:
                        logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
                        timestampIsCurrent=False
                

            else:
                #We are not using GPS for timing
                if logLine.startswith('MOT'):
                    if len(logData['timestamp'])==0:
                        #first timestamp index should be the startTime argument
                        logData['timestamp'].append(startTime)
                    else:
                        logData['timestamp'].append(logData['timestamp'][-1]+logSampleLag['MOTORS'])
                        logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
           
    logData=pandas.DataFrame(logData['motors_out'],index=logData['timestamp'][0:len(logData['motors_out'])],dtype='int32')
    return(logData)

def plotWithTimeBar(logData, filenumber, timeBarLoc, beginTime=None, endTime=None, outputDir='frames'):
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    hold(True)
    figure(1)
    logData.plot(subplots=False,figsize=(8,2),legend=False)
    if beginTime or endTime:
        xlim(beginTime,endTime)
    axvline(timeBarLoc, linewidth=5)
    #figFileName='/'+'%04d'%filenumber+str(timeBarLoc).replace(' ','_')+'.png'
    figFileName='/'+'%04d'%filenumber+'.png'
    savefig(outputDir+figFileName,transparent=True)
    close('all')
    hold(False)

def plotAllFrames(logData, scrollPlot=True, windowLengthSecs=10):
    filenumber=0
    for timeStamp in logData.index:
        if not scrollPlot:
            plotWithTimeBar(logData, filenumber, timeBarLoc=timeStamp)
            filenumber += 1
        if scrollPlot:
            windowLength=datetime.timedelta(seconds=windowLengthSecs)
            plotWithTimeBar(logData, filenumber, timeBarLoc=timeStamp, beginTime=timeStamp-windowLength, endTime=timeStamp+windowLength)
            filenumber += 1

def basicStats(logFilePath=logFilePath):
    pass

def loadVideo(videoFilePath, videoType, syncinfo):
    pass

def duplicateFrames(directory,numcopies):
    dirlist=os.listdir(directory)
    framenum=0
    for filename in dirlist:
       fileNum=int(filename[0:4])
       for x in range(numcopies):
           shutil.copyfile(filename, '../newFrameRate/%04d.png'%framenum)
           framenum+=1
           
