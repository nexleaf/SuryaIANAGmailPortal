'''
Created on Nov 15, 2010

@author: surya
'''
import os
import sys
import time
import json
import email
import rfc822
import pycurl
import imaplib
import logging
import cStringIO

from ImageUtils.ImageCache import ImageCache
from ImageUtils.sampleExifN80 import get_original_datetime_N80
from Logging.Logger import getLog
from Locking.AppLock import getLock
from IANAGmailSettings.Settings import setting
from GmailMonitorFramework.GmailMonitorFramework import GmailMonitorFramework
from email.mime.text import MIMEText

class IANAGmailMonitor(GmailMonitorFramework):
    ''' This class implements the functionality to poll gmail accounts for
        image data, and uploads it to the SuryaWebPortal to be stored in 
        the database for subsequent Image Analysis.
    '''
    
    def __init__(self):
        ''' Constructor
        '''
        self.imcache = ImageCache('/home/surya/imagecache')
        
    def checkInbox(self):
        ''' Refer GmailMonitorFramework.checkInbox for documentation. 
        '''
        
        tags = self.gmontags + " IANA"
        
        
        self.log.info("Checking Gmail... {0}".format(str(setting.get("poll_interval"))), extra=tags)
        gmailConn = imaplib.IMAP4_SSL(setting.get("imap_host"), setting.get("imap_port"))
        
        #Login: ('OK', ['20'])
        (status, rsps) = gmailConn.login(setting.get("username"), setting.get("password"))
        if status == 'OK':
            self.log.info("Login successfully username: " + setting.get("username"), extra=tags)
        else:
            self.log.error("Login fail." + str(status) + ":" + str( rsps), extra=tags)
            raise 'Gmail Login Failed'
        
        #Select INBOX: ('OK', ['20'])
        (status, rsps) = gmailConn.select("INBOX")
        if status == 'OK':
            self.log.info("Selecting INBOX successfully.", extra=tags)
        else:
            self.log.error("Cannot select INBOX" + str(status) + ":" + str( rsps), extra=tags)
            raise 'Inbox Selection Failed'
        
        # Search UNSEEN UNDELETED: ('OK', ['1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19'])
        (status, rsps) = gmailConn.search(None, "(UNSEEN UNDELETED)")
        mailIds = rsps[0].split()
        if status == 'OK':
            self.log.info("Finding {0:s} new emails.".format(str(len(mailIds))) +
                 ("unprocessed mail ids: " + rsps[0]) if len(mailIds) else "", extra=tags)
        else:
            self.log.error("Errors while searching (UNSEEN UNDELETED) mails."+ str(status) + ":" + str(rsps), extra=tags)
            return 'Errors searching for Unseen mails'
        
        for mid in mailIds:
            (status, rsps) = gmailConn.fetch(mid, '(RFC822)')
            if status == 'OK':
                self.log.info("Successfully fetching mail (mail id:{0:s})...".format(str(mid)), extra=tags)                    
            else:
                self.log.error("Errors while fetching mail (mail id:{0:s})...".format(str(mid)), extra=tags)
                continue
            
            mailText = rsps[0][1]
            mail = email.message_from_string(mailText)
            
            fromField = rfc822.parseaddr(mail.get("FROM"))[1]
            toField = rfc822.parseaddr(mail.get("TO"))[1]
            
            subjectField = mail.get("SUBJECT") # should be szu###

            if "Result" in subjectField:
                continue
            
            #TODO: add spam detection: only from "surya." with subject "szu" is considered valid.
            self.log.info("The mail (id: {0:s}) is from: <{1:s}> with subject: {2:s}" 
                          .format(str(mid), fromField, subjectField), extra=tags)
            
            
            configDict = {"fromemail":fromField, "toemail":toField}
            isImage = False                
            
            #Downloading attachment from gmail
            parts = mail.walk()
            for p in parts:
                if 'text/plain' in p.get_content_type():
                    message = p.get_payload(decode=True)
                    self.log.info('payload: '+str(message), extra=tags)
                    if message is not None:
                        configParams = [v.split(':', 1) for v in message.splitlines() if ':' in v]
                        for param in configParams:
                            configDict[param[0]] = param[1]
                            
                if p.get_content_maintype() !='multipart' and p.get('Content-Disposition') is not None:
                    fdata = p.get_payload(decode=True)
                    filename = p.get_filename()
                    # Store the file in the file cache
                    picFileName = self.imcache.put(filename, fdata)
                    
                    if picFileName is None:
                        self.log.error('Could Not save ' + filename + ' in the cache', extra=tags)
                        continue
                    
                    #Reading EXIF info
                    (status, pic_datetime_info) = get_original_datetime_N80(picFileName)
                        
                    if status:
                        self.log.info("From Exif metadata, the picture {0:s} is taken at {1:s}"
                             .format(picFileName, pic_datetime_info.strftime("%Y,%m,%d,%H,%M,%S")).replace(',0',','), extra=tags)
                    else:
                        self.log.error("Cannot get original datetime from picture: " + picFileName + "details: " + str(pic_datetime_info), extra=tags)
                        self.imcache.remove(filename)
                        continue # try next part
                    isImage = True

            if isImage:                    
                message = json.dumps(configDict)
                #Uploading to http server
                
                response = cStringIO.StringIO()
    
                curl = pycurl.Curl()
                curl.setopt(curl.WRITEFUNCTION, response.write)
                curl.setopt(curl.POST, 1)
                curl.setopt(curl.URL, setting.get("upload_url"))
                curl.setopt(curl.HTTPPOST,[
                    ("device_id", subjectField),
                    ("aux_id", ""), #TODO: using CronJob to read QR code
                    ("misc", message), #not used
                    ("record_datetime", pic_datetime_info.strftime("%Y,%m,%d,%H,%M,%S").replace(',0',',')), #change 08->8, otherwise the server will complaints because we cannot run datetime(2010,08,23,18,1,1)
                    #("gps", ""), #not used
                    ("data_type", "image/jpeg"),
                    ("version", setting.get("http_post_version")),
                    ("deployment_id", toField[0:toField.index('@')]), #e.g. surya.pltk1 ("from email")
                    ("tag", ""), #not used  
                    ("bin_file", (curl.FORM_FILE, picFileName))
                    ])
                curl.perform()
                self.log.info("Running http post to: "+setting.get("upload_url"), extra=tags)
                server_rsp = str(response.getvalue())
                curl.close()
                if str(server_rsp).startswith("upok"):
                    self.log.info("Successfully Uploading."+ str(server_rsp), extra=tags)
                else:
                    self.log.error("The server returns errors."+ str(server_rsp), extra=tags)
                self.imcache.remove(filename)        
                self.log.info("Deleting uploaded temporary file: " + str(picFileName), extra=tags)  
                    
        gmailConn.close()
        gmailConn.logout()

if __name__ == '__main__':
    gmon = IANAGmailMonitor()
    gmon.run("IANAGmailMonitor.pid", "IANAGmailMonitor", 10)    
    