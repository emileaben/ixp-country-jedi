#!/usr/bin/env python
import urllib2
import urllib
import json
import sys

API_HOST='https://atlas.ripe.net'
API_URL='%s/api/v1/measurement/' % ( API_HOST )

def query(**kwargs):
   if not 'limit' in kwargs:
      kwargs['limit'] = 200
   objects = {} 
   url = "%s?%s" % (API_URL, urllib.urlencode( kwargs ) )
   try:
      conn = urllib2.urlopen( url )
   except:
      raise ValueError("URL fetch error on: %s" % (url) )
   result = json.load( conn )
   objects = result['objects'] 
   while result['meta']['next'] != None:
      continurl = "%s/%s" % (API_HOST, result['meta']['next'] )
      print continurl
      try:
         contin = urllib2.urlopen( continurl )
      except:
         raise ValueError("URL fetch error on: %s" % (continurl) )
      result = json.load( contin )
      objects.extend( result['objects'] )
   keyed_objects = {}
   for obj in objects:
      keyed_objects[ obj['msm_id'] ] = obj
   return keyed_objects

if __name__ == '__main__':
   args = dict([arg.split('=') for arg in sys.argv[1:]])
   f=query(**args)
   print json.dumps(f,indent=2)
   
   
