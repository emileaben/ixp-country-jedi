#!/usr/bin/env python
from collections import Counter
from urlparse import urlparse
import argparse
import time
import urllib2
import arrow
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

MEASUREMENT_TYPES = set([
   'probe-mesh',
   'http-traceroute',
   'https-traceroute'
])

sources = {}
dests = {}

def country_stats( cc ):
   stats = {}
   stats['routed_asns'] = routed_asns_for_country(cc)
   # add more stats here?
   return stats

def routed_asns_for_country( cc ):
   ## find country routing stats
   routed_asns = None
   yyyymmdd = arrow.now().format('YYYY-MM-01')
   routed_asns_url = "https://stat.ripe.net/data/country-routing-stats/data.json?resource=%s&starttime=%s&endtime=%s" % (cc, yyyymmdd, yyyymmdd )
   try:
      conn = urllib2.urlopen( routed_asns_url )
      info = json.load (conn )
      routed_asns = info['data']['stats'][0]['asns_ris'] # should really be one
   except:
      print >>sys.stderr, "problem getting routed ASNs for '%s' from RIPEstat" % ( cc )
   return routed_asns
   

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
      ## probes with auto-geoloc have unreliable geolocation :( :( :(
      #if 'tags' in prb_info and 'system-auto-geoip-country' in prb_info['tags']:
      #   print >>sys.stderr, "EEPS system-auto-geoip-country %s" % ( prb_id )
      #   continue
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
         'address_v6': probes[prb_id]['address_v6'],
         'country_code': probes[prb_id]['country_code']
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

## probably make this blacklist configurable
alexa_blacklist = set([
   'xhamster.com',
   'pornhub.com',
   'xvideos.com',
   'xnxx.com',
   'bongacams.com'
])

def alexa_country_top25( countries ):
   targets = []
   for cc in countries:
      al_url= "http://www.alexa.com/topsites/countries/%s" % ( cc )
      req = urllib2.urlopen( al_url )
      # when alexa changes layout this needs to change too
      soup = BeautifulSoup( req )
      tr = soup.findAll('p', class_='desc-paragraph')
      for t in tr:
         site = t.find('a').string.lower()
         if site in alexa_blacklist:
            print >>sys.stderr, "this alexa-top site for country:%s was blocked by ixp-country-jedi blacklist: %s" % ( cc, site )
            print >>sys.stderr, "please adapt the blacklist (in source code) if you want this site measured anyways"
            continue
         ## add 'www'?
         targets.append( site )
   print >>sys.stderr, "WARNING: when using alexa-country-top25 lists, some sites may be considered offensive"
   print >>sys.stderr, "WARNING: please consider looking at the 'targets' list in basedata.json and see if any of the sites"
   print >>sys.stderr, "WARNING: that are going to be measured to might be offensive. Please be considerate to our RIPE Atlas Probe hosts"
   print >>sys.stderr, "Targets found: %s\n" % ( '\n'.join( targets ) )
   time.sleep( 5 )
   return targets

def hitlist_from_websites( urls ):
   '''
   Get list of hostnames from a list of urls
   See for example: http://www.top.ge/cat.php?c=2&where=Government%2C+Ministries%2C+Departments
   Or: http://en.wikipedia.org/wiki/List_of_banks_in_Georgia_%28country%29
   '''
   targets = set()
   for url in urls:
      req_urlp = urlparse( url )
      req = urllib2.urlopen( url )
      soup = BeautifulSoup( req )
      for link in soup.findAll('a', href=True):
         ex_url=link['href']
         ex_urlp = urlparse( ex_url )
         # remove all but full-qualified urls (get rid of website internal stuff typically)
         if not ex_urlp.scheme in ('http','https'):
            continue
         if ex_urlp.hostname == req_urlp.hostname:
            continue
         # remove everything that has url-path (typically website internal stuff)
         if ex_urlp.path not in ('','/'):
            continue
         targets.add( ex_urlp.hostname )
   print >>sys.stderr, "WARNING: when using alexa-country-top25 lists, some sites may be considered offensive"
   print >>sys.stderr, "WARNING: please consider looking at the 'targets' list in basedata.json and see if any of the sites"
   print >>sys.stderr, "WARNING: that are going to be measured to might be offensive. Please be considerate to our RIPE Atlas Probe hosts"
   print >>sys.stderr, "Targets found: %s\n" % ( '\n'.join( targets ) )
   time.sleep( 5 )
   return list(targets)
   

