import datetime
import lxml
import pytz

from billy.scrape.events import EventScraper, Event


class NCEventScraper(EventScraper):
    jurisdiction = 'nc'
    _tz = pytz.timezone('US/Eastern')

    def scrape(self, session, chambers):
        url = 'http://www.ncleg.net/LegislativeCalendar/'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        date_format = '%a, %B %d, %Y %I:%M %p'

        for td in doc.xpath('//td[@colspan="3"]'):
            start_day = td.text_content().strip()

            for tr in td.getparent().itersiblings():
                #print tr.text_content().replace("\n",'')
                if tr.xpath('count(.//td)') == 3:
                    tds = tr.xpath('.//td')

                    start_time = tds[0].text_content().strip()
                    start_time = start_time.replace(u'\xa0', ' ').replace(u'\xc2', '')
                    subject = tds[1].text_content().strip()
                    where = tds[2].text_content().strip()

                    if 'Convenes' not in subject:
                        when = datetime.datetime.strptime(start_day+' '+start_time, date_format)

                        meeting_type = 'committee:meeting'
                        
                        event = Event(session, when, meeting_type,
                                      subject, where)
                                      
                        if tds[1].xpath('count(.//a)') > 0:
                            com_url = tds[1].xpath('.//a')[0].attrib['href']
                            com_html = self.get(com_url).text
                            com_doc = lxml.html.fromstring(com_html)
                            com_title = com_doc.xpath('//div[@id="title"]')[0].text_content().strip()
                            com_type = com_doc.xpath('//div[@class="titleSub"]')[0].text_content().strip()
                            
                            print com_type
                            
                            chambers = {
                                "house" : "lower",
                                "joint" : "joint",
                                "senate" : "upper",
                                "non-standing": "other"
                            }

                            com_chamber = "other"
                            for key in chambers:
                                if key in com_type.lower():
                                    com_chamber = chambers[key]
                            
                            if 'Joint' in com_title:
                                com_chamber = 'joint'
                                
                            event.add_participant('host', com_title, 'committee',
                                              chamber=com_chamber)
                                              
                        event.add_source(url)
                        self.save_event(event)
                else:
                    break
