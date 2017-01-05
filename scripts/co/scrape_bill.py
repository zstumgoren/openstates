'''Targeted scrape of one or more CO bills

USAGE:

    $ python scrape_bill.py HB16-1359

'''
import re
import sys
import itertools

from openstates.utils import mkdir_p
from openstates.co import COBillScraper, metadata, session_list


class COSoloBillScraper(object):

    def __init__(self, bill_ids=[]):
        self.bill_ids = bill_ids
        self.output_dir = 'data/co/'
        mkdir_p(self.output_dir)
        self.scraper = COBillScraper(metadata, output_dir=self.output_dir)

    def run(self):
        target_bills = [self._parse_bill_id(bill_id) for bill_id in self.bill_ids]
        self._build_raw_bill_lookup(target_bills)
        for bill_data in target_bills:
            bill_id = bill_data['id']
            chamber = bill_data['chamber']
            upper_lower = {"Senate": "upper", "House": "lower"}[chamber]
            # Below data has some extra bits that are also needed...
            data = self._bill_sheet_row_lkup[bill_id]
            self.scraper.process_bill_sheet_row(data['row'], data['session'], chamber, upper_lower, data['url'])

    def _parse_bill_id(self, bill_id):
        bill_type, session_year, bill_num = re.match(r'([A-Z]{2,3})(\d{2})-(.+)', bill_id).groups()
        return {
            'id': bill_id,
            'chamber': 'House' if bill_type.startswith('H') else 'Senate',
            'session_year': session_year,
            'bill_num': bill_num.strip()
        }

    def _build_raw_bill_lookup(self, bills):
        pairs = self._get_session_chamber_pairs(bills)
        index_page_meta = self._get_index_page_meta(pairs)
        #self._raw_pages_lkup = {}
        self._bill_sheet_row_lkup = {}
        for session, chamber, sheet_url in index_page_meta:
            raw_index_page_rows = self.scraper.get_bill_sheet_rows(session, chamber)[1]
            #self._raw_pages_lkup[(session, chamber)] = raw_index_page_rows
            for row in raw_index_page_rows:
                # if it has a bill id, store it
                try:
                    # bill id, if it exists, is in first column and may have a .pdf file extension
                    bill_id = row.text_content().split('\n')[0].split('.')[0]
                    if bill_id:
                        self._bill_sheet_row_lkup[bill_id] = { 'row': row, 'url': sheet_url, 'session': session }
                except TypeError:
                    continue

    def _get_session_chamber_pairs(self, bill_data):
        '''
        Get all target pairings of session and chamber

        NOTE: Leg. term has multiple sessions spanning multiple years
        and each combo has its own bill index page.
        '''
        payload = []
        for bill in bill_data:
            chamber = bill['chamber']
            session_year = bill['session_year']
            for term in self.scraper.metadata['terms']:
                if session_year in term['name']:
                    # Pairs of chambers/sessions e.g. (House, 2016A)
                    pairings = [chamber_session_pair for chamber_session_pair in itertools.product([chamber], term['sessions'])]
                    payload.extend(pairings)
                    break
        return payload

    def _get_index_page_meta(self, session_chamber_pairs):
        index_page_urls = []
        for chamber, session in session_chamber_pairs:
            url = self.scraper.get_bill_folder(session, chamber)
            index_page_urls.append((session, chamber, url))
        return index_page_urls

def main():
    try:
        bill_ids = [bill_id.strip() for bill_id in sys.argv[1:]]
    except IndexError:
        msg = "\nERROR: You must supply one or more bill ids! Example:\n\n\tpython {} HB16-1359\n".format(__file__)
        sys.exit(msg)
    scraper = COSoloBillScraper(bill_ids)
    scraper.run()

if __name__ == '__main__':
    main()
