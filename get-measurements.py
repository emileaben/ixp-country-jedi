#!/usr/bin/env python
import os
import sys
sys.path.append("%s/lib" % ( os.path.dirname(os.path.realpath(__file__) ) ) )
from Atlas import MeasurementInfo
from Atlas import MeasurementFetch
from Atlas import MeasurementPrint
from Atlas import MeasurementEnhance
from Atlas import ProbeInfo
import json
import re
import time
import ripe.atlas.sagan
from radix import Radix

### static definitions
MAX_PARALLEL_PROCESSES=10
RESULTDIR='./results'
###

def check_if_via_ixp( tr, ixp_radix ):
   ips = set()
   ip2minhop = {}
   ixps = []
   for h in tr.ip_path:
      for ip in h:
         if isinstance(ip, str):
            ips.add( ip )
            if not ip in ip2minhop:
               ip2minhop[ ip ] = h.index
            elif ip2minhop[ ip ] > h.index:
               ip2minhop[ ip ] = h.index
   ## ips lowest to highest hop (so lan that was encountered first is listed first)
   sorted_ips = sorted( ips, key=lambda ip:ip2minhop[ ip ] )
   last = None
   for ip in sorted_ips:
      rnode = ixp_radix.search_best( ip )
      if rnode != None:
         ixp = rnode.data['name']
         if last == None or last != ixp:
            ixps.append( ixp )
            last = ixp
   return ixps

def create_ixp_radix( basedata ):
   ixp_radix = Radix()
   for ixp_name,ixp_entry in basedata['ixps'].iteritems():
      for prefix in ixp_entry['peeringlans']:
         node = ixp_radix.add( prefix )
         node.data['name'] = ixp_name 
   return ixp_radix

def check_if_is_in_country( countries, locs):
   for loc in locs:
      if loc != None: 
         cc_in_loc = loc.rsplit(',',1)[1]
         if not cc_in_loc in countries:
            return False
   return True

def get_destination_rtts( tr ):
   rtts = []
   for hop in tr.hops:
      for packet in hop.packets:
         if packet.origin and tr.destination_address == packet.origin:
            if isinstance( packet.rtt, float):
               rtts.append( packet.rtt )
   return rtts

