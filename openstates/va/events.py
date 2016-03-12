import datetime
import json
import csv
import pytz

from billy.scrape.events import EventScraper, Event

import cStringIO as StringIO

class VAEventScraper(EventScraper):
    jurisdiction = 'va'
    _tz = pytz.timezone('US/Eastern')
    
    def scrape(self, session, chambers):                
        url = 'http://lis.virginia.gov/cgi-bin/legp607.exe?161+n15'
        page = self.get(url).text
        events = csv.reader(StringIO.StringIO(page))
        next(events, None)  # skip the headers
        
        for row in events:
            if 'CANCELLED' in row[2] or 'recessed' in row[2] or 'Adjourned' in row[2]:
                continue
            start_date = row[0].strip()
            start_time = row[1].strip()
            
            #row[2] format is LIS: Meeting Title here; Location; Floor; Room Number
            subject = row[2].split(';', 1)[0].replace('LIS: ','')
            where = row[2].split(';',1)[1]
            when = datetime.datetime.strptime(start_date+' '+start_time, '%m/%d/%y %I:%M %p')

            event = Event(session, when, 'other:meeting',
                              subject, where)
            event.add_source(url)
                    
            self.save_event(event)
                              