def capital_city_for_country( country_code ):
   ''' 
      Use world bank API to return Capital city for a given country-code 
      Example: returns 'Jakarta,ID' if country_code=='ID'.
   '''
   try:
      wb_url = "http://api.worldbank.org/countries/%s/?format=json" % ( country_code.lower() )
      req = urllib2.urlopen( wb_url )
      resp = json.loads(req.read())
      lat = float(resp[1][0]['latitude'])
      lon = float(resp[1][0]['longitude'])
      name = "%s,%s" % ( resp[1][0]['capitalCity'], country_code )
      return (name,lat,lon)
   except:
      raise ValueError("can't get capital city for '%s' from WorldBank API" % ( country_code ) )

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
      'countries': [], ## countries by iso code
      'country-stats': {}, ## various stats per country
      'measurement-types': [], ## list of measurements we do
      'targets': [], ## list of targets (if not probe-mesh)
   }  ## auxiliary info that we want saved
   ####
   # country
   ####
   if not 'country' in conf:
      print "need a country, exiting"
      sys.exit(1)
   # 'list'-ify country
   if type( conf['country'] ) != list:
      basedata['countries'] = [ conf['country'] ]
   else:
      basedata['countries'] = conf['country']
   # uppercase all
   basedata['countries'] = map(lambda x:x.upper(), basedata['countries'])
   ####
   # stats per country
   ####
   for cc in basedata['countries']:
      basedata['country-stats'][ cc ] = country_stats( cc )
   ####
   # measurement-types
   ####
   if 'measurement-type' in conf:
      if type( conf['measurement-type'] ) != list :
         conf['measurement-type'] = [ conf['measurement-type'] ]
      for mtype in conf['measurement-type']:
         if not mtype in MEASUREMENT_TYPES:
            print >> sys.stderr, "measurement-type '%s' not supported (supported types: %s)" % (mtype, MEASUREMENT_TYPES)
            sys.exit(1)
         else:
            basedata['measurement-types'].append( mtype )
         ### probably need better syntax checking etc. here
   else:
      ## maybe make default 'http-traceroute' if 'targets' is defined?
      basedata['measurement-types'] = ['probe-mesh']
   ####
   # targets
   ####
   if 'targets' in conf: 
      if type( conf['targets'] ) == list:
         basedata['targets'] = conf['targets']
      else:
         print >> sys.stderr, "config has 'targets', but that is not a list"
   elif 'target-type' in conf:
      if conf['target-type'] == 'alexa-country-top25':
         basedata['targets'] = alexa_country_top25( basedata['countries'] )
      else:
         print >> sys.stderr, "unknown target-type of '%s' in config, bailing out"
         sys.exit(1)
   elif 'targets-from-websites' in conf:
      if type(conf['targets-from-websites']) != list:
         print >> sys.stderr, "unknown 'targets-from-websites' needs to be a list, baling out"
         sys.exit(1)
      basedata['targets'] = hitlist_from_websites( conf['targets-from-websites'] )
   ####
   # locations
   ####
   ## If no location present, select the capital of the first country in list
   if not 'locations' in conf or len( conf['locations'] ) == 0:
      capital_str,lat,lon = capital_city_for_country( basedata['countries'][0] )
      print >> sys.stderr, "No location info available for probe selection, defaulting to capital city of country (%s)" % ( capital_str )
      basedata['locations'][ capital_str ] = {'lat': lat, 'lon': lon} 
   else:
      for loc in conf['locations']:
         lat,lon = locstr2latlng( loc ) 
         basedata['locations'][ loc ] = {'lat': lat, 'lon': lon} 
   if 'ixps' in conf:
      for ixp in conf['ixps']:
         basedata['ixps'][ ixp['name'] ] = {
            'peeringlans': ixp['peeringlans']
         }
         if 'memberlist' in ixp:
            member_asn_set = get_memberlist( ixp['memberlist'] )
            print member_asn_set
            basedata['ixps'][ ixp['name'] ]['memberlist'] = ixp['memberlist']
            basedata['ixps'][ ixp['name'] ]['memberlist_asns'] = sorted( list( member_asn_set ) )
   if os.path.isfile('probeset.json'):
      print >>sys.stderr, "probeset.json file exists, not making a new probe selection"
   else: 
      selected_probes = []
      for country in basedata['countries']:
         print >>sys.stderr, "Preparing country: %s" % ( country )
         probes_cc = find_probes_in_country( country )
         sel_probes_for_cc = do_probe_selection( probes_cc, conf, basedata )
         selected_probes += sel_probes_for_cc
         print >>sys.stderr, "END country: %s" % ( country )
      ## writing to probeset.json
      print "writing probe selection to probeset.json (%s probes)" % ( len( selected_probes ) )
      with open('probeset.json','w') as outfile:
         json.dump( selected_probes, outfile, indent=2 )
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
