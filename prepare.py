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
import fetch_news_sites

# One-off traceroute msm cost 
COST_OF_TRACEROUTE = 60

# Number of Alexa top sites to be included in the analysis
# Maximum is 50
TOP_ALEXA_SITES = 25

## find connected probes

MEASUREMENT_TYPES = set([
   'probe-mesh',
   'traceroute',
   'http-traceroute',
   'https-traceroute',
   'local-news-traceroute',
   'local-tld-traceroute',
])

GEONAMES_USER=None
authfile = "%s/.geonames/auth" % os.path.dirname(os.path.realpath(__file__) )
if not os.path.exists(authfile):
    print >>sys.stderr, ("Geonames authentication file %s not found" % authfile)
    sys.exit(1)
auth = open(authfile)
GEONAMES_USER = auth.readline()[:-1]
auth.close()
GEONAMES_USER.rstrip()

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

def find_probes_in_country(cc, eyeball=False, threshold=90):
   probes = {}
   base_url = (
      'http://data.labs.apnic.net/ipv6-measurement/Economies/{}/{}.asns.json'
   )
   coverage = 0
   if cc:
      if eyeball:
         url = base_url.format(cc, cc)
         eyeball_distribution = json.loads(urllib2.urlopen(url).read())
         for asn in eyeball_distribution:
            if coverage >= threshold:
               break
            probes.update(ProbeInfo.query(country_code=cc, asn_v4=asn['as'], is_public=True))
            probes.update(ProbeInfo.query(country_code=cc, asn_v6=asn['as'], is_public=True))
            coverage += asn['percent']
      else:
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

def do_probe_selection_from_tag( tag ):
   probes = ProbeInfo.query(tags=tag, status=1)
   return map( _to_probedata, probes.values() )

def do_probe_selection_from_ids( ids ):
   probes = ProbeInfo.query(id__in=ids, status=1)
   return map( _to_probedata, probes.values() )

def do_probe_selection( probes, conf, basedata ):
   probes_per_asn={}
   for prb_id in probes:
      prb_info = probes[prb_id]
      print >>sys.stderr, "%s" % (prb_info)
      status = prb_info['status']
      ## down probes are not useful:
      if status != 1:
         continue
      ## Exclude probes with system tag IPv4 or IPv4 not working
      if("system-ipv4-works" not in probes[prb_id]['tags'] and "system-ipv6-works" not in probes[prb_id]['tags']):
         continue
      ### we want the set of probes that is stable enough
      stable_tag_cnt = len( filter( lambda x: x.startswith('system-ipv4-stable-') or x.startswith('system-ipv6-stable-'), probes[prb_id]['tags'] ) )
      if stable_tag_cnt == 0:
            continue
      #if("system-ipv4-stable-1d" not in probes[prb_id]['tags'] and "system-ipv6-stable-1d" not in probes[prb_id]['tags']):
      #   continue
      ## probes with auto-geoloc have unreliable geolocation :( :( :(
      if 'tags' in prb_info and 'system-auto-geoip-country' in prb_info['tags']:
         print >>sys.stderr, "EEPS system-auto-geoip-country %s" % ( prb_id )
         continue
      dists = {}
      loc_close_enough = False  ## this is only for location-constrained
      for loc in basedata['locations']:
         loclat = basedata['locations'][loc]['lat']
         loclon = basedata['locations'][loc]['lon']
         dists[ loc ] = haversine_km( loclat, loclon, prb_info['latitude'], prb_info['longitude'] )
         if 'location-constraint' in basedata:
            if dists[ loc ] < basedata['location-constraint']:
                loc_close_enough = True
      if 'location-constraint' in basedata and loc_close_enough == False:
        # don't put this probe in the list of probes to consider
        # it is too far from any of the locations we consider
        continue

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
      outdata.append( _to_probedata( probes[prb_id] ) )
   return outdata

def _to_probedata( prb_dict ):
    struct = {
         'probe_id': prb_dict['id'],
         'asn_v4': prb_dict['asn_v4'],
         'asn_v6': prb_dict['asn_v6'],
         'address_v4': prb_dict['address_v4'],
         'address_v6': prb_dict['address_v6'],
         'country_code': prb_dict['country_code'],
         'description': prb_dict['description']
    }
    try:
        if 'latitude' in prb_dict: #v1 api, or a shim pretending to be v1 api:
            struct['lat'] = prb_dict['latitude']
            struct['lon'] = prb_dict['longitude']
            struct['tags'] = prb_dict['tags']
        else:
            struct['lat'] = prb_dict['geometry']['coordinates'][1]
            struct['lon'] = prb_dict['geometry']['coordinates'][0]
            struct['tags'] = map(lambda x: x['slug'], prb_dict['tags'] )
        if 'dists' in prb_dict:
            struct['dists'] = prb_dict['dists']
    except:
        print prb_dict
        raise
    return struct

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

