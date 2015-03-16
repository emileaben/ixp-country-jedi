#!/usr/bin/env python
import os
import sys
sys.path.append("%s/lib" % ( os.path.dirname(os.path.realpath(__file__) ) ) )
from Atlas import MeasurementFetch,MeasurementPrint,IPInfoCache
import json
import urllib2
import ripe.atlas.sagan
import ipaddress
import re
#import random

ipinfo = {}

def get_asnmeta( asn ):
   meta = {'asn': asn, 'as_name': '<unknown>', 'as_description': '<unknown>', 'as_country': 'XX', 'ips_v4': None, '48s_v6': None}
   ### find long name and asn-size
   ## call https://stat.ripe.net/data/as-overview/data.json?resource=%s
   ## and https://stat.ripe.net/data/routing-status/data.json?resource=%s
   name_url = "https://stat.ripe.net/data/as-overview/data.json?resource=AS%s" % ( asn )
   size_url = "https://stat.ripe.net/data/routing-status/data.json?resource=AS%s" % ( asn )
   try:
      nconn = urllib2.urlopen( name_url , timeout=60 )
   except:
      try:
         nconn = urllib2.urlopen( name_url , timeout=60 )
      except:
         print "URL fetch error on: %s" % (name_url)
         #raise ValueError("URL fetch error on: %s" % (name_url) )
   try:
      ndata = json.load( nconn )
      holder = ndata['data']['holder']
      name,desc_cc = holder.split(" ",1)
      desc,cc = desc_cc.rsplit(",",1)
      meta['as_name'] = name
      meta['as_description'] = desc
      meta['as_country'] = cc
   except:
      print "asn name extraction failed for %s" % ( asn )
   try:
      sconn = urllib2.urlopen( size_url , timeout=60 )
   except:
      try:
         sconn = urllib2.urlopen( size_url , timeout=60 )
      except:
         print "URL fetch error on: %s" % (name_url)
         #raise ValueError("URL fetch error on: %s" % (size_url) )
   try:
      sdata = json.load( sconn )
      meta['ips_v4'] = sdata['data']['announced_space']['v4']['ips']
      meta['48s_v6'] = sdata['data']['announced_space']['v6']['48s']
   except:
      print "asn size extraction failed for %s" % ( asn )
   return meta

def main():
   ips=set()
   with open('measurementset.json','r') as infile:
      msms = json.load( infile )
      msm_list = msms['v4'] + msms['v6']
#      random.shuffle( msm_list ) 
      count=0
      for m in msm_list:
         print >>sys.stderr, "(%d/%d) msm gathering, now fetching %s" % ( count, len(msm_list), m )
         for data in MeasurementFetch.fetch( m['msm_id'] ):
            tr = ripe.atlas.sagan.TracerouteResult( data )
            for hop in tr.hops:
               for pkt in hop.packets:
                  ip = pkt.origin
                  if pkt.arrived_late_by: ## these are 'weird' packets ignore ehm (better would be to filter out pkts with 'edst')
                     continue
                  if ip != None:
                     ips.add( ip )
         count+=1
   no_ips = len(ips)
   print >>sys.stderr, "ip gathering finished, now analysing. ip count: %s" % ( no_ips )
   ipcache = IPInfoCache.IPInfoCache()
   counter=1
   ips = list(ips)
   ips.sort()
   asns = set()
   for ip in ips:
      res= ipcache.findIPInfo( ip )
      print "(%d/%d) %s / %s" % ( counter, no_ips, ip, res )
      counter += 1
      if 'asn' in res and res['asn'] != None and res['asn'] != '':
         asns.add( res['asn'] )
   # writes this file
   ipcache.toJsonFragments('ips.json-fragments')
   asn_info = []
   for asn in asns:
      asnmeta = get_asnmeta( asn )
      print asnmeta
      asn_info.append( asnmeta )
   with open('asns.json','w') as asnf:
      json.dump(asn_info, asnf, indent=4) 
   
main()
