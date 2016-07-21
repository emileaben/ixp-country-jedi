#!/usr/bin/env python
import json
import time
import os
import sys
sys.path.append("%s/lib" % ( os.path.dirname(os.path.realpath(__file__) ) ) )
from Atlas import Measure

### read a probeset.json (default in current dir)
### spit out measurementset.json

probes=[]
basedata = {}
with open("probeset.json",'r') as infile:
    probes = json.load( infile )
with open("basedata.json",'r') as infile:
    basedata = json.load( infile )

v6src=[] # src are probe IDs
v4src=[]
for p in probes:
    tags = [v for d in p['tags'] for k, v in d.items()]

    if 'address_v4' in p and p['address_v4'] != None and 'system-ipv4-works' in tags:
        v4src.append( p['probe_id'] )
    else:
        print "skipping v4 measurements for probe: %s" % ( p['probe_id'] )

    if 'address_v6' in p and p['address_v6'] != None and 'system-ipv6-works' in tags:
        v6src.append( p['probe_id'] )
    else:
        print "skipping v6 measurements for probe: %s" % ( p['probe_id'] )

v4dst=[] # dst are IP addresses
v6dst=[]

for mtype in basedata['measurement-types']:
    if mtype == 'probe-mesh':
        for p in probes:
            tags = [v for d in p['tags'] for k, v in d.items()]

            if 'address_v4' in p and p['address_v4'] != None and 'system-ipv4-works' in tags:
                v4dst.append( p['address_v4'] )
            if 'address_v6' in p and p['address_v6'] != None and 'system-ipv6-works' in tags:
                v6dst.append( p['address_v6'] )
    elif mtype in ('traceroute','http-traceroute','https-traceroute'):
        v4dst += basedata['targets']
        v6dst += basedata['targets']

v4src_string = ','.join( map(str,v4src) )
v6src_string = ','.join( map(str,v6src) )

msms={'v4':[], 'v6':[]}
for mtype in basedata['measurement-types']:
    if mtype == 'probe-mesh':
        for v4target in v4dst:
            #TODO remove probe itself from list?
            msm_id = Measure.oneofftrace(v4src, v4target, af=4, paris=1, description="ixp-country-jedi to %s (IPv4)" % ( v4target ) )
            msms['v4'].append({
                'msm_id': msm_id,
                'dst': v4target,
                'type': 'probe-mesh'
            })
            print >>sys.stderr,"dst:%s msm_id:%s (probe-mesh)" % ( v4target, msm_id )
            time.sleep(2)

        for v6target in v6dst:
            msm_id = Measure.oneofftrace(v6src, v6target, af=6, paris=1, description="ixp-country-jedi to %s (IPv6)" % ( v6target ) )
            msms['v6'].append({
                'msm_id': msm_id,
                'dst': v6target,
                'type': 'probe-mesh'
            })
            print >>sys.stderr,"dst:%s msm_id:%s (probe-mesh)" % ( v6target, msm_id, )
            time.sleep(2)
    #TODO refactor http/https and normal traceroute taking
    if mtype in ('http-traceroute','https-traceroute'):
        port = 80
        if mtype == 'https-traceroute': port = 443
        for target in v4dst: ## 
            for ipproto in (4,6):
                try:
                    ipstr = "v%s" % ( ipproto )
                    try:
                        msm_id = Measure.oneofftrace(
                             v4src,
                             target,
                             af=ipproto,
                             paris=1,
                             protocol='TCP',
                             port=port,
                             resolve_on_probe=True,
                             description="ixp-country-jedi to %s (IPv%s)" % ( target, ipproto )
                        )
                    except:
                        print "measurement creation failed for dst:%s (IPv%s)" % ( target, ipproto )
                    msms[ ipstr ].append({
                      'msm_id': msm_id,
                      'dst': target,
                      'type': mtype
                    })
                    print >>sys.stderr,"dst:%s msm_id:%s (%s)" % ( target, msm_id, mtype )
                    time.sleep(2)
                except:
                    print "something went wrong"
    if mtype in ('traceroute'):
        for target in v4dst:
            for ipproto in (4,6):
                try:
                    ipstr = "v%s" % ( ipproto )
                    try:
                        msm_id = Measure.oneofftrace(
                         v4src,
                         target,
                         af=ipproto,
                         paris=1,
                         protocol='ICMP',
                         resolve_on_probe=True,
                         description="ixp-country-jedi to %s (IPv%s)" % ( target, ipproto )
                        )
                    except:
                        print "measurement creation failed for dst:%s (IPv%s)" % ( target, ipproto )
                    msms[ ipstr ].append({
                     'msm_id': msm_id,
                     'dst': target,
                     'type': mtype
                    })
                    print >>sys.stderr,"dst:%s msm_id:%s (%s)" % ( target, msm_id, mtype )
                    time.sleep(2)
                except:
                    print "something went wrong"

print >>sys.stderr, "finished measuring, writing results to 'measurementset.json'"
with open("measurementset.json",'w') as outfile:
    json.dump(msms,outfile,indent=2)