def alexa_country_top25( countries, maxsites ):
   for cc in countries:
      targets = []
      targetsitenames = []
      al_url= "http://www.alexa.com/topsites/countries/%s" % ( cc )
      req = urllib2.urlopen( al_url )
      # when alexa changes layout this needs to change too
      soup = BeautifulSoup( req )
      tr = soup.findAll('div', class_='td DescriptionCell')
      targetsites = 0
      for t in tr:
         site = t.find('a').string.lower()
         if site in alexa_blacklist:
            print >>sys.stderr, "this alexa-top site for country:%s was blocked by ixp-country-jedi blacklist: %s" % ( cc, site )
            print >>sys.stderr, "please adapt the blacklist (in source code) if you want this site measured anyways"
            continue
         # Check if the site is a duplicate (e.g. google.com, google.ru)
         site_elements = site.split(".")
         sitename = site_elements[0]
         if sitename in targetsitenames:
            print >>sys.stderr, "this site for country:%s is a duplicate: %s" % ( cc, site )
         else:
            targetsitenames.append(sitename)
            ## add 'www'?
            if targetsites < maxsites:
               targets.append( site )
               targetsites = targetsites + 1
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
      geocode_url = "http://api.geonames.org/searchJSON?q=%s&maxRows=10&username=%s" % ( locstr, GEONAMES_USER )

      req = urllib2.urlopen(geocode_url)

      resp = json.loads(req.read())
      if 'error_message' in resp:
         raise SystemExit("Maps geocode error: %s" % resp['error_message'])

      ll = resp['geonames'][0]
      return (float(ll['lat']), float(ll['lng']))
   except (ValueError, IndexError):
      print "could not determine lat/long for '%s'" % ( locstring )
      pass


def extract_websites_in_tld(country_code, max_results=100):
   """Given a TLD, fetch a list of the top websites in this TLD for use as
   targets"""
   base_url = ("https://domainpunch.com/tlds/topm.php?dtd&draw=3"
      "&columns[0][data]=0&columns[0][name]=&columns[0][searchable]=true"
      "&columns[0][orderable]=false&columns[0][search][value]="
      "&columns[0][search][regex]=false&columns[1][data]=1&columns[1][name]="
      "&columns[1][searchable]=true&columns[1][orderable]=true"
      "&columns[1][search][value]=&columns[1][search][regex]=false"
      "&columns[2][data]=2&columns[2][name]=&columns[2][searchable]=true"
      "&columns[2][orderable]=true&columns[2][search][value]="
      "&columns[2][search][regex]=false&columns[3][data]=3&columns[3][name]="
      "&columns[3][searchable]=true&columns[3][orderable]=true"
      "&columns[3][search][value]={}&columns[3][search][regex]=false"
      "&columns[4][data]=4&columns[4][name]=&columns[4][searchable]=true"
      "&columns[4][orderable]=true&columns[4][search][value]="
      "&columns[4][search][regex]=false&order[0][column]=2&order[0][dir]=asc"
      "&start=0&length={}&search[value]=&search[regex]=false"
   ).format(country_code.lower(), max_results)
   websites = json.loads(urllib2.urlopen(base_url).read())
   return [website['1'] for website in websites['data']]

