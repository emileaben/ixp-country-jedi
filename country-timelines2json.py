#!/usr/bin/env python
import json
import sys
import re

## input: the names of all asgraph.json files
# like this: ./data/2015-06-03/FI/analysis/asgraph/asgraph.json
## output: a json struct that has the these grouped per country per date 
#    to stdout, or into a file if specified as sys.argv[1]

# data
d = {}

regex = r'(\d{4}-\d{2}-\d{2})\/(\w{2})\/'

for line in sys.stdin:
    match = re.search(regex, line)
    # If-statement after search() tests if it succeeded
    if match:                      
        date = match.group(1)
        cc = match.group(2)
        d.setdefault( cc, [] )
        d[ cc ].append( date )
    else:
        print >> sys.stderr, 'did not find regex in line %s' % line

out = []
for cc in sorted( d.keys() ):
    dates = sorted( set( d[ cc ] ) )
    out.append( {'country': cc, 'dates': dates } )

if len( sys.argv ) == 2:
    with open( sys.argv[1], 'w' ) as outf:
        print >>outf, json.dumps( out, indent=2 )
else:
    print json.dumps( out, indent=2 )

