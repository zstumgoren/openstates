from os.path import join, abspath, dirname
import json

import logbook
from jinja2 import Template

from billy.models import db
import jsindex
from operator import itemgetter


logger = logbook.Logger('jsindex')

templates = {
    'committees': Template(
        '{{obj.committee}} {{obj.subcommittee}}'),

    'legislators': Template(
        '{{obj.full_name}} {{obj.district}} {{obj.party}}'),
    }


def build_index(state):
    index = jsindex.IndexBuilder()

    cname = 'legislators'
    storekeys = ['full_name', '_type', 'chamber', 'district', 'party',
                 'state', '_id', 'photo_url']
    coll = getattr(db, cname)
    spec = {'state': state, 'active': True}
    objects = coll.find(spec)
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    cname = 'committees'
    storekeys = ['committee', 'chamber', '_type', 'state', '_id', 'members']
    coll = getattr(db, cname)
    spec = {'state': state}
    objects = coll.find(spec)
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    spec.update(session='20112012')
    storekeys = ['bill_id', 'title', '_type', 'subjects', 'type', 'scraped_subjects',
                 'state', '_id', 'session']
    objects = db.bills.find(spec)
    print 'adding', objects.count(), 'bills', 'with spec %r' % spec
    renderer = lambda obj: templates['bills'].render(obj=obj)
    index.add('b', objects, renderer, substrs=True, storekeys=storekeys)

    ROOT = 'build/index/'

    # I hate doing this.
    HERE = dirname(abspath(__file__))
    index_dir = join(HERE, ROOT)

    for stem, stem_id in index.stem2id.items():
        results = index.index[stem_id]
        second = itemgetter(2)
        types = map(second, results)
        bills_count = types.count('B')
        committees_count = types.count('C')
        legislators_count = types.count('L')
        data = dict(
            bills_count=bills_count,
            committees_count=committees_count,
            legislators_count=legislators_count,
            results=list(results))
        path = join(index_dir, stem)
        with open(path, 'w') as f:
            json.dump(data, f)
