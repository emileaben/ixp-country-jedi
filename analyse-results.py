#!/usr/bin/env python
import json
import sys
import os
import shutil
import math
import codecs
from collections import Counter

## this allows to pipe output to a file and have it be utf-8
# adapted from http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

BASEDIR=os.path.dirname( os.path.realpath(__file__) )
PROBE_BLACKLIST_FILE="%s/probe-blacklist.txt" % BASEDIR

# globally available
PROBES = []
with open('probeset.json','r') as probesin:
   PROBES = json.load( probesin )
PROBES_BY_ID = {}
for p in PROBES:
   PROBES_BY_ID[ p['probe_id'] ] = p

PROBE_BLACKLIST = set()
if os.path.isfile( PROBE_BLACKLIST_FILE ):
    with open( PROBE_BLACKLIST_FILE ) as inf:
        for line in inf:
            line = line.rstrip('\n');
            try:
                prb_id,rest = line.split(None,1)
                prb_id = int(prb_id)
                PROBE_BLACKLIST.add( prb_id )
                print "PROBE %s blacklisted" % prb_id
            except:
                print "can't parse this line in %s: %s" % ( PROBE_BLACKLIST_FILE, line )
                sys.exit(1)

## filter probe list through blacklist

def data_line_generator():
   infilename = 'measurementset.json'
   proto = None
   with open(infilename,'r') as infile:
      msms = json.load( infile , encoding='utf-8')
      for meas_proto in msms:
         proto = meas_proto
         for msm_entry in msms[meas_proto]:
            if 'msm_id' in msm_entry:
               with open('./results/msm.%s.json' % ( msm_entry['msm_id'] ),'r') as msmfile:
                  data = json.load( msmfile )
                  for entry in data:
                     if 'src_prb_id' in entry and entry['src_prb_id'] in PROBE_BLACKLIST:
                        continue
                     elif 'dst_prb_id' in entry and entry['dst_prb_id'] in PROBE_BLACKLIST:
                        continue
                     else:
                        yield proto, entry
            else:
               print >>sys.stderr," error on msm entry: %s " % ( msm_entry )


### common . For stuff general enough to apply to multiple analyses.
### example is text representation for traces, indexed by srcprb.dstprb
def init_common( basedata, probes ):
  return {'v4': {}, 'v6': {}, 'timestamps': set() } 

def do_common_entry( data, proto, data_entry ):
   detail_key = '.'.join(map(str,[ data_entry['src_prb_id'] , data_entry['dst_prb_id'] ]))
   if not detail_key in data[proto]:
      data[proto][detail_key] = []
   data[proto][detail_key].append( data_entry )

   ## support timestamps
   data['timestamps'].add(data_entry['ts'])
   

def do_common_printresult( data ):
   COMMONPATH='./analysis/common/details'
   for proto in ('v4','v6'):
      cpp = "%s/%s" % (COMMONPATH,proto)
      for detail_key in data[ proto ].keys():
         data_sorted = sorted( data[proto][detail_key], key=lambda x:x['ts'])
         data_latest = data_sorted[-1]
         src_prb,dst_prb = detail_key.split('.')
         ldir = "%s/%s/%s/%s" % ( COMMONPATH, proto, src_prb, dst_prb )
         if not os.path.exists( ldir ):
            os.makedirs( ldir )
         latest_file = "%s/latest.json" % (ldir)
         # see ixpcountry template for example of how to use these latest.json files
         with open(latest_file, 'w') as outfile:
            json.dump( data_latest, outfile )

   ## CommonInit
   CommonFormat = {} 

   ## Timestamp period (Alex ixp tools codespring)     
   # Inits    
   ts_Start =  sys.maxint   
   ts_End   = -sys.maxint 
   from datetime import datetime

   for time in data['timestamps']:
      if time < ts_Start:
         ts_Start = time
      if time > ts_End:
         ts_End = time
   CommonFormat["StartTime"] = ts_Start
   CommonFormat["EndTime"]   = ts_End
   CommonFormat["StartUTC"] = str(datetime.utcfromtimestamp(ts_Start))
   CommonFormat["EndUTC"]   = str(datetime.utcfromtimestamp(ts_End))
   print "\nTimestamp period: %d - %d "%(CommonFormat["StartTime"],CommonFormat["EndTime"])
   print "UTC time period : %s - %s "%(CommonFormat["StartUTC"],CommonFormat["EndUTC"])

   ## Unique AS list calculation (Alex ixp tools codespring) 
   ASV4 = set()
   ASV6 = set()
   for p in PROBES:
      if p['asn_v4'] is not None:
         ASV4.add(p['asn_v4'])
      if p['asn_v6'] is not None:
         ASV6.add(p['asn_v6'])
   CommonFormat["ASV4"] = list(ASV4)
   CommonFormat["ASV6"] = list(ASV6)

   ## Printing to file
   with open(COMMONPATH+'/MsmDescr.json','w') as outfile:
      json.dump( CommonFormat, outfile, indent=2 )
   print "CommonInfo at: '%s'" % (COMMONPATH+'MsmDescr.json')