def main():
   msms = {}
   with open('measurementset.json','r') as infile:
      msms = json.load( infile )
   probes = {}
   with open('probeset.json','r') as infile:
      probes = json.load( infile )
   probes_by_ip = {}
   probes_by_id = {}
   for p in probes:
      probes_by_id[ p['probe_id'] ] = p
      if 'address_v4' in p and p['address_v4'] != None:
         probes_by_ip[ p['address_v4'] ] = p['probe_id']
      if 'address_v6' in p and p['address_v6'] != None:
         probes_by_ip[ p['address_v6'] ] = p['probe_id']
   #NOTE: there are IPs with multiple probes behind them, this just picks one.

   # all auxilliary data should come from 'basedata' prepare-step should put it there
   # this is so we can fill out the blanks in prepare-stage
   #conf = {}
   #with open('config.json','r') as infile:
   #   conf = json.load ( infile )
   basedata = {}
   with open('basedata.json','r') as infile:
      basedata = json.load ( infile )
   ixp_radix = create_ixp_radix( basedata )
   MeasurementPrint.IPInfoCacheFromFile('ips.json-fragments')
   MeasurementPrint.setCacheOnly( True )
   MeasurementEnhance.IPInfoCacheFromFile('ips.json-fragments')
   MeasurementEnhance.setCacheOnly( True )
   if not os.path.exists(RESULTDIR):
      os.makedirs(RESULTDIR)
   def process_msm( msm_spec, protocol ):
      # msm_spec has msm_id
      msm_id = msm_spec['msm_id']
      print >>sys.stderr, "starting processing of %s" % ( msm_id )
      ## exit if .msm.%s file already exists
      outfilename = "%s/msm.%s.json" % (RESULTDIR, msm_id )
      if os.path.exists( outfilename ):
         print >>sys.stderr, "file already exists %s" % ( outfilename )
         return
      outdata = []      
      for data in MeasurementFetch.fetch( msm_id ):
         tr = ripe.atlas.sagan.TracerouteResult( data )
         tracetxt = MeasurementPrint.trace2txt( data )
         src_prb_id = data['prb_id']
         src_prb = probes_by_id[ src_prb_id ]
         dst_prb_id = None
         dst_prb = None
         try:
            dst_prb_id = probes_by_ip[ data['dst_addr'] ]
            dst_prb = probes_by_id[  dst_prb_id ]
         except: pass
         if src_prb_id == dst_prb_id:
            ### probe to itself is not interesting/useful
            ## TODO filter this out in the measurement creation
            continue
         ixps = check_if_via_ixp( tr, ixp_radix ) 
         via_ixp = False
         if len(ixps) > 0: via_ixp = True
         #print "IXPS: %s" % ( ixps )
         #print tracetxt
         locs = MeasurementPrint.trace2locs( data )
         as_links = MeasurementEnhance.aslinksplus( data, ixp_radix )
         geojson = MeasurementEnhance.togeojson( data, src_prb , dst_prb )
         #print as_links
         countries = basedata['countries']
         is_in_country = check_if_is_in_country( countries, locs )
         #print "INCOUNTRY: %s" % (is_in_country)
         dst_rtts = get_destination_rtts( tr )
         outdata.append( {
            'ts': data['timestamp'],
            'result': data['result'],
            'protocol': protocol,
            'msm_id': msm_id,
            'as_links': as_links,
            'src_prb_id': src_prb_id,
            'dst_prb_id': dst_prb_id,
            #'src_asn': src_asn,
            #'dst_asn': dst_asn,
            #'last_rtt': tr.last_rtt,
            'dst_rtts': dst_rtts,
            #'target_responded': tr.target_responded,
            #'src_is_member': srcmb,
            #'dst_is_member': dstmb,
            ### more correctly: geojson linestring array
            'geojson': geojson,
            'in_country': is_in_country,
            'via_ixp': via_ixp,
            'ixps': ixps,
            'tracetxt': tracetxt,
            'locations': list(locs)
         } )
      with open(outfilename,'w') as outfile:
         json.dump( outdata, outfile, indent=2 )
   ## loop over measurements
   parallel_proc = 0
   children = set()
   msm_list = msms['v4'] + msms['v6']
   for m in msm_list:
      child_pid = os.fork()
      if child_pid == 0:
         process_msm( m, 4) # only v4 atm
         sys.exit(0)
      else:
         children.add( child_pid )
         parallel_proc += 1
         if parallel_proc >= MAX_PARALLEL_PROCESSES:
            cpid,cstatus = os.wait()
            children.remove( cpid )
            parallel_proc -= 1
   for cpid in children:
      print "was still waiting for cpid: %s" % ( cpid )
      os.waitpid(cpid,0)
   print "FINISHED!"

main()

