from pylab import *
import pandas, cv

logFilePath="/scratch/copterlogs/logs/2012-07-09 10-02 6.log"
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
    logData=pandas.DataFrame(logData['motors_out'],index=logData['timestamp'])
    return(logData)

loadDataFromLog()
