from bs4 import BeautifulSoup
import urllib2
import time
import subprocess
import numpy as np

#---------------------------------------
# Cryptocurrency mining switcher
# TipJar (BTC): 1NhathL6LpcgofDnHELSS6Hej6kU9xrVgp
# Author: area
#---------------------------------------

#Enable the coins you want to mine here.
minebtc = True
mineltc = True
mineppc = False
minenvc = False
minetrc = False

#Mine vanity addresses
minevanity = False

#If you're merged mining some altcoins when you're bitcoin mining, set
#the relevant coins below to 'True'
mmNMC=False
mmDVC=False
mmIXC=False



#You should have scripts that stop all other forms of mining, set 
#your clocks and environment variables appropriately, and start
# mining the appropriate coin. I have these called 'litecoin.sh',
# 'bitcoin.sh' etc., but edit and/or replace these as you see fit.

#Any coins you aren't mining you can just leave blank.

ltcscript = './litecoin.sh'
btcscript = './bitcoin.sh'
vanityscript = './vanitymine.sh'
ppcscript = './ppcoin.sh'
nvcscript = './novacoin.sh'
trcscript = './terracoin.sh'

#Set the threshold where we move from BTC to other MMCs, assuming that 
#BTC has a profitability of 100
threshold = 105
#In an ideal world, this would be 100 i.e. as soon as it's more profitable
#to mine another coin, stop mining BTC. But I've given BTC a little 
#extra edge here, just because of convenience i.e. the time and effort
#required to turn altcoins into BTC.


#And now some information to calculate Vanity Address mining profitability
gkeypersec = float(0.05) #Gigakeys per second you can test
ghashpersec = float(0.7) #Gigahash per second you can output doing normal BTC mining.


#-----------
#Hopefully nothing below this needs editing.
#-----------

url = 'http://dustcoin.com/mining'

btcMining = False
ltcMining = False
trcMining = False
ppcMining = False
nvcMining = False
vanityMining = False
while True:
    #get data from the incredible dustcoin
    usock = urllib2.urlopen(url)
    data = usock.read()
    usock.close()
    soup = BeautifulSoup(data)

    coins = soup.findAll('tr',{ "class":"coin" })
    i = 0
    
    
    ltcprofit = 0
    ppcprofit = 0
    trcproft=0
    nvcprofit=0
    vanityprofit =0
    nmcprofit=0
    ixcprofit=0
    dvcprofit=0
    btcprofit = float(threshold)
    
    for coinrow in coins:
        coinName, profit = coinrow.find('strong',text=True).text, coinrow.find('td',{"id":"profit"+str(i)}).text.replace('%','')
        if profit =='?': profit = 0
        #No BTC here, because mining BTC is always 100% compared to BTC
        if coinName == "Litecoin" and mineltc:
            ltcprofit = float(profit)
            print coinName, profit
        elif coinName == "PPCoin" and mineppc:
            ppcprofit = float(profit)
            print coinName, profit
        elif coinName == "Terracoin" and minetrc:
            trcprofit = float(profit)
            print coinName, profit
        elif coinName == "NovaCoin" and minenvc:
            nvcprofit = float(profit)
            print coinName, profit
        elif coinName == "Namecoin" and mmNMC:
            nmcprofit = float(profit)
            print coinName, profit
        elif coinName == "Devcoin" and mmDVC:
            dvcprofit = float(profit)
            print coinName, profit
        elif coinName == "Ixcoin" and mmIXC:
            ixcprofit = float(profit)
            print coinName, profit
        i+=1
  
    #Now work out how profitable btc mining is, if we're doing any merged mining
    btcprofit +=nmcprofit + dvcprofit + ixcprofit
    print "Bitcoin:", btcprofit

    #Now get data for vanity mining
    if minevanity:
        usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/bitcoin-value')
        btcperghash = usock.read()
        usock.close()
        usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/vanitypool-value')
        btcpergkey = usock.read()
        usock.close()
        #Now put vanity mining in terms of BTC mining. 
        vanitybtcsec = gkeypersec * float(btcpergkey)
        miningbtcsec = ghashpersec * float(btcperghash)
        vanityprof = vanitybtcsec / miningbtcsec * 100
        print 'Vanity Mining', vanityprof
    
    bestprof = np.amax([float(btcprofit),float(vanityprof),float(ltcprofit),float(trcprofit),float(ppcprofit), float(nvcprofit)])
    print 'best:',bestprof
    if bestprof == ltcprofit and ltcMining == False:
        ltcMining = True
        btcMining = False
        vanityMining = False
        ppcMining=False
        trcMining=False
        nvcMining = False
        print 'Switch to LTC'
        subprocess.Popen([ltcscript])
    elif bestprof == vanityprof and vanityMining == False:
        ltcMining = False
        btcMining = False
        vanityMining = True
        ppcMining=False
        trcMining=False
        nvcMining = False
        print 'Switch to Vanity'
        subprocess.Popen([vanityscript])
    elif bestprof == ppcprofit and ppcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=True
        trcMining=False
        nvcMining = False
        print 'Switch to PPC'
        subprocess.Popen([ppcscript])
    elif bestprof == trcprofit and trcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=False
        trcMining=True
        nvcMining = False
        print 'Switch to TRC'
        subprocess.Popen([trcscript])
    elif bestprof == nvcprofit and nvcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=False
        trcMining=False
        nvcMining = True
        print 'Switch to NVC'
        subprocess.Popen([nvcscript])
    elif bestprof == btcprofit and btcMining==False:
        ltcMining = False
        btcMining = True
        vanityMining = False
        trcMining=False
        ppcMining = False
        nvcMining = False
        print 'Switch to BTC'
        subprocess.Popen([btcscript])
    time.sleep(3600)
    print time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
