# psTrace

psTrace is a traceroute analysis tool written in PythonV3 which retrieves traceroute/tracepath data from a PerfSONAR Measurement Archive (MA).


## Prerequisites

- Python Version 3.5.2 +
- Python Jinja2 Template module - Install via pip for PythonV3

      pip install Jinja2

- Apache Web Server 
- Postfix for sending out email alerts

## Using the psTrace Analysis Tool

1. Clone repository into your preferred directory

        git clone https://github.com/spgreen/psTrace.git
             
2. Soft link the `html` folder to the web document root that will be served by Apache. 
   <br>e.g. /var/www/html/ is the usual default directory served by Apache. **Note**: You will need to remove the html folder if it exist otherwise an error will occur when trying to soft link
   
        ln -s /full/path/to/pstrace/html/folder/ /var/www/html
    
3. Edit email constant values within `conf/email_configuration.py` to approriate values within your environment. Currently only supports sending emails to a SMTP server that does not require authentication. 

4. Run psTrace Tool

        python perfsonar_traceroute_analysis.py <base perfSONAR MA URL> <time period in seconds>
  
  or
  
       python3 perfsonar_traceroute_analysis.py <base perfSONAR MA URL> <time period in seconds>
       
  depending on your system
  
  1. ``<base perfSONAR MA URL>`` is either the IP address or base url without http:// or https:// of the MA
  2. ``<time period in seconds>`` - e.g. 86400 = 1 day, 1290600 = 2 weeks, etc 
  
4. Results will be stored as HTML pages within the `html` folder


TODO:// Finish Documentation
