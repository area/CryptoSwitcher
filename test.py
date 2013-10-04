from bs4 import BeautifulSoup
import urllib2
import time
import subprocess
import numpy as np
import sys
# Ugly hack so git submodule init is adequate.
sys.path.insert(0, './btce-api/')
import btceapi
sys.path.insert(0, './pyvircurex/')
import vircurex as vircurexapi
sys.path.insert(0, './PyCryptsy/')
from PyCryptsy import PyCryptsy

import ConfigParser

import simplejson
import socket

import pprint

#req = urllib2.Request("http://pubapi.cryptsy.com/api.php?method=marketdata")
#opener_cyp = urllib2.build_opener()
#opener_cyp.addheaders = [('User-agent', 'CryptoSwitcher')]
#f = opener_cyp.open(req, timeout = 5)
#data_cyp = simplejson.load(f)
#for i in data_cyp['return']['markets']:
#  if data_cyp['return']['markets'][i]['secondarycode']=='BTC':
#    print i, data_cyp['return']['markets'][i]['buyorders'][0]['price']


req = urllib2.Request("http://pubapi.cryptsy.com/api.php?method=orderdata")
opener_cyp = urllib2.build_opener()
opener_cyp.addheaders = [('User-agent', 'CryptoSwitcher')]
f = opener_cyp.open(req, timeout = 5)
data_cyp = simplejson.load(f)
#pprint.pprint(data_cyp)
for i in data_cyp['return']:
  if data_cyp['return'][i]['secondarycode']=='BTC':
    print i, data_cyp['return'][i]['buyorders'][0]['price']


