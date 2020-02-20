#!/usr/bin/env python
import glob
import json
import sys
from haversine import haversine
import atexit
import curses  # Get the module
stdscr = curses.initscr()  # initialise it

@atexit.register
def goodbye():
    """ Reset terminal from curses mode on exit """
    curses.nocbreak()
    if stdscr:
        stdscr.keypad(0)
    curses.echo()
    curses.endwin()

## analysis base as sys.argv[1]
# for example ../data/2019-01-01/NL
ICJ_BASE_GLOB = '%s/results/*' % sys.argv[1]

def load_base( loc ):
    with open( "%s/basedata.json" % loc ) as inf:
        base = json.load( inf )
    return base

def load_probeset( loc ):
    out = {}
    with open( "%s/probeset.json" % loc ) as inf:
        d = json.load( inf )
        for prb in d:
            out[ prb['probe_id'] ] = prb
    return out

def load_ips( loc ):
    ips = {}
    with open( "%s/ips.json-fragments" % loc ) as inf:
        for line in inf:
            d = json.loads( line )
            ips[ d['ip'] ] = d
            if 'oloc' in ips[ d['ip'] ]:
                del( ips[ d['ip'] ]['oloc'] )
    return ips

def load_traces( loc ):
    # assuming it's still in results
    # and key by min_rtt for any IP
    ip2trace = {}
    for infile in glob.glob( ICJ_BASE_GLOB ):
        with open( infile ) as inf:
            d = json.load( inf )
            for trace in d:
                for hop in trace['result']:
                    for reply in hop['result']:
                        if 'from' in reply and 'rtt' in reply:
                            ip = reply['from']
                            rtt = reply['rtt']
                            if not ip in ip2trace or rtt < ip2trace[ ip ]['rtt']:
                                ip2trace[ ip ] = {
                                    'rtt':    rtt,
                                    'prb_id': trace['src_prb_id'],
                                    'txt': trace['tracetxt']
                                }
    return ip2trace

### pager etc
def process( objs, start, page_size ):
    stdscr.clear()
    for idx,obj in enumerate( objs ):
        stdscr.addstr(idx, 0, "%s %s/%s %skm ipmap:%s\n" % ( chr(idx+97), obj['ip'], obj['hostname'], int(obj['dist']), obj['location']  ) )
    #txt_in = raw_input("what entry do you want to explore? (n:next page, q:quit) ")
    stdscr.insertln()
    stdscr.insertln()
    stdscr.addstr("what entry do you want to explore? (y:next page, z:quit) ", curses.A_STANDOUT)
    stdscr.refresh()
    c = stdscr.getch()
    if c == ord('z'):
        sys.exit(0)
    elif c == ord('y'):
        start = start+page_size
    else:
        try:
            in_idx = int( c-97 )
            print in_idx
        except:
            print "doesn't look like a number! nice try though"
            return start
        process_detailed( objs[ in_idx ] )
    return start

def process_detailed( obj ):
    stdscr.clear()
    stdscr.move(0,0)
    stdscr.addstr("### process detailed!", curses.A_STANDOUT)
    stdscr.addstr(" %s/%s " % (obj['ip'], obj['hostname'] ) )
    trace = trace_with_lowest_rtt( obj['ip'])
    stdscr.refresh()
    #txt_in = raw_input("change loc / something else? ")

def trace_with_lowest_rtt( ip ):
    # create new subcurses thingie
    for line in ip2trace[ ip ]['txt'].split('\n'):
        stdscr.addstr( line )


def main():
    probeset = load_probeset( bdir )
    base = load_base( bdir )
    locs = base['locations'].keys()
    if len( locs ) != 1:
        print "can't run this analysis with locs > 1"
    lat = base['locations'][ locs[0] ]['lat']
    lon = base['locations'][ locs[0] ]['lon']
    ips = load_ips( bdir )
    wloc = []
    for ip in ips.keys():
        iplat = ips[ ip ]['lat']
        iplon = ips[ ip ]['lon']
        if iplat and iplon:
            dist = haversine( (lat,lon), (iplat,iplon) )
            ips[ ip ]['dist'] = dist
            wloc.append( ips[ ip ] )
    wloc.sort( key=lambda x:x['dist'], reverse=True )
    ## now do the user-input part
    ## show first X
    page_size = 20
    start = 0
    stdscr.addstr(" DONE",
        curses.A_REVERSE)
    stdscr.refresh()
    while 1:
        objs = []
        for x in wloc[start:min(start+page_size, len( wloc ) )]:
            objs.append( x )
        start = process( objs, start, page_size )

stdscr.clear()  # Clear the screen
stdscr.addstr(0, 0, "Initialising, plz wait... ",
    curses.A_REVERSE)
stdscr.refresh()
bdir = sys.argv[1]
ip2trace = load_traces( bdir )
main()

'''
[u'dst_rtts', u'dst_prb_id', u'protocol', u'msm_id', u'as_links', u'locations', u'geojson', u'ts', u'tracetxt', u'result', u'src_prb_id', u'in_country', u'via_ixp', u'ixps']
'''