'''

probes = ProbeInfo.query(country_code=country)
def probeinfo( prb_id, key ):
   global probes
   if prb_id in probes:
      return probes[ prb_id ][ key ]
   else:
      newp = ProbeInfo.query(**{'id': prb_id})
      for k,v in newp.items(): 
         probes[ k ] = v
      return probes[ prb_id ][ key ]

now = int(time.time())
#then = now - 8*3600
then = now - 3600

def check_if_is_in_country( countries, locs):
   for loc in locs:
      if loc != None:
         cc_in_loc = loc.rsplit(',',1)
            if cc_in_loc in countries:
               return False
   return True

def check_if_via_ixp( tr, ixp_radix ):
   ips = set()
   for h in tr.ip_path:
      for ip in h:
         if isinstance(ip, str):
            ips.add( ip )
   for ip in ips:
      rnode = ixp_radix.search_best( ip )
      if rnode != None:
         return True
   return False

def get_destination_rtts( tr ):
   rtts = []
   for hop in tr.hops:
      for packet in hop.packets:
         if packet.origin and tr.destination_address == packet.origin:
            if isinstance( packet.rtt, float):
               rtts.append( packet.rtt )
   return rtts

count=0
v4_count=0
v6_count=0

in_country_count=0
v4_in_country_count=0
v6_in_country_count=0

data_entries = []
probe_entries = {}

for msm_id,msm_meta in f.items():
   print msm_meta['description']
   rem = re.search(r'probe:\s+(\d+),\s+IPv(\d+)', msm_meta['description'])
   dst_prb = None
   protocol = None
   if rem:
      dst_prb = int(rem.group(1))
      protocol = int(rem.group(2))
   else:
      raise ValueError("measurement description doesn't contain probeID and IP protocol version")
   dst_asn = None
   if protocol == 4:
      dst_asn = probeinfo( dst_prb, 'asn_v4' )
   elif protocol == 6:
      dst_asn = probeinfo( dst_prb, 'asn_v6' )
   else:
      raise ValueError("IP protocol needs to be 4 or 6")


   dstmb=None
   if dst_asn in member_asn_set:
      dstmb=True
   else:
      dstmb=False
      
   for data in MeasurementFetch.fetch( msm_id, start=then , stop=now ): 
      tr = ripe.atlas.sagan.TracerouteResult( data )
      src_prb = data['prb_id']
      src_asn = None
      if protocol == 4:
         src_asn = probeinfo( src_prb , 'asn_v4' )
      elif protocol == 6:
         src_asn = probeinfo( src_prb , 'asn_v6' )
      else:
         raise ValueError("IP protocol needs to be 4 or 6")
      srcmb=None
      if src_asn in member_asn_set:
         srcmb=True
      else:
         srcmb=False
      tracetxt = MeasurementPrint.trace2txt( data )
      print tracetxt
      locs = MeasurementPrint.trace2locs( data )
      is_in_country = check_if_is_in_country( country, locs )
      via_ixp = check_if_via_ixp( tr, ixp_radix )
      dst_rtts = get_destination_rtts( tr )
      if not src_prb in probe_entries:
         probe_entries[ src_prb ] = {
            'id': src_prb,
            'asn_v4': probeinfo( src_prb, 'asn_v4'),
            'asn_v6': probeinfo( src_prb, 'asn_v6'),
            'is_member': srcmb,
         }
      if not dst_prb in probe_entries:
         probe_entries[ dst_prb ] = {
            'id': dst_prb,
            'asn_v4': probeinfo( dst_prb, 'asn_v4'),
            'asn_v6': probeinfo( dst_prb, 'asn_v6'),
            'is_member': dstmb,
         }
      data_entries.append( {
         'ts': data['timestamp'],
         'protocol': protocol,
         'msm_id': msm_id,
         'src_prb_id': data['prb_id'],
         'dst_prb_id': dst_prb,
         'src_asn': src_asn,
         'dst_asn': dst_asn,
         'last_rtt': tr.last_rtt,
         'dst_rtts': dst_rtts,
         'target_responded': tr.target_responded,
         'src_is_member': srcmb,
         'dst_is_member': dstmb,
         'in_country': is_in_country,
         'via_ixp': via_ixp,
         'tracetxt': tracetxt,
      } )
      print "## ipv:%s\tmsm:%s\tsrcprb:%s\tdstprb:%s\tsrcasn:%s\tdstasn:%s\tlastrtt:%s\tdstreached:%s\tsrcmb:%s\tdstmb:%s\tincountry:%s\tixp:%s\tlocs:%s" % (protocol,msm_id, data['prb_id'], dst_prb, src_asn, dst_asn, tr.last_rtt, tr.target_responded, srcmb, dstmb, is_in_country, via_ixp, MeasurementPrint.trace2locs( data ) )
      count += 1
      if is_in_country:
         in_country_count +=1
      
      if protocol == 4:
         v4_count += 1
         if is_in_country:
            v4_in_country_count +=1
      elif protocol == 6:
         v6_count += 1
         if is_in_country:
print "#### KLOTR index: %.2f%%" % ( 100*float(in_country_count)/count )
print "#### v4 KLOTR index: %.2f%%" % ( 100*float(v4_in_country_count)/v4_count )
print "#### v6 KLOTR index: %.2f%%" % ( 100*float(v6_in_country_count)/v6_count )

data_entries.sort(key=lambda k: k['ts'])

json_out = {
   'columns': probe_entries,
   'data': data_entries
}
with open(json_output, 'w') as outfile:
      print >>outfile, json.dumps( json_out, sort_keys=True, indent=2 )
'''
