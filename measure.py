#!/usr/bin/env python
import json
import sys
import time
from Atlas import Measure

### read a probeset.json (default in current dir)
### spit out measurementset.json

probes=[]
with open("probeset.json",'r') as infile:
   probes = json.load( infile )

v6src=[] # src are probe IDs
v4src=[]
v4dst=[] # dst are IP addresses
v6dst=[]

for p in probes:
   if 'address_v4' in p and p['address_v4'] != None:
      v4src.append( p['probe_id'] )
      v4dst.append( p['address_v4'] )
   if 'address_v6' in p and p['address_v6'] != None:
      v6src.append( p['probe_id'] )
      v6dst.append( p['address_v6'] )

v4src_string = ','.join( map(str,v4src) )
v6src_string = ','.join( map(str,v6src) )

msms={'v4':[], 'v6':[]}
for v4target in v4dst:
   #TODO remove probe itself from list?
   msm_id = Measure.oneofftrace(v4src, v4target, af=4, paris=1)
   msms['v4'].append({
      'msm_id': msm_id,
      'dst': v4target
   })
   print >>sys.stderr,"dst:%s msm_id:%s" % ( v4target, msm_id )
   time.sleep(2)

v6msms=[]
for v6target in v6dst:
   msm_id = Measure.oneofftrace(v6src, v6target, af=6, paris=1)
   msms['v6'].append({
      'msm_id': msm_id,
      'dst': v6target
   })
   print >>sys.stderr,"dst:%s msm_id:%s" % ( v6target, msm_id )
   time.sleep(2)

with open("measurementset.json",'w') as outfile:
   json.dump(msms,outfile,indent=2)
