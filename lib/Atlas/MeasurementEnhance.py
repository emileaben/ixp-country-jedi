#!/usr/bin/env python
#### enhances a trace object with metadata
import socket
import urllib2
import json
from Atlas import IPInfoCache
from ripe.atlas.sagan import TracerouteResult
# http://code.google.com/p/py-radix/
from radix import Radix

## globals
ipcache=IPInfoCache.IPInfoCache()
cache_only=False
## manage IP cache
def IPInfoCacheFromFile( filename ):
   ''' loads the IPinfo cache from file '''
   global ipcache
   ipcache.fromJsonFragments( filename )
def setCacheOnly(flag):
   ''' configures the IPInfo cache to not try for missing info '''
   global cache_only
   cache_only = flag
def getipinfo( ip ):
   ## returns a hash of IP info and caches the result
   info = {}
   if cache_only:
      info = ipcache.getIPInfo(ip)
   else:
      info = ipcache.findIPInfo(ip)
   return info
### end IP-info related stuff

class TracerouteResultAnalysis( TracerouteResult ):
   pass

def __ipsetforhop( hop ):
   '''
   gets an hop object from ripe atlas traceroute json, and returns IP addresses for that hop
   '''
   ips = set()
   if 'result' in hop:
      for hr in hop['result']:
         if 'from' in hr:
            if hr['from'] not in ips:
               ips.add( hr['from'] )
   return ips

def togeojson( data, srcprb, dstprb ):
   '''
   converts a trace to geojson data
     srcprb and dstprb are dictionaries with probe info
     dstprb can be None if the dst is not a probe
   '''
   entries = []
   if 'result' in data:
      proto = data['proto']
      res = data['result']
      last_resp_hop_nr = 0
      last_resp_hop_locs = set(['%s|%s|Probe' % (srcprb['lat'],srcprb['lon'])  ])
      last_resp_hop_ases = set([ srcprb['asn_v4'] ] )
      if proto == 6:
            last_resp_hop_ases = set([ srcprb['asn_v6'] ] )
      for hop in res:
         this_resp_hop_nr = hop['hop']
         this_hop_locs = set()
         this_hop_ases = set()
         ips = __ipsetforhop( hop )
         for ip in ips:
            info = getipinfo( ip )
            if 'lat' in info and info['lat'] != None and 'lon' in info and info['lon'] != None:
               this_hop_locs.add( '%s|%s|%s' % ( info['lat'], info['lon'], info['location'] ) )
            if 'asn' in info and info['asn'] != '':
               this_hop_ases.add( info['asn'] )
         if len( this_hop_locs ) == 1 and len( last_resp_hop_locs ) == 1:    
            this_loc = list(this_hop_locs)[0]
            last_loc = list(last_resp_hop_locs)[0]
            if this_loc != last_loc:
               is_direct = True
               if this_resp_hop_nr - last_resp_hop_nr > 1:
                  is_direct = False #indirect
               slat,slon,sloc = last_loc.split('|')
               dlat,dlon,dloc = this_loc.split('|')
               sasn = '|'.join( map(str, list(last_resp_hop_ases) ) )
               dasn = '|'.join( map(str, list(this_hop_ases) ) )
               asn = None
               if sasn == dasn:
                  asn = sasn
               entries.append({
                  'type': 'LineString',
                  'coordinates': [[ slon, slat ], [ dlon, dlat ]],
                  'properties': {
                     'sloc': sloc,
                     'dloc': dloc,
                     'sasn': sasn,
                     'dasn': dasn,
                     'asn': asn,
                     'is_direct': is_direct
                  } 
               })
         elif len(this_hop_locs) == 0 or len(last_resp_hop_locs) == 0:
            pass #uninteresting
         else:
            #TODO cases where AS-hop-shifts seem to be happening, and other weird stuff
            ## ie. hop 2: ASX
            ##     hop 3: ASX,ASY
            print "Uncaught situation at hop no %s->%s: %s->: %s" % ( last_resp_hop_nr, this_resp_hop_nr , last_resp_hop_ases, this_hop_ases )
         if len(this_hop_locs) > 0:
            last_resp_hop_locs = this_hop_locs
            last_resp_hop_ases = this_hop_ases
            last_resp_hop_nr = this_resp_hop_nr
      # add dst probe info
      if len(last_resp_hop_locs) == 1 and dstprb:
         last_loc = list(last_resp_hop_locs)[0]
         slat,slon,sloc = last_loc.split('|')
         dlat = dstprb['lat']
         dlon = dstprb['lon']
         dloc = 'Probe'
         slat = float( slat )
         slon = float( slon )
         if slat != dlat and slon != dlon:
            asn = None
            sasn = '|'.join( map(str, list(last_resp_hop_ases) ) )
            dasn = dstprb['asn_v4']
            if proto == 'v6': dasn = dstprb['asn_v6']
            if sasn == dasn:
               asn = sasn
            entries.append({
               'type': 'LineString',
               'coordinates': [[ slon, slat ], [ dlon, dlat ]],
               'properties': {
                  'sloc': sloc,
                  'dloc': dloc,
                  'sasn': sasn,
                  'dasn': dasn,
                  'asn': asn,
                  'is_direct': False   #white lie, need to do better, eventually
               }
            })
      else:
         print "Uncaught situation at end of trace no %s: %s" % ( last_resp_hop_nr, last_resp_hop_ases )
   return entries

