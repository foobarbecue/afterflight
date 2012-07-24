from pylab import *
import pandas, cv, os

logFilePath="/home/aaron/Mission Planner 1.1.96/logs/2012-07-09 10-02 6.log"
startTime=datetime.datetime(2012,07,9)
def loadDataFromLog(logFilePath=logFilePath,dataType='all',startTime=startTime):
    logData={'timestamp':[],'motors_out':np.empty(dtype='int32', shape=(0,4))}
    logFile=open(logFilePath,'r')
    timestampIsCurrent=False
    for logLine in logFile:
        if dataType=='all':
            if logLine.startswith('GPS'):
                logLine=logLine.split(',')
                logData['timestamp'].append(datetime.timedelta(milliseconds=int(logLine[1]))+startTime)
                timestampIsCurrent=True
            elif logLine.startswith('MOT'):
                if timestampIsCurrent:
                    logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
                    #Throw away data until we get another timestamp
                    timestampIsCurrent=False
    logData=pandas.DataFrame(logData['motors_out'],index=logData['timestamp'],dtype='int32')
    return(logData)

def plotWithTimeBar(logData, filenumber, timeBarLoc, outputDir='frame'):
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    hold(True)
    figure(1)
    logData.plot(subplots=False,figsize=(8,2),legend=False)
    axvline(timeBarLoc)
    savefig(outputDir+'/'+'%04d'%filenumber+str(timeBarLoc)+'.png',transparent=True)
    hold(False)

def plotAllFrames(logData):
    filenumber=0
    for timeStamp in logData.index:
        plotWithTimeBar(logData, filenumber, timeStamp)
        filenumber++

def basicStats(logFilePath=logFilePath):
    pass

