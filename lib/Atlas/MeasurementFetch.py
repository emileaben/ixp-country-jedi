#!/usr/bin/env python
import urllib2
import urllib
import json
import sys

API_HOST='https://atlas.ripe.net'
API_URI='/api/v1/measurement'
API_URI_LATEST='/api/v1/measurement-latest'

def fetch(msm_id, **kwargs):
   default_args = {
      'format': 'txt'
   }
   ## some fixes for common pitfalls
   if 'start' in kwargs:
      kwargs['start'] = int( kwargs['start'] )
   if 'stop' in kwargs:
      kwargs['stop'] = int( kwargs['stop'] )
   api_args = dict( default_args.items() + kwargs.items() )
   url = "%s/%s/%d/result/?%s" % (API_HOST,API_URI,msm_id,urllib.urlencode( api_args ) )
   conn = None
   retries = 0
   ex = None
   while not conn and retries < 3:
      try:
         conn = urllib2.urlopen( url )
      except:
         retries += 1
         print >>sys.stderr, "retrying url:%s" % ( url )
         if retries > 3: raise
   for l in conn:
      data = json.loads( l )
      yield( data )

def fetch_latest(msm_id, **kwargs):        
   default_args = {
      'format': 'txt'
   }
   api_args = dict( default_args.items() + kwargs.items() )
   url = "%s/%s/%d/result/?%s" % (API_HOST,API_URI_LATEST,msm_id,urllib.urlencode( api_args ) )
   conn = urllib2.urlopen( url )
   for l in conn:
      data = json.loads( l )
      yield( data )

