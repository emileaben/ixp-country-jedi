#!/usr/bin/env python
import socket
import urllib2
import json
import sys
import dns.resolver
import traceback
#import ssl
import time

#if hasattr(socket, 'setdefaulttimeout'):
#   socket.setdefaulttimeout(20)

class IPInfoCache():
    def __init__(self,**kwargs):
        self.ips = {}
        r = dns.resolver.Resolver()
        r.lifetime = 7.01
        self.resolver = r

    def getIPInfo(self,ip):
        if ip in self.ips:
            return self.ips[ip]
        else: 
            return {}

    def findIPInfo(self, ip):
        ''' tries to find info for this IP in cache, if not it will collect it from external sources '''
        self.findHostname(ip)
        self.findLocation(ip)
        self.findAsn(ip)
        return self.ips[ ip ]

    def getLocation(self, ip ):
        ''' get location from cache '''
        loc = None
        lat = None
        lon = None
        try: loc=self.ips[ip]['location']
        except: pass
        try: lat=self.ips[ip]['lat']
        except: pass
        try: lon=self.ips[ip]['lon']
        except: pass
        return loc,lat,lon

    def findLocation(self, ip ):
        ''' find location info, either from cache, or external data source (openipmap) '''
        t1 = time.time()
        loc,lat,lon = self.getLocation( ip ) 
        if not loc is None: ## loc is already set
            return loc,lat,lon
        if not ip in self.ips:
            self.ips[ip] = {}
        try:
            #gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            #locinfo = urllib2.urlopen( "https://marmot.ripe.net/openipmap/ipmeta.json?ip=%s" % ( ip ), context=gcontext )
            locinfo = urllib2.urlopen( "https://marmot.ripe.net/openipmap/ipmeta.json?ip=%s" % ( ip ) )
            locjson = json.load( locinfo )
            if len( locjson['crowdsourced'] ) > 0:
                loc = locjson['crowdsourced'][0]['canonical_georesult']
                lat = locjson['crowdsourced'][0]['lat']
                lon = locjson['crowdsourced'][0]['lon']
            else:
                loc = ''
        except:
            sys.stderr.write( "eeps: problem in loading routergeoloc for ip: %s\n" % ( ip ) )
            traceback.print_exc(file=sys.stderr)
            return None ## todo proper error handling
        self.ips[ip]['location'] = loc
        self.ips[ip]['lat'] = lat
        self.ips[ip]['lon'] = lon
        return loc,lat,lon

    def getAsn(self, ip ):
        ''' get asn from cache '''
        asn = None
        try: loc=self.ips[ip]['asn']
        except: pass
        return asn

    def findAsn(self, ip ):
        ''' find asn info, either from cache, or external data source (ripestat) '''
        asn = self.getAsn( ip )
        if asn: ## asn already set
            return asn
        if not ip in self.ips:
            self.ips[ip] = {}
        try:  
            asninfo = urllib2.urlopen( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
            asnjson = json.load( asninfo )
            if len( asnjson['data']['asns'] ) > 0:
                asn = asnjson['data']['asns'][0]['asn']
            else:
                asn = ''
        except: 
            sys.stderr.write( "eeps: problem in ASN for ip: %s\n" %  (ip ) )
            return None ## todo proper error handling
        self.ips[ip]['asn'] = asn
        return asn

    def getHostname(self, ip ):
        ''' get hostname from cache '''
        host = None
        try: host=self.ips[ip]['hostname']
        except: pass
        return host

    def findHostname(self, ip ):
        ''' find hostname info, either from cache, or external data source (reverse DNS query) '''
        host = self.getHostname( ip )
        if host: ## host already set
            return host
        if not ip in self.ips:
            self.ips[ip] = {}
        try:
            resolve = self.resolver.query(dns.reversename.from_address( ip ),'PTR')
            if len( resolve.response.answer ) > 0 :
                host = str(resolve.response.answer[0].items[0])
                host = host.rstrip('.')
                host = host.lower()
            else:
                host = ''
        except dns.resolver.NXDOMAIN: host = ''
        except Exception as e: 
            ## timeout?
            #print >>sys.stderr, " %s " % ( e )
            return None
        # at this point resolving worked
        self.ips[ip]['hostname'] = host
        return host

    def toJsonFragments(self, outfilename):
        ''' print ipinfo cache to file as fragmented json, 1 entry per line '''
        with open(outfilename,'w') as outf:
            for ip,ipinfo in self.ips.iteritems():
                ipinfo['ip'] = ip
                print >> outf, json.dumps( ipinfo )

    def fromJsonFragments(self, infilename):
        self.ips={}
        with open(infilename,'r') as inf:
            for line in inf:
                data = json.loads( line )
                ip = data['ip']
                del data['ip']
                self.ips[ ip ] = data
