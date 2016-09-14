import re
import pytz
import datetime
import json
import lxml.html

from billy.scrape.events import EventScraper, Event

class NVEventsScraper(EventScraper):
    jurisdiction = 'nv'
    _tz = pytz.timezone('US/Pacific')

    def scrape(self, chamber, session):
        chambers_url = 'https://www.leg.state.nv.us/App/NELIS/REL/78th2015/NavTree/GetCommitteeHierarchy?itemKey=47&_=1473861333363'
        
        chamber_name = 'Senate' if chamber == 'upper' else 'Assembly'
        
        chambers_json = self.get(chambers_url).text
        chambers_json = json.loads(chambers_json)
        
        for item in chambers_json:
            if item['text'] == chamber_name:
                chamber_id = item['Id']
       
        if not item['Id']:
            print "OOPS"
           
        chamber_url = 'https://www.leg.state.nv.us/App/NELIS/REL/78th2015/NavTree/GetCommitteeHierarchy?itemKey=47&id=%s&_=1473861333364' % chamber_id
        
        chamber_json = self.get(chamber_url).text
        chamber_json = json.loads(chamber_json)
        
        print json.dumps(chamber_json)
        
        for item in chamber_json:
            self.scrape_event(item)
        
        
    def scrape_event(self, item):
        event_url = 'https://www.leg.state.nv.us/App/NELIS/REL/78th2015/Committee/FillSelectedCommitteeTab?selectedTab=Meetings&committeeOrSubCommitteeKey=%s&_=1473861333365' % item['Id']
        
        event_page = self.get(event_url).text
        event_page = lxml.html.fromstring(event_page)
        
        #NV returns a list of events per committee as one big HTML fragment
        
        event_seperators = event_page.xpath('//div[@class="gradient-hr"]')
        
        for i, node in enumerate(event_seperators):
            print i
            i = i + 1
            #/*/p[count(preceding-sibling::divider)=1]
            for event_fragment in event_page.xpath('//div[@class="gradient-hr"][%d]/preceding-sibling::div[contains(@class, "top-padding-xs") and count(preceding-sibling::div[@class="gradient-hr"])=1]' % i):
                print event_fragment