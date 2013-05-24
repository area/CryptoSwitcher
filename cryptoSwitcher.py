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
        self.source = ''

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
coins['bqc'] =  Coin('BBQCoin')
coins['trc'] =  Coin('TerraCoin')
coins['ftc'] =  Coin('FeatherCoin')
coins['mnc'] =  Coin('Mincoin')
coins['cnc'] =  Coin('CHNCoin')
coins['btb'] =  Coin('Bitbar')
coins['wdc'] =  Coin('Worldcoin')
coins['dgc'] =  Coin('DigitalCoin')
#Kind of an alternate coin...
coins['vanity'] = Coin('Vanity Mining')

#Read in config file
Config = ConfigParser.ConfigParser()
Config.read('./cryptoSwitcher.config')

#Enable the coins you want to mine here.
for key in coins:
    try:
        coins[key].willingToMine = Config.getboolean('MineCoins','mine'+key)
    except:
        continue

#You should have scripts that stop all other forms of mining, set
#your clocks and environment variables appropriately, and start
# mining the appropriate coin. I have these called 'litecoin.sh',
# 'bitcoin.sh' etc., but edit and/or replace these as you see fit.

#Any coins you aren't mining you can just leave blank.
for key in coins:
    try:
        coins[key].command = Config.get('Scripts',key+'script')
    except:
        continue

#read source list
source = [x.strip() for x in Config.get('Misc','source').split(',')]

#get idle time between two profitability check cycles
idletime = int(Config.get('Misc','idletime'))

#get the coinfees
for key in coins:
    try:
        coins[key].fee = float(Config.get('Fees','fee'+key))
    except:
        continue


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
for key in coins:
    try:
        coins[key].willingToSell = Config.getboolean('Sell','sell'+key)
    except:
        continue


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