### perasn
def init_perasn( basedata, probes ):
    d = {'asns': {}}
    return d

def do_perasn_entry( asns_d , proto, data ):
    terminal_asns = set()
    try:
        src_asn = PROBES_BY_ID[ data['src_prb_id'] ]['asn_%s' % proto ]
        if src_asn != None:
            terminal_asns.add( src_asn )
        dst_asn = PROBES_BY_ID[ data['dst_prb_id'] ]['asn_%s' % proto ]
        if dst_asn != None:
            terminal_asns.add( dst_asn )
    except:
        # remove for now
        pass
    if len(terminal_asns) != 2:
        return
    for asn in terminal_asns:
        other_asn = filter(lambda x: x != asn, terminal_asns)[0]
        asns_d['asns'].setdefault( asn, {'facets': {
            'out_of_country':   {'asns': {}, 'path_count': 0},
            'intermediates':    {'asns': {}, 'path_count': 0}
        } } )
        ## process the facet: 'out_of_country'
        if data['in_country'] == False:
            asns_d['asns'][ asn ]['facets']['out_of_country']['asns'].setdefault( other_asn, [] )
            asns_d['asns'][ asn ]['facets']['out_of_country']['asns'][ other_asn ].append(
                {
                    'src_prb_id': data['src_prb_id'],
                    'dst_prb_id': data['dst_prb_id'],
                    'proto': proto
                }
            )
            asns_d['asns'][ asn ]['facets']['out_of_country']['path_count'] += 1
        ## process next facet. did we detect extra ASNs between src and dst
        src_dst_with_intermediates = set() #need this because of duplicates
        for intermediate in data['as_links']['nodes']:
            if intermediate in terminal_asns:
                continue
            if intermediate.startswith('_'): # it's an IXP
                continue
            src_dst_with_intermediates.add( ( data['src_prb_id'], data['dst_prb_id'] ) )
        for sdwi in src_dst_with_intermediates:
            asns_d['asns'][ asn ]['facets']['intermediates']['asns'].setdefault( other_asn, [] )
            asns_d['asns'][ asn ]['facets']['intermediates']['asns'][ other_asn ].append(
                {
                   'src_prb_id': sdwi[0],
                   'dst_prb_id': sdwi[1],
                   'proto': proto
                }
            )
            asns_d['asns'][ asn ]['facets']['intermediates']['path_count'] += 1
        ## process next facet, symmetry?
        ## hmmm. would need a lot of caching and put it in printresult?
        ## just show the probes then

def do_perasn_printresult( asns_d ):
   DATAPATH='./analysis/perasn/'
   if not os.path.exists( DATAPATH ):
      os.makedirs( DATAPATH )
   for asn,asn_data in asns_d['asns'].iteritems():
      asn_file = "%s/%s.json" % ( DATAPATH, asn)
      # see ixpcountry template for example of how to use these latest.json files
      with open(asn_file, 'w') as outfile:
         json.dump( asn_data, outfile, indent=2 )


