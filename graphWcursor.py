from pylab import *
import pandas, cv, os

logFilePath="/home/aaron/Mission Planner 1.1.96/logs/2012-07-09 10-02 6.log"
start_time=datetime.datetime(2012,07,9)
def loadDataFromLog(logFilePath=logFilePath,dataType='all',start_time=start_time):
    logData={'timestamp':[],'motors_out':np.empty(dtype='int32', shape=(0,4))}
    logFile=open(logFilePath,'r')
    timestampIsCurrent=False
    for logLine in logFile:
        if dataType=='all':
            if logLine.startswith('GPS'):
                logLine=logLine.split(',')
                logData['timestamp'].append(datetime.timedelta(milliseconds=int(logLine[1]))+start_time)
                timestampIsCurrent=True
            elif logLine.startswith('MOT'):
                if timestampIsCurrent:
                    logData['motors_out']=vstack((logData['motors_out'],logLine.split(',')[1:]))
                    #Throw away data until we get another timestamp
                    timestampIsCurrent=False
    logData=pandas.DataFrame(logData['motors_out'],index=logData['timestamp'],dtype='int32')
    return(logData)

def plotWithTimeBar(logData, timeBarLoc, outputDir='frame'):
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    hold(True)
    figure(1,figsize=(800,200),dpi=100,bbox_inches=0)
    logData.plot(subplots=False)
    axvline(timeBarLoc)
    savefig(outputDir+'/'+str(timeBarLoc)+'.png',transparent=True)
    hold(False)

def plotAllFrames(logData):
    for timeStamp in logData.index:
        plotWithTimeBar(logData, timeStamp)

def basicStats(logFilePath=logFilePath):
    pass
    
