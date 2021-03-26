#!/usr/bin/env python
import os
import sys

from lib.Atlas import MeasurementFetch,MeasurementPrint,IPInfoCache
sys.path.append( os.path.dirname(os.path.realpath(__file__) ) )
from libixpcountryjedi import ip2asn,ip2hostname,ICJRun
import requests
import json
import urllib2
import ripe.atlas.sagan
import ipaddress
import re
import concurrent.futures
import threading
from multiprocessing import cpu_count
#import random

from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
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
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

ipinfo = {}
counter = 1

run = ICJRun('.')

### read openipmap info, and key by IP
#openipmap = {}
#with open("ips-openipmap.json-fragments") as inf:
#    for line in inf:
#        d = json.loads( line )
#        openipmap[ d['ip'] ] = d

def get_asnmeta( asn ):
   meta = {'asn': asn, 'as_name': '<unknown>', 'as_description': '<unknown>', 'as_country': 'XX', 'ips_v4': None, '48s_v6': None}
   ### find long name and asn-size
   ## call https://stat.ripe.net/data/as-overview/data.json?resource=%s
   ## and https://stat.ripe.net/data/routing-status/data.json?resource=%s
   name_url = "https://stat.ripe.net/data/as-overview/data.json?resource=AS%s" % ( asn )
   size_url = "https://stat.ripe.net/data/routing-status/data.json?resource=AS%s" % ( asn )
   MAX_RETRIES=5

   nconn = None
   nretries = 0
   if nconn == None and nretries <= MAX_RETRIES:
      try:
         nconn = urllib2.urlopen( name_url , timeout=60 )
      except:
         nretries += 1
   if not nconn:
      print "URL fetch error on: %s" % (name_url)
   else:
      try:
         ndata = json.load( nconn )
         holder = ndata['data']['holder']
         name_desc,cc = holder.rsplit(",",1)
         nd_list = name_desc.split(" ",1)
         name = nd_list[0]
         desc = None
         if len(nd_list) == 1:
            desc = nd_list[0]
         else:
            desc = nd_list[1]
         meta['as_name'] = name
         meta['as_description'] = desc
         meta['as_country'] = cc
      except:
         print "asn name extraction failed for %s (%s)" % ( asn, ndata )

   sconn = None
   sretries = 0
   if sconn == None and sretries <= MAX_RETRIES:
      try:
         sconn = urllib2.urlopen( size_url , timeout=60 )
      except:
         sretries += 1
   if not sconn:
      print "URL fetch error on: %s" % (size_url)
   else:
      try:
         sdata = json.load( sconn )
         meta['ips_v4'] = sdata['data']['announced_space']['v4']['ips']
         meta['48s_v6'] = sdata['data']['announced_space']['v6']['48s']
      except:
         print "asn size extraction failed for %s (%s)" % ( asn, sdata )
   return meta

def main():
   iprtt={}
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
                  rtt = pkt.rtt
                  if pkt.arrived_late_by: ## these are 'weird' packets ignore ehm (better would be to filter out pkts with 'edst')
                     continue
                  if ip != None:
                     if not ip in iprtt or iprtt[ ip ]['rtt'] > rtt:
                        iprtt[ ip ] = {
                            'rtt': rtt, 
                            'prb_id': tr.probe_id,
                            'msm_id': tr.measurement_id,
                        }


         count+=1
   ips = list( iprtt.keys() )
   ips.sort()
   ip_count = len( ips )
   print >>sys.stderr, "ip gathering finished, now analysing. ip count: %s" % ( ip_count )
   outf = open("ips.json-fragments","w")
   outf_geoerr = open('geo-err.json-fragments',"w")

   no_result_cnt = 0
   for ip in ips:
        print >>sys.stderr, "attempting %s" % ip
        j = None
        #if True:
        try:
            out = {'ip': ip, 'lon': None, 'location': '', 'lat': None, 'hostname': "", 'asn': "", 'geo_error': None}
            req = requests.get("https://ipmap.ripe.net/api/v1/locate/%s/partials?engines=probeslocation,crowdsourced,ixp" % ip , timeout=25 )
            j = req.json()
            j['ip'] = ip
            #del( j['meta'] )
            #print "%s" % json.dumps( j )
            have_result = False
            try:
                out['hostname'] = ip2hostname( ip )
            except:
                print >>sys.stderr, "hostname lookup failed for %s" % ip
                pass
            try:
                out['asn'] = ip2asn( ip )
            except:
                print >>sys.stderr, "asn lookup failed for %s" % ip
                pass
            if 'partials' in j and len( j['partials'] ) > 0:
                for p in j['partials']:
                    if not have_result and p['engine'] in ('probelocations','crowdsourced','ixp') and len( p['locations'] ) > 0:
                        #print '# %s' % ( p['locations'][0], )
                        for loc in p['locations']:
                            if 'cityNameAscii' in loc:
                                out['lat'] = loc['latitude']
                                out['lon'] = loc['longitude']
                                out['location'] = u"%s,%s" % ( loc['cityNameAscii'], loc['countryCodeAlpha2'] )
                                # {"ip": "213.19.197.126", "hostname": "infopact-ne.ear3.amsterdam1.level3.net", "lon": null, "location": "", "lat": null, "asn": 3356}
                                #print u'%s %s "%s"' % ( ip, p['engine'], loc['cityName'], loc['countryCodeAlpha2'] )
                                have_result = True
                                # now get the probe lat/lon and compare to ipmap + RTT
                                if out['lon'] and out['lat']:
                                        prb = run.probes_by_id[ iprtt[ ip ]['prb_id'] ]
                                        geodist = haversine( out['lon'], out['lat'], prb['lon'], prb['lat'] )
                                        rttdist = iprtt[ ip ]['rtt'] * 100
                                        # don't make geo_err judgements when prb-ip distance is under 100km
                                        if geodist < 100 or geodist < rttdist:
                                            out['geo_error'] = False
                                        else:
                                            out['geo_error'] = True
                                            g = out
                                            g['prb_id'] = iprtt[ip]['prb_id']
                                            g['msm_id'] = iprtt[ip]['msm_id']
                                            g['rtt'] = iprtt[ip]['rtt']
                                            g['geo_km'] = geodist
                                            g['rtt_km'] = rttdist
                                            print >>outf_geoerr, json.dumps( g )
                                            ## now reset the location, as we don't want it to be used in the real jedi
                                            out['lat'] = None
                                            out['lon'] = None
                                            out['location'] = ''
                                        print >>sys.stderr, "#RTT %s geo_km:%.2f rtt_km:%.2f prb_id:%s rtt:%.2f (%s)" % ( ip, geodist, rttdist, iprtt[ip]['prb_id'], iprtt[ip]['rtt'], out['geo_error'] )
                                else:
                                        print >>sys.stderr, "#error: no lat/lon in new ipmap?! %s" % ( out )
                                break
        except:
            print >>sys.stderr, "#error on json for %s: %s" % (ip, j )
        print >>outf, u'%s' % json.dumps( out )
        if not have_result:
            no_result_cnt += 1
        #if 'locations' in j and len( j['locations'] ) > 0:
        # do something smart with ipmap
   # and write out to ipmap.json-fragments

   # RIPEstat API slow/times out on very large ASNs 
   #asn_info = []
   #for asn in asns:
   #   asnmeta = get_asnmeta( asn )
   #   print asnmeta
   #   asn_info.append( asnmeta )
   #with open('asns.json','w') as asnf:
   #   json.dump(asn_info, asnf, indent=4) 
   
main()
