import calendar

def datetime2jsTstamp(datetime):
    return calendar.timegm(datetime.timetuple())*1000