def calculate_cost_of_measurement(selected_probes):
   ## Calculate the number of IPv4 and IPv6 addresses
   number_of_addresses = {"ipv4" : 0, "ipv6" : 0}
   for probe in selected_probes:
      if('address_v4' in probe and probe['address_v4'] != None and "system-ipv4-stable-1d" in probe['tags']):
         number_of_addresses['ipv4'] += 1
      if('address_v6' in probe and probe['address_v6'] != None and "system-ipv6-stable-1d" in probe['tags']):
         number_of_addresses['ipv6'] += 1
   credits_ipv4 = ( int(number_of_addresses['ipv4']) * (int(number_of_addresses['ipv4'])) ) * COST_OF_TRACEROUTE
   credits_ipv6 = ( int(number_of_addresses['ipv6']) * (int(number_of_addresses['ipv6'])) ) * COST_OF_TRACEROUTE
   print "* * *\nThe IXP Country Jedi will consume " + str(credits_ipv4+credits_ipv6) + " credits,"
   print str(credits_ipv4) + " and " + str(credits_ipv6) + " for IPv4 and IPv6 measurements, respectively. \n * * *"

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
   # country / or other probe selection
   ####
   ####### would be nice if we could do both country+probetag
   has_sources = False
   if 'country' in conf:
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
      has_sources = True
   if 'probetag' in conf:
      # selects probes with certain probetag and looks at their connectivity
      basedata['probetag'] = conf['probetag']
      has_sources = True
   if 'probe_ids' in conf:
      basedata['probe_ids'] = conf['probe_ids']
      has_sources = True
   if not has_sources:
      print >>sys.stderr, "need 'country' and/or 'probetag' or a list of probe ids ('probe_ids')"
      sys.exit(1)
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
         if 'alexa-maxsites' in conf:
            alexa_maxsites = conf['alexa-maxsites']
         else:
            alexa_maxsites = TOP_ALEXA_SITES
         basedata['targets'] = alexa_country_top25( basedata['countries'], alexa_maxsites )
      elif conf['target-type'] == 'local-news-traceroute' in conf['measurement-type']:
         pages = fetch_news_sites.fetch_country_pages()
         basedata['targets'] = [urlparse(url).hostname for url in
         fetch_news_sites.news_sites_for_country(pages[conf['country']])]
      elif 'local-tld-traceroute' in conf['measurement-type']:
         basedata['targets'] = extract_websites_in_tld(conf['country'])
      else:
         print >> sys.stderr, "unknown target-type of '%s' in config, bailing out"
         sys.exit(1)
   elif 'targets-from-websites' in conf:
      if type(conf['targets-from-websites']) != list:
         print >> sys.stderr, "unknown 'targets-from-websites' needs to be a list, baling out"
         sys.exit(1)
      basedata['targets'] = hitlist_from_websites( conf['targets-from-websites'] )
   ####
   # locations (only applies when 'countries' is in basedata
   ####
   ## If no location present, select the capital of the first country in list
   if len(basedata['countries']) > 0:
      print basedata
      if not 'locations' in conf or len( conf['locations'] ) == 0:
         capital_str,lat,lon = capital_city_for_country( basedata['countries'][0] )
         print >> sys.stderr, "No location info available for probe selection, defaulting to capital city of country (%s)" % ( capital_str )
         basedata['locations'][ capital_str ] = {'lat': lat, 'lon': lon} 
      else:
         for loc in conf['locations']:
            lat,lon = locstr2latlng( loc ) 
            basedata['locations'][ loc ] = {'lat': lat, 'lon': lon} 
      # 'constrain to only the probes X km from the location
      if 'location-constraint' in conf:
           basedata['location-constraint'] = conf['location-constraint']
   ### IXPs
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
   else:
      # get them all?
      # get them for countries, or if no country specified, get them all?
      pass
   if os.path.isfile('probeset.json'):
      print >>sys.stderr, "probeset.json file exists, not making a new probe selection"
   else: 
      selected_probes = []
      if 'probetag' in basedata and len(basedata['countries']) > 0:
         ## only take probes in these countries
         country_set = set( basedata['countries'] )
         print >>sys.stderr, "finding probes for tag: %s AND countries: %s" % ( basedata['probetag'], country_set )
         selected_probes = do_probe_selection_from_tag( basedata['probetag'] )
         selected_probes = filter( lambda x: x['country_code'] in country_set, selected_probes )
      elif len(basedata['countries']) > 0:
         for country in basedata['countries']:
            eyeball_threshold = conf.get('eyeball_threshold')
            print >>sys.stderr, "Preparing country: %s" % ( country )
            if eyeball_threshold:
               probes_cc = find_probes_in_country(country, True, eyeball_threshold)
            else:
               probes_cc = find_probes_in_country( country )
               print >>sys.stderr, "preselected %d probes for %s" % ( len( probes_cc ), country )
            sel_probes_for_cc = do_probe_selection( probes_cc, conf, basedata )
            print >>sys.stderr, "selected %d probes for %s" % ( len(sel_probes_for_cc), country )
            selected_probes += sel_probes_for_cc
         print >>sys.stderr, "found: %d probes" % ( len( sel_probes_for_cc ) )
         print >>sys.stderr, "END country: %s" % ( country )
         # If there are probes manually selected in config.json, add them as well
         if 'probe_ids' in basedata:
            probes_from_ids = []
            selected_probeids = []
            print >>sys.stderr, "Adding probes from probe_ids list"
            for sel_prb in selected_probes:
               selected_probeids.append(sel_prb['probe_id'])
            probes_from_ids = do_probe_selection_from_ids( basedata['probe_ids'] )
            # Add probes from probe_ids without duplicates
            for prb in probes_from_ids:
               if prb['probe_id'] not in selected_probeids:
                  selected_probes.append(prb)
      elif 'probetag' in basedata:
         print >>sys.stderr, "finding probes for tag: %s" % ( basedata['probetag'] )
         selected_probes = do_probe_selection_from_tag( basedata['probetag'] ) 
      elif 'probe_ids' in basedata:
         print >>sys.stderr, "finding probes for probe_ids list"
         selected_probes = do_probe_selection_from_ids( basedata['probe_ids'] ) 
        
      print >>sys.stderr, "found %s probes!" % ( len( selected_probes ) )
      ## estimate the cost of measurement
      calculate_cost_of_measurement(selected_probes)
      ## writing to probeset.json
      print "writing probe selection to probeset.json (%s probes)" % ( len( selected_probes ) )
      with open('probeset.json','w') as outfile:
         json.dump( selected_probes, outfile, indent=2 )
      print >>sys.stderr, "writing basedata (locations/ixps) to basedata.json"
   with open('./basedata.json','w') as bdfile:
      json.dump( basedata, bdfile, indent=2 )
