import re
import itertools
import collections
from datetime import datetime

import lxml.html
import lxml.etree

from billy.scrape.bills import BillScraper, Bill
import billy.utils


# Utils----------------------------------------------------------
class Cached(object):
    '''Computes attribute value and caches it in instance.

    Example:
        class MyClass(object):
            def myMethod(self):
                # ...
            myMethod = Cached(myMethod)
    Use "del inst.myMethod" to clear cache.
    http://code.activestate.com/recipes/276643/
    '''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result


class UrlData(object):
    '''Given a url, its nickname, and a scraper instance,
    provide the parsed lxml doc, the raw html, and the url
    '''
    def __init__(self, name, url, scraper, urls_object):
        '''urls_object is a reference back to the Urls container.
        '''
        self.url = url
        self.name = name
        self.scraper = scraper
        self.urls_object = urls_object

    def __repr__(self):
        return 'UrlData(url=%r)' % self.url

    def __iter__(self):
        for key in dict.__getattr__(self, 'keys')():
            if key not in ('_scraper', '_urls'):
                yield key

    @Cached
    def text(self):
        text = self.scraper.urlopen(self.url)
        self.urls_object.validate(self.name, self.url, text)
        return text

    @Cached
    def resp(self):
        '''Return the decoded html or xml or whatever. sometimes
        necessary for a quick "if 'page not found' in html:..."
        '''
        return self.text.response

    @Cached
    def doc(self):
        '''Return the page's lxml doc.
        '''
        doc = lxml.html.fromstring(self.text)
        doc.make_links_absolute(self.url)
        return doc

    @Cached
    def etree(self):
        '''Return the documents element tree.
        '''
        return lxml.etree.fromstring(self.text)


class UrlsMeta(type):
    '''This metaclass aggregates the validator functions marked
    using the Urls.validate decorator.
    '''
    def __new__(meta, name, bases, attrs):
        validators = collections.defaultdict(set)
        for attr in attrs.values():
            if hasattr(attr, 'validates'):
                validators[attr.validates].add(attr)
        attrs['_validators'] = validators
        cls = type.__new__(meta, name, bases, attrs)
        return cls


class Urls(object):
    '''Contains urls we need to fetch during this scrape.
    '''
    __metaclass__ = UrlsMeta

    def __init__(self, urls, scraper):
        '''Sets a UrlData object on the instance for each named url given.
        '''
        self.urls = urls
        self.scraper = scraper
        for url_name, url in urls.items():
            url = UrlData(url_name, url, scraper, urls_object=self)
            setattr(self, url_name, url)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.urls)

    def __iter__(self):
        '''A generator of this object's UrlData members.
        '''
        for url_name in self.urls:
            yield getattr(self, url_name)

    @staticmethod
    def validates(url_name, retry=False):
        '''A decorator to mark validator functions for use on a particular
        named url. Use like so:

        @Urls.validates('history')
        def must_have_actions(self, url, text):
            'Skip bill that hasn't been introduced yet.'
            if 'no actions yet' in text:
                raise Skip('Bill had no actions yet.')
        '''
        def decorator(method):
            method.validates = url_name
            method.retry = retry
            return method
        return decorator

    def validate(self, url_name, url, text):
        '''Run each validator function for the named url and its text.
        '''
        for validator in self._validators[url_name]:
            try:
                validator(self, url, text)
            except Exception as e:
                if validator.retry:
                    validator(self, url, text)
                else:
                    raise e


# Base classes.
# ---------------------
class Skip(Exception):
    '''An error bill scrapers can raise when it's time to
    skip a fubar'd bill.
    '''


class TimespanScraper(object):
    '''The time scraper is a timespan-specific scraper that
    will be used for its declared sessions.
    '''
    def __init__(self, chamber, session, scraper):
        self.scraper = scraper
        self.chamber = chamber
        self.session = session

    @property
    def meta(self):
        return billy.utils.metadata(self.jurisdiction)

    def scrape_session(self):
        '''Scrape all bills for the session.
        '''
        self.skipped = 0
        for bill_id, kwargs in self.generate_ids():
            try:
                saveable = self.scrape_bill(bill_id, **(kwargs or {}))
            except Skip as exc:
                self.scraper.warning('skipping %s: %r' % (bill_id, exc))
                self.skipped += 1
                continue
            self.scraper.save_bill(saveable)

    def scrape_bill(self, bill_id, **kwargs):
        '''Scrape one bill.
        '''
        urls = self.make_urls(bill_id)

        if 'urls_dict' not in kwargs:
            # If kwargs contains no urls, generate them.
            kwargs['urls_dict'] = urls
        else:
            # Otherwise add the make_urls to the urls_dict.
            urls.update(kwargs['urls_dict'])
            kwargs['urls_dict'] = urls

        bill = self.bill_context(bill_id, context=self, **kwargs)
        data = bill.saveable()
        return data

    def generate_ids(self):
        '''A generator of bill_id strings. This could also be
        broken down further to allow us to scrape only bills with
        a certain prefix, like resolutions as opposed to bills.
        That's something I would use.
        '''
        raise NotImplemented

        # For example:
        for prefix in ['HB', 'SB']:
            for number in itertools.count(1):
                bill_id = prefix + str(number)
                yield bill_id, dict(title='And act to amend cows')

    def scrape(self):
        '''This method is just here to provide compatibility
        with billy-update. But this (or something similar) would
        be where we put logic that dictates what bills will get
        scraped. Some possibilities:

        For example, maybe it would inspect the command line options,
        etc:

        - scrape a single bill
        - scrape all bills for a session
        - scrape all bills with prefix "XYZ" for session
        '''
        self.scrape_session()

    def make_urls(self, bill_id):
        '''Given a bill_id, return a dict of (name, url) items.
        '''
        raise NotImplemented

        # For example:
        tmpl = 'http://pault.ag/bill?session=%s&id=%s'
        return dict(detail=tmpl % (self.session, bill_id))


