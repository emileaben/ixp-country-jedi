#!/usr/bin/env python
import json
import time
import os
import sys

from lib.Atlas import Measure

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
   # select probes with stable properties

   stable_tag4_cnt = len( filter(lambda x: x.startswith('system-ipv4-stable-'), p['tags'] ) )
   if 'address_v4' in p and p['address_v4'] != None and stable_tag4_cnt > 0:
      v4src.append( p['probe_id'] )
   else:
      print "skipping v4 measurements for probe: %s (stable tag cnt:%s)" % ( p['probe_id'], stable_tag4_cnt )

   stable_tag6_cnt = len( filter(lambda x: x.startswith('system-ipv6-stable-'), p['tags'] ) )
   if 'address_v6' in p and p['address_v6'] != None and stable_tag6_cnt > 0:
      v6src.append( p['probe_id'] )
   else:
      print "skipping v6 measurements for probe: %s (stable tag cnt:%s)" % ( p['probe_id'], stable_tag6_cnt )

v4dst=[] # dst are IP addresses
v6dst=[]

for mtype in basedata['measurement-types']:
   if mtype == 'probe-mesh':
      for p in probes:
         if 'address_v4' in p and p['address_v4'] != None:
            v4dst.append( p['address_v4'] )
         if 'address_v6' in p and p['address_v6'] != None and 'system-ipv6-ula' not in p['tags']:
            v6dst.append( p['address_v6'] )
   elif mtype in ('traceroute','http-traceroute',
                    'https-traceroute', 'local-news-traceroute', 'local-tld-traceroute'):
      v4dst += basedata['targets']
      v6dst += basedata['targets']

v4src_string = ','.join( map(str,v4src) )
v6src_string = ','.join( map(str,v6src) )

msms={'v4':[], 'v6':[]}
for mtype in basedata['measurement-types']:
   if mtype == 'probe-mesh':
      for v4target in v4dst:
         #TODO remove probe itself from list?
         tag_list = ['ixp-country-jedi','probe-mesh-ipv4', 'country-%s' % ( "-".join( basedata['countries'] ).lower() ) ]
         msm_id = None
         max_attempts = 10
         attempts = 0
         while attempts <= max_attempts and msm_id == None:
            msm_id = Measure.oneofftrace(v4src, v4target, tags=tag_list, af=4, paris=1, description="ixp-country-jedi to %s (IPv4)" % ( v4target ) )
            attempts += 1
            if msm_id == None:
                time.sleep( attempts * 30) # assume there is an API problem, and exponential backoff works?
         msms['v4'].append({
            'msm_id': msm_id,
            'dst': v4target,
            'type': 'probe-mesh'
         })
         print >>sys.stderr,"dst:%s msm_id:%s (probe-mesh)" % ( v4target, msm_id )
         time.sleep(2)

      for v6target in v6dst:
         tag_list = ['ixp-country-jedi','probe-mesh-ipv6', 'country-%s' % ( "-".join( basedata['countries'] ).lower() ) ]
         msm_id = Measure.oneofftrace(v6src, v6target, tags=tag_list, af=6, paris=1, description="ixp-country-jedi to %s (IPv6)" % ( v6target ) )
         msms['v6'].append({
            'msm_id': msm_id,
            'dst': v6target,
            'type': 'probe-mesh'
         })
         print >>sys.stderr,"dst:%s msm_id:%s (probe-mesh)" % ( v6target, msm_id, )
         time.sleep(2)
   #TODO refactor http/https and normal traceroute taking
   if mtype in ('http-traceroute','https-traceroute',
                    'local-news-traceroute', 'local-tld-traceroute'):
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
               except InsecurePlatformWarning as e:
                   pass
               except Exception as e:
                  print "measurement creation failed for dst:%s (IPv%s)" % ( target, ipproto )
                  print e
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
