#!/usr/bin/env python
import urllib2
import urllib
import json

from APIConverter import ProbeConverter

#  pip install https://github.com/RIPE-NCC/ripe-atlas-cousteau/zipball/latest
from ripe.atlas.cousteau import ProbeRequest

# PROBE_API_HOST='https://atlas.ripe.net'
# PROBE_API_URL_ARCHIVE='%s/api/v1/probe-archive/' % ( PROBE_API_HOST )

# def query_archive(**kwargs):
#     '''
#     query the probe API archive for a specific day
#     '''
#     objects = {}
#     # sensible defaults
#     if not 'format' in kwargs:
#         kwargs['format'] = 'json'
#     ## day=latest is special for latest
#     if kwargs['day'] == 'latest':
#         del kwargs['day']
#     url = "%s?%s" % (PROBE_API_URL_ARCHIVE, urllib.urlencode( kwargs ) )
#     try:
#         conn = urllib2.urlopen( url, timeout=300 )
#     except urllib2.URLError, e:
#         raise Exception("There was an error: %r (url:%s)" % (e,url))
#     result = json.load( conn )
#     for obj in result['objects']:
#         objects[ obj['id'] ] = obj
#     return ProbeConverter(objects)


def query(**kwargs):
    # if 'day' in kwargs:
    #     return query_archive(**kwargs)

    keyed_objects = {}
    probes = ProbeRequest(**kwargs)
    for probe in probes:
        keyed_objects[probe["id"]] = probe

    return ProbeConverter(keyed_objects)