class BillContext(object):
    '''A class to maintain the state of a single bill scrape. It has
    references to the scraper, the bill object under construction,
    the session context, shortcuts for accessing urls and their lxml
    docs, etc.
    '''
    def __init__(self, bill_id, context, **kwargs):
        '''
        context: The Term188 TimespanScraper instance defined above.
        '''
        self.bill_id = bill_id
        self.context = context
        self.urls_dict = kwargs.get('urls_dict') or {}
        self.bill = Bill(context.session, context.chamber, bill_id,
            title=kwargs.get('title'))

        # More aliases for convience later:
        self.scraper = context.scraper

    @Cached
    def urls(self):
        return self.urls_class(self.urls_dict, scraper=self.scraper)

    def add_sources_from_urls(self):
        for urldata in self.urls:
            self.bill.add_source(urldata.url)

    @property
    def doc(self):
        '''A shortcut to the main lxml doc for this bill.
        '''
        return self.urls.detail.doc

    @property
    def url(self):
        '''A shortcut to the main url for this bill.
        '''
        return self.urls.detail.url

    @property
    def text(self):
        '''A shortcut to the unicode reponse of this bill's main page.
        '''
        return self.urls.detail.text

    def saveable(self):
        '''Or name this something else, y'know whatevers. There
        are dozens of different ways to go about this.
        '''
        raise NotImplemented
        # For example:
        self.build_everthing()
        return self.bill


# MA subclasses.
# --------------------------------------------------
class MABillScraper(BillScraper):
    '''The scraper instance handles fetching pages. In a perfect
    world, I'd personally rather call "save_thing" on something other
    than a specialized web client. Maybe self.db_layer.save_thing.

    If we went this route, most scrapers wouldn't need to define
    any of the three methods below.
    '''
    jurisdiction = 'ma'

    def __init__(self, *args, **kwargs):
        '''We can still put scraper-specific init information in here.
        '''
        super(MABillScraper, self).__init__(*args, **kwargs)
        # forcing these values so that 500s come back as skipped bills
        self.retry_attempts = 0
        self.raise_errors = False

    def scrape(self, chamber, session):
        '''As an example, just delegate out to the timespan scraper system
        here.
        '''
        timespan_scraper = self.get_timespan_scraper(chamber, session)
        return timespan_scraper(chamber, session, scraper=self).scrape()

    def get_timespan_scraper(self, chamber, session):
        '''Finding the right scraper would happen here, but it's
        hardcoded while this is a simple example. This would probably
        end up in a base class.
        '''
        return Term188


class MA_Urls(Urls):
    '''This class is a subclass of Urls and defines the needed
    page validation logic.
    '''
    @Urls.validates('detail')
    def check_not_found(self, url, text):
        '''Sometimes a guessed ID is just bogus.
        '''
        if 'Unable to find the Bill' in text:
            raise Skip('There was no bill for this id.')

    @Urls.validates('detail', retry=True)
    def check_not_truncated(self, url, text):
        '''Sometimes the site breaks, missing vital data.
        '''
        if 'billShortDesc' not in text:
            self.scraper.warning('truncated page on %s' % url)
            raise Skip('The page was truncated. Skipped it.')


