#!/usr/bin/env python
import random
import os
import sys
import arrow
import time
import json
import errno
import requests
sys.path.append("%s/lib" % ( os.path.dirname(os.path.realpath(__file__) ) ) )
from lib.Atlas import ProbeInfo

WEBROOT='/var/www/html/emile/ixp-country-jedi'

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
    ccix = {}

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

def main():
    os.environ["PYTHONIOENCODING"] = "UTF-8"
    rundate = arrow.utcnow().format('YYYY-MM-DD')
    basedir = os.path.dirname( os.path.realpath(__file__) )
    datadir = "%s/data/%s" % ( basedir, rundate )
    prep_cmd = "%s/prepare.py" % basedir
    meas_cmd = "%s/measure.py" % basedir
    ips_cmd = "%s/get-ips.py" % basedir
    fetch_cmd = "%s/get-measurements.py" % basedir
    anal_cmd = "%s/analyse-results.py" % basedir

    if not os.path.exists(datadir): os.makedirs(datadir)

    ## redirect stdout to logfile
    #LOGFILE = "%s/run.log" % ( datadir, )
    #print "redirecting stdout to %s" % ( LOGFILE )
    #sys.stdout = open(LOGFILE, 'w')
    ixlans_per_country = get_ixp_info()
    ## store ixlans info
    with open("%s/ixp_info.json" % datadir ,'w') as outf:
        json.dump( ixlans_per_country, outf )
    #sys.exit(0)

    countries = countries_with_enough_diversity( min_asn_v4_diversity=3 )
    random.shuffle( countries )
    went_wrong = []
    for cc in countries:
        try:
            ccdir = "%s/%s" % ( datadir, cc )
            print "starting run in %s" % ccdir
            print "\n\n----\nCOUNTRY: %s\n----" % cc
            if not os.path.exists(ccdir): os.makedirs(ccdir)
            os.chdir(ccdir)
            if not cc in ixlans_per_country:
                ixlans_per_country[ cc ] = []
            create_configfile( cc, ixlans_per_country[ cc ] )
            os.system( prep_cmd )
            os.system( meas_cmd )
            time.sleep( 360 ) # 6 mins ok?
            os.system( ips_cmd )
            os.system( fetch_cmd )
            ## now create symlink
            WEBDEST = "%s/history/%s/%s" % (WEBROOT,rundate,cc)
            if not os.path.exists(WEBDEST): os.makedirs(WEBDEST)
            os.symlink( WEBDEST, './analysis')
            ## now the analytics should have output in WEBDEST
            os.system( anal_cmd )
        except:
            print "SOMETHING WENT WRONG FOR COUNTRY: %s" % cc
            went_wrong.append( cc )
    exec_log = {}
    exec_log['countries'] = countries
    exec_log['countries_errs'] = went_wrong
    print "COUNTRIES WITH PROBLEMS: %s" % went_wrong
    force_symlink(
        "%s/history/%s/" % (WEBROOT, rundate),
        "%s/latest" % (WEBROOT)
    )
    os.chdir( basedir )
    os.system('tar czvf %s/ixp-country-jedi-confs.tgz ./data/20*/*/*json*' % (WEBROOT) )
    #os.system('find %s/history -name "asgraph.json" | ./country-timelines2json.py %s/country-timelines.json' % (WEBROOT,WEBROOT) )
    os.system('ls %s/history/*/*/asgraph/asgraph.json | ./country-timelines2json.py %s/history/country-timelines.json' % (WEBROOT,WEBROOT) )
    # now print characteristics for this run
    WEBDEST_EXECLOG = "%s/history/%s/exec_log.json" % (WEBROOT,rundate)
    with open(WEBDEST_EXECLOG,'w') as outf:
        json.dump( exec_log, outf )
main()