### ixpcount
def init_ixpcount( basedata, probes ):
   ixps = {
      'ixps_per_path': {},
      'seen': {'_none': 0, '_total': 0},
      'seen_v4': {'_none': 0, '_total': 0},
      'seen_v6': {'_none': 0, '_total': 0}
   }
   return ixps

def do_ixpcount_entry( ixps, proto, data ):
   # proto_key (either 'seen_v4' or 'seen_v6')
   pkey = 'seen_%s' % ( proto )
   if not 'ixps' in data:
      print "no ixp?!"
      return
   if not len(data['ixps']) in ixps['ixps_per_path']:
      ixps['ixps_per_path'][ len( data['ixps'] )] = 0
   ixps['ixps_per_path'][ len( data['ixps'] )] += 1
   ixps['seen']['_total'] += 1
   ixps[pkey]['_total'] += 1
   if len(data['ixps']) == 0:
      ixps['seen']['_none'] += 1
      ixps[pkey]['_none'] += 1
   else:
      for ixp in data['ixps']:
         if ixp not in ixps['seen']:
            ixps['seen'][ixp] = 0
         ixps['seen'][ixp] += 1
         if ixp not in ixps[pkey]:
            ixps[pkey][ixp] = 0
         ixps[pkey][ixp] += 1

def do_ixpcount_printresult( ixps ):
   print "Results for: IXPcount analysis"
   print "=============================="
   #print "%s" % ( ixps )
   key2desc = [
      ['seen', "Overall"],
      ['seen_v4', "IPv4"],
      ['seen_v6', "IPv6"]
   ]
   for kv in key2desc:
      (key,desc) = kv
      txt = "Results %s" % ( desc )
      print txt
      print '=' * len(txt)
      for ixp in sorted( ixps[ key ], key=lambda x: ixps[ key ][x] , reverse=True ):
         pct = 0
         try:
            pct = 100.0*ixps[key][ixp]/ixps[key]['_total']
         except: pass
         print "%02d\t%.1f%%\t%s" % ( ixps[key][ixp] , pct, ixp )

### incountry
def init_incountry( basedata, probes ):
   data = {
      'countries': basedata['countries'],
      'routed_asns': 0,
      'probes': PROBES,
   }
   for cc in basedata['country-stats']:
      if 'routed_asns' in basedata['country-stats'][ cc ]:
         if basedata['country-stats'][ cc ]['routed_asns'] != None:
            data['routed_asns'] += basedata['country-stats'][ cc ]['routed_asns']
   for proto in ('v4','v6'):
      data[ proto ] = {
         'path_count': 0,
         'incountry_count': 0,
         'abroad': {},
         'ooc_probes': Counter()   #tracks the probes that cause out of country paths (both src and dst)
      }
   return data

def do_incountry_entry( data, proto, entry ):
   data[ proto ]['path_count'] += 1
   if entry['in_country'] == True:
      data[ proto ]['incountry_count'] += 1
   elif entry['in_country'] == False:
      data[ proto ]['ooc_probes'][ entry['src_prb_id'] ] += 1
      data[ proto ]['ooc_probes'][ entry['dst_prb_id'] ] += 1
   country_set = set()
   for loc in entry['locations']:
      country = None
      try: 
         country = loc.split(',')[-1]
         country_set.add( country )
      except: pass
   for country in country_set:      
      #TODO exclude guest country
         if not country in data['countries']:
            if not country in data[ proto ]['abroad']:
               data[ proto ]['abroad'][ country ] = 0
            data[ proto ]['abroad'][ country ] += 1