class MABillContext(BillContext):
    '''The actual scraping code for an indivual bill goes here. The main
    idea is to decouple individual bill scrapes from a session-wide scrape
    and from session-specfic scrapes.
    '''
    urls_class = MA_Urls

    def saveable(self):
        self.add_basics()
        self.add_actions()
        self.add_sponsors()
        self.add_versions()
        self.add_sources_from_urls()
        return self.bill

    def add_basics(self):
        title = self.doc.xpath('//h2/text()')[0]
        desc = self.doc.xpath('//p[@class="billShortDesc"]/text()')[0]
        self.bill['title'] = title.strip()
        self.bill['summary'] = desc.strip()

    def add_actions(self):
        for act_row in self.urls.detail.doc.xpath('//tbody[@class="bgwht"]/tr'):
            date = act_row.xpath('./td[@headers="bDate"]/text()')[0]
            date = datetime.strptime(date, "%m/%d/%Y")
            actor_txt = act_row.xpath('./td[@headers="bBranch"]')[0].text_content().strip()
            if actor_txt:
                actor = self.context.chamber_map[actor_txt]
            action = act_row.xpath('./td[@headers="bAction"]')[0].text_content().strip()
            atype, whom = self.classify_action(action)
            kwargs = {}
            if not whom is None:
                kwargs['committees'] = [whom]
            self.bill.add_action(actor, action, date, type=atype, **kwargs)

    def add_sponsors(self):
        ''''I tried to, as I was finding the sponsors, detect whether a
        sponsor was already known. One has to do this because an author
        is listed in the "Sponsors:" section and then the same person
        will be listed with others in the "Petitioners:" section. We are
        guessing that "Sponsors" are authors and "Petitioners" are
        co-authors. Does this make sense?
        '''
        sponsors = dict((a.get('href'), a.text) for a in
                        self.doc.xpath('//p[@class="billReferral"]/a'))
        petitioners = dict((a.get('href'), a.text) for a in
                           self.doc.xpath('//div[@id="billSummary"]/p[1]/a'))

        if len(sponsors) == 0:
            xpath = '//p[@class="billReferral"]'
            spons = self.doc.xpath(xpath)[0].text_content()
            spons = spons.strip()
            spons = spons.split("\n")
            cspons = []
            for s in spons:
                if s and s.strip() != "":
                    cspons.append(s)

            sponsors = dict((s, s) for s in cspons)

        # remove sponsors from petitioners
        for k in sponsors:
            petitioners.pop(k, None)

        for sponsor in sponsors.values():
            if sponsor == 'NONE':
                continue
            self.bill.add_sponsor('primary', sponsor)

        for petitioner in petitioners.values():
            if sponsor == 'NONE':
                continue
            self.bill.add_sponsor('cosponsor', petitioner)

    def add_versions(self):
        doc = self.urls.detail.doc
        # sometimes html link is just missing
        bill_text_url = (
            doc.xpath('//a[contains(@href, "BillHtml")]/@href') or
            doc.xpath('//a[contains(@href, "Bills/PDF")]/@href')
        )
        if bill_text_url:
            if 'PDF' in bill_text_url[0]:
                mimetype = 'application/pdf'
            else:
                mimetype = 'text/html'
            self.bill.add_version('Current Text', bill_text_url[0],
                             mimetype=mimetype)

    _classifiers = (
        ('Bill Filed', 'bill:filed'),
        ('Referred to', 'committee:referred'),
        ('Read second', 'bill:reading:2'),
        ('Read third.* and passed', ['bill:reading:3', 'bill:passed']),
        ('Committee recommended ought NOT', 'committee:passed:unfavorable'),
        ('Committee recommended ought to pass', 'committee:passed:favorable'),
        ('Bill reported favorably', 'committee:passed:favorable'),
        ('Signed by the Governor', 'governor:signed'),
        ('Amendment.* (A|a)dopted', 'amendment:passed'),
        ('Amendment.* (R|r)ejected', 'amendment:failed'),
    )

    def classify_action(self, action):
        whom = None
        for pattern, type in self._classifiers:
            if re.match(pattern, action):
                if "committee:referred" in type:
                    whom = re.sub("Referred to the committee on the ", "", action)
                return (type, whom)
        return ('other', whom)


class Term188(TimespanScraper):

    # This scraper applies to ma.
    jurisdiction = 'ma'

    # Will be used if the scrape occurs in the 188th term.
    terms = ['188']

    # Optionally restrict it to sessions.
    sessions = ['188th']

    # This one is used for both chambers.
    chamber = None

    # Whenever I can't think of a name for something, it gets
    # called foo_context
    bill_context = MABillContext

    def generate_ids(self):
        # Keep track of how many we've had to skip.
        for n in itertools.count(1):
            bill_id = '%s%d' % (self.chamber_slug[0], n)
            if self.skipped == 10:
                # Lets assume if 10 bills are missing we're done.
                break

            # The format is bill_id, kwargs.
            yield bill_id, None

    def make_urls(self, bill_id):
        url = 'http://www.malegislature.gov/Bills/%s/%s/%s'
        url = url % (self.session_slug, self.chamber_slug, bill_id)
        return dict(detail=url)

    @property
    def session_slug(self):
        return self.session[:-2]

    @property
    def chamber_slug(self):
        return 'House' if self.chamber == 'lower' else 'Senate'

    chamber_map = {
        'House': 'lower', 'Senate': 'upper', 'Joint': 'joint',
        'Governor': 'executive'}

