"""
Author: Abu Ashraf Masnun
Link: http://masnun.com/2010/01/01/sending-mail-via-postfix-a-perfect-python-example.html
"""
import smtplib
from email.mime import multipart
from email.mime import base
from email.mime import text
from email.utils import COMMASPACE, formatdate
from email import encoders
import os


def send_mail(to, fro, subject, message, files="", server="localhost"):
    """
    
    :param to: 
    :param fro: 
    :param subject: 
    :param message: 
    :param files: 
    :param server: 
    :return: 
    """
    assert type(to)==list
    assert type(files)==list

    for (index, value) in message:
        print(index, value)
    msg = multipart.MIMEMultipart()
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(text.MIMEText(message))

    for file in files:
        part = base.MIMEBase('application', "octet-stream")
        part.set_payload(open(file,"rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    smtp = smtplib.SMTP(server)
    smtp.sendmail(fro, to, msg.as_string())
    smtp.close()