cnt_all = 0
while True:
    #get data from sources
    print "\n\n\n<<< Round %d >>>" % (cnt_all+1)
    print "time:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print "getting data...",
    #coinchoose
    try:
        req = urllib2.Request("http://www.coinchoose.com/api.php")
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'CryptoSwitcher')]
    except:
        print "\nnotice: something wrong with coinchoose\n"

    #dustcoin
    try:
        usock = urllib2.urlopen('http://dustcoin.com/mining')
        data = usock.read()
        usock.close()
        soup = BeautifulSoup(data)
        table_dustcoin = soup.findAll('tr',{ "class":"coin" })
    except:
        print "\nnotice: something wrong with dustcoin\n"

    #coinotron
    try:
        usock = urllib2.urlopen('https://coinotron.com/coinotron/AccountServlet?action=home')
        data = usock.read()
        usock.close()
        soup = BeautifulSoup(data)
        table_coinotron = soup.findAll('tr')
    except:
        print "\nnotice: something wrong with coinotron"
    print "done"

    print "decoding data...",
    #assign data to coins
    #loop through coins
    for abbreviation, c in coins.items():
        #current read marked as unsuccessful by default
        success = 0
        #loop trough source list. try first entry first.
        for x in source:
            if x=='coinchoose':
                try:
                    f = opener.open(req)
                    output = simplejson.load(f)
                    for item in output:
                        if item['symbol'].lower()==abbreviation:
                            coins[item['symbol'].lower()].ratio = float(item['ratio'])
                            coins[item['symbol'].lower()].source = 'cc'
                            success = 1
                            break
                except:
                    continue

            elif x=='dustcoin':
                try:
                    i=0
                    for coinrow in table_dustcoin:
                        coinName, profit = coinrow.find('strong',text=True).text, coinrow.find('td',{"id":"profit"+str(i)}).text.replace('%','')
                        #make sure the profit we read is floating value, if not, continue loop and keep old profit value until next check
                        try:
                            profit = float(profit)
                        except:
                            continue
                        #calculate profitabilty
                        if coinName == coins[abbreviation].name:
                            coins[abbreviation].ratio = float(profit)
                            coins[abbreviation].source = 'dc'
                            success = 1
                            break
                        i+=1
                except:
                    continue

            elif x=='coinotron':
                try:
                    i = 0
                    for coinrow in table_coinotron:
                        coinName = coinrow.findNext('td').contents[0]
                        profit = coinrow.findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').findNext('td').contents[0]
                        #when all coins where read, leave loop
                        if i == 5: break
                        i+=1
                        #convert profitability to percent
                        profit = float(profit)*100
                        #calculate profitabilty
                        if coinName.lower()==abbreviation:
                            coins[abbreviation].ratio = float(profit)
                            coins[abbreviation].source = 'ct'
                            success = 1
                            break
                        i+=1
                except:
                    continue

            if success==1:
                break

    #Now work out how profitable btc mining really is, if we're doing any merged mining
    if coins['nmc'].willingToMine:
        coins['btc'].ratio +=coins['nmc'].ratio
    if coins['dvc'].willingToMine:
        coins['btc'].ratio +=coins['dvc'].ratio
    if coins['ixc'].willingToMine:
        coins['btc'].ratio +=coins['ixc'].ratio

    print "done"


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
            #print 'Vanity Mining', vanityprof

    #Now find the best profit coin
    bestcoin = 'btc'
    bestprof = 0
    print "comparing profitabilty..."
    print "-"*36
    for abbreviation, c in coins.items():
        if c.willingToMine:
            print "%11s: %3d  (fee: %2d, src: %s)" % (coins[abbreviation].name, c.ratio, coins[abbreviation].fee, coins[abbreviation].source)
        if c.ratio-coins[abbreviation].fee > bestprof and c.willingToMine:
            bestcoin = abbreviation
            bestprof=c.ratio-coins[abbreviation].fee
    print "-"*36
    print "=> Best: %d, mining %s" % (bestprof, coins[bestcoin].name)
    coins[bestcoin].median = ((coins[bestcoin].median * coins[bestcoin].cnt) + coins[bestcoin].ratio-coins[bestcoin].fee) / (coins[bestcoin].cnt+1)
    coins[bestcoin].cnt = coins[bestcoin].cnt+1


    if coins[bestcoin].miningNow == False:
        #i.e. if we're not already mining the best coin
        print '=> Switching to %s (running %s)' % (coins[bestcoin].name, coins[bestcoin].command)
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

    #create status output strings
    sname = "#        "
    smedian = "# Median:"
    stime = "# Time:  "
    median_all = 0
    cnt_all = 0
    for abbreviation, c in coins.items():
        if c.willingToMine:
            coins[abbreviation].h, coins[abbreviation].m = divmod(coins[abbreviation].cnt*idletime, 60)
            coins['dgc'].h = 10
            if coins[abbreviation].h < 10:
                sname += "%5s  " % (abbreviation.upper())
                smedian += "%5d |" % (coins[abbreviation].median)
                stime += "%2d:%02d |" % (coins[abbreviation].h, coins[abbreviation].m)
            elif coins[abbreviation].h < 100:
                sname += "%6s  " % (abbreviation.upper())
                smedian += "%6d |" % (coins[abbreviation].median)
                stime += "%3d:%02d |" % (coins[abbreviation].h, coins[abbreviation].m)
            else:
                sname += "%7s  " % (abbreviation.upper())
                smedian += "%7d |" % (coins[abbreviation].median)
                stime += "%4d:%02d |" % (coins[abbreviation].h, coins[abbreviation].m)
            if coins[abbreviation].cnt > 0:
                median_all = ((median_all * cnt_all) + (coins[abbreviation].median*coins[abbreviation].cnt)) / (cnt_all+coins[abbreviation].cnt)
                cnt_all += coins[abbreviation].cnt

    #remove last chars
    sname = sname[:-2]
    smedian = smedian[:-2]
    stime = stime[:-2]

    smedian_all = '# Total Median:%5d' % (median_all)
    stime_all = '# Total Time:%4d:%02d' % (divmod(cnt_all*idletime, 60))

    #fill strings to screen width and add "#" to the end
    sname = "%s%s%s" % (sname, " "*(79-len(sname)), "#")
    smedian = "%s%s%s" % (smedian, " "*(79-len(smedian)), "#")
    stime = "%s%s%s" % (stime, " "*(79-len(stime)), "#")
    smedian_all = "%s%s%s" % (smedian_all, " "*(79-len(smedian_all)), "#")
    stime_all = "%s%s%s" % (stime_all, " "*(79-len(stime_all)), "#")

    #output status strings
    print "\n", "#"*80+sname+smedian+stime+smedian_all+stime_all+"#"*80

    #sleep
    print 'Going to sleep...'
    i=0
    while i<idletime*60:
        print "Seconds remaining:", (idletime*60-i),
        time.sleep(1)
        print '\r',
        i+=1
