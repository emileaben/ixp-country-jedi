#!/usr/bin/env python
import sys
import os
from jinja2 import Environment

from datetime import datetime
from ripe.atlas.cousteau import (
  Traceroute,
  AtlasSource,
  AtlasCreateRequest
)

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

def measure_from_template( template_file, template_vars ):
    env = Environment()
    template = env.get_template( template_file )
    msm_spec = template.render(**{template_vars})

    traceroute = Traceroute( ** msm_spec['definitions']  )
    source = AtlasSource( ** msm_spec['probes']  )
    atlas_request = AtlasCreateRequest(
        start_time = datetime.utcnow(),
        key = KEY,
        measurements = [traceroute],
        sources = [source],
        is_oneoff = True
    )

    (is_success, response) = atlas_request.create()

    return response['measurements'][0]

def measure( msm_spec ):
    traceroute = Traceroute( ** msm_spec['definitions']  )
    source = AtlasSource( ** msm_spec['probes']  )
    atlas_request = AtlasCreateRequest(
        start_time = datetime.utcnow(),
        key = KEY,
        measurements = [traceroute],
        sources = [source],
        is_oneoff = True
    )

    (is_success, response) = atlas_request.create()

    return response['measurements'][0]


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

    data =  {
        'definitions': defs,
        'probes': 
            {
                'requested': len( probe_list ),
                'type': 'probes',
                'value': ','.join( map( str, probe_list ) )
            }
    };
    
    traceroute = Traceroute( ** data['definitions']  )
    source = AtlasSource( ** data['probes']  )
    atlas_request = AtlasCreateRequest(
        start_time = datetime.utcnow(),
        key = KEY,
        measurements = [traceroute],
        sources = [source],
        is_oneoff = True
    )

    (is_success, response) = atlas_request.create()

    return response['measurements'][0]