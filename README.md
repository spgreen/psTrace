# psTrace

psTrace is a traceroute analysis tool written in PythonV3 which retrieves traceroute/tracepath data from a PerfSONAR Measurement Archive (MA).

## How to use the psTrace Tool

1. Clone repository

  ``git clone https://github.com/spgreen/psTrace.git``
    
2. Run using PythonV3

  ``python perfsonar_traceroute_analysis.py <base perfSONAR MA URL> <time period in seconds>``
  
  or
  
  ``python3 perfsonar_traceroute_analysis.py <base perfSONAR MA URL> <time period in seconds>``
  
  1. <base perfSONAR MA URL> is either the IP address or base url without http:// or https:// of the MA
  2. <time period in seconds> - e.g. 86400 = 1 day, 1290600 = 2 weeks, etc 
  
3. Results will be stored as HTML pages within the html folder


TODO:// Finish Documentation