def do_incountry_printresult( data ):
   DATAPATH='./analysis/incountry/'
   if not os.path.exists( DATAPATH ):
      os.makedirs( DATAPATH )
   # ooc = out of country
   ooc_pct = {'v4': None, 'v6': None}
   ooc_pct_per_ooc = {'v4': Counter(), 'v6': Counter()}
   print "Paths with out-of-country IP addresses"
   print "========================================="
   for proto in ('v4','v6'):
      if data[ proto ]['path_count'] > 0:
         ooc_pct[ proto ] = 100 - data[ proto ]['incountry_count'] * 100.0 / data[ proto ]['path_count']
         print "IP%s : %.2f%%" % ( proto , ooc_pct[ proto ] )
         for country in sorted( data[ proto ]['abroad'], key=lambda x:data[proto]['abroad'][x], reverse=True):
            cnt = data[ proto ]['abroad'][ country ]
            pct = cnt * 100.0 / data[ proto ]['path_count']
            ooc_pct_per_ooc[ proto ][ country ] = pct
            print "  %s : %.2f%% (%d)" % ( country , pct, cnt)
         ## probes contributing most to out of country:
         print "TOP 10 probes contributing to out-of-country-paths"
         for prb_id,count in data[ proto ]['ooc_probes'].most_common(10):
            involvepct = 100.0 * count / math.sqrt( data[ proto ]['path_count'] ) # roughly correct
            print "  prb_id:%s / AS%s / %d/%d paths / involvepct:%.1f" % ( prb_id, PROBES_BY_ID[prb_id]['asn_%s' % proto] , count, data[proto]['path_count'], involvepct )
   print "Country stats based on this"
   print "---------------------------"
   probe_asns = {'v4': set(), 'v6': set()}
   for prb_info in data['probes']:
      if 'asn_v4' in prb_info and prb_info['asn_v4'] != None:
         probe_asns['v4'].add( prb_info['asn_v4'] )
      if 'asn_v6' in prb_info and prb_info['asn_v6'] != None:
         probe_asns['v6'].add( prb_info['asn_v6'] )
   print "   ASNs in routing: %s" % ( data['routed_asns'] )
   probe_asn_counts =  {'v4': None, 'v6': None}
   for proto in ('v4','v6'):
      cnt = len(probe_asns[ proto ])
      print "   ASNs with public probes: %s (%s)" % ( cnt, proto )
      probe_asn_counts[ proto ] = cnt
   inc_data = {
      'routed_asn_count': data['routed_asns'],
      'probe_asn_count': probe_asn_counts,
      'out_of_country_pct': ooc_pct,
      'out_of_country_country_pct': {
        'v4': ooc_pct_per_ooc['v4'].most_common(),
        'v6': ooc_pct_per_ooc['v6'].most_common()
      }
   }
   inc_json_file = "%s/incountry.json" % ( DATAPATH )
   with open( inc_json_file,'w') as outf:
      json.dump( inc_data, outf )
   print "INCOUNTRY data file at: '%s'" % (inc_json_file)

### ixpcountry
def init_ixpcountry( basedata, probes ):

   rows = { 'v4' : list(), 'v6' : list() }
   _6to4 = []
   for probe in PROBES:
      if(probe['asn_v6'] == None and 'address_v6' in probe.keys() and probe['address_v6'] != None):
        if(probe['address_v6'][:4] == '2002'):
          _6to4.append(probe['probe_id'])

      if('address_v4' in probe and probe['address_v4'] != None and "system-ipv4-works" in probe['tags']):
         rows['v4'].append({
            'id': probe['probe_id'],
            'asn_v4': probe['asn_v4'],
            'asn_v6': probe['asn_v6']
         })

      if('address_v6' in probe and probe['address_v6'] != None and "system-ipv6-works" in probe['tags']):
         rows['v6'].append({
            'id': probe['probe_id'],
            'asn_v4': probe['asn_v4'],
            'asn_v6': probe['asn_v6']
         })

   ## can do data reduction step here if data is too big
   d = {'summary':{},'details':{}}
   for proto in ('v4','v6'):
      d['summary'][proto] = {
         'rows': rows[proto],
         'cols': rows[proto],
         'cells': [],
         '_6to4': _6to4,
      }
      d['details'][proto] = {}
   return d

def do_ixpcountry_entry( ixpcountry, proto, data ):
   my_cells = ixpcountry['summary'][proto]['cells']
   my_cells.append({
      'row': data['src_prb_id'],
      'col': data['dst_prb_id'],
      'data': {'in_country': data['in_country'], 'via_ixp': data['via_ixp']}
   })
   details = ixpcountry['details'][proto]
   detail_key = '.'.join(map(str,[ data['src_prb_id'] , data['dst_prb_id'] ]))
   details[ detail_key ] = data

