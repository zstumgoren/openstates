from os.path import join

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
    storekeys = ['committee', 'chamber', '_type', 'state', '_id', 'members']
    coll = getattr(db, cname)
    spec = {'state': state}
    objects = coll.find(spec)
    renderer = lambda obj: templates[cname].render(obj=obj)
    index.add(cname[0], objects, renderer, all_substrs=True, storekeys=storekeys)

    return index


def main(output_folder, abbrs):
    for abbr in abbrs:
        logger.info('Building index for %r' % abbr)
        index = build_index(abbr)
        path = join(output_folder, '%s.json' % abbr)
        with open(path, 'w') as f:
            logger.info('  ..writing index to %r' % path)
            index.dump(f)


if __name__ == '__main__':
    import sys
    output_folder = sys.argv[1]
    abbrs = sys.argv[2:] or db.metadata.distinct('_id')
    main(output_folder, abbrs)
