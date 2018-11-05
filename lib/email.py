#!/usr/bin/python3
"""
TODO: Add Description
"""

import smtplib
from email.mime import multipart
from email.mime import text
from email.utils import COMMASPACE, formatdate

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


def send_mail(to, fro, subject, message, server="localhost"):
    """
    Sends mail to SMTP relay which in return will send out to the recipients
    :param to: Recipients email address
    :param fro: Email address of sender 
    :param subject: Subject Message
    :param message: Message contents
    :param server: IP Address or FQDN of the SMTP server
    :return: 
    """
    assert type(to) == list

    msg = multipart.MIMEMultipart()
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach(text.MIMEText(message, 'html'))

    smtp = smtplib.SMTP(server)
    smtp.sendmail(fro, to, msg.as_string())
    smtp.close()

