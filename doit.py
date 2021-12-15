#!/usr/bin/env python
import random
import os
import sys
import arrow
import time
import json
import errno
import requests

from lib.Atlas import ProbeInfo

from multiprocessing import Pool, cpu_count
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser(description='Process the Jedi arguments.')
parser.add_argument(
    '--dir-www',
    dest='webroot',
    type=str,
    default='/export/jedi/www',
    help='Webroot directory'
)
parser.add_argument(
    '--dir-run',
    type=str,
    default='/export/jedi/run',
    help='Data directory.'
)
parser.add_argument(
    '--ccs',
    dest='ccs',
    type=str,
    nargs='+',
    default=None,
    required=False,
    help='CCs to run the Jedi through'
)
parser.add_argument(
    '--parallel',
    dest='parallel',
    type=int,
    default=1,  # let's keep it single-threaded by default for the time being, later on we can start using default=cpu_count(),
    help='Amount of parallel threads to run (through a multiprocessing.Pool)'
)
parser.add_argument(
    '--log',
    dest='logfile',
    type=str,
    default='',
    help='Redirect stderr to this logfile'
)

args = parser.parse_args()

WEBROOT = args.webroot
DATA_DIR = args.dir_run
CCS = args.ccs
PARALLEL = args.parallel
LOGFILE = args.logfile

### monkey patch SSL/requests
# http://stackoverflow.com/questions/14102416/python-requests-requests-exceptions-sslerror-errno-8-ssl-c504-eof-occurred/24166498#24166498
import ssl
from functools import wraps
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)
## end monkey-patch



def get_ixp_info():
    ## ccix contains country code with lists of IXP peering LANs
    ccix = defaultdict(list)
    # ccix = {}

    ## contains useful info on peering lans, indexed by peeringdb ix_id
    ix2lans = {}

    ## contains set of pfxes per ixlan
    ixlan2ixpfx = {}

    r_ixpfx = requests.get("https://www.peeringdb.com/api/ixpfx")
    j_ixpfx = r_ixpfx.json()
    for ixpfx in j_ixpfx['data']:
        ixlan_id = int( ixpfx['ixlan_id'] )
        ixlan2ixpfx.setdefault( ixlan_id , [] )
        ixlan2ixpfx[ ixlan_id ].append( ixpfx['prefix'] )

    r_ixlan = requests.get("https://www.peeringdb.com/api/ixlan")
    j_ixlan = r_ixlan.json()

    for ixlan in j_ixlan['data']:
        ix_id = ixlan['ix_id']
        ixlan_id = int(ixlan['id'])
        #pfx_set = ixlan['prefix_set']
        peeringlans = []
        if ixlan['id'] in ixlan2ixpfx:
            peeringlans = ixlan2ixpfx[ ixlan['id'] ]
        #if len( pfx_set ) == 0:
        #    continue
        #for pe in pfx_set:
        #    if 'prefix' in pe:
        #    peeringlans.append( pe['prefix'] )
        if not ix_id in ix2lans:
            ix2lans[ ix_id ] = []
        ix2lans[ ix_id ].append({
            'name': ixlan['name'],
            'desc': ixlan['descr'],
            'peeringlans': peeringlans
        })
    print >>sys.stderr, "IXLANS %s" % ( ix2lans )

    r_ix = requests.get("https://www.peeringdb.com/api/ix")
    j_ix = r_ix.json()
    for ix in j_ix['data']:
        ix_id = ix['id']
        if not ix_id in ix2lans:
            continue
        icountry = ix['country']
        icity = ix['city']
        iname = ix['name']
        if not icountry in ccix:
            ccix[ icountry ] = []
        # beware of name colisions @@TODO
        ixlan_name = iname
        for ixlan_info in ix2lans[ ix_id ]:
            if ixlan_info['name']:
                ixlan_name += "-%s" % ixlan_info['name']
            elif ixlan_info['desc']:
                ixlan_name += "-%s" % ixlan_info['name']
            ccix[ icountry ].append({
                'name': ixlan_name,
                'peeringlans': ixlan_info['peeringlans']
            })
    return ccix

def countries_with_enough_diversity( min_asn_v4_diversity=2 ):
    cc_probe_diversity = {}
    probes = ProbeInfo.query( status=1, is_public=True )
    for prb_id in probes:
        prb_info = probes[prb_id]
        if 'tags' in prb_info and 'system-auto-geoip-country' in prb_info['tags']:
            continue
        else:
            cc = prb_info['country_code']
            if not cc in cc_probe_diversity:
                cc_probe_diversity[ cc ] = set()
            if 'asn_v4' in prb_info and prb_info['asn_v4']:
                cc_probe_diversity[ cc ].add( prb_info['asn_v4'] )
    diverse_cc = []
    for cc in cc_probe_diversity:
        if len( cc_probe_diversity[ cc ] ) >= min_asn_v4_diversity:
            diverse_cc.append( cc )
    return diverse_cc