def aslinksplus( data, teh_radix ):
   '''
   Takes a raw traceroute result and returns a datastructure with ASes and links between them
   extra_nets_radix is an optional Radix object (for instance for IXP peering LANs) that specifies non-ASes prefixes that
   should be considered before origin-ASes.
   '''
   aslinks = {'_nodes': set(), '_links': set() }
   has_radix = False
   if isinstance(teh_radix, Radix):
      has_radix = True
   if 'result' in data:
      res = data['result']
      last_resp_hop_nr = None
      last_resp_hop_ases = set()
      for hop in res:
         this_resp_hop_nr = hop['hop']
         ips = __ipsetforhop( hop )
         this_hop_ases = set()
         for ip in ips:
            if has_radix and teh_radix.search_best( ip ):
               node = teh_radix.search_best( ip )
               nodename = node.data['name']
               ## prepend with '_' to be able to disambiguate from 'AS'
               this_hop_ases.add( '_%s' % (nodename) )
            else:
               info = getipinfo( ip )
               if 'asn' in info and info['asn'] != '':
                  this_hop_ases.add( 'AS%d' % (info['asn']) )
         if len(this_hop_ases) == 1 and len(last_resp_hop_ases) == 1:
            this_asn = list(this_hop_ases)[0]
            last_asn = list(last_resp_hop_ases)[0]
            if this_asn != last_asn:
               link_type = 'd' #direct
               if this_resp_hop_nr - last_resp_hop_nr > 1:
                  link_type = 'i' #indirect
               try:
                  #link_name = '>'.join(map(str,[last_asn,this_asn,link_type]))
                  link_name = u"{}>{}>{}".format(last_asn,this_asn,link_type)
               except:
                  print last_asn
                  print this_asn
                  print link_type
                  raise
               aslinks['_nodes'].add( this_asn )
               aslinks['_nodes'].add( last_asn )
               aslinks['_links'].add( link_name )
         elif len(this_hop_ases) == 0 or len(last_resp_hop_ases) == 0:
            pass #uninteresting
         else:
            #TODO cases where AS-hop-shifts seem to be happening, and other weird stuff
            ## ie. hop 2: ASX
            ##     hop 3: ASX,ASY
            print "Uncaught situation at hop no %s->%s: %s->: %s" % ( last_resp_hop_nr, this_resp_hop_nr , last_resp_hop_ases, this_hop_ases )
         if len(this_hop_ases) > 0:
            last_resp_hop_ases = this_hop_ases
            last_resp_hop_nr = this_resp_hop_nr
   aslinks['nodes'] = []
   for asn in aslinks['_nodes']:
      aslinks['nodes'].append( u"{}".format(asn) )
   aslinks['links'] = []
   for link in aslinks['_links']:
      src,dst,typ= link.split('>')
      aslinks['links'].append( {'src': src, 'dst': dst, 'type': typ } )
   del(aslinks['_links'])
   del(aslinks['_nodes'])
   return aslinks

def trace2txt( data ):
   res = data['result']
   msm_id = data['msm_id']
   for hop in res:
      ips = {}
      for hr in hop['result']:
         if 'from' in hr:
            if hr['from'] not in ips:
               ips[ hr['from'] ] = [ hr['rtt'] ]
            else:
               ips[ hr['from'] ].append( hr['rtt'] )
         else:
            print "%s err:%s" % ( hop['hop'] , hr )

      for ip in ips:
         host = ip
         try:
            ghba = socket.gethostbyaddr(ip)
            host = ghba[0]
         except: pass
         asn = None
         try:
            asninfo = urllib2.urlopen( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
            asnjson = json.load( asninfo )
            asn = asnjson['data']['asns'][0]['asn']
         except: pass
         print "%s [AS%s] %s (%s) %s" % ( hop['hop'], asn, host, ip , sorted(ips[ip]) )
