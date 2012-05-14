'''
Created on Nov 15, 2010

@author: surya
'''
import os
import sys
import time
import json
import logging
import smtplib

from django.conf import settings as djsettings
from django.template.loader import render_to_string

from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from Collections.SuryaProcessingList import *
from Collections.SuryaProcessResult import *
from Logging.Logger import getLog
from Locking.AppLock import getLock
from IANAGmailSettings.Settings import setting
from mongoengine import *

from GmailResultsFramework.GmailResultsFramework import GmailResultsFramework

connect('SuryaDB', tz_aware=True)

# Setup some variables for the djano template loader to work
# Need to make this not be a call to set an environment variable... does pwd work from here?
djsettings.configure(DEBUG=True, TEMPLATE_DEBUG=True, \
                     TEMPLATE_DIRS=(os.path.dirname(__file__)+'/templates',))

class IANAGmailResults(GmailResultsFramework):
    ''' This class implements the functionality to poll the SuryaDB
for results on processing uploaded images and emails the
sender with these results.
'''
    
    def checkResults(self):
        ''' Refer GmailResultsFramework.checkResults for documentation'''
        tags = self.grestags + " IANA"
        
        gmail_user = setting.get("username")
        gmail_pwd = setting.get("password")
        smtpserver = smtplib.SMTP("smtp.gmail.com",587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo()
        smtpserver.login(gmail_user, gmail_pwd)
        
        self.log.info("Checking Results... {0}".format(str(setting.get("poll_interval"))), extra=tags)
        
        for item in SuryaIANAResult.objects(isEmailed=False):
            
            try:
                misc = item.item.misc
                misc_dict = json.loads(misc)
            except ValueError as ve:
                self.log.error('[ Sanity ] The misc input is not a json syntax string. Store it as { "rawstring": (...input...)} . The orignial Input:' + str(misc)+ "Reason:" + str(ve), extra=tags)
                misc = '{ "rawString":"' + str(misc) + '"}'
                
            if misc_dict.has_key("fromemail"):

                # Header so To:, From:, and Subject: are set correctly
                if misc_dict.has_key("toemail"):
                    # core gmail address must be configured to send as this user too! See settings->accounts
                    msghdr = "From: " + misc_dict["toemail"] + "\n"
                    sendFrom = misc_dict["toemail"]
                else:
                    msghdr = "From: " + setting.get("username") + "\n"
                    sendFrom = setting.get("username")
                
                msghdr += "To: " + misc_dict["fromemail"] + "\n"
                msghdr += "Subject: BC Results for " + str(item.item.filename) + '\n'
                
                msg = MIMEMultipart('localhost')

                flowratestr = "cc/m"
                if item.computationConfiguration.airFlowRate < 20:
                    flowratestr = "l/m"
                
                text = render_to_string("result_email_default.html", {'item': item, 'flowratestr': flowratestr})
                                
                textmsg = MIMEText(text)
                
                msg.attach(textmsg)

                smtpserver.sendmail(sendFrom, misc_dict["fromemail"], msghdr + msg.as_string())
                    
                self.log.info("sent email", extra=tags)
                item.isEmailed = True
                item.save()
                    
        for item in SuryaIANAFailedResult.objects(isEmailed=False):
            
            try:
                misc = item.item.misc
                misc_dict = json.loads(misc)
            except ValueError as ve:
                self.log.error('[ Sanity ] The misc input is not a json syntax string. Store it as { "rawstring": (...input...)} . The orignial Input:' + str(misc)+ "Reason:" + str(ve), extra=tags)
                misc = '{ "rawString":"' + str(misc) + '"}'
                
            if misc_dict.has_key("fromemail"):

                # Header so To:, From:, and Subject: are set correctly
                if misc_dict.has_key("toemail"):
                    # core gmail address must be configured to send as this user too! See settings->accounts
                    msghdr = "From: " + misc_dict["toemail"] + "\n"
                    sendFrom = misc_dict["toemail"]
                else:
                    msghdr = "From: " + setting.get("username") + "\n"
                    sendFrom = setting.get("username")
                
                msghdr += "To: " + misc_dict["fromemail"] + "\n"
                msghdr += "Subject: BC Results for " + str(item.item.filename) + '\n'
                
                msg = MIMEMultipart('localhost')

                text = render_to_string("failed_email_debug.html", {'item': item})
                
                msgtext = MIMEText(text)
                msg.attach(msgtext)
                smtpserver.sendmail(sendFrom, misc_dict["fromemail"], msghdr + msg.as_string())
                self.log.info("sent email", extra=tags)
                item.isEmailed = True
                item.save()
                     
        smtpserver.close()

        
if __name__ == '__main__':
    runinterval = 10
    if len(sys.argv) > 1:
        runinterval = int(sys.argv[1])
    connect('SuryaDB', tz_aware=True)
    gres = IANAGmailResults()
    gres.run("IANAGmailResults.pid", "IANAGmailResults", runinterval)