def create_configfile( cc, ixlans ):
    """
    create a config.json for this country
    """
    conf = {
        "country": cc,
        "ixps": ixlans
    }
    with open("config.json",'w') as outf:
        json.dump(conf, outf, indent=2)

def force_symlink(file1, file2):
    try:
        os.symlink(file1, file2)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(file2)
            os.symlink(file1, file2)




def doit(cc):
    went_wrong = []

    try:
        ccdir = "%s/%s" % (datadir, cc)
        print "starting run in %s" % ccdir
        print "\n\n----\nCOUNTRY: %s\n----" % cc
        if not os.path.exists(ccdir): os.makedirs(ccdir)
        os.chdir(ccdir)
        if not cc in ixlans_per_country:
            ixlans_per_country[cc] = []
        create_configfile(cc, ixlans_per_country[cc])
        os.system(prep_cmd)
        os.system(meas_cmd)
        time.sleep(360)  # 6 mins ok?
        # os.system( ips_old_cmd )
        os.system(ips_cmd)
        os.system(fetch_cmd)
        ## now create symlink
        WEBDEST = "%s/history/%s/%s" % (WEBROOT, rundate, cc)
        if not os.path.exists(WEBDEST): os.makedirs(WEBDEST)
        os.symlink(WEBDEST, './analysis')
        ## now the analytics should have output in WEBDEST
        os.system(anal_cmd)
    except:
        print "SOMETHING WENT WRONG FOR COUNTRY: %s" % cc
        went_wrong.append(cc)

    return went_wrong




rundate = arrow.utcnow().format('YYYY-MM-DD')
basedir = os.path.dirname(os.path.realpath(__file__))
datadir = "%s/%s" % (DATA_DIR, rundate)
if not os.path.exists(datadir): os.makedirs(datadir)
prep_cmd = "%s/prepare.py" % basedir
meas_cmd = "%s/measure.py" % basedir
# ips_old_cmd = "%s/get-ips-old.py" % basedir
ips_cmd = "%s/get-ips.py" % basedir
fetch_cmd = "%s/get-measurements.py" % basedir
anal_cmd = "%s/analyse-results.py" % basedir
os.environ["PYTHONIOENCODING"] = "UTF-8"

ixlans_per_country = get_ixp_info()
# store ixlans info
with open("%s/ixp_info.json" % datadir ,'w') as outf:
    json.dump( ixlans_per_country, outf )

# redirect stdout to logfile
if LOGFILE:
    LOGFILE = "%s/%s" % (datadir, LOGFILE)
    print "redirecting stdout to %s" % ( LOGFILE )
    sys.stdout = open(LOGFILE, 'w')

def main():

    countries = countries_with_enough_diversity( min_asn_v4_diversity=3 )
    random.shuffle( countries )

    if CCS:
        # we keep those countries chosen by the user
        countries = list(
            set(countries).intersection(CCS)
        )

    pool = Pool(PARALLEL)
    went_wrong = pool.map(
        func=doit,
        iterable=countries
    )
    pool.close()
    pool.join()

    exec_log = {}
    exec_log['countries'] = countries
    exec_log['countries_errs'] = went_wrong
    print "COUNTRIES WITH PROBLEMS: %s" % went_wrong
    force_symlink(
        "%s/history/%s/" % (WEBROOT, rundate),
        "%s/latest" % (WEBROOT)
    )
    # the tar command needs a relative path to the data, otherwise the absolute path
    # is included in the archive
    os.chdir(DATA_DIR)
    os.system('tar czvf %s/ixp-country-jedi-confs.tgz ./20*/*/*json*' % WEBROOT )
    #os.system('find %s/history -name "asgraph.json" | ./country-timelines2json.py %s/country-timelines.json' % (WEBROOT,WEBROOT) )
    os.chdir( basedir )
    os.system('ls %s/history/*/*/asgraph/asgraph.json | ./country-timelines2json.py %s/history/country-timelines.json' % (WEBROOT,WEBROOT) )
    # now print characteristics for this run
    WEBDEST_EXECLOG = "%s/history/%s/exec_log.json" % (WEBROOT,rundate)
    with open(WEBDEST_EXECLOG,'w') as outf:
        json.dump( exec_log, outf )
main()
