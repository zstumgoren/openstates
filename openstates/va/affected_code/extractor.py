import os
import logging

import scrapelib

from .utils import CachedAttr


class Base(object):
    'I need to think up better names for things than "Extractor"'

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
        defaults = self._request_defaults
        defaults.update(getattr(self, 'request_defaults', {}))
        return scrapelib.Scraper(**defaults)

    def iter_blurbs(self, bill):
        '''Subclasses define a generator function that returns
        blurbs to be analyzed for affected code citations.'''
        raise NotImplemented

    def latest_version_data(self, bill):
        url = bill['versions'][-1]['url']
        self.logger.info('GET - %r' % url)
        data = self.session.get(url).text
        return data

    def get_graph(self, bill):
        for impact in self.iter_blurbs(bill):
            analyzed = self.analyze(impact)