def do_ixpcountry_printresult( ixpcountry ):
   VIZPATH='./analysis/ixpcountry/'
   VIZDETAILSPATH='./analysis/ixpcountry/details'
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   if not os.path.exists( VIZDETAILSPATH ):
      os.makedirs( VIZDETAILSPATH )
   for proto in ('v4','v6'):
      with open('%s/ixpcountry.%s.json' % (VIZPATH,proto), 'w') as outfile:
         json.dump( ixpcountry['summary'][ proto ], outfile )
      for detail_key in ixpcountry['details'][ proto ].keys():
         with open('%s/%s.%s.json' % ( VIZDETAILSPATH, detail_key, proto ), 'w') as outfile:
            json.dump( ixpcountry['details'][ proto ][ detail_key ], outfile )
   print "IXPCOUNTRY viz results available in %s" % ( VIZPATH )

### rttmesh
def init_rttmesh( basedata, probes ):

   rows = { 'v4' : list(), 'v6' : list() }
   _6to4 = []
   for probe in PROBES:
      if(probe['asn_v6'] == None and 'address_v6' in probe.keys() and probe['address_v6'] != None):
        if(probe['address_v6'][:4] == '2002'):
          _6to4.append(probe['probe_id'])

      if('address_v4' in probe and probe['address_v4'] != None and "system-ipv4-works" in probe['tags']):
         rows['v4'].append({
            'id': probe['probe_id'],
            'asn_v4': probe['asn_v4'],
            'asn_v6': probe['asn_v6']
         })

      if('address_v6' in probe and probe['address_v6'] != None and "system-ipv6-works" in probe['tags']):
         rows['v6'].append({
            'id': probe['probe_id'],
            'asn_v4': probe['asn_v4'],
            'asn_v6': probe['asn_v6']
         })

   ## can do data reduction step here if data is too big
   d = {'summary':{},'details':{}}
   for proto in ('v4','v6'):
      d['summary'][proto] = {
         'rows': rows[proto],
         'cols': rows[proto],
         'cells': [],
         '_6to4': _6to4,
      }
      d['details'][proto] = {}
   return d

def do_rttmesh_entry( rttmesh, proto, data ):
   my_cells = rttmesh['summary'][proto]['cells']
   my_cells.append({
      'row': data['src_prb_id'],
      'col': data['dst_prb_id'],
      'data': {'dst_rtts': data['dst_rtts']}
   })
   details = rttmesh['details'][proto]
   detail_key = '.'.join(map(str,[ data['src_prb_id'] , data['dst_prb_id'] ]))
   details[ detail_key ] = data

def do_rttmesh_printresult( rttmesh ):
   VIZPATH='./analysis/rttmesh/'
   VIZDETAILSPATH='./analysis/rttmesh/details'
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   if not os.path.exists( VIZDETAILSPATH ):
      os.makedirs( VIZDETAILSPATH )
   for proto in ('v4','v6'):
      with open('%s/rttmesh.%s.json' % (VIZPATH,proto), 'w') as outfile:
         json.dump( rttmesh['summary'][ proto ], outfile )
      for detail_key in rttmesh['details'][ proto ].keys():
         with open('%s/%s.%s.json' % ( VIZDETAILSPATH, detail_key, proto ), 'w') as outfile:
            json.dump( rttmesh['details'][ proto ][ detail_key ], outfile )
   print "RTTMESH viz results available in %s" % ( VIZPATH )

### aspath
def init_asgraph( basedata, probes ):
   d = {'nodes': Counter(),
        'links': Counter()
       }
   return d

