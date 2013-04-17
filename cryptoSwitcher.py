from bs4 import BeautifulSoup
import urllib2
import time
import subprocess
import numpy as np
import sys
#Ugly hack so git submodule init is adequate.
sys.path.insert(0, './btce-api/')
import btceapi
sys.path.insert(0, './pyvircurex/')
import vircurex as vircurexapi

import ConfigParser

import simplejson
import socket

#-----------
#Hopefully nothing below this needs editing.
#-----------

class Coin:
    def __init__(self, name):
        self.ratio=0 #assume totally unprofitable unless otherwise shown to be the case.
        self.willingToMine = False
        self.miningNow = False
        self.merged = False
        self.willingToSell = False
        self.command = '' #the command that is run when we want to mine this coin.
        self.name = name

coins = {}
coins['btc'] =  Coin('Bitcoin')
coins['bte'] =  Coin('Bytecoin')
coins['dvc'] =  Coin('Devcoin')
coins['dvc'].merged = True
coins['frc'] =  Coin('Freicoin')
coins['ixc'] =  Coin('IXCoin')
coins['ixc'].merged = True
coins['ltc'] =  Coin('Litecoin')
coins['nmc'] =  Coin('NameCoin')
coins['nmc'].merged = True
coins['ppc'] =  Coin('PPCoin')
coins['nvc'] =  Coin('NovaCoin')
coins['sc'] =  Coin('SolidCoin')
coins['trc'] =  Coin('TerraCoin')
#Kind of an alternate coin...
coins['vanity'] = Coin('Vanity Mining')

#Read in config file
Config = ConfigParser.ConfigParser()
Config.read('./cryptoSwitcher.config')

#Enable the coins you want to mine here.
coins['btc'].willingToMine = Config.getboolean('MineCoins','minebtc')
coins['ltc'].willingToMine = Config.getboolean('MineCoins','mineltc')
coins['ppc'].willingToMine = Config.getboolean('MineCoins','mineppc')
coins['nvc'].willingToMine = Config.getboolean('MineCoins','minenvc')
coins['trc'].willingToMine = Config.getboolean('MineCoins','minetrc')
coins['sc'].willingToMine = Config.getboolean('MineCoins','minesc')
coins['bte'].willingToMine = Config.getboolean('MineCoins','minebte')
coins['frc'].willingToMine = Config.getboolean('MineCoins','minefrc')

#Mine vanity addresses
coins['vanity'].willingToMine = Config.getboolean('MineCoins','minevanity')

#If you're merged mining some altcoins when you're bitcoin mining, set
#the relevant coins below to 'True'

coins['nmc'].willingToMine=Config.getboolean('MineCoins','mmNMC')
coins['dvc'].willingToMine=Config.getboolean('MineCoins','mmDVC')
coins['ixc'].willingToMine=Config.getboolean('MineCoins','mmIXC')

#You should have scripts that stop all other forms of mining, set 
#your clocks and environment variables appropriately, and start
# mining the appropriate coin. I have these called 'litecoin.sh',
# 'bitcoin.sh' etc., but edit and/or replace these as you see fit.

#Any coins you aren't mining you can just leave blank.

coins['btc'].command=Config.get('Scripts','btcscript')
coins['ltc'].command=Config.get('Scripts','ltcscript')
coins['vanity'].command=Config.get('Scripts','vanityscript')
coins['ppc'].command=Config.get('Scripts','ppcscript')
coins['nvc'].command=Config.get('Scripts','nvcscript')
coins['trc'].command=Config.get('Scripts','trcscript')
coins['sc'].command=Config.get('Scripts','scscript')
coins['bte'].command=Config.get('Scripts','btescript')

source = Config.get('Misc','source')
#Set the threshold where we move from BTC to other MMCs, assuming that 
#BTC has a profitability of 100
threshold = float(Config.get('Misc','threshold'))
#In an ideal world, this would be 100 i.e. as soon as it's more profitable
#to mine another coin, stop mining BTC. But I've given BTC a little 
#extra edge here, just because of convenience i.e. the time and effort
#required to turn altcoins into BTC.


#And now some information to calculate Vanity Address mining profitability
gkeypersec = float(Config.get('Misc','gkeypersec')) #Gigakeys per second you can test
ghashpersec = float(Config.get('Misc','ghashpersec')) #Gigahash per second you can output doing normal BTC mining.

#If you want to sell your coins on BTCE ASAP, then there's a bit more setup for you
enableBTCE = Config.getboolean('Sell','enableBTCE')

enableVircurex = Config.getboolean('Sell','enableVircurex')
vircurexSecret = Config.get('Sell','vircurexSecret')
vircurexUsername = Config.get('Sell','vircurexUsername')

#And flag which coins you want to sell as they come in. These coins will only
#sell for BTC, not for USD or any other cryptocoin.
coins['ltc'].willingToSell = Config.getboolean('Sell','sellLTC')
coins['nmc'].willingToSell= Config.getboolean('Sell','sellNMC')
coins['trc'].willingToSell= Config.getboolean('Sell','sellTRC')
coins['ppc'].willingToSell= Config.getboolean('Sell','sellPPC')
coins['nvc'].willingToSell= Config.getboolean('Sell','sellNVC')
coins['dvc'].willingToSell= Config.getboolean('Sell','sellDVC')
coins['ixc'].willingToSell= Config.getboolean('Sell','sellIXC')


