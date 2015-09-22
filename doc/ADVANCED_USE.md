Advanced Use
============

Rerunning analysis on existing measurements
===========================================

If you want to rerun analysis, for instance with
a changed config file (common case: you want to add
exchange point information). This is how to do this.

    * Remove analysis and results directories
    * Edit config.json
    * Rerun _prepare.py_
        * This will not touch the existing probeset, but will update all other meta information in basedata.json
    * (Do *not* rerun _measure.py_ , measurements have already been created, right?)
    * Sometimes you want to rerun _get-ips.py_, for instance if you have updated OpenIPMap geoloc for some IPs
        * This needs a better solution, because this process is painfully slow.
    * Rerun _get-measurements.py_ , this step will reapply config.json information to enhance measurement data, and store that in _./results_
    * Rerun _analyse-results.py_ , this will create _./analyse_


Hacking analysis scripts
========================

The _./template_ directory contains all the html/css/javascript etc for each of the visualisations that the _analyse_ step produces.
What the _analyse_ step does is first copy over the tempates and then create json data files in there that customise the visualisation
for each run of the ixp-country-jedi.

The analysis step is structured so that, hopefully, extra analysis steps are easy to implement.
Each analysis consists of 3 parts:

    * initialisation code to initialise a data-structure specific for the analysis
    * code that gets run for each measurement-blob (that is already enhanced in the _get-measurements_ step)
    * exit code. This typically saves aggregate data to a file, and/or prints aggregate information to stdout

