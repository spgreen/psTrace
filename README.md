# psTrace

psTrace is a traceroute analysis tool written in PythonV3 which retrieves traceroute/tracepath data from a PerfSONAR Measurement Archive (MA).

## Features

- Results matrix of all traceroute test 
- Detailed information for each traceroute test
- Historical Traceroute information for each traceroute test
- Email alerts when routes change
- Results accessed via a web browser as results are stored as HTML files

## Prerequisites

- Python Version 3.5.2 +
- Python Jinja2 Template module - Install via pip for PythonV3

      $ pip install Jinja2

- Web Server (Apache, Nginx, etc)
- SMTP Server (Postfix, etc) that does not require authentication for sending out email alerts 
- Accesss to a PerfSONAR Measurement Archive with traceroute/tracepath data

## Using the psTrace Analysis Tool

1. Clone repository into your preferred directory

        $ git clone https://github.com/spgreen/psTrace.git
             
2. Soft link the psTrace `html` folder to the web document root that will be served by Apache. 
   <br>e.g. /var/www/html/ is the usual default directory served by Apache. <br>**Note**: You will need to remove the html folder if it exist otherwise an error will occur creating the soft link
   
        $ ln -s /full/path/to/pstrace/html/folder/ /var/www/html
    
3. Edit the email constants within `conf/email_configuration.py` to values appropriate to your environment. Currently only supports sending emails to a SMTP server that does NOT require authentication. 

    1. Set `ENABLE_EMAIL_ALERTS = 1` to enable alerts when traceroute changes occur. <br>**Default:** `ENABLE_EMAIL_ALERTS = 0`
    2. Multiple recipients can be added by modifying `EMAIL_TO` with one address after the other separated by a comma within the square brackets.
    3. `EMAIL_SERVER` is the SMTP Server that will be used to send out the email alerts. <br>**Default:** `EMAIL_SERVER = localhost`
    
4. Run psTrace Tool

       $ python perfsonar_traceroute_analysis.py <PS MA base URL or IP> <period in seconds>
  
      or
  
       $ python3 perfsonar_traceroute_analysis.py <PS MA base URL or IP> <period in seconds>
       
      depending on your system
  
  - **``<PS MA base URL or IP>``** is either the IP address or base url without http:// or https:// of the perfSONAR Measurement archive you wish to retrieve traceroute/tracepath data from.
     
  - **``<period in seconds>``** - e.g. 86400 = analysis for last 1 day, 1290600 = analysis for last 2 weeks, etc 
  
5. Results will be stored as HTML pages within the psTrace `html` folder

6. Access results by using a web browser and type the address of the web server hosting the results. 

## Schedule automatic psTrace analysis using Cron

- Setup a cron script

        $ crontab -e

- Add the following within said cron script:
        
        */30 * * * * /path/to/psTrace/perfsonar_traceroute_analysis.py  <PS MA base URL or IP> <period in seconds> 2>&1 >/dev/null

  1. **``<PS MA base URL or IP>``** - either the IP address or base url without http:// or https:// of the perfSONAR Measurement archive you wish to retrieve traceroute/tracepath data from.
  2. **``<period in seconds>``** - e.g. 86400 = analysis for last 1 day, 1290600 = analysis for last 2 weeks, etc 

This will run the perfsonar_traceroute_analysis.py script every 30 minutes. Change the time appropriately for your environment 
<br>e.g. For SingAREN's case, their PerfSONAR Node runs traceroute tests every 15 minutes so setting the cron script to run the analysis tool every 30 minutes is sufficient.
