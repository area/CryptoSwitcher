from bs4 import BeautifulSoup
import urllib2
import time
import subprocess
import numpy as np
import sys
#Ugly hack so git submodule init is adequate.
sys.path.insert(0, './btce-api/')
import btceapi
import ConfigParser


#Read in config file
Config = ConfigParser.ConfigParser()
Config.read('./cryptoSwitcher.config')

#Enable the coins you want to mine here.
minebtc = Config.getboolean('MineCoins','minebtc')
mineltc = Config.getboolean('MineCoins','mineltc')
mineppc = Config.getboolean('MineCoins','mineppc')
minenvc = Config.getboolean('MineCoins','minenvc')
minetrc = Config.getboolean('MineCoins','minetrc')

#Mine vanity addresses
minevanity = Config.get('MineCoins','minevanity')

#If you're merged mining some altcoins when you're bitcoin mining, set
#the relevant coins below to 'True'

mmNMC=Config.getboolean('MineCoins','mmNMC')
mmDVC=Config.getboolean('MineCoins','mmDVC')
mmIXC=Config.getboolean('MineCoins','mmIXC')

#You should have scripts that stop all other forms of mining, set 
#your clocks and environment variables appropriately, and start
# mining the appropriate coin. I have these called 'litecoin.sh',
# 'bitcoin.sh' etc., but edit and/or replace these as you see fit.

#Any coins you aren't mining you can just leave blank.

btcscript=Config.get('Scripts','btcscript')
ltcscript=Config.get('Scripts','ltcscript')
vanityscript=Config.get('Scripts','vanityscript')
ppcscript=Config.get('Scripts','ppcscript')
nvcscript=Config.get('Scripts','nvcscript')
trcscript=Config.get('Scripts','trcscript')

#Set the threshold where we move from BTC to other MMCs, assuming that 
#BTC has a profitability of 100
threshold = Config.get('Misc','threshold')
#In an ideal world, this would be 100 i.e. as soon as it's more profitable
#to mine another coin, stop mining BTC. But I've given BTC a little 
#extra edge here, just because of convenience i.e. the time and effort
#required to turn altcoins into BTC.


#And now some information to calculate Vanity Address mining profitability
gkeypersec = float(Config.get('Misc','gkeypersec')) #Gigakeys per second you can test
ghashpersec = float(Config.get('Misc','ghashpersec')) #Gigahash per second you can output doing normal BTC mining.

#If you want to sell your coins on BTCE ASAP, then there's a bit more setup for you
enableBTCE = Config.getboolean('Sell','enableBTCE')

#And flag which coins you want to sell as they come in. These coins will only
#sell for BTC, not for USD or any other cryptocoin.
sellLTC = Config.getboolean('Sell','sellLTC')
sellNMC = Config.getboolean('Sell','sellNMC')
sellTRC = Config.getboolean('Sell','sellTRC')
sellPPC = Config.getboolean('Sell','sellPPC')
sellNVC = Config.getboolean('Sell','sellNVC')

#Now edit the file called 'key.sample' to contain your api key, your secret,
#and a nonce on three separate lines. If you haven't used the key before, a
#nonce of '100' should be fine. Rename 'key.sample' to 'key'.








#-----------
#Hopefully nothing below this needs editing.
#-----------

def sellCoin(coin, tradeapi):
    r = tradeapi.getInfo()
    balance = getattr(r, 'balance_'+coin)
    if balance > 0:
        #i.e. if we're selling and we have some to sell... 
        asks, bids = btceapi.getDepth(coin + '_btc')
        tr = tradeapi.trade(coin + '_btc', 'sell',bids[0][0],balance)       
        #This sells at the highest price someone currently has a bid lodged for.
        #It's possible that this won't totally deplete our reserves, but any 
        #unsold immediately will be left on the book, and will probably sell shortly.

url = 'http://dustcoin.com/mining'

btcMining = False
ltcMining = False
trcMining = False
ppcMining = False
nvcMining = False
vanityMining = False

if enableBTCE:
    key_file = './key' 
    handler = btceapi.KeyHandler(key_file)
    key = handler.keys.keys()[0]
    secret, nonce =  handler.keys[handler.keys.keys()[0]]
    authedAPI = btceapi.TradeAPI(key, secret, nonce)




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
    vanityprof =0
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
        vanityDataValid = True
        try:
            usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/bitcoin-value')
            btcperghash = usock.read()
            usock.close()
        except urllib2.URLError, e:
            print "There was an error: ,", e
            vanityDataValid = False

        try:
            usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/vanitypool-value')
            btcpergkey = usock.read()
            usock.close()
        except urllib2.URLError, e:
            print "There was an error: ,", e
            vanityDataValid = False
            
        if vanityDataValid:
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
        subprocess.Popen(ltcscript, shell=True)
    elif bestprof == vanityprof and vanityMining == False:
        ltcMining = False
        btcMining = False
        vanityMining = True
        ppcMining=False
        trcMining=False
        nvcMining = False
        print 'Switch to Vanity'
        subprocess.Popen([vanityscript],shell=True)
    elif bestprof == ppcprofit and ppcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=True
        trcMining=False
        nvcMining = False
        print 'Switch to PPC'
        subprocess.Popen([ppcscript],shell=True)
    elif bestprof == trcprofit and trcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=False
        trcMining=True
        nvcMining = False
        print 'Switch to TRC'
        subprocess.Popen([trcscript],shell=True)
    elif bestprof == nvcprofit and nvcMining==False:
        ltcMining = False
        btcMining = False
        vanityMining = False
        ppcMining=False
        trcMining=False
        nvcMining = True
        print 'Switch to NVC'
        subprocess.Popen([nvcscript],shell=True)
    elif bestprof == btcprofit and btcMining==False:
        ltcMining = False
        btcMining = True
        vanityMining = False
        trcMining=False
        ppcMining = False
        nvcMining = False
        print 'Switch to BTC'
        subprocess.Popen([btcscript],shell=True)
    
    
    #Now sell some coins if that's what we're into. 
    if sellLTC:
        sellCoin('ltc', authedAPI) 
    if sellNMC:
        sellCoin('nmc', authedAPI) 
    if sellNVC:
        sellCoin('nvc', authedAPI) 
    if sellTRC:
        sellCoin('trc', authedAPI) 
    if sellPPC:
        sellCoin('ppc', authedAPI) 

    #...and now save the keyfile in case the script is aborted.
    if enableBTCE:
        handler.save(key_file)            
    print 'Sleeping for 1 hour'
    time.sleep(3600)
    print time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
