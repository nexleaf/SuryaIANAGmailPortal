'''
Created on Nov 15, 2010

@author: surya
'''

######################
# File Configuration #
######################


setting = {"smtp_host": "smtp.gmail.com",
           "smtp_port": 587,
           "imap_host": "imap.gmail.com",
           "imap_port": 993,
           "username": "surya.pltk1@gmail.com",
           "password": "replaceme",
           "use_tls":  "True",
           "poll_interval": 10,
           "upload_url": "http://127.0.0.1:8000/upload_image/",
           "http_post_version":"SuryaIANAGmailPortal",
           "config_keys":['exposedtime', 'flowrate', 'filterradius', 'toemail', 'fromemail']
           }

try:
    from Settings_local import *
except ImportError:
    pass

