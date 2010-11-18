'''
Created on Nov 15, 2010

@author: surya
'''
import sys
import time
import json
import logging
import smtplib

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

connect('SuryaDB')

class IANAGmailResults(GmailResultsFramework):
    ''' This class implements the functionality to poll the SuryaDB
        for results on processing uploaded images and emails the 
        sender with these results.
    '''
    
    def checkResults(self):
        ''' Refer GmailResultsFramework.checkResults for documentation
        '''        
        
        tags = self.grestags + " IANA"
        
        gmail_user = setting.get("username")
        gmail_pwd = setting.get("password")
        smtpserver = smtplib.SMTP("smtp.gmail.com",587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo
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
                
                msg = MIMEMultipart('localhost')
                                   
                # attach preProcessingResult.
                text = 'Results on PREPROCESSING the Image for configuration: \n'
                preProcessingConfiguration = item.preProcessingConfiguration
                text += 'PreProcessing Parameters Used: \n'
                text += 'dp           : '+str(preProcessingConfiguration.dp) + '\n'
                text += 'minimumRadius: '+str(preProcessingConfiguration.minimumRadius) + '\n'
                text += 'maximumRadius: '+str(preProcessingConfiguration.maximumRadius) + '\n'
                text += 'highThreshold: '+str(preProcessingConfiguration.highThreshold) + '\n'
                text += 'accumulatorThreshold: '+str(preProcessingConfiguration.accumulatorThreshold) + '\n'
                text += 'minimumDistance: '+str(preProcessingConfiguration.minimumDistance) + '\n'
                text += 'samplingFactor : '+str(preProcessingConfiguration.samplingFactor) + '\n\n'
                
                text += 'Results: \n'
                text += 'SampledRGB  : ' + str(item.preProcessingResult.sampled) + '\n'
                text += 'DebugPicName: '+item.preProcessingResult.debugImage.name + '\n\n'
                
                # attach computation Result.
                text += 'Results on COMPUTATION of the Results: \n'
                computationConfiguration = item.computationConfiguration
                text += 'Computation parameters Used: \n'
                text += 'filterRadius: ' + str(computationConfiguration.filterRadius) + '\n'
                text += 'exposedTime : ' + str(computationConfiguration.exposedTime) + '\n'
                text += 'bcStrip     : ' + str(item.bcStrips.bcStrips) + '\n'
                text += 'airFlowRate : ' + str(computationConfiguration.airFlowRate) + '\n\n'

                result = item.computationResult.result
                text += 'Results: \n'
                text += 'BCAreaRed    : ' + str(result.BCAreaRed) + '\n'
                text += 'BCAreaGreen  : ' + str(result.BCAreaGreen) + '\n'
                text += 'BCAreaBlue   : ' + str(result.BCAreaBlue) + '\n'
                text += 'BCVolRed     : ' + str(result.BCVolRed) + '\n'
                text += 'BCVolGreen   : ' + str(result.BCVolGreen) + '\n'
                text += 'BCVolBlue    : ' + str(result.BCVolBlue) + '\n\n'
                text += 'chartFileName: ' + str(item.computationResult.chartImage.name) + '\n'
                
                textmsg = MIMEText(text)
                msg.attach(textmsg)
                
                smtpserver.sendmail(setting.get("username"), misc_dict["fromemail"], msg.as_string())
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
                
                msg = MIMEMultipart('localhost')
                    
                # if item failed in PPROCCALIB PHASE
                if "PPROCCALIB" in item.status:
                    text = "Failed to Fetch PreProcessingData for item : "+item.item.file.name+'\n\n'
                # if item failed in PPROC PHASE
                elif "PPROC" in item.status:
                    text = "Failed to PreProcess the item: "+item.item.file.name+"\n\n"
                    preProcessingConfiguration = item.preProcessingConfiguration
                    text += 'PreProcessing Parameters Used: \n'
                    text += 'dp           : '+str(preProcessingConfiguration.dp) + '\n'
                    text += 'minimumRadius: '+str(preProcessingConfiguration.minimumRadius) + '\n'
                    text += 'maximumRadius: '+str(preProcessingConfiguration.maximumRadius) + '\n'
                    text += 'highThreshold: '+str(preProcessingConfiguration.highThreshold) + '\n'
                    text += 'accumulatorThreshold: '+str(preProcessingConfiguration.accumulatorThreshold) + '\n'
                    text += 'minimumDistance: '+str(preProcessingConfiguration.minimumDistance) + '\n'
                    text += 'samplingFactor : '+str(preProcessingConfiguration.samplingFactor) + '\n\n'
                    text += 'DebugPicName   : '+str(item.preProcessingResult.debugImage.name) + '\n\n'
                    
                # if item failed in COMPUCALIB PHASE
                elif "COMPUCALIB" in item.status:
                    text = "Failed to Fetch Computation Calibration info: "+item.item.file.name+"\n\n"
                    
                    text += 'Results on PREPROCESSING the Image for configuration: \n'
                    preProcessingConfiguration = item.preProcessingConfiguration
                    text += 'PreProcessing Parameters Used: \n'
                    text += 'dp           : '+str(preProcessingConfiguration.dp) + '\n'
                    text += 'minimumRadius: '+str(preProcessingConfiguration.minimumRadius) + '\n'
                    text += 'maximumRadius: '+str(preProcessingConfiguration.maximumRadius) + '\n'
                    text += 'highThreshold: '+str(preProcessingConfiguration.highThreshold) + '\n'
                    text += 'accumulatorThreshold: '+str(preProcessingConfiguration.accumulatorThreshold) + '\n'
                    text += 'minimumDistance: '+str(preProcessingConfiguration.minimumDistance) + '\n'
                    text += 'samplingFactor : '+str(preProcessingConfiguration.samplingFactor) + '\n\n'
                    
                    text += 'Results: \n'
                    text += 'SampledRGB  : ' + str(item.preProcessingResult.sampled) + '\n'
                    text += 'DebugPicName: '+str(item.preProcessingResult.debugImage.name) + '\n\n'
                    
                # if item failed in COMPU PHASE
                elif "COMPU" in item.status:
                        text = "Failed to Computate Results: "+item.item.file.name+"\n\n"
                        
                        text += 'Results on PREPROCESSING the Image for configuration: \n'
                        preProcessingConfiguration = item.preProcessingConfiguration
                        text += 'PreProcessing Parameters Used: \n'
                        text += 'dp           : '+str(preProcessingConfiguration.dp) + '\n'
                        text += 'minimumRadius: '+str(preProcessingConfiguration.minimumRadius) + '\n'
                        text += 'maximumRadius: '+str(preProcessingConfiguration.maximumRadius) + '\n'
                        text += 'highThreshold: '+str(preProcessingConfiguration.highThreshold) + '\n'
                        text += 'accumulatorThreshold: '+str(preProcessingConfiguration.accumulatorThreshold) + '\n'
                        text += 'minimumDistance: '+str(preProcessingConfiguration.minimumDistance) + '\n'
                        text += 'samplingFactor : '+str(preProcessingConfiguration.samplingFactor) + '\n\n'
                        
                        text += 'Results: \n'
                        text += 'SampledRGB  : ' + str(item.preProcessingResult.sampled) + '\n'
                        text += 'DebugPicName: '+str(item.preProcessingResult.debugImage.name) + '\n\n'
                        
                        # attach computation Result.
                        text += 'Results on COMPUTATION of the Results: \n'
                        computationConfiguration = item.computationConfiguration
                        text += 'Computation parameters Used: \n'
                        text += 'filterRadius: ' + str(computationConfiguration.filterRadius) + '\n'
                        text += 'exposedTime : ' + str(computationConfiguration.exposedTime) + '\n'
                        text += 'bcStrip     : ' + str(item.bcStrips.bcStrips) + '\n'
                        text += 'airFlowRate : ' + str(computationConfiguration.airFlowRate) + '\n\n'

                # if item failed in SAVIN PHASE
                elif "SAVIN" in item.status:
                        text = "Failed to Save Results for item : "+item.item.file.name+'\n\n'
                
                else:
                        text = "Failed processing item: "+item.item.file.name+'\n'
                        
                msgtext = MIMEText(text)
                msg.attach(msgtext)
                smtpserver.sendmail(setting.get("username"), misc_dict["fromemail"], msg.as_string())
                self.log.info("sent email", extra=tags)
                item.isEmailed = True
                item.save()
                     
        smtpserver.close()

        
if __name__ == '__main__':
    connect('SuryaDB')
    gres = IANAGmailResults()
    gres.run("IANAGmailResults.pid", "IANAGmailResults", 10)