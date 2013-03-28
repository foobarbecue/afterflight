import calendar

def dt2jsts(datetime):
    """
    Given a python datetime, convert to javascript timestamp format (milliseconds since Jan 1 1970).
    Do so with microsecond precision, and without adding any timezone offset.
    """
    return calendar.timegm(datetime.timetuple())*1e3+datetime.microsecond/1e3