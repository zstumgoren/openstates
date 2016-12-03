'''Dump JSON for a DC bill

USAGE:

    $ python dump_bill_json.py PR21-0316

'''
import json
import pprint
import sys

import requests

from openstates.utils import mkdir_p

def main():
    headers = {"Content-Type":"application/json"}
    bill_url = "http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx/GetPublicData"
    try:
        bill_id = sys.argv[1]
    except IndexError:
        msg = "\nERROR: You must supply a bill id! Example:\n\n\tpython {} PR21-0316\n".format(__file__)
        sys.exit(msg)
    bill_params = { "legislationId" : bill_id }
    bill_info = requests.post(bill_url, headers=headers, data=json.dumps(bill_params))
    bill_info = decode_json(bill_info.json()["d"])["data"]
    output_dir = 'data/dc/bills_raw/'
    outfile = "".join([output_dir, "{}.json".format(bill_id)])
    mkdir_p(output_dir)
    with open(outfile, 'w') as out:
        json.dump(bill_info, out, sort_keys=True, indent=4, separators=(',', ': '))
    pprint.pprint(bill_info)
    print("\nRaw bill data saved: {}\n".format(outfile))

def decode_json(stringy_json):
    #the "json" they send is recursively string-encoded.
    if type(stringy_json) == dict:
        for key in stringy_json:
            stringy_json[key] = decode_json(stringy_json[key])
    elif type(stringy_json) == list:
        for i in range(len(stringy_json)):
            stringy_json[i] = decode_json(stringy_json[i])
    elif type(stringy_json) in (str,unicode):
        if len(stringy_json) > 0 and stringy_json[0] in ["[","{",u"[",u"{"]:
            return decode_json(json.loads(stringy_json))
    return stringy_json


if __name__ == '__main__':
    main()
