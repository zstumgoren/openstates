import datetime
import json
import re
import sys

import lxml.etree
from lxml.etree import tostring

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin

#Amendment
_scrapable_types = ['Bill','Bill&Amend']

_action_pairs = [
    ('ctl00_ContentPlaceHolder_DateIntroLabel','Introduced','bill:introduced'),
    ('ctl00_ContentPlaceHolder_DateRecLabel','Received','bill:filed'),
    ('ctl00_ContentPlaceHolder_DateAssignLabel','Assigned','other'),
    ('ctl00_ContentPlaceHolder_DateToSenLabel','Sent to Senator','other'),
    ('ctl00_ContentPlaceHolder_DateToGovLabel','Sent to Governor','governor:received'),
    ('ctl00_ContentPlaceHolder_DateAppGovLabel','Signed by Governor','governor:signed'),
    ('ctl00_ContentPlaceHolder_DateVetoedLabel','Vetoed','governor:vetoed'),
    ('ctl00_ContentPlaceHolder_DateOverLabel','Governor Veto Overriden','bill:veto_override:passed'),    
]

class VIBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'vi'
    session = ''

    def scrape(self, session, chambers):
        self.session = session
        
        #First we get the Form to get our ASP viewstate variables
        search_url = 'http://www.legvi.org/vilegsearch/default.aspx'
        doc = lxml.html.fromstring(self.get(url=search_url).text)
        
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath(
            '//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation, ) = doc.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        (previouspage, ) = doc.xpath('//input[@id="__PREVIOUSPAGE"]/@value')

        form = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__PREVIOUSPAGE': previouspage,
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder$leginum',
            'ctl00$ContentPlaceHolder$leginum': session,
            'ctl00$ContentPlaceHolder$sponsor': '',
            'ctl00$ContentPlaceHolder$billnumber': '',
            'ctl00$ContentPlaceHolder$actnumber': '',
            'ctl00$ContentPlaceHolder$subject': '',
            'ctl00$ContentPlaceHolder$BRNumber': '',
            'ctl00$ContentPlaceHolder$ResolutionNumber': '',
            'ctl00$ContentPlaceHolder$AmendmentNumber': '',
            'ctl00$ContentPlaceHolder$GovernorsNumber': '',
        }
                
        #Then we post the to the search form once to set our ASP viewstate
        form = self.post(url=search_url, data=form, allow_redirects=True)        
        doc = lxml.html.fromstring(form.text)
        
        (viewstate, ) = doc.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator, ) = doc.xpath(
            '//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation, ) = doc.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        (previouspage, ) = doc.xpath('//input[@id="__PREVIOUSPAGE"]/@value')

        form = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__PREVIOUSPAGE': previouspage,
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder$leginum',
            'ctl00$ContentPlaceHolder$leginum': session,
            'ctl00$ContentPlaceHolder$sponsor': '',
            'ctl00$ContentPlaceHolder$billnumber': '',
            'ctl00$ContentPlaceHolder$actnumber': '',
            'ctl00$ContentPlaceHolder$subject': '',
            'ctl00$ContentPlaceHolder$BRNumber': '',
            'ctl00$ContentPlaceHolder$ResolutionNumber': '',
            'ctl00$ContentPlaceHolder$AmendmentNumber': '',
            'ctl00$ContentPlaceHolder$GovernorsNumber': '',
        }
        #Then we submit to the results url to actually get the bill list
        results_url = 'http://www.legvi.org/vilegsearch/Results.aspx'
        bills_list = self.post(url=results_url, data=form, allow_redirects=True)        
        bills_list = lxml.html.fromstring(bills_list.text)

        bills_list.make_links_absolute('http://www.legvi.org/vilegsearch/');
        bills = bills_list.xpath('//table[@id="ctl00_ContentPlaceHolder_BillsDataGrid"]/tr')
        
        for bill_row in bills[1:]:
            (bill_type,) = bill_row.xpath('./td[6]/font/text()')
            
            if bill_type in _scrapable_types:
                (landing_page,) = bill_row.xpath('.//td/font/a/@href')
                self.scrape_bill(landing_page)
    
    def scrape_bill(self, bill_page_url):
        bill_page = lxml.html.fromstring(self.get(bill_page_url).text)
        
        title = bill_page.xpath('//span[@id="ctl00_ContentPlaceHolder_SubjectLabel"]/text()')
        if title:
            title = title[0]
        else:
            self.warning('Missing bill title {}'.format(bill_page_url))    
        
        bill_no = bill_page.xpath('//span[@id="ctl00_ContentPlaceHolder_BillNumberLabel"]/a/text()')
        if bill_no:
            print bill_no[0]
        else:
            self.error('Missing bill number {}'.format(bill_page_url))
                
        bill = Bill(
            session=self.session,
            chamber='upper',
            bill_id=bill_no,
            title=title,
            type='bill'
        )
                
        sponsors = bill_page.xpath('//span[@id="ctl00_ContentPlaceHolder_SponsorsLabel"]/text()')
        if sponsors:
            self.assign_sponsors(bill, sponsors[0], 'primary')

        cosponsors = bill_page.xpath('//span[@id="ctl00_ContentPlaceHolder_CoSponsorsLabel"]/text()')
        if cosponsors:
            self.assign_sponsors(bill, cosponsors[0], 'cosponsor')

        #introduced = bill_page.xpath('//span[@id="ctl00_ContentPlaceHolder_DateIntroLabel"]/text()')
        #if introduced:
        #    bill.add_action(actor='upper',
        #                    action='Introduced',
        #                    date=self.parse_date(introduced[0]),
        #                    type="bill:introduced")

        self.parse_date_actions(bill, bill_page)

        self.save_bill(bill)
        
    def clean_names(self, name_str):
        #Clean up the names a bit to allow for comma splitting
        name_str = re.sub(", Jr", " Jr.", name_str, flags=re.I)
        name_str = re.sub(", Sr", " Sr.", name_str, flags=re.I)
        return name_str
    
    def assign_sponsors(self, bill, sponsors, sponsor_type):
        sponsors = self.clean_names(sponsors)
        sponsors = sponsors.split(',')
        for sponsor in sponsors:
            bill.add_sponsor(type=sponsor_type, name=sponsor.strip())
            
    def parse_date_actions(self, bill, bill_page):
        # There's a set of dates on the bill page denoting specific actions
        # These are mapped in _action_pairs above
        for pair in _action_pairs:
            action_date = bill_page.xpath('//span[@id="{}"]/text()'.format(pair[0]))
            if action_date:
                bill.add_action(actor='upper',
                                action=pair[1],
                                date=self.parse_date(action_date[0]),
                                type=pair[2])
    
    def parse_date(self, date_str):
        return datetime.datetime.strptime(date_str, '%m/%d/%Y').date()
                                