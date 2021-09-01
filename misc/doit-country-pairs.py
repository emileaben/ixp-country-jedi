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
from Atlas import ProbeInfo

WEBROOT='/var/www/html/emile/ixp-country-jedi/country-pairs'
GEONAMES_USER='emileaben'

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

def countries_with_enough_diversity( min_asn_v4_diversity=3 ):
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

def create_configfile_pair( pair, ixlans ):
    all_lans = []
    for lans in ixlans.values():
        all_lans += lans
    conf = {
        "country": pair,
        "ixps": all_lans
    }
    with open("config.json",'w') as outf:
        json.dump(conf, outf, indent=2)

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

custom_neigh = {
        'IS': ['GL','GB','NO'], ### for open house
        'MT': ['IT','TN']
}

def get_neighbor_cc( cc ):
    if cc in custom_neigh:
            print( "## custom neighbor set selected" )
            return custom_neigh[ cc ]
    neigh_url = "http://api.geonames.org/neighboursJSON?country={}&username={}".format( cc, GEONAMES_USER )
    neigh_str = requests.get( neigh_url )
    neigh = neigh_str.json()
    neigh_cc = []
    try:
        for entry in neigh['geonames']:
            if 'countryCode' in entry:
                neigh_cc.append( entry['countryCode'] )
    except:
        pass
    print >>sys.stderr, "NEIGHBORS: %s" % ( neigh_cc )
    return neigh_cc

def main():
    os.environ["PYTHONIOENCODING"] = "UTF-8"
    rundate = arrow.utcnow().format('YYYY-MM-DD')
    basedir = os.path.dirname( os.path.realpath(__file__) )
    datadir = "%s/data-pairs/%s" % ( basedir, rundate )
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

    countries = countries_with_enough_diversity( min_asn_v4_diversity=1 )
    focus_countries = []
    single_country = False
    if len( sys.argv ) == 2:
        # user defined a country to focus on, lets use that
        focus_countries = [ sys.argv[1] ]
        single_country = True
    else:
        print "COUNTRIES %s" %  (countries )
        random.shuffle( countries )
        focus_countries = countries
    went_wrong = []
    for cc in focus_countries:
        print "CC %s" % ( cc, )
        neigh_cc_list = get_neighbor_cc( cc )
        print "NEIGH %s" % ( neigh_cc_list, )
        for neigh_cc in neigh_cc_list:
            if neigh_cc not in countries:
                print "TOO BAD, neigh not enough probes"
                continue
            if single_country == False and neigh_cc < cc: # lexographical '>' because we want a half matrix
                print "TOO BAD, lexo order is wrong %s < %s" % ( neigh_cc, cc )
                continue
            print "ABCD %s -> %s " % ( cc, neigh_cc )
            pair = [cc,neigh_cc]
            pair.sort()
            try:
                ccdir = "%s/%s-%s" % ( datadir, pair[0], pair[1] )
                print "starting run in %s" % ccdir
                print "\n\n----\nCOUNTRY: %s-%s\n----" % (pair[0],pair[1])
                if not os.path.exists(ccdir): os.makedirs(ccdir)
                os.chdir(ccdir)
                for cc in pair:
                    if not cc in ixlans_per_country:
                        ixlans_per_country[ cc ] = []
                create_configfile_pair( pair, ixlans_per_country )
                os.system( prep_cmd )
                os.system( meas_cmd )
                time.sleep( 60*8 ) # 8 mins ok?
                os.system( ips_cmd )
                os.system( fetch_cmd )
                ## now create symlink
                WEBDEST = "%s/history/%s/%s-%s" % (WEBROOT,rundate,pair[0],pair[1])
                if not os.path.exists(WEBDEST): os.makedirs(WEBDEST)
                os.symlink( WEBDEST, './analysis')
                ## now the analytics should have output in WEBDEST
                os.system( anal_cmd )
            except:
                print "SOMETHING WENT WRONG FOR COUNTRY: %s" % (pair,)
                went_wrong.append( pair, )
    print "COUNTRIES WITH PROBLEMS: %s" % went_wrong
    force_symlink(
        "%s/history/%s/" % (WEBROOT, rundate),
        "%s/latest" % (WEBROOT)
    )
    #os.system('tar czvf %s/ixp-country-jedi-confs.tgz ./data/20*/*/*json*' % (WEBROOT) )

main()
