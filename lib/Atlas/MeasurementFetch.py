#!/usr/bin/env python

import sys
from ripe.atlas.cousteau import AtlasResultsRequest, AtlasLatestRequest

def fetch(msm_id, **kwargs):
    kwargs['msm_id']=msm_id
    is_success, results = AtlasResultsRequest(** kwargs).create()
    if(is_success):

        if (len(results)>0):
            for l in results:
                yield( l )

def fetch_latest(msm_id, **kwargs):        
    kwargs['msm_id']=msm_id
    is_success, results = AtlasLatestRequest(** kwargs).create()
    if(is_success):

        if (len(results)>0):
            for l in results:
                yield( l )
