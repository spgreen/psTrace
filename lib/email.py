"""
Author: Abu Ashraf Masnun
Link: http://masnun.com/2010/01/01/sending-mail-via-postfix-a-perfect-python-example.html
"""
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import os


def send_mail(to, fro, subject, text, files=[], server="localhost"):
    """
    
    :param to: 
    :param fro: 
    :param subject: 
    :param text: 
    :param files: 
    :param server: 
    :return: 
    """
    assert type(to)==list
    assert type(files)==list

    for (index, value) in text:
        print(index, value)
    msg = MIMEMultipart()
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for file in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(file,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    smtp = smtplib.SMTP(server)
    smtp.sendmail(fro, to, msg.as_string() )
    smtp.close()

