
# Advanced Usage


## Rerunning the analysis on existing measurements

If you want to rerun the analysis, for instance with
a changed config file (common case: you want to add
exchange point information), this is how to do this.


1. Remove analysis and results directories
2. Edit config.json
3. Rerun _prepare.py_ . This will not touch the existing probeset, but will update all other meta information in basedata.json
4. (Do *not* rerun _measure.py_ , measurements have already been created, right?)
5. Sometimes you want to rerun _get-ips.py_ but typically not. For instance if you have updated OpenIPMap geoloc for some IPs you need to rerun this step. This needs a better solution, because this process is painfully slow.
6. Rerun _get-measurements.py_ , this step will reapply config.json information to enhance measurement data, and store that in _./results_
7. Rerun _analyse-results.py_ , this will create _./analyse_


## Hacking the analysis scripts

The _./template_ directory contains all the html/css/javascript etc for each of the visualisations that the _analyse_ step produces.
What the _analyse_ step does is first copy over the tempates and then create json data files in there that customise the visualisation
for each run of the ixp-country-jedi.

The analysis step is structured so that, hopefully, extra analysis steps are easy to implement.
Each analysis consists of 3 parts:

1. Initialisation code to initialise a data-structure specific for the analysis
2. code that gets run for each measurement-blob (that is already enhanced in the _get-measurements_ step)
3. exit code. This typically saves aggregate data to a file, and/or prints aggregate information to stdout

The code contains a _stub_ version of a specific analysis

```python

### below might be easy to copy-paste for additional analyses
### stub_
def init_stub( basedata, probes ):
	return {}
def do_stub_entry( data, proto, data_entry ):
	pass
def do_stub_printresult( data ):
	pass

```

Adding 'stub' to the _defs_ dictionary (in _main_ ) with value _True_ will make this stub code run.
