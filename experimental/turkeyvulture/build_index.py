import os
from os.path import join, abspath, dirname
import json
from itertools import groupby
from operator import itemgetter

import logbook
from jinja2 import Template

from billy.models import db
import jsindex


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
    storekeys = ['committee', 'chamber', '_type', 'state', '_id']
    coll = getattr(db, cname)
    spec = {'state': state}
    objects = coll.find(spec)
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    # spec.update(session='20112012')
    # storekeys = ['bill_id', 'title', '_type', 'subjects', 'type', 'scraped_subjects',
    #              'state', '_id', 'session']
    # objects = db.bills.find(spec)
    # print 'adding', objects.count(), 'bills', 'with spec %r' % spec
    # renderer = lambda obj: templates['bills'].render(obj=obj)
    # index.add('b', objects, renderer, substrs=True, storekeys=storekeys)

    ROOT = 'build/index/' + state

    # I hate doing this.
    HERE = dirname(abspath(__file__))
    index_dir = join(HERE, ROOT)
    try:
        os.makedirs(index_dir)
    except OSError:
        pass

    for stem, stem_id in index.stem2id.items():
        results = index.index[stem_id]
        objects = map(index.objects.get, results)
        res = {}
        for _type, objs in groupby(objects, itemgetter('_type')):
            res[_type] = list(objs)[:5]
        for key in ('person', 'committee'):
            if key not in res:
                res[key] = []
        path = join(index_dir, stem)
        with open(path, 'w') as f:
            json.dump(res, f)


if __name__ == '__main__':
    import sys
    build_index(sys.argv[1])