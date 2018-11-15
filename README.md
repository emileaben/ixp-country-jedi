
# IXP Country Jedi

IXP Country Jedi is a project that shows if the Internet traffic paths stay within the country, and if the paths between two networks within the country go through an Internet eXchange Point (IXP). 

You can get the pre-processed data here: https://sg-pub.ripe.net/emile/ixp-country-jedi/

You can read more about the use-cases in these articles:
* https://labs.ripe.net/Members/emileaben/looking-at-france-ix-with-ripe-atlas-and-ris
* https://labs.ripe.net/Members/emileaben/improving-ripe-atlas-coverage-what-networks-are-missing
* https://labs.ripe.net/Members/emileaben/measuring-countries-and-ixps-in-the-see-region
* https://labs.ripe.net/Members/emileaben/measuring-ixps-with-ripe-atlas 

## Probe mesh measurements

This codebase contains a couple of scripts to make probe mesh measurements feasible/easy.

Monthly runs of this code for all countries with enough diversity in RIPE Atlas probes can be found here: https://sg-pub.ripe.net/emile/ixp-country-jedi/

The way the scripts are used/tested is to first create a directory for
your measurement campaign, and run the scripts as follows:

```shell

mkdir 'SE-2015-03'
cd SE-2015-03 
<create config.json file here>
<run scripts relative to current directory, ie. ../prepare.py ; 
../measure.py ...>

```

The scripts depend on this convention.

Dependencies on external python modules are in 'requirements.txt',
so you can run

```shell
pip install -r requirements.txt
```

to fulfill these.

Before you use the scripts, create a config file specifying what
mesh you would like to do.

## config.json

This file contains base data used for creating measurements and
analysing the results.  It can contain various parts:

* *country*:   ISO 2 letter code for the country under analysis, or list of countries under analysis (ie. NL, IT, CH);
* *ixps*: List of IXPs one wants to detect/report on;
* *locations*: List of cities on which probe selection will be based (if applicable)
* *probetag*: Probetag on which probe selection criteria is based.
* *probe_ids*: List of probes you want to measure from.

examples are provided in the _examples_ directory. For probe selection it is mandatory to either have _country_ , _probetag_ , or _probe_ids_
defined. It is possible to combine _probetab_ and _country_ (which will take
all the probes with that probetag in the specified country/countries).
It is also possible to combine _probe_ids_ and _country_: after selecting the probes
in the specified country/ies, the _probe_ids_ specified will be added (any duplicates
will be removed).
Without a *locations* section, the capital of *country* (or the first country, if *country*
is a list) is used for probe selection (see below).

One can set an extra 'location-constraint' config key. The value of this
configuration directive needs to be an integer. When this is set, the probe
selection part of ixp-country-jedi will only select probes that are within
'location-constraint' kilometers from any of the given locations.
This can be useful if you only want to measure a specific city.  In that case,
set the 'location'-list to that specific city, and set a 'location-constraint'
to a reasonable value (for instance 50, so you'll cover 50 kilometers from the
city centre).

Note: The interaction between various of the configuration settings hasn't been
thoroughly tested, so beware of combining. What is known to work is _probetag_
as a stand-alone probe selection option, and _country_ is known to work well
together with all other config options.

## prepare.py

This script reads _config.json_ and generates two output files:
1. basedata.json
2. probeset.json

For each one of the IXPs listed in _config.json_ it will try to find the
member ASNs.

Based on the country and locations specified it will do a probe
selection.  It will:

- only select public probes (because the measurements we are going to create 
will use their their public IP address);
- for every ASN, it will select up to twice the number of locations specified.

If an ASN hosts more than 2 probes, the selection will be a maximum of 2x
the number of locations in _config.json_: the closest as well as the
furthest probe from each location will be selected.  Note that this
can result in less than 2 times the _number-of-locations_ probes per
ASN even when there are more probes available in that ASN, because
a single probe could be the furthest away from multiple locations.

In the preparation/data gathering phase this script uses the GeoNames
service for geocoding.  Please put a valid geonames username in
_~/.geonames/auth_.

for more information on GeoNames see http://www.geonames.org/export/web-services.html

This script also relies on Google Maps Geocoding API to geocode a location from list of probes. The limit is
[2500 free requests](https://developers.google.com/maps/documentation/geocoding/usage-limits). You can pass your own
API key by using environment variable `GOOGLEMAPS_API_KEY`.

## measure.py

This script runs one-off measurements for the probes specified in
_probeset.json_ and stores their results in _measurementset.json_

This uses the RIPE Atlas measurement API for measurement creation,
and it needs a valid measurement creation API key in _~/.atlas/auth_
. 

For more information on RIPE Atlas API keys see https://atlas.ripe.net/docs/keys/

## get-ips.py

This script gathers metadata for all the IPs in the collected data.
This is done separately from the rest of the analysis-code because it
is time-consuming and ideally is done pretty soon after running all the
measurements. If done too soon, not all measurement results would be in
yet, if done much later (think days) meta-data - like reverse hostname
mapping - might have changed, so  is don't get-ips a few
minutes after _measure.py_. This step will create a file called _ips.json-fragments_
file with reverse DNS lookups, ASNs and geoloc (via OpenIPMap, not
MaxMind) of IPs encountered in the traceroutes.

## get-measurements.py

This script fetches measurements (from _measurementset.json_) and
does some initial analysis on them using information from _config.json_,
_basedata.json_, _probeset.json_ and _ips.json-fragments_.  It creates a
local _results_ directory and outputs a single json file per
measurement (_analysed.<msmid>.json_) which is a list of analysis
results, one result per src/dst combination.

## analyse-results.py

This script produces text and/or webpages with analysis and visualisation in a
local _analysis_ directory. For webpages, these need to be on an actual
webserver for some of the javascript in them to work. One can easily create a
local webserver that would work for this purpose like this: 

```shell

cd analysis ; python -m SimpleHTTPServer 3333

```

and then pointing your browser at localhost:3333/<viz-name> 

Note that some visualisations use libraries in a common directory located
in the _analysis_ directory, so the webserver needs to run with the
'analysis'-directory (or lower) as root.

Templates (HTML,javascript,CSS) for webpages are in the _templates_
directory and copied over each time the _analyse-results.py_ script
is run.

If you want to tweak the visualisations, tweaking them in the
_templates_ directory and then running the _analyse-results.py_ script
again will probably do what you want.

# Install the user-to-user graph locally

The user-to-user graph (dixit: 'eyeballsgraph') is a js/react application that can be ran locally with webpack-dev-server.

To do so:

- You'll need node.js installed to make this work. Go to https://nodejs.org/en/download/package-manager/ to see an overview of options for all OSes. I greatly prefer using nodesource.com for linux distros. For MacOS I prefer using the bash install script instead of homebrew, but YMMV.
- Clone this repo somewhere on you local machine with `git clone git@github.com:emileaben/ixp-country-jedi.git`
- Go into the eyeballsgraph directory: `cd template/eyeballsgraph/`
- Install all dependencies with: `npm install`
- Right now we don't have a (public) npm package for one dependency, the @ripe-rnd/ui-components library. You'll have to link this manually like this:
  - Clone the ui-components library `git clone git@github.com:RIPE-NCC/rnd-ui-components.git` in a directory of your liking.
  - Go into the root of the library with `cd ui-components`
  - Make a linked local package out of this repo with `npm link`
  - Now go (back) into the `template/eyeballsgraph/` diretory of the ixp-country-jedi repo and install the linked package with `npm link @ripe-rnd/ui-components`.
  - Edit `template/eyeballsgraph/webpack.config.js` replacing `4042.ripe.net` to `localhost` (lines 65 and 68).
- Now you can start the dev server with `npm start` and go with you favourite web-browser to `localhost:4042`

In the future we will have a npm package of the @ripe-rnd/ui-components and the link steps will go away.

Note that you might run into trouble with the CORS settings of the RIPE NCC webservers when making XHR calls to the json files hosted on the webservers of the RIPE NCC. A workaround is to locally edit your /etc/hosts file to point localhost to something.ripe.net and change the webpack-dev-server port to port 80. Now if you go to https://something.ripe.net on your browser you'll be able to download the JSON files (the CORS headers are set to *.ripe.net).

