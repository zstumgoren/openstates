# -*- coding: utf-8 -*-
'''This stuff is the base scraping code that would (theoretically)
wind up in billy or some other common location.
'''
import os
import logging
import collections

import scrapelib

from tater.core import parse
from tater.tokentype import Token as t
from tater.visit import VisitorBase


from .utils import CachedAttr


class ExtractionError(Exception):
    'Raise if we need to bail.'


class Extractor(object):
    '''The base class for state Extractor instances.
    It's hard-coded to be in fast mode for now.
    '''

    _request_defaults = {

        # scrapelib settings
        'cache_obj': scrapelib.FileCache('cache'),
        'cache_write_only': False,
        'use_cache_first': True,
        'requests_per_minute': 0,

        # requests settings
        'timeout': 5.0,
        'follow_robots': False,
    }

    @CachedAttr
    def datadir(self):
        DATA = os.path.join('data', self.abbr, 'billtext')
        try:
            os.makedirs(DATA)
        except OSError:
            pass
        return DATA

    @CachedAttr
    def logger(self):
        return logging.getLogger('billy.%s.affected_code' % self.abbr)

    @CachedAttr
    def session(self):
        '''The requests session.
        '''
        defaults = self._request_defaults
        defaults.update(getattr(self, 'request_defaults', {}))
        return scrapelib.Scraper(**defaults)

    def iter_blurbs(self, bill):
        '''Subclasses define a generator function that returns
        blurbs to be analyzed for affected code citations.'''
        raise NotImplemented

    def latest_version_data(self, bill):
        '''Get the full text of the latest version.
        '''
        try:
            url = bill['versions'][-1]['url']
        except IndexError:
            msg = 'Bill {bill_id} has no versions!'
            raise ExtractionError(msg.format(**bill))
        self.logger.info('GET - %r' % url)
        data = self.session.get(url).text
        return data

    def iter_graphs(self, bill):
        '''Iterate over the impact clauses found in the bill_id
        and parse each one into an AST.
        '''
        for impact in self.iter_blurbs(bill):
            yield Graph(self.analyze(impact, bill), extractor=self)

    def serializable(self, bill):
        '''Get serializable data for each graph and combine
        them into a single serializable.
        '''
        data = None
        seen_details = []
        for graph in self.iter_graphs(bill):
            if data is None:
                data = graph.serializable()

                # Add the details to the complete details list.
                for details in data['details']:
                    if details not in seen_details:
                        seen_details.append(details)

            else:
                more_data = graph.serializable()

                # Combine their verbs.
                data['verbs'] |= more_data['verbs']

                # Combine their enum_sets.
                for key, enum_set in more_data.items():
                    data['enumerations'][key] |= enum_set

                # Combine the details dicts.
                for details in more_data['details']:
                    if details not in seen_details:
                        seen_details.append(details)

        # Replace non-serializable data types.
        data['enumerations'] = dict(
            (k, list(v)) for (k, v) in data['enumerations'].items())
        data['verbs'] = list(data['verbs'])
        data['details'] = seen_details

        # attected_code is None if there are no values.
        if not all(data.values()):
            return
        return data

    def analyze(self, blurb, bill):
        toks = self.lexer.tokenize(blurb)
        return parse(self.start_node, iter(toks))


class Graph(object):
    '''Provide methods for parse tree/graph obtained
    from Extractor.iter_graphs.'''

    def __init__(self, graph, extractor):
        self.graph = graph
        self.extractor = extractor

    def serializable(self):
        '''Return a JSON-serializable structure that can be
        added to the top-level bill document in mongo.

        Example for:

        A BILL to amend and reenact § 4.1-100, of the Code of Virginia;
        to amend the Code of Virginia by adding a section numbered
        11-16.1; and to amend the Code of Virginia by adding in
        Title 59.1 a chapter numbered 50, relating to cats.

        imapct = {

            # These two keys enable indexing and querying.
            'enumerations': {
                'sections': ['4.1-100', '11-16.1'],
                'titles': ['59.1'],
                'chapters': ['50']
                }
            'verbs': {
                'amend': ['4.1-100', '11-16.1', '59.1'],
                'add': ['50'],
                }

            # And this key contains the deets.
            'details': [{'enum': '4.1-100'],
                         'division': 'section',
                         'verb': 'amend',
                         'source_id': 'code'},

                        {'enum': '11-16.1'],
                         'division': 'section',
                         'verb': 'amend',
                         'source_id': 'code'},

                        {'enum': '50',
                         'division': 'chapter',
                         'supernodes': [{
                            'enum': '59.1',
                            'division': 'title'}]
                         'verb': 'add',
                         'source_id': 'code'}]
        }
        '''
        visitor = NodeVisitor(self.extractor)
        visitor.visit(self.graph)
        data = visitor.data
        return data


def get_supernodes(node):
    '''Return the supernodes of a node as a list like:
    [['title', '4'], ['chapter', 'I']]
    '''
    path = []
    segment = []

    # Burn the parent if this node is an enumeration.
    if node.first_token() == t.Enumeration:
        node = node.parent

    while True:
        node = node.parent
        tok = node.first_token()
        if tok is t.Enumeration:
            if segment:
                path.append(segment[::-1])
                segment = []
            segment.append(node.first_text().rstrip('s'))
        elif tok is t.Division:
            segment.append(node.first_text())
        else:
            break
    if segment:
        path.append(segment[::-1])

    return path[::-1]


class NodeVisitor(VisitorBase):
    '''Visits the graph and emits serializable data.
    '''
    def __init__(self, extractor):
        VisitorBase.__init__(self)

        # Keep a reference to the extractor so we can
        # access its helper functions.
        self.extractor = extractor

        # The final data structure.
        self.data = {
            'enumerations': collections.defaultdict(set),
            'verbs': set(),
            'details': []}

    def visit_Source(self, node):
        # Usually, source_id will be 'code'
        node.context['source_id'] = self.extractor.get_source_id(node)

        # But when it's a session law, also add the year.
        for _, tok, text in node.items:
            if tok is t.SessionLaws.Year:
                node.context['session_law_year'] = text

    def visit_Amend(self, node):
        '''Set the verb on the node's context--also add it
        to this bill's verbs set for mongo queryability.
        '''
        node.context['verb'] = 'amend'
        self.data['verbs'].add('amend')

    def visit_Division(self, node):
        first_token = node.first_token()
        if first_token == t.SecSymbol:
            name = 'section'
            node.context['name'] = 'section'
        elif first_token == t.Division:
            name = node.first_text().rstrip('s')
            node.context['name'] = name

    def visit_Enumeration(self, node):
        # Add the enumeration to the top-level enumerations
        # defaultdict so we can query them easily in mongo.
        enum = node.first_text()
        self.data['enumerations'][node.context['name']].add(enum)

        # Also add it to the node's context.
        node.context['enum'] = enum

        # If this is a terminal node, add it to the details list.
        if not node.children:
            self.finalize_details_dict(node)

    def visit_Add(self, node):
        node.context['verb'] = 'add'
        self.data['verbs'].add('add')

    def visit_Repeal(self, node):
        node.context['verb'] = 'repeal'
        self.data['verbs'].add('repeal')

    def finalize_details_dict(self, node):
        '''Get the current state and create a details dict
        to add to the graph's main serializable data structure.
        '''
        details = dict(node.context.items())
        supernodes = get_supernodes(node)
        if supernodes:
            details['supernodes'] = supernodes
        if details.get('verb') != 'add':
            details['url'] = self.extractor.make_url(details)
        self.data['details'].append(details)
