#!/usr/bin/env python
import socket
import urllib2
import json
import sys
import arrow
import IPInfoCache

if hasattr(socket, 'setdefaulttimeout'):
   socket.setdefaulttimeout(20)

## globals
ipcache=IPInfoCache.IPInfoCache()
cache_only=False

def IPInfoCacheFromFile( filename ):
   ''' loads the IPinfo cache from file '''
   global ipcache
   ipcache.fromJsonFragments( filename )

def setCacheOnly(flag):
   ''' configures the IPInfo cache to not try for missing info '''
   global cache_only
   cache_only = flag

def _getips( data ):
   ips = set()
   for hop in data:
      if not 'result' in hop:
         continue
      for hr in hop['result']:
         if 'from' in hr and 'rtt' in hr:
            if hr['from'] not in ips:
               ips.add( hr['from'] )
   return ips

def getipinfo( ip ):
   ## returns a hash of IP info and caches the result
   info = {}
   if cache_only:
      info = ipcache.getIPInfo(ip)
   else:
      info = ipcache.findIPInfo(ip)
   return info

def trace2locs( data ):
   locs = set()
   msm_id = data['msm_id']
   ips = _getips( data['result'] )
   for ip in ips:
      ipdata = getipinfo(ip)
      loc = None
      try:
         loc = ipdata['location']
         if loc != '' and loc != None:
            locs.add( loc )
      except: pass
   return locs

def trace2txt( data, **kwargs ):
   '''
      text representation of a raw json traceroute structure as text, annotating it with ASN, hostname, geoloc
      required arguments:
         data: traceroute data (Atlas json.loads for individual measurement)
      optional arguments:
         hostnames=False : don't look up hostnames
   '''
   txt = ''
   res = data['result']
   msm_id = data['msm_id']
   print_hostnames = True
   if 'hostnames' in kwargs:
      print_hostnames = kwargs['hostnames']
   ## print a header
   tstring = arrow.get( data['timestamp'] ).format('YYYY-MM-DD HH:mm:ss ZZ')
   txt += "## msm_id:%s prb_id:%s dst:%s ts:%s\n" % (msm_id, data['prb_id'], data['dst_addr'], tstring )

   for hop in res:
      ips = {}
      err_set = set()
      if not 'result' in hop:
         continue
      for hr in hop['result']:
         if 'from' in hr and 'rtt' in hr:
            if hr['from'] not in ips:
               ips[ hr['from'] ] = [ hr['rtt'] ]
            else:
               ips[ hr['from'] ].append( hr['rtt'] )
         else:
            err_set.add( "%s err:%s\n" % ( hop['hop'] , hr ) )
      if len(err_set) > 0:
         txt += '\n'.join(list(err_set))

      for ip in ips:
         ipinfo = getipinfo(ip)
         host = ''
         try: host = ipinfo['hostname']
         except: pass
         asn = ''
         try: asn = ipinfo['asn']
         except: pass
         loc = '' 
         try: loc = ipinfo['location']
         except: pass
         #print "%s [AS%s] %s (%s) %s |%s| %s" % ( hop['hop'], asn, host, ip , sorted(ips[ip]), loc, type(loc) )
         if asn != '':
            asn = 'AS%s' % ( asn )
         if print_hostnames == False or host == None or host == '':
            host = ip
         if loc == None:
            loc = ''
         txt += "%s (%s) %s %s |%s|\n" % ( hop['hop'], asn, host , sorted(ips[ip]), loc.encode('ascii','replace') )
   return txt 
