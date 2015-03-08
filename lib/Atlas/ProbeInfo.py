#!/usr/bin/env python
import urllib2
import urllib
import json

PROBE_API_HOST='https://atlas.ripe.net'
PROBE_API_URL='%s/api/v1/probe/' % ( PROBE_API_HOST )

PROBE_API_URL_ARCHIVE='%s/api/v1/probe-archive/' % ( PROBE_API_HOST )

def query_archive(**kwargs):
   '''
   query the probe API archive for a specific day
   '''
   objects = {}
   # sensible defaults
   if not 'format' in kwargs:
      kwargs['format'] = 'json'
   ## day=latest is special for latest
   if kwargs['day'] == 'latest':
      del kwargs['day']
   url = "%s?%s" % (PROBE_API_URL_ARCHIVE, urllib.urlencode( kwargs ) )
   try:
      conn = urllib2.urlopen( url, timeout=300 )
   except urllib2.URLError, e:
      raise Exception("There was an error: %r (url:%s)" % (e,url))
   result = json.load( conn )
   for obj in result['objects']:
      objects[ obj['id'] ] = obj
   return objects

def query(**kwargs):
   if 'day' in kwargs:
      return query_archive(**kwargs)
   if not 'limit' in kwargs:
      kwargs['limit'] = 200
   objects = {} 
   url = "%s?%s" % (PROBE_API_URL, urllib.urlencode( kwargs ) )
   try:
      conn = urllib2.urlopen( url )
   except:
      raise ValueError("URL fetch error on: %s" % (url) )
   result = json.load( conn )
   objects = result['objects'] 
   while result['meta']['next'] != None:
      continurl = "%s/%s" % ( PROBE_API_HOST, result['meta']['next'] )
      #print continurl
      try:
         contin = urllib2.urlopen( continurl )
      except:
         raise ValueError("URL fetch error on: %s" % (continurl) )
      result = json.load( contin )
      objects.extend( result['objects'] )
   keyed_objects = {}
   for obj in objects:
      keyed_objects[ obj['id'] ] = obj
   return keyed_objects
