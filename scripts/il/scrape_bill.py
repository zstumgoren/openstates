'''Targeted scrape of one or more IL bill

USAGE:

    Provide the bill ID/session
    (see the "metadata" dictionary in openstates/il/__init__.py 
    for a valid list session names)

    $ python scrape_bill.py HB2822/99th

'''
import re
import sys
import urlparse

from openstates.utils import mkdir_p
from openstates.il import metadata, ILBillScraper


class ILSoloBillScraper(object):

    def __init__(self, bill_ids=[]):
        self.bill_ids = bill_ids
        self.output_dir = 'data/il/'
        mkdir_p(self.output_dir)
        self.bill_urls = {}
        self.scraper = ILBillScraper(metadata, output_dir=self.output_dir)

    def run(self):
        target_bills = [self._parse_bill_info(bill_id) for bill_id in self.bill_ids]
        for bill_data in target_bills:
            chamber = bill_data['chamber']
            session = bill_data['session_id']
            doc_type_id  = bill_data['doc_type_id']
            doc_num = bill_data['doc_num']
            bill_url = self.get_bill_url(chamber, session, doc_type_id, doc_num)
            self.scraper.scrape_bill(chamber, session, doc_type_id, bill_url)

    def _parse_bill_info(self, bill_info):
        doc_type_id, doc_num, session = re.match(r'([A-Z]+)(\d+)/(.+)', bill_info).groups()
        return {
            'chamber': 'House' if doc_type_id.startswith('H') else 'Senate',
            'session_id': session.strip(),
            'doc_type_id': doc_type_id,
            'doc_num': doc_num,
        }

    def get_bill_url(self, chamber, session, doc_type_id, doc_num):
        key = (chamber, session, doc_type_id, doc_num)
        try:
            return self.bill_urls[key]
        except KeyError:
            self._build_url_lookup(chamber, session, doc_type_id)
            try:
                return self.bill_urls[key]
            except KeyError:
                print("No bills found for chamber ({}), session ({}), bill {}{}".format(key))

    def _build_url_lookup(self, chamber, session, doc_type):
        for bill_url in self.scraper.get_bill_urls(chamber, session, doc_type):
            parsed_url = urlparse.urlparse(bill_url)
            get_params = dict(urlparse.parse_qsl(parsed_url.query))
            key = (chamber, session, doc_type, get_params['DocNum'])
            self.bill_urls[key] = bill_url

def main():
    try:
        bill_ids = [bill_id.strip() for bill_id in sys.argv[1:]]
    except IndexError:
        msg = "\nERROR: You must supply one or more bill ID with session! Example:\n\n\tpython {} HB2822/99th\n".format(__file__)
        sys.exit(msg)
    scraper = ILSoloBillScraper(bill_ids)
    scraper.run()

if __name__ == '__main__':
    main()
