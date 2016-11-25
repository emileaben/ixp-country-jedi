import sys, arrow, json

def ProbeConverter(obj):

	for result in obj:

		try:
			probe = obj[result]

			if probe['geometry']:
				probe['latitude'] = probe['geometry']['coordinates'][1]
				probe['longitude'] = probe['geometry']['coordinates'][0]
				del(probe['geometry'])

			if probe['status'] and probe['status']['since']:
				status_since = arrow.get(probe['status']['since'])
				status_since = status_since.timestamp
				probe['status_name'] = probe['status']['name']
				probe['status_since'] = status_since
				probe['status'] = probe['status']['id']

			if probe['description']:
				del(probe['description'])

			if probe['tags'] and isinstance(probe['tags'],list):
				probe['tags'] = [tag['slug'] for tag in probe['tags']]

			obj[result] = probe

		except Exception,e:
			print 'Converter Exception',e

	return obj
