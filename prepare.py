#!/usr/bin/env python
from collections import Counter
import argparse
import urllib2
import sys
import re
import json
from bs4 import BeautifulSoup
from math import radians, cos, sin, asin, sqrt
import os
import sys
sys.path.append("%s/lib" % ( os.path.dirname(os.path.realpath(__file__) ) ) )
from Atlas import ProbeInfo

## find connected probes
PROBE_URL = 'https://atlas.ripe.net/api/v1/probe/?limit=100'

sources = {}
dests = {}

def get_asns( cand_list ):
   nums = set()
   for asn_cand in cand_list:
      matched = re.match(r'\s*(?:AS)?(\d+)\s*$', asn_cand.upper())
      if matched:
         asnum = matched.group(1)
         nums.add( int(asnum) )
   # some kind of clinchers to distinguish from lists of low numbers 
   if len(nums) <= len( cand_list ) / 4: 
      #print "num / cand_list %s/%s : %s" % ( len(nums) , len(cand_list), nums )
      return False
   # sanity-check, to see if a column is not just something with low numbers. woodynet/AS42 is always there ;)
   if max(nums) < 42: return []
   return nums

def haversine_km(lat1,lon1,lat2,lon2):
    """
    http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km

def find_probes_in_country( cc ):
   probes = {}
   if cc:
      probes = ProbeInfo.query(country_code=cc, is_public=True)
   else:
      probes = ProbeInfo.query(is_public=True)
   '''
   asns_v4 = Counter()
   asns_v6 = Counter()
   for prb_id in probes:
      if probes[prb_id]['asn_v4'] != None:
         asns_v4[ probes[prb_id]['asn_v4'] ] += 1
      if probes[prb_id]['asn_v6'] != None:
         asns_v6[ probes[prb_id]['asn_v6'] ] += 1
   return asns_v4,asns_v6,probes
   '''
   return probes

def do_probe_selection( probes, conf, basedata ):
   probes_per_asn={}
   for prb_id in probes:
      prb_info = probes[prb_id]
      status = prb_info['status']
      ## down probes are not useful:
      if status != 1:
         continue
      dists = {}
      for loc in basedata['locations']:
         loclat = basedata['locations'][loc]['lat']
         loclon = basedata['locations'][loc]['lon']
         dists[ loc ] = haversine_km( loclat, loclon, prb_info['latitude'], prb_info['longitude'] )
      # feed the distance back into the 'probes' data struct too
      probes[prb_id]['dists'] = dists

      ### TODO deal with too far away probes
      asn = prb_info['asn_v4']
      ### TODO fix cases where 
      if asn == None:
         print >>sys.stderr, "no ASN for probe?!,what's up RIPE Atlas backend?. %s" % ( prb_info )
         continue
      if not asn in probes_per_asn:
         probes_per_asn[ asn ] = []
      probes_per_asn[ asn ].append({
         'dists': dists,
         'prb_id': prb_id,
         'status': prb_info['status']
      })
   selected_probes = []

   asn_count = 0 
   asn_multiprobe_count = 0 
   selected_asn_set = set()
   selected_asn_probes = {} ## probe IDs per ASN for selected probes
   ## stats
   prb_per_asn_distr = {}
   for asn in probes_per_asn:
      asn_count += 1
      selected_asn_set.add( asn )
      selected_asn_probes[asn] = set()
      ### in principle this selects the closest and furthest probe for each of the list of locations
      if len( probes_per_asn[asn] ) <= 2*len( basedata['locations'] ): 
         # not enough probes for the fancy selection, just select them all
         for prb in probes_per_asn[asn]:
            selected_asn_probes[asn].add( prb['prb_id'] )
      else: ## we need to do fancy selections
         for loc in basedata['locations']:
            loc_sorted = sorted( probes_per_asn[asn], key=lambda k: k['dists'][ loc ] ) 
            selected_asn_probes[asn].add(loc_sorted[0]['prb_id'])
            selected_asn_probes[asn].add(loc_sorted[-1]['prb_id'])
         asn_multiprobe_count += 1
      print "AS%s %s" % ( asn, list(selected_asn_probes[asn]) )
      prb_per_asn = len(selected_asn_probes[asn])
      if not prb_per_asn in prb_per_asn_distr:
         prb_per_asn_distr[ prb_per_asn ] = 0
      prb_per_asn_distr[ prb_per_asn ] += 1
      
      for p in selected_asn_probes[asn]:
         selected_probes.append( p )
   '''
   print "member ASN set size: %s\n(%s)" % ( len( member_asn_set ), member_asn_set )

   overlap_asns = selected_asn_set.intersection( member_asn_set )
   print "overlap member+country ASN set: %s\n(%s)" % ( len( overlap_asns ) , overlap_asns )

   selected_nonmember_asns = selected_asn_set.difference( member_asn_set )
   print "In selection, but not member: %s\n(%s)" % ( len( selected_nonmember_asns ), selected_nonmember_asns )

   nonselected_member_asns = member_asn_set.difference( selected_asn_set )
   print "Member, but not in selection: %s\n(%s)" % ( len( nonselected_member_asns ), nonselected_member_asns )

   print "selected asncount: %s, multiprobe: %s\n(%s)" % ( asn_count, asn_multiprobe_count, selected_asn_set )
   print ' '.join(["--add=%s" % (x) for x in selected_probes ])
   '''
   if len(prb_per_asn_distr.keys()) == 0:
      return []
   # print some stats
   print "distribution of probes per ASN:"
   for i in range(1,1+max( prb_per_asn_distr.keys() )):
      count = 0
      try: count = prb_per_asn_distr[ i ]
      except: pass
      plural = 's'
      if count==1: 
         plural = ''
      print "  ASNs with %s probe%s: %s" % ( i , plural, count )
   
   outdata = []
   for prb_id in selected_probes:
      outdata.append({
         'probe_id': prb_id,
         'lat': probes[prb_id]['latitude'],
         'lon': probes[prb_id]['longitude'],
         'asn_v4': probes[prb_id]['asn_v4'],
         'asn_v6': probes[prb_id]['asn_v6'],
         'dists': probes[prb_id]['dists'],
         'tags': probes[prb_id]['tags'],
         'address_v4': probes[prb_id]['address_v4'],
         'address_v6': probes[prb_id]['address_v6']
      })
   return outdata

def get_memberlist( murl ):
   try:
      url = urllib2.Request( murl )
      conn = urllib2.urlopen( url )
   except:
      print "eeps"
   if murl.endswith('.json'):
      return get_memberlist_json( conn )
   else:
      return get_memberlist_html_table( conn )

def get_memberlist_json( conn ):
   try:
      data = json.load( conn )
   except:
      print >>sys.stderr, "reading json failed"
      return None
   memberlist = []
   if 'member_list' in data:
      for mem in data['member_list']:
         if 'asnum' in mem:
            memberlist.append( mem['asnum'] )
   return memberlist
      
def get_memberlist_html_table( conn ):
   soup = BeautifulSoup(conn)
   tables = soup.find_all('table')
   #print >>sys.stderr, "found %s tables in html" % ( len( tables ) )
   max_table=None
   max_table_len=0
   for t in tables:
      if len( str(t) ) > max_table_len:
         max_table = t
         max_table_len = len( str(t) )
   ## use the max-size table
   rows = max_table.findAll('tr')
   col_idx=0
   asn_col = None
   name_col = None
   url_col = None
   asns = []
   while True:
      col_vals = []
      # deal with headers properly
      #for row in rows[1:]:
      for row in rows:
         try:
            #print row
            #print row.findAll('td')
            col_val = row.findAll('td')[col_idx].text
            col_vals.append( col_val )
         except: pass
      if len( col_vals ) > 0:
         are_asns = get_asns( col_vals )
         if are_asns > 0:
            asn_col = col_idx
            asns = are_asns
            #print "asns: %s" % ( are_asns )
            #print "len %d" % ( len( are_asns ) )
      else:
         break
      col_idx += 1
   return asns

def locstr2latlng( locstring ):
   try:
      locstr = urllib2.quote( locstring )
      geocode_url = "http://maps.googleapis.com/maps/api/geocode/json?address=%s&sensor=false" % locstr
      req = urllib2.urlopen(geocode_url)
      resp = json.loads(req.read())
      ll = resp['results'][0]['geometry']['location']
      return ( ll['lat'], ll['lng'] )
   except:
      print "could not determine lat/long for '%s'" % ( locstring )


def main( args ):
   member_asn_set = set()
   if args.memberlist_url:
      member_asn_set = set( get_memberlist( args.memberlist_url ) )
   probe_asns_v4,probe_asns_v6,probes = find_probes_in_country( args.country )
   selected_probes = do_probe_selection( probes, args, member_asn_set )


if __name__ == '__main__':
   with open('./config.json','r') as conffile:
      conf = json.load( conffile )
   basedata = { # aux info we want saved
      'locations': {}, ## locations keyed by name
      'ixps': {}, ## IXPs keyed by name
   }  ## auxiliary info that we want saved
   ## location infos
   for loc in conf['locations']:
      lat,lon = locstr2latlng( loc ) 
      basedata['locations'][ loc ] = {'lat': lat, 'lon': lon} 
   for ixp in conf['ixps']:
      basedata['ixps'][ ixp['name'] ] = {
         'peeringlans': ixp['peeringlans']
      }
      if 'memberlist' in ixp:
         member_asn_set = get_memberlist( ixp['memberlist'] )
         print member_asn_set
         basedata['ixps'][ ixp['name'] ]['memberlist'] = ixp['memberlist']
         basedata['ixps'][ ixp['name'] ]['memberlist_asns'] = sorted( list( member_asn_set ) )
   if 'country' in conf:
      if os.path.isfile('probeset.json'):
         print >>sys.stderr, "probeset.json file exists, not making a new probe selection"
      else: 
         countries = conf['country']
         selected_probes = []
         if type(countries) != list:
            countries = [ countries ]
         for country in countries:
            probes_cc = find_probes_in_country( country )
            sel_probes_for_cc = do_probe_selection( probes_cc, conf, basedata )
            selected_probes += sel_probes_for_cc
         ## writing to probeset.json
         print "writing probe selection to probeset.json (%s probes)" % ( len( selected_probes ) )
         with open('probeset.json','w') as outfile:
            json.dump( selected_probes, outfile, indent=2 )
   else:      
      ## TODO figure out how to deal with multi-country, or no country defined
      print "need a country, exiting"
   print >>sys.stderr, "writing basedata (locations/ixps) to basedata.json"
   with open('./basedata.json','w') as bdfile:
      json.dump( basedata, bdfile, indent=2 )

'''
if __name__ == '__main__':
   parser = argparse.ArgumentParser()
   parser.add_argument('-m','--memberlist_url', help="URL for IXP memberlist (optional)")
   parser.add_argument('-l','--location', help="Location string (that can be geocoded to a lat/lon)")
   parser.add_argument('-r','--radius', type=int, help="Select only probes in this radius (km) around <location>")
   parser.add_argument('-c','--country',help="Select only probes in this country")
   args = parser.parse_args()
   if args.location:
      lat,lon = locstr2latlng( args.location )
      args.lat = lat
      args.lon = lon
   main( args )
'''
