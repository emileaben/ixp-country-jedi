#!/usr/bin/env python
#import socket
import glob
import json
import sys
import dns.resolver
import traceback
import requests
#import ssl
import time

class ICJRun(object):
    def __init__(self,basedir):
        self.basedir = basedir
        # base structures
        with open( "%s/config.json" % basedir ) as inf:
            self.config = json.load( inf )
        with open( "%s/probeset.json" % basedir ) as inf:
            self.probes = json.load( inf )
        with open( "%s/measurementset.json" % basedir ) as inf:
            self.measurements = json.load( inf )
        with open( "%s/ips.json-fragments" % basedir ) as inf:
            self.iplocs = []
            for line in inf:
                iploc = json.loads( line )
                self.iplocs.append( iploc )
        with open( "%s/basedata.json" % basedir ) as inf:
            self.basedata = json.load( inf )
        # keyed by useful keys
        self.probes_by_id = {}
        for prb in self.probes:
            self.probes_by_id[ prb['probe_id'] ] = prb
        self.measurements_by_id = {}
        for af in self.measurements:
            for msm in self.measurements[ af ]:
                self.measurements_by_id[ msm['msm_id'] ] = msm
                self.measurements_by_id[ msm['msm_id'] ]['af'] = af # record address family anyways
        self.iplocs_by_ip = {}
        for iploc in self.iplocs:
            self.iplocs_by_ip[ iploc['ip'] ] = iploc
    def __ipsetforhop( self, hop ):
        '''
        gets an hop object from ripe atlas traceroute json, and returns IP addresses for that hop
        '''
        ips = set()
        if 'result' in hop:
            for hr in hop['result']:
                if 'from' in hr and not 'late' in hr:
                    ips.add( hr['from'] )
        return ips

    def outOfCountryPaths( self ):
        lines = {} # keyed by lat0,lon0,lat1,lon1 tuples
        if isinstance( self.config['country'], list):
            config_country_set = set( self.config['country'] )
        else:
            config_country_set = set( [ self.config['country'] ] )
        ## find the location things are centered around in a deterministic way
        centroid = ()
        baselocs = self.basedata['locations'].keys()
        if len( baselocs ) == 1:
            centroid = self.basedata['locations'][ baselocs[0] ]
        else:
            raise
        for rfile in glob.glob("%s/results/*.json" % self.basedir):
            with open(rfile) as inf:
                traces = json.load( inf )
                for trace in traces:
                    segments = []
                    trace_out_of_country = False
                    # use centroids!
                    #src_prb_lat = self.probes_by_id[ trace['src_prb_id'] ]['lat']
                    #src_prb_lon = self.probes_by_id[ trace['src_prb_id'] ]['lon']
                    src_prb_lat = centroid['lat']
                    src_prb_lon = centroid['lon']
                    last_hop_w_loc = {
                        'nr': 0,
                        'locs': set( [ ( src_prb_lat, src_prb_lon ) ] ),
                        'country_codes': set( [ self.probes_by_id[ trace['src_prb_id'] ]['country_code'] ] )
                    }
                    if 'result' in trace:
                        for hopresult in trace['result']:
                            hop_out_of_country = False
                            this_hop = {
                                'nr': hopresult['hop'],
                                'locs': set(),
                                'country_codes': set()
                            }
                            ipset = self.__ipsetforhop( hopresult )
                            for ip in ipset:
                                try:
                                    iploc = self.iplocs_by_ip[ ip ]
                                    if isinstance( iploc['location'], unicode ) and iploc['location'] != '':
                                        loc_cc = iploc['location'].split(',')[-1]
                                        this_hop['country_codes'].add( loc_cc )
                                        if not loc_cc in config_country_set:
                                            hop_out_of_country = True
                                            trace_out_of_country = True
                                    if iploc['lat'] != None and iploc['lon'] != None:
                                        if hop_out_of_country:
                                            this_hop['locs'].add( ( iploc['lat'], iploc['lon'] ) )
                                        else:
                                            this_hop['locs'].add( ( centroid['lat'], centroid['lon'] ) )
                                except:
                                    print >>sys.stderr, "ERROR"
                            ## now process it!
                            if len( this_hop['locs'] ) == 1 and len( last_hop_w_loc['locs'] ) == 1:
                                this_loc = list(this_hop['locs'])[0]
                                last_loc = list(last_hop_w_loc['locs'])[0]
                                if this_loc != last_loc:
                                    is_direct = True
                                    if this_hop['nr'] - last_hop_w_loc['nr'] > 1:
                                        is_direct = False
                                    # we've got a segment. now add it to segments keyed by src_lat|lon, dst_lat|lon 4tuple
                                    segments.append({
                                        'lat0': last_loc[0],
                                        'lon0': last_loc[1],
                                        'cc0' : list(last_hop_w_loc['country_codes']),
                                        'lat1': this_loc[0],
                                        'lon1': this_loc[1],
                                        'cc1' : list(this_hop['country_codes'])
                                    })
                                    ## reset stuff now a segment is found
                                    last_hop_w_loc = this_hop
                            elif len( this_hop['locs'] ) == 0 or len(last_hop_w_loc['locs']) == 0:
                                pass # no new geoloc to be processed
                            else:
                                print >>sys.stderr, "Uncaught situation at hop no %s->%s: %s -> %s (%s)" % ( last_hop_w_loc['nr'], this_hop['nr'], len(  last_hop_w_loc['locs'] ), len( this_hop['locs'] ), ipset )
                    ## add the final segment
                    segments.append({
                        'lat0': list(last_hop_w_loc['locs'])[0][0],
                        'lon0': list(last_hop_w_loc['locs'])[0][1],
                        'cc0' : list(last_hop_w_loc['country_codes']),
                        #'lat1': self.probes_by_id[ trace['dst_prb_id'] ]['lat'],
                        #'lon1': self.probes_by_id[ trace['dst_prb_id'] ]['lon'],
                        'lat1': centroid['lat'],
                        'lon1': centroid['lon'],
                        'cc1' : self.probes_by_id[ trace['dst_prb_id'] ]['country_code']
                    })
                    if trace_out_of_country == True:
                        ### find if/how we add it to our out of country stuff
                        trace_id = "%s-%s-%s" % ( trace['msm_id'], trace['src_prb_id'], trace['ts'] )
                        for seg in segments:
                            lines_key = ( seg['lat0'],seg['lon0'], seg['lat1'], seg['lon1'] )
                            if not lines_key in lines:
                                lines[ lines_key ] = []
                            lines[ lines_key ].append( trace_id )
        # make 'lines' into geojson
        oocGeoJSON = {'type': 'FeatureCollection', 'features':[]}
        for coords in lines.keys():
            count = len( lines[ coords ] )
            oocGeoJSON['features'].append({
                'type': 'Feature',
                'properties': {
                    'count': count
                    # add trace_ids here too?
                },
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [
                        [ coords[1], coords[0] ], [ coords[3], coords[2] ] # latlon inversion too
                    ],
                }
            })
        return oocGeoJSON

r = dns.resolver.Resolver()
r.lifetime = 7.01

def ip2asn( ip ):
        ''' find asn info, either from cache, or external data source (ripestat) '''
        asn = ''
        try:
            d = requests.get( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
            asnjson = d.json()
            if len( asnjson['data']['asns'] ) > 0:
                asn = asnjson['data']['asns'][0]['asn']
            else:
                asn = ''
        except: 
            sys.stderr.write( "eeps: problem in ASN for ip: %s\n" %  (ip ) )
            return None ## todo proper error handling
        return asn

def ip2hostname( ip ):
        ''' find hostname info, either from cache, or external data source (reverse DNS query) '''
        host = ''
        try:
            resolve = r.query(dns.reversename.from_address( ip ),'PTR')
            if len( resolve.response.answer ) > 0 :
                host = str(resolve.response.answer[0].items[0])
                host = host.rstrip('.')
                host = host.lower()
            else:
                host = ''
        except dns.resolver.NXDOMAIN: host = ''
        except Exception as e: 
            ## timeout?
            print >>sys.stderr, " %s " % ( e )
            return None
        # at this point resolving worked
        return host

