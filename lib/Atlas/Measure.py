#!/usr/bin/env python
import urllib2
import sys
import os
import json
from jinja2 import Environment

### AUTH
authfile = "%s/.atlas/auth" % os.environ['HOME']
if not os.path.exists(authfile):
    print >>sys.stderr, ("Authentication file %s not found" % authfile)
    sys.exit(1)
auth = open(authfile)
KEY = auth.readline()[:-1]
auth.close()
KEY.rstrip()
### END AUTH

MSM_URL = "https://atlas.ripe.net/api/v1/measurement/?key=%s" % KEY

class JsonRequest(urllib2.Request):
    def __init__(self, url):
        urllib2.Request.__init__(self, url)
        self.add_header("Content-Type", "application/json")
        self.add_header("Accept", "application/json")

def measure_from_template( template_file, template_vars ):
   env = Environment()
   template = env.get_template( template_file )
   msm_spec = template.render(**{template_vars})
   msm_req = JsonRequest(MSM_URL)
   try:
      msm_conn = urllib2.urlopen(msm_req, json_data)
   except urllib2.HTTPError as e:
        print >>sys.stderr, ("Fatal error when reading results: %s" % e.read())
        sys.exit(1)
   msm_meta = json.load(msm_conn)
   msm_id = msm_meta["measurements"][0]
   return msm_id

def measure( msm_spec ):
   msm_req = JsonRequest(MSM_URL)
   try:
      msm_conn = urllib2.urlopen(msm_req, json.dumps( msm_spec ) )
   except urllib2.HTTPError as e:
      print >>sys.stderr, ("Fatal error when reading results: %s" % e.read())
      sys.exit(1)
   msm_meta = json.load(msm_conn)
   msm_id = msm_meta["measurements"][0]
   return msm_id

def oneofftrace( probes_def, dst, **kwargs ):
   probe_list = []
   if isinstance(probes_def, int):
      probe_list.append( probes_def )
   elif isinstance(probes_def, list):
      probe_list = probes_def
   else:
      raise ValueError("Probes definition needs to be of type int or list, not %s" % ( type(probes_def) ) )
   default_defs = {
      'target': dst,
      'type': 'traceroute',
      'protocol': 'ICMP',
      'resolve_on_probe': True,
      'is_oneoff': True
   }
   defs = dict( default_defs.items() + kwargs.items() )
   # handle 'af'
   if not 'af' in defs:
      if ':' in dst:
         defs['af']=6
      else: #default to 4
         defs['af']=4
   # handle 'descr'
   if not 'description' in defs:
      defs['description'] = 'trace to %s (IPv%d)' % ( dst, defs['af'] )

   data = {
      'definitions': [ defs ],
      "probes": [
         {
            'requested': len( probe_list ),
            'type': 'probes',
            'value': ','.join( map( str, probe_list ) )
         }
      ]
   };
   json_data = json.dumps( data )
   msm_req = JsonRequest(MSM_URL)
   try:
      msm_conn = urllib2.urlopen(msm_req, json_data)
   except urllib2.HTTPError as e:
        print >>sys.stderr, ("Fatal error when reading results: %s" % e.read())
        sys.exit(1)
   # Now, parse the answer
   msm_meta = json.load(msm_conn)
   msm_id = msm_meta["measurements"][0]
   return msm_id