def do_asgraph_entry( d, proto, entry ):
   # 'meta'-characters:
   ## '#': probe
   ## '_': ixp

   # make sure source probe is a link in the viz too
   #src_prb_meta = '#probe_%s' % entry['src_prb_id']
   src_prb_meta = '#%s' % PROBES_BY_ID[ entry['src_prb_id'] ]['description']
   src_prb_asn =  PROBES_BY_ID[ entry['src_prb_id'] ]['asn_v4']
   if src_prb_asn != None:
      src_prb_asn = "AS%s" % src_prb_asn
      d['nodes'][ src_prb_meta ] += 1
      d['nodes'][ src_prb_asn ] += 0
      link_key = '>'.join([ src_prb_meta, src_prb_asn, 'prb' ])
      d['links'][ link_key ] += 1

   # now the AS links
   for n in entry['as_links']['nodes']:
      d['nodes'][ n ] += 1
   for l in entry['as_links']['links']:
      ## {u'src': u'NETNOD-MMO-B-1500', u'dst': u'AS29518', u'type': u'd'}
      link_key = '>'.join([ l['src'], l['dst'], l['type'] ])
      d['links'][ link_key ] += 1
   
def do_asgraph_printresult( d ):
   result = {'nodes': [], 'edges': []}
   VIZPATH='./analysis/asgraph/'
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   name2idx={}
   idx=0
   for n in d['nodes']:
      count = d['nodes'][n]
      name2idx[ n ] = idx
      typ = 'asn'
      if n.startswith('_'):
         typ = 'ixp'
         n = n.lstrip('_');
      elif n.startswith('#'):
         typ = 'prb'
         n = n.lstrip('#');
      result['nodes'].append({'id': idx, 'name': n, 'type': typ, 'count': count })
      idx += 1
   for l in d['links']:
      src,dst,typ = l.split('>',2)
      if src in name2idx and dst in name2idx:
        result['edges'].append({'source': name2idx[src], 'target': name2idx[dst], 'type': typ})
      else: 
        print >>sys.stderr, "problem with this src/dst: %s/%s" % ( src, dst )
   with open('%s/asgraph.json' % ( VIZPATH), 'w') as outfile:
      json.dump( result , outfile )
   print "ASGRAPH viz results in '%s'" % ( VIZPATH )

## geopath stuff
def init_geopath( basedata, probes ):
   return {'v4':[], 'v6':[]}

def do_geopath_entry( data, proto, data_entry ):
   geojson_pieces = data_entry['geojson']
   for piece in geojson_pieces:
      # {u'type': u'LineString', u'properties': {u'dloc': u'Stockholm,Stockholm,SE', u'is_direct': False, u'dasn': u'', u'sloc': u'Probe', u'sasn': u'59521', u'asn': None}, u'coordinates': [[u'18.0385', u'59.3305'], [u'18.0649', u'59.33258']]}
      # leaflet is picky on it's GeoJson?
      prop = piece['properties']
      del( piece['properties'] )
      data[ proto ].append({
         'geometry': piece,
         'properties': prop,
         'type': 'Feature'
      })

def do_geopath_printresult( data ):
   VIZPATH='./analysis/geopath/'
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   for proto in ('v4','v6'):
      geojson = {'type':'FeatureCollection', 'features': data[ proto ] }
      with open('%s/geopath.%s.json' % ( VIZPATH, proto ), 'w') as outfile:
         json.dump( geojson , outfile )
   print "GEOPATH viz results in '%s'" % ( VIZPATH )

### ixplans (ixp-lans, not ix-plans ;) )
def init_ixplans( basedata, probes ):
   # group by IP
   struct = {}
   for proto in ('v4','v6'):
      struct[ proto ] = {
         'nodes': set(),
         'links': set(),
         'ixps': Counter()
      }
   return struct
def do_ixplans_entry( data, proto, data_entry ):
   src_prb_id = data_entry['src_prb_id']
   dst_prb_id = data_entry['dst_prb_id']
   data[ proto ]['nodes'].add( src_prb_id )
   data[ proto ]['nodes'].add( dst_prb_id )
   if 'ixps' in data_entry:
      for ixp in data_entry['ixps']:
         link_key = u'{}>{}>{}'.format(src_prb_id, dst_prb_id, ixp)
         data[ proto ]['links'].add( link_key )
         data[ proto ]['ixps'][ ixp ] += 1

