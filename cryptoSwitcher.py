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
        self.cnt = 0
        self.median = 0
        self.m = 0
        self.h = 0
        self.fee = 0

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
coins['frc'].command=Config.get('Scripts','frcscript')

source = Config.get('Misc','source')
#Set the threshold where we move from BTC to other MMCs, assuming that
#BTC has a profitability of 100

#get idle time between two profitability check cycles
idletime = int(Config.get('Misc','idletime'))

#get the coinfees
coins['btc'].fee = float(Config.get('Fees','feebtc'))
coins['ltc'].fee = float(Config.get('Fees','feeltc'))
coins['ppc'].fee = float(Config.get('Fees','feeppc'))
coins['nvc'].fee = float(Config.get('Fees','feenvc'))
coins['trc'].fee = float(Config.get('Fees','feetrc'))
coins['sc'].fee = float(Config.get('Fees','feesc'))
coins['bte'].fee = float(Config.get('Fees','feebte'))
coins['frc'].fee = float(Config.get('Fees','feefrc'))


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
    try:
        balance = getattr(r, 'balance_'+coin)
    except:
        #probably a coin that BTCE doesn't have an exchange for, so just return
        return
    if balance > 0.1:
        #i.e. if we're selling and we have some to sell that's larger than the minimum order...
        asks, bids = btceapi.getDepth(coin + '_btc')
        tr = tradeapi.trade(coin + '_btc', 'sell',bids[0][0],balance)
        #This sells at the highest price someone currently has a bid lodged for.
        #It's possible that this won't totally deplete our reserves, but any
        #unsold immediately will be left on the book, and will probably sell shortly.

def sellCoinVircurex(coin):
    pair = vircurexapi.Pair(coin+'_btc')
    try:
        bid = pair.highest_bid
    except:
        #probably a coin that Vircurex doesn't have an exchange for, so just return
        return
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

    elif source=='dustcoin':
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
            #make sure the profit we read is floating value, if not, continue loop and keep old profit value until next check
            try:
                profit = float(profit)
            except:
                continue
            #calculate profitabilty
            if coinName == "Bitcoin":
                coins['btc'].ratio = float(profit)
            elif coinName == "Litecoin":
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

    elif source=='coinotron':
        #get data from coinotron
        url = 'https://coinotron.com/coinotron/AccountServlet?action=home'
        usock = urllib2.urlopen(url)
        data = usock.read()
        usock.close()
        soup = BeautifulSoup(data)

        tablecoins = soup.findAll('tr')
        i = 0

        for coinrow in tablecoins:
            coinName = coinrow.findNext('td').contents[0]
            profit = coinrow.findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').contents[0]
            #make sure the profit we read is floating value, if not, continue loop and keep old profit value until next check
            try:
                profit = float(profit)*100
            except:
                continue
            #calculate profitabilty
            if coinName == "BTC":
                coins['btc'].ratio = float(profit)
            elif coinName == "PPC":
                coins['ppc'].ratio = float(profit)
            elif coinName == "LTC":
                coins['ltc'].ratio = float(profit)
            elif coinName == "TRC":
                coins['trc'].ratio = float(profit)
                break
            elif coinName == "FRC":
                coins['frc'].ratio = float(profit)
                break
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
        except (urllib2.URLError, ValueError, socket.timeout) as  e:
            print "There was an error: ,", e
            vanityDataValid = False

        try:
            usock = urllib2.urlopen('http://www.fizzisist.com/mining-value/api/vanitypool-value',timeout=1)
            btcpergkey = usock.read()
            btcpergkey = float(btcpergkey)
            usock.close()
        except (urllib2.URLError, ValueError, socket.timeout) as  e:
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
    print "\n\n<<<Get best profitabilty>>>"
    print "-"*27
    for abbreviation, c in coins.items():
        if c.willingToMine:
            print "%10s: %3d (fee: %3d)" % (coins[abbreviation].name, c.ratio, coins[abbreviation].fee)
        if c.ratio-coins[abbreviation].fee > bestprof and c.willingToMine:
            bestcoin = abbreviation
            bestprof=c.ratio-coins[abbreviation].fee
    print "-"*27
    print "=> Best: %d, mining %s" % (bestprof, coins[bestcoin].name)
    coins[bestcoin].median = ((coins[bestcoin].median * coins[bestcoin].cnt) + coins[bestcoin].ratio-coins[bestcoin].fee) / (coins[bestcoin].cnt+1)
    coins[bestcoin].cnt = coins[bestcoin].cnt+1


    if coins[bestcoin].miningNow == False:
        #i.e. if we're not already mining the best coin
        print '=> Switching to',coins[bestcoin].name
        for abbreviation, c in coins.items():
            c.miningNow = False
        coins[bestcoin].miningNow = True
        subprocess.Popen(coins[bestcoin].command)

    #Sell some coins if that's what we're into
    sellCoinBTCE('ttt',authedAPI)
    sellCoinVircurex('ttt')
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

    #create status output strings
    smedian = "# Median: "
    stime = "# Time:   "
    median_all = 0
    cnt_all = 0
    for abbreviation, c in coins.items():
        if c.willingToMine:
            coins[abbreviation].h, coins[abbreviation].m = divmod(coins[abbreviation].cnt*idletime, 60)
            smedian += abbreviation.upper()
            smedian += " = %5d |  " % (coins[abbreviation].median)
            stime += abbreviation.upper()
            stime += " = %2d:%02d |  " % (coins[abbreviation].h, coins[abbreviation].m)
            if coins[abbreviation].cnt > 0:
                median_all = ((median_all * cnt_all) + (coins[abbreviation].median*coins[abbreviation].cnt)) / (cnt_all+coins[abbreviation].cnt)
                cnt_all += coins[abbreviation].cnt

    #remove last chars
    smedian = smedian[:-4]
    stime = stime[:-4]
    
    smedian_all = '# Median (all): %5d' % (median_all)
    stime_all = '# Time (all): %4d:%02d' % (divmod(cnt_all*idletime, 60))

    #fill strings to screen width and add "#" to the end
    smedian = "%s%s%s" % (smedian, " "*(78-len(smedian)), "#")
    stime = "%s%s%s" % (stime, " "*(78-len(stime)), "#")
    smedian_all = "%s%s%s" % (smedian_all, " "*(78-len(smedian_all)), "#")
    stime_all = "%s%s%s" % (stime_all, " "*(78-len(stime_all)), "#")

    #output status strings
    print "#"*79
    print smedian
    print stime
    print smedian_all
    print stime_all
    print "#"*79

    #sleep
    print 'Sleeping for %d Minutes...' % (idletime)
    time.sleep(idletime*60)
    
    print time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
