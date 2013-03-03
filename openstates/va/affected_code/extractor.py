# -*- coding: utf-8 -*-
import re
import lxml.html

from tater.tokentype import Token as t

from . import base
from .ast_ import Start
from .lexer import Lexer


class Extractor(base.Extractor):
    '''This class is responsible for provider a lexer
    instance, a start node, the state's abbreviation, and
    helpers to extract blurbs from the bill, convert tokenizer
    source tokens to strings to be used as dictionary keys,
    and making urls to the relevant laws website.
    '''
    abbr = 'va'
    lexer = Lexer()
    start_node = Start

    def iter_blurbs(self, bill):
        '''A a generator function yeilding impact phrases from
        the bill like "Section 123 is amended by blah blah:"
        '''
        html = self.latest_version_data(bill)
        if '<h4>Sorry, your query could not be processed.</h4>' in html:
            raise base.ExtractionError('Got query error from server.')
        doc = lxml.html.fromstring(html)
        blurb = doc.xpath('//div[@id="mainC"]//i')[0].text_content()
        blurb = re.sub(r'\s+', ' ', blurb)
        yield blurb.strip()

    def get_source_id(self, source):
        '''Given the token for a particular source, convert it
        to the string used for the source_id key in the details
        dictionary being stored in mongo.
        '''
        return {
            t.Source.VACode: 'code',
            t.SessionLaws.Name: 'session_laws',
        }[source.get_token()]

    def make_url(self, details_dict):
        '''Given a details_dict, return a url to the resource.
        '''
        return 'http://vacode.org/%s/' % details_dict['enum']