def do_ixplans_printresult( data ):
   VIZPATH='./analysis/ixplans/'
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   for proto in ('v4','v6'):
      name2idx={}
      idx=0
      result = {'nodes': [], 'links': [], 'ixps': []}
      for n in data[proto]['nodes']:
         lat = PROBES_BY_ID[ n ]['lat']
         lon = PROBES_BY_ID[ n ]['lon']
         asn = PROBES_BY_ID[ n ]['asn_%s' % ( proto ) ]
         result['nodes'].append({'probe_id': n, 'asn': asn, 'lat': lat, 'lon': lon})
         name2idx[ n ] = idx
         idx += 1
      for l in data[proto]['links']:
         src,dst,ixp = l.split('>',2)
         result['links'].append({'source': name2idx[ int(src)], 'target': name2idx[ int(dst)], 'ixp': ixp})
      #for i in sorted( data[proto]['ixps'], key=lambda x:data[proto]['ixps'][x], reverse=True ):
      for i in sorted( data[proto]['ixps'], reverse=True ):
         result['ixps'].append( i )
      with open('%s/ixplans.%s.json' % ( VIZPATH, proto ), 'w') as outfile:
         json.dump( result , outfile )
   print "IXP LANs: viz results in '%s'" % ( VIZPATH )

### probetags
def init_probetags( basedata, probes ):
   return {}
def do_probetags_entry( data, proto, data_entry ):
   pass
def do_probetags_printresult( data ):
   print "PROBETAGS"
   VIZPATH="./analysis/probetags/"
   if not os.path.exists( VIZPATH ):
      os.makedirs( VIZPATH )
   tags = {
      'system': Counter(),
      'user': Counter()
   }
         
   json_out = {
      'system': [],
      'user': [],
   }
   for p in PROBES:
      if 'tags' in p:
         for t in p['tags']:
            if t.startswith('system-'):
               t = t[7:]
               tags['system'][ t ] += 1
            else:
               tags['user'][ t ] += 1
   for tagtype in tags:
      for tag in sorted( tags[tagtype].keys() ):
         json_out[tagtype].append({'text': tag, 'count': tags[tagtype][tag]})
   with open("%s/tags.json" % ( VIZPATH ), 'w') as outfile:
      json.dump( json_out, outfile )
   print "PROBE TAGS: viz results in '%s'" % ( VIZPATH )

   
### viaanchor
def init_viaanchor( basedata, probes ):
   data = {}
   for proto in ('v4','v6'):
      data[ proto ] = {
         'probeset': set(),
         'rtts': {}
      }
   return data

def do_viaanchor_entry( data, proto, data_entry ):
   #if data_entry['via_ixp'] == False and len( data_entry['dst_rtts'] ) > 0:
   if len( data_entry['dst_rtts'] ) > 0:
      key = '|'.join(map(str,[data_entry['src_prb_id'],data_entry['dst_prb_id']]))
      if not key in data[ proto ]:
         data[proto][ key ]['rtts'] = data_entry['dst_rtts']
      else:
         # in case of multiple intervals measured
         for rtt in data_entry['dst_rtts']:
            data[proto][ key ]['rtts'].append( rtt )

