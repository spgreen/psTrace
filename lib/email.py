import smtplib
from email.mime import multipart
from email.mime import text
from email.utils import COMMASPACE, formatdate


def send_mail(to, fro, subject, message, server="localhost"):
    """
    
    :param to: email address of recipient
    :param fro: 
    :param subject: 
    :param message: 
    :param server: 
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