def sellCoinBTCE(coin, tradeapi):
    r = tradeapi.getInfo()
    balance = getattr(r, 'balance_'+coin)
    if balance > 0.1:
        #i.e. if we're selling and we have some to sell that's larger than the minimum order...
        asks, bids = btceapi.getDepth(coin + '_btc')
        tr = tradeapi.trade(coin + '_btc', 'sell',bids[0][0],balance)       
        #This sells at the highest price someone currently has a bid lodged for.
        #It's possible that this won't totally deplete our reserves, but any 
        #unsold immediately will be left on the book, and will probably sell shortly.

def sellCoinVircurex(coin):
    pair = vircurexapi.Pair(coin+'_btc')
    bid = pair.highest_bid
    account = vircurexapi.Account(vircurexUsername, vircurexSecret)
    balance = account.balance(coin.upper())
    if balance >= 0.1:
        order = account.sell(coin.upper(),balance, 'BTC', bid)
        account.release_order(order['orderid'])

if enableBTCE:
    key_file = './key' 
    handler = btceapi.KeyHandler(key_file)
    key = handler.keys.keys()[0]
    secret, nonce =  handler.keys[handler.keys.keys()[0]]
    authedAPI = btceapi.TradeAPI(key, secret, nonce)

while True:
    if source=='coinchoose':
        #Then we're getting data from coinchoose

        req = urllib2.Request("http://www.coinchoose.com/api.php")
        opener = urllib2.build_opener()
        f = opener.open(req)
        output = simplejson.load(f)
        for item in output:
            coins[item['symbol'].lower()].ratio = float(item['ratio'])
        coins['btc'].ratio = threshold

    elif source=='dustcoin':
        coins['btc'].ratio = threshold
        #get data from dustcoin
        url = 'http://dustcoin.com/mining'
        usock = urllib2.urlopen(url)
        data = usock.read()
        usock.close()
        soup = BeautifulSoup(data)

        tablecoins = soup.findAll('tr',{ "class":"coin" })
        i = 0
        
        for coinrow in tablecoins:
            coinName, profit = coinrow.find('strong',text=True).text, coinrow.find('td',{"id":"profit"+str(i)}).text.replace('%','')
            if profit =='?': profit = 0
            #No BTC here, because mining BTC is always 100% compared to BTC
            if coinName == "Litecoin":
                coins['ltc'].ratio = float(profit)
            elif coinName == "PPCoin":
                coins['ppc'].ratio = float(profit)
            elif coinName == "Terracoin":
                coins['trc'].ratio = float(profit)
            elif coinName == "NovaCoin":
                coins['nvc'].ratio = float(profit)
            elif coinName == "Namecoin":
                coins['nmc'].ratio = float(profit)
            elif coinName == "Devcoin":
                coins['dvc'].ratio = float(profit)
            elif coinName == "Ixcoin":
                coins['ixc'].ratio = float(profit)
            i+=1
    else:
        print 'Invalid source given. Exiting'
        exit()

    #Now work out how profitable btc mining really is, if we're doing any merged mining
    if coins['nmc'].willingToMine:
        coins['btc'].ratio +=coins['nmc'].ratio
    if coins['dvc'].willingToMine:
        coins['btc'].ratio +=coins['dvc'].ratio
    if coins['ixc'].willingToMine:
        coins['btc'].ratio +=coins['ixc'].ratio

    #Now get data for vanity mining
    if coins['vanity'].willingToMine:
        vanityDataValid = True
        try:
            usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/bitcoin-value',timeout=1)
            btcperghash = usock.read()
            usock.close()
            btcperghash = float(btcperghash)
        except (urllib2.URLError, ValueError) as  e:
            print "There was an error: ,", e
            vanityDataValid = False

        try:
            usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/vanitypool-value',timeout=1)
            btcpergkey = usock.read()
            btcpergkey = float(btcpergkey)
            usock.close()
        except (urllib2.URLError, ValueError) as  e:
            print "There was an error: ,", e
            vanityDataValid = False
            
        if vanityDataValid:
            #Now put vanity mining in terms of BTC mining. 
            vanitybtcsec = gkeypersec * btcpergkey
            miningbtcsec = ghashpersec * btcperghash
            vanityprof = vanitybtcsec / miningbtcsec * 100
            coins['vanity'].ratio = vanityprof
            print 'Vanity Mining', vanityprof
    
    #Now find the best profit coin
    bestcoin = 'btc'
    bestprof = 0
    for abbreviation, c in coins.items():
        print coins[abbreviation].name, ':', c.ratio
        if c.ratio > bestprof and c.willingToMine:
            bestcoin = abbreviation
            bestprof=c.ratio
    print 'best:',bestprof,'mining',coins[bestcoin].name
   
    
    if coins[bestcoin].miningNow == False:
        #i.e. if we're not already mining the best coin
        print 'Switch to',coins[bestcoin].name
        for abbreviation, c in coins.items():
            c.miningNow = False
        coins[bestcoin].miningNow = True
        subprocess.Popen(coins[bestcoin].command)

    #Sell some coins if that's what we're into
    for abbreviation, c in coins.items():
        if c.willingToSell and (c.miningNow or c.merged) and enableBTCE:
            #i.e. if we're willing to sell it AND it's still worth more than BTC - 
            #with pool payout delays and wild exchange swings, while it might be
            #profitable to have mined it, we didn't sell it quickly enough. This
            #keeps hold of the coin until you've made a decision.
            sellCoinBTCE(abbreviation, authedAPI)
        #elif c.willingToSell and c.miningNow and enableVircurex:
        if c.willingToSell and enableVircurex and (c.miningNow or c.merged):
            sellCoinVircurex(abbreviation)

    #...and now save the keyfile in case the script is aborted.
    if enableBTCE:
        handler.setNextNonce(key,time.time()) #Thanks, jsorchik
        handler.save(key_file)            
    print 'Sleeping for 1 hour'
    time.sleep(3600)
    print time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