def do_viaanchor_printresult( data ):
   VIZPATH='./analysis/viaanchor';
   MIN_RESPONSE_COUNT=3
   ## anchors are 6XXX
   anchors = set( filter( lambda x:x>=6000 and x<7000, PROBES_BY_ID.keys() ) )
   for anchor_id in anchors:
      ANCHORPATH= "%s/%s/" % ( VIZPATH, anchor_id )
      if not os.path.exists( ANCHORPATH ):
         os.makedirs( ANCHORPATH )
      for proto in ('v4','v6'):
         result = {'cells':[], 'probeset': set()}
         for pair,rtts in data[ proto ].iteritems():
            if len( rtts ) < MIN_RESPONSE_COUNT: continue
            direct_minrtt = min(rtts)
            src_prb, dst_prb = pair.split('|')
            if anchor_id in (src_prb, dst_prb):
               continue
            pair1 = "%s|%s" % ( src_prb, anchor_id )
            pair2 = "%s|%s" % ( anchor_id, dst_prb )
            if not pair1 in data[ proto ]: continue
            if not pair2 in data[ proto ]: continue
            if len( data[ proto ][ pair1 ] ) < MIN_RESPONSE_COUNT: continue
            if len( data[ proto ][ pair2 ] ) < MIN_RESPONSE_COUNT: continue
            stitch_minrtt = min( data[ pair1 ] ) + min( data[ pair2 ] )
            result['probeset'].add( src_prb )
            result['probeset'].add( dst_prb )
            result['cells'].append({
               'src_prb': src_prb,
               'dst_prb': dst_prb,
               'direct_minrtt': direct_minrtt,
               'stitch_minrtt': stitch_minrtt,
               'stitch_rtt_gain': direct_minrtt - stitch_minrtt
            })
         result['probes'] = []
         for prb_id in result['probeset']:
            result['probes'].append({
            })
         with open("%s/stitching.%s.json" % ( ANCHORPATH, proto ) ,'w') as f:
            print >>f, json.dumps( result, indent=2 )
      print "VIAANCHOR viz results for anchor %s in '%s'" % ( anchor_id, ANCHORPATH )

def init_cities( basedata, probes ):
   return {'v4': Counter(), 'v6': Counter()}

def do_cities_entry( data, proto, data_entry ):
   for city in data_entry['locations']:
      data[proto][city] += 1

def do_cities_printresult( data ):
   print "CITIES"
   print "======"
   for proto in ('v4','v6'):
      print "IP%s" % ( proto )
      for city,count in data[ proto ].most_common():
         print "  %s (%s)" % (city, count)

### below might be easy to copy-paste for additional analyses
### stub 
def init_stub( basedata, probes ):
   return {}
def do_stub_entry( data, proto, data_entry ):
   pass
def do_stub_printresult( data ):
   pass

## http://stackoverflow.com/a/13814557/1520581
def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)

def main():
   ## ixps
   ### analysis types available
   # maybe can make a nice dispatch table out of this
   ### and/or specify this at command line, ie. ./analyse-results.py <analysis-name> <analysis-name>
   # 'ixp_county'
   # 'ixpcountry'
   basedata = None
   with open("basedata.json") as inf:
      basedata = json.load( inf )
   probes = None
   #with open("probeset.json") as inf:
   #   probes = json.load( inf )
   defs={
      'ixpcount': True,
      'incountry': True,
      'ixpcountry': True,
      'rttmesh': True,
      'cities': True,
      'asgraph': True,
      'geopath': True,
      'ixplans': True,
      'probetags': True,
      'viaanchor': False, ## buggy
      'perasn': True
   }
   #defs={'perasn': True}

   if len( sys.argv ) > 1:
      # take defs from stdin arguments
      # so you can say:   analyse-results.py incountry
      defs = {}
      for df in sys.argv[1:]:
        defs[df]=True

   defs['common']=True ## always true
   ### initialise all analyses
   data = {}
   ### copy template viz stuff
   copytree('%s/template/' % BASEDIR ,'./analysis')
   ## only the analyses that are 'True'
   analysis_list = sorted( filter(lambda x: defs[x], defs.keys() ) )
   for analysis in analysis_list:
      ## this is a fancy way of saying: 
      #data['ixpcount']   = init_ixpcount( basedata, probes )
      #data['incountry']   = init_incountryy( basedata, probes )
      data[ analysis ] = globals()['init_%s' % analysis]( basedata , PROBES )

   ### loop over all traceroutes
   for proto,data_entry in data_line_generator():
      for analysis in analysis_list:
         ## this calls:
         # do_ixpcountry_entry( data['ixpcountry'], proto, data_entry )
         globals()["do_%s_entry" % analysis]( data[ analysis ], proto, data_entry )

   ### print analyses results
   for analysis in analysis_list:
      globals()["do_%s_printresult" % analysis]( data[analysis] )

if __name__ == '__main__':
   #try:
      main()
   #except UnicodeEncodeError, e:
   #   print e
   #   print "If you encounter errors like described here:"
   #   print " http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file"
   #   print "Consider setting the env var: PYTHONIOENCODING=UTF-8"


