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

import calendar, datetime, re, scipy

def dt2jsts(mdatetime):
    """
    Given a python datetime, convert to javascript timestamp format (milliseconds since Jan 1 1970).
    Do so with microsecond precision, and without adding any timezone offset.
    """
    return calendar.timegm(mdatetime.timetuple())*1e3+mdatetime.microsecond/1e3

def logpath2dt(filepath):
    """
    given a dataflashlog in the format produced by Mission Planner,
    return a datetime which says when the file was downloaded from the APM
    """
    return datetime.datetime.strptime(re.match(r'.*/(.*) .*$',filepath).groups()[0],'%Y-%m-%d %H-%M')

class UTC(datetime.tzinfo):
    """
    No timezones are provided in python stdlib (gaargh) so we have to make one here
    """

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)
utc=UTC()

def cross(series, cross=0, direction='cross'):
    """
    From http://stackoverflow.com/questions/10475488/calculating-crossing-intercept-points-of-a-series-or-dataframe

    Given a Series returns all the index values where the data values equal 
    the 'cross' value. 

    Direction can be 'rising' (for rising edge), 'falling' (for only falling 
    edge), or 'cross' for both edges
    """
    # Find if values are above or bellow yvalue crossing:
    above=series.values > cross
    below=scipy.logical_not(above)
    left_shifted_above = above[1:]
    left_shifted_below = below[1:]
    x_crossings = []
    # Find indexes on left side of crossing point
    if direction == 'rising':
        idxs = (left_shifted_above & below[0:-1]).nonzero()[0]
    elif direction == 'falling':
        idxs = (left_shifted_below & above[0:-1]).nonzero()[0]
    else:
        rising = left_shifted_above & below[0:-1]
        falling = left_shifted_below & above[0:-1]
        idxs = (rising | falling).nonzero()[0]

    # Calculate x crossings with interpolation using formula for a line:
    x1 = series.index.values[idxs]
    x2 = series.index.values[idxs+1]
    y1 = series.values[idxs]
    y2 = series.values[idxs+1]
    x_crossings = (cross-y1)*(x2-x1)/(y2-y1) + x1

    return x_crossings
