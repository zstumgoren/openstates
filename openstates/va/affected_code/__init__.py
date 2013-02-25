# -*- coding: utf-8 -*-
import re
import lxml.html

from tater.core import parse
from tater.tokentype import Token as t

from . import extractor
from .ast_ import Start
from .tokenize_ import Tokenizer


class Extractor(extractor.Base):
    abbr = 'va'
    tokenizer = Tokenizer()
    # start_node = Start

    def iter_blurbs(self, bill):
        html = self.latest_version_data(bill)
        if '<h4>Sorry, your query could not be processed.</h4>' in html:
            raise extractor.ExtractionError('Got query error from server.')
        doc = lxml.html.fromstring(html)
        blurb = doc.xpath('//div[@id="mainC"]//i')[0].text_content()
        blurb = re.sub(r'\s+', ' ', blurb)
        yield blurb.strip()

    def analyze(self, blurb, bill):
        #blurb = 'A BILL to amend and reenact §§ 6.2-303, 6.2-312, 6.2-1501, 6.2-2107, 59.1-200, and 59.1-203 of the Code of Virginia and to repeal Chapter 18 (§§ 6.2-1800 through 6.2-1829) of Title 6.2 of the Code of Virginia, relating to payday lending.'
        toks = self.tokenizer.tokenize(blurb)
        return parse(Start, iter(toks))

    def get_source_id(self, source):
        return {
            t.Source.VACode: 'code',
            t.SessionLaws.Name: 'session_laws',
            }[source.get_token()]

    def make_url(self, details_dict):
        if details_dict.get('verb') != 'add':
            return 'http://vacode.org/%s/' % details_dict['enum']
