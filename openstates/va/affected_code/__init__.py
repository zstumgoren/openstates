import re
import lxml.html

from tater.core import parse

from . import extractor
from .ast_ import Start
from .tokenize_ import Tokenizer


class Extractor(extractor.Base):
    abbr = 'va'
    tokenizer = Tokenizer()
    # start_node = Start

    def iter_blurbs(self, bill):
        html = self.latest_version_data(bill)
        doc = lxml.html.fromstring(html)
        blurb = doc.xpath('//div[@id="mainC"]//i')[0].text_content()
        blurb = re.sub(r'\s+', ' ', blurb)
        yield blurb.strip()

    def analyze(self, blurb):
        toks = list(self.tokenizer.tokenize(blurb))
        import pprint;pprint.pprint(toks)
        print blurb
        tree = parse(Start, iter(toks))
        tree.printnode()
        import pdb; pdb.set_trace()
