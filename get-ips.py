#!/usr/bin/env python
from Atlas import MeasurementFetch,MeasurementPrint,IPInfoCache
import json
import ripe.atlas.sagan
import ipaddress
import sys
import re
#import random

ipinfo = {}

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
   for ip in ips:
      res= ipcache.findIPInfo( ip )
      print "(%d/%d) %s / %s" % ( counter, no_ips, ip, res )
      counter += 1
   # writes this file
   ipcache.toJsonFragments('ips.json-fragments')

main()
