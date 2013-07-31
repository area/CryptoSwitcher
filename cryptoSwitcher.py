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

# -----------
# Hopefully nothing below this needs editing.
# -----------

class Coin:
    def __init__(self, name):
        self.ratio=0 # assume totally unprofitable unless otherwise shown to be the case.
        self.willingToMine = False
        self.miningNow = False
        self.merged = False
        self.willingToSell = False
        self.command = '' # the command that is run when we want to mine this coin.
        self.name = name
        self.cnt = 0
        self.median = 0
        self.m = 0
        self.h = 0
        self.fee = 0
        self.source = '--'
        self.price = 0.0
        self.diff = 9999999999.9 # start off with ridiculously high diff so we dont mine the wrong coin
        self.reward = 0
        self.algo = ""

coins = {}
coins['amc'] =  Coin('AmericanCoin')
coins['anc'] =  Coin('Anoncoin')
coins['arg'] =  Coin('Argentum')
coins['bqc'] =  Coin('BBQCoin')
coins['btb'] =  Coin('Bitbar')
coins['btc'] =  Coin('Bitcoin')
coins['bte'] =  Coin('Bytecoin')
coins['cap'] =  Coin('Bottlecap')
coins['cgb'] =  Coin('CryptogenicBullion')
coins['cnc'] =  Coin('CHNCoin')
coins['dbl'] =  Coin('Doubloons')
coins['dgc'] =  Coin('DigitalCoin')
coins['emd'] =  Coin('Emerald')
coins['elc'] =  Coin('Elacoin')
coins['ezc'] =  Coin('EZCoin')
coins['frc'] =  Coin('Freicoin')
coins['frk'] =  Coin('Franko')
coins['fst'] =  Coin('Fastcoin')
coins['ftc'] =  Coin('Feathercoin')
coins['gld'] =  Coin('GLDCoin')
coins['hyc'] =  Coin('Hypercoin')
coins['kgc'] =  Coin('Krugercoin')
coins['jkc'] =  Coin('Junkcoin')
coins['lky'] =  Coin('Luckycoin')
coins['ltc'] =  Coin('Litecoin')
coins['mec'] =  Coin('Megacoin')
coins['mem'] =  Coin('Memecoin')
coins['mnc'] =  Coin('Mincoin')
coins['nbl'] =  Coin('Nibble')
coins['nvc'] =  Coin('NovaCoin')
coins['ppc'] =  Coin('PPCoin')
coins['pwc'] =  Coin('Powercoin')
coins['pxc'] =  Coin('Phenixcoin')
coins['ryc'] =  Coin('RoyalCoin')
coins['trc'] =  Coin('TerraCoin')
coins['wdc'] =  Coin('Worldcoin')
coins['yac'] =  Coin('YaCoin')
# Merged
coins['dvc'] =  Coin('Devcoin')
coins['dvc'].merged = True
coins['ixc'] =  Coin('IXCoin')
coins['ixc'].merged = True
coins['nmc'] =  Coin('NameCoin')
coins['nmc'].merged = True
# Kind of an alternate coin...
coins['vanity'] = Coin('Vanity Mining')

# Read in config file
Config = ConfigParser.ConfigParser()
Config.read('./cryptoSwitcher.config')

# Enable the coins you want to mine here.
for key in coins:
    try:
        coins[key].willingToMine = Config.getboolean('MineCoins','mine'+key)
    except:
        continue

# You should have scripts that stop all other forms of mining, set
# your clocks and environment variables appropriately, and start
# mining the appropriate coin. I have these called 'litecoin.sh',
# 'bitcoin.sh' etc., but edit and/or replace these as you see fit.

# Any coins you aren't mining you can just leave blank.
for key in coins:
    try:
        coins[key].command = Config.get('Scripts',key+'script')
    except:
        continue

# read source list
try:
    source = [x.strip() for x in Config.get('Data-Source','source').split(',')]
except:
    try:
        source = [x.strip() for x in Config.get('Misc','source').split(',')]
        print "warning: you are using an old config file structure. please update using the config sample file."
    except:
        sys.exit("ERROR: Cannot read source from config file.")



# read source list
try:
    source_cryptoswitcher = [x.strip() for x in Config.get('Data-Source','source_cryptoswitcher').split(',')]
except:
    source_cryptoswitcher = ''
    print "warning: couldnt read source_cryptoswitcher from config file. Leaving blank."

# read hashrates
try:
    hashrate_sha256 = int(Config.get('Data-Source','hashrate_sha256'))
    hashrate_scrypt = int(Config.get('Data-Source','hashrate_scrypt'))
except:
    hashrate_sha256 = 1000
    hashrate_scrypt = 1
    print "warning: couldnt read hashrates from config file. Setting to 1:1000."

# get idle time between two profitability check cycles
try:
    idletime = int(Config.get('Misc','idletime'))
except:
    idletime = 5
    print "warning: couldnt read idletime from config file. Setting to 5 min."

# get the coinfees
for key in coins:
    try:
        coins[key].fee = float(Config.get('Fees','fee'+key))
    except:
        continue


# And now some information to calculate Vanity Address mining profitability
try:
    gkeypersec = float(Config.get('Misc','gkeypersec')) #Gigakeys per second you can test
    ghashpersec = float(Config.get('Misc','ghashpersec')) #Gigahash per second you can output doing normal BTC mining.
except:
    print "warning: couldnt read gkeypersec and ghashpersec from config file."

# If you want to sell your coins on BTCE ASAP, then there's a bit more setup for you
try:
    enableBTCE = Config.getboolean('Sell','enableBTCE')
    enableVircurex = Config.getboolean('Sell','enableVircurex')
    enableCryptsy = Config.getboolean("Sell", "enableCryptsy")
    vircurexSecret = Config.get('Sell','vircurexSecret')
    vircurexUsername = Config.get('Sell','vircurexUsername')
    cryptsyPubkey = Config.get("Sell", "cryptsyPublicKey")
    cryptsyPrivkey = Config.get("Sell", "cryptsyPrivateKey")
except:
    enableBTCE = False
    enableVircurex = False
    enableCryptsy = False
    print "warning: couldnt read sell information from config file. Disabling auto sell."

# And flag which coins you want to sell as they come in. These coins will only
# sell for BTC, not for USD or any other cryptocoin.
for key in coins:
    try:
        coins[key].willingToSell = Config.getboolean('Sell','sell'+key)
    except:
        continue

#Trade multiplier. i.e. Don't sell for the highest current bid if this is
#larger than 1, but make a new ask at highest_bid * tradeMultiplier.

tradeMultiplier = 1
try: 
    tradeMultiplier = float(Config.get('Misc','tradeMultiplier'))
except:
    pass

tradeMultiplierCheck = False
try:
    tradeMultiplierCheck = Config.getboolean ('Misc', 'tradeMultiplierCheck')
except:
    pass

def sellCoinBTCE(coin, tradeapi):
    r = tradeapi.getInfo()
    try:
        balance = getattr(r, 'balance_'+coin)
    except:
        # probably a coin that BTCE doesn't have an exchange for, so just return
        return
    if balance > 0.1:
        # i.e. if we're selling and we have some to sell that's larger than the minimum order...
        asks, bids = btceapi.getDepth(coin + '_btc')
        price = bids[0][0]*tradeMultiplier
        if price > asks[0][0] and tradeMultiplierCheck == True:
            price = asks[0][0] - 0.00000001
        tr = tradeapi.trade(coin + '_btc', 'sell', price, balance)
        # If tradeMultiplier is 1, then this sells at the highest price someone
        # currently has a bid lodged for.  It's possible that this won't
        # totally deplete our reserves, but any unsold immediately will be left
        # on the book, and will probably sell shortly.
        # A higher trade multiplier than 1 will not sell right away, but will
        # leave an order on the book.

def sellCoinVircurex(coin):
    pair = vircurexapi.Pair(coin+'_btc')
    try:
        bid = pair.highest_bid
        ask = pair.lowest_ask
    except:
        # probably a coin that Vircurex doesn't have an exchange for, so just return
        return
    account = vircurexapi.Account(vircurexUsername, vircurexSecret)
    balance = account.balance(coin.upper())
    if balance >= 0.1:
        price = bid * tradeMultiplier
        if price > ask and tradeMultiplierCheck == True:
            price = ask - 0.00000001
        order = account.sell(coin.upper(),balance, 'BTC', price)
        account.release_order(order['orderid'])

def sellCoinCryptsy(coin):
    acct = PyCryptsy(cryptsyPubkey, cryptsyPrivkey)
    bal = acct.GetAvailableBalance(coin)
    price = acct.GetBuyPrice(coin, "BTC")*tradeMultiplier
    sell = acct.GetSellPrice(coin, "BTC")
    if price > sell and tradeMultiplierCheck == True:
        price = sell - 0.00000001
    if price > 0:
        acct.CreateSellOrder(coin, "BTC", bal, price)
    return

if enableBTCE:
    key_file = './key'
    handler = btceapi.KeyHandler(key_file)
    key = handler.keys.keys()[0]
    secret, nonce =  handler.keys[handler.keys.keys()[0]]
    authedAPI = btceapi.TradeAPI(key, secret, nonce)


# create http handler
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'CryptoSwitcher')]

# disable extended status output (=> coin price and difficulty) by default. only
# enable it, if at least one coins profitability is calculated by cryptoswitcher
extout = False

# main loop
cnt_all = 0
while True:
    # print header
    print "\n\n\n<<< Round %d >>>" % (cnt_all+1)
    print "time:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # get data from sources
    prestr = "getting data... "

    for x in source:
        # coinchoose
        if x=='coinchoose' or x=='cryptoswitcher':
            try:
                fullstr = prestr + "coinchoose"
                print fullstr + (79-len(fullstr))*" " + "\r",
                req = urllib2.Request("http://www.coinchoose.com/api.php")
                opener_cc = urllib2.build_opener()
                opener_cc.addheaders = [('User-agent', 'CryptoSwitcher')]
                f = opener_cc.open(req, timeout = 5)
                data_cc = simplejson.load(f)
            except:
                pass

        # dustcoin
        elif x=='dustcoin':
            try:
                fullstr = prestr + "dustcoin"
                print fullstr + (79-len(fullstr))*" " + "\r",
                usock = urllib2.urlopen('http://dustcoin.com/mining', timeout = 5)
                data = usock.read()
                usock.close()
                soup = BeautifulSoup(data)
                table_dustcoin = soup.findAll('tr',{ "class":"coin" })
            except:
                pass

        # coinotron
        elif x=='coinotron':
            try:
                fullstr = prestr + "coinotron"
                print fullstr + (79-len(fullstr))*" " + "\r",
                usock = urllib2.urlopen('https://coinotron.com/coinotron/AccountServlet?action=home', timeout = 5)
                data = usock.read()
                usock.close()
                soup = BeautifulSoup(data)
                table_coinotron = soup.findAll('tr')
            except:
                pass


    for x in source_cryptoswitcher:
        # cryptsy
        if x=='cryptsy':
            try:
                fullstr = prestr + "cryptsy"
                print fullstr + (79-len(fullstr))*" " + "\r",
                req = urllib2.Request("http://pubapi.cryptsy.com/api.php?method=orderdata")
                opener_cyp = urllib2.build_opener()
                opener_cyp.addheaders = [('User-agent', 'CryptoSwitcher')]
                f = opener_cyp.open(req, timeout = 5)
                data_cyp = simplejson.load(f)
            except:
                pass



    # assign data to coins
    # loop through coins
    for abbreviation, c in coins.items():
        # only get profitability for coins which we are interested in.
        # this saves network traffic and running time
        if c.willingToMine==False:
            continue

        success = 0
        # loop trough source list. try first entry first.
        for x in source:
            if x=='coinchoose':
                try:
                    for item in data_cc:
                        if item['symbol'].lower()==abbreviation:
                            coins[item['symbol'].lower()].ratio = float(item['adjustedratio'])
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
                        # make sure the profit we read is floating value, if not, continue loop and keep old profit value until next check
                        try:
                            profit = float(profit)
                        except:
                            continue
                        # calculate profitabilty
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
                        # when all coins where read, leave loop
                        if i == 5: break
                        i+=1
                        # convert profitability to percent
                        profit = float(profit)*100
                        # calculate profitabilty
                        if coinName.lower()==abbreviation:
                            coins[abbreviation].ratio = float(profit)
                            coins[abbreviation].source = 'ct'
                            success = 1
                            break
                        i+=1
                except:
                    continue

            # lets calulate profitability ourself
            elif x=='cryptoswitcher':
                # get difficulty and block rewards
                # source for difficulty data depends on coin
                try:
                    # if this is the first time we come here, update btc as well.
                    # otherwise we are unable to calculate the profitabilty.
                    fullstr = prestr + "difficulty of " + coins[abbreviation].name
                    print fullstr + (79-len(fullstr))*" " + "\r",
                    if coins['btc'].reward == 0:
                        for item in data_cc:
                            if item['symbol'].lower()=='btc':
                                coins['btc'].diff = float(item['difficulty'])
                                coins['btc'].reward = float(item['reward'])
                                break

                    # get difficulty values from coinchoose by default
                    for item in data_cc:
                        if item['symbol'].lower()==abbreviation:
                            coins[item['symbol'].lower()].diff = float(item['difficulty'])
                            coins[item['symbol'].lower()].reward = float(item['reward'])
                            coins[item['symbol'].lower()].algo = item['algo']
                            break

                    # if we dont have a difficulty source for our coin, continue loop and get profitabilty from
                    # other sources
                    if item['symbol'].lower()!=abbreviation:
                        continue

                    # for trc: use a different source for difficulty
                    if abbreviation == 'trc':
                        req = urllib2.Request("http://cryptocoinexplorer.com:3750/chain/Terracoin/q/getdifficulty")
                        f = opener.open(req, timeout = 5)
                        coins['trc'].diff = simplejson.load(f)

                    # for btc: we dont need to calculate
                    if abbreviation=='btc':
                        coins['btc'].ratio=100.0
                        coins['btc'].source = '--'
                        coins['btc'].algo = "SHA-256"
                        coins['btc'].price = 1.0
                        success = 1
                        break

                except:
                    continue


                # calculate highest buy value
                # use only data sources defined in source_cryptoswitcher
                coins[abbreviation].price = 0.0
                for y in source_cryptoswitcher:

                    # if coin profitability couldnt be processed manually in the
                    # last round, then they are probably not traded on the chosen
                    # markets. so the coin is removed from manual processing.
                    if coins[abbreviation].source != '--' and coins[abbreviation].source != 'cs':
                        continue

                    # btc-e
                    if y=='btce':
                        try:
                            fullstr = prestr + "price of " + coins[abbreviation].name + " at BTC-E"
                            print fullstr + (79-len(fullstr))*" " + "\r",
                            req = urllib2.Request("https://btc-e.com/api/2/" + abbreviation + "_btc/ticker")
                            f = opener.open(req, timeout = 5)
                            output = simplejson.load(f)
                            if coins[abbreviation].price < float(output['ticker']['sell']):
                                coins[abbreviation].price = float(output['ticker']['sell'])
                        except:
                            continue

                    # bter
                    elif y=='bter':
                        try:
                            fullstr = prestr + "price of " + coins[abbreviation].name + " at Bter"
                            print fullstr + (79-len(fullstr))*" " + "\r",
                            req = urllib2.Request("https://bter.com/api/1/ticker/" + abbreviation + "_btc")
                            f = opener.open(req, timeout = 5)
                            output = simplejson.load(f)
                            if coins[abbreviation].price < float(output['buy']):
                                coins[abbreviation].price = float(output['buy'])
                        except:
                            continue

                    # vircurex
                    elif y=='vircurex':
                        try:
                            fullstr = prestr + "price of " + coins[abbreviation].name + " at Vircurex"
                            print fullstr + (79-len(fullstr))*" " + "\r",
                            req = urllib2.Request("https://vircurex.com/api/get_highest_bid.json?base=" + abbreviation + "&alt=btc")
                            f = opener.open(req, timeout = 5)
                            output = simplejson.load(f)
                            if coins[abbreviation].price < float(output['value']):
                                coins[abbreviation].price = float(output['value'])
                        except:
                            continue

                    # cryptsy
                    elif y=='cryptsy':
                        try:
                            fullstr = prestr + "price of " + coins[abbreviation].name + " at Cryptsy"
                            print fullstr + (79-len(fullstr))*" " + "\r",
                            for item in data_cyp['return']:
                                if item.lower()==abbreviation:
                                    if data_cyp['return'][item]['secondarycode']=='BTC':
                                        if coins[abbreviation].price < float(data_cyp['return'][item]['buyorders'][0]['price']):
                                            coins[abbreviation].price = float(data_cyp['return'][item]['buyorders'][0]['price'])
                                    success = 1
                                    break
                        except:
                            continue

                # calculate profitability
                if coins[abbreviation].price!=0.0:
                    try:
                        if coins[abbreviation].algo == 'scrypt':
                            coins[abbreviation].ratio = (coins[abbreviation].reward/coins[abbreviation].diff)/(coins['btc'].reward/coins['btc'].diff)*coins[abbreviation].price*100/(hashrate_sha256/hashrate_scrypt)
                        else:
                            coins[abbreviation].ratio = (coins[abbreviation].reward/coins[abbreviation].diff)/(coins['btc'].reward/coins['btc'].diff)*coins[abbreviation].price*100
                        coins[abbreviation].source = 'cs'
                        success = 1

                        # at least one coins profitability was calculated by cryptoswitcher
                        # => enable extended status output
                        extout = True
                        break
                    except:
                        continue

            if success==1:
                break


    # Now work out how profitable btc mining really is, if we're doing any merged mining
    if coins['nmc'].willingToMine:
        coins['btc'].ratio +=coins['nmc'].ratio
    if coins['dvc'].willingToMine:
        coins['btc'].ratio +=coins['dvc'].ratio
    if coins['ixc'].willingToMine:
        coins['btc'].ratio +=coins['ixc'].ratio

    fullstr = prestr + "done"
    print fullstr + (79-len(fullstr))*" " + "\r"


    # Now get data for vanity mining
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
            # Now put vanity mining in terms of BTC mining.
            vanitybtcsec = gkeypersec * btcpergkey
            miningbtcsec = ghashpersec * btcperghash
            vanityprof = vanitybtcsec / miningbtcsec * 100
            coins['vanity'].ratio = vanityprof
            # print 'Vanity Mining', vanityprof

    # Now find the best profit coin
    bestcoin = 'btc'
    bestprof = 0
    print "comparing profitabilty..."
    print "-"*36
    for abbreviation, c in coins.items():
        if c.willingToMine:
            print "%11s: %3d  (fee: %2d, src: %s)" % (coins[abbreviation].name, c.ratio, coins[abbreviation].fee, coins[abbreviation].source),
            if extout == True:
                if coins[abbreviation].source == "cs" or abbreviation == "btc":
                    print "(pr: %.5f, di[%s]: %.2f)" % (coins[abbreviation].price, coins[abbreviation].algo, coins[abbreviation].diff),
                else:
                    # if diff is valid print it
                    if coins[abbreviation].reward != 0:
                        print "(pr:  -NA-  , di[%s]: %.2f)" % (coins[abbreviation].algo, coins[abbreviation].diff),
                    else:
                        print "(pr:  -NA-  , di[%s]:  -NA-  )" % (coins[abbreviation].algo),
            print ""

        if c.ratio-coins[abbreviation].fee > bestprof and c.willingToMine:
            bestcoin = abbreviation
            bestprof=c.ratio-coins[abbreviation].fee
    print "-"*36
    print "=> Best: %d, mining %s" % (bestprof, coins[bestcoin].name)
    coins[bestcoin].median = ((coins[bestcoin].median * coins[bestcoin].cnt) + coins[bestcoin].ratio-coins[bestcoin].fee) / (coins[bestcoin].cnt+1)
    coins[bestcoin].cnt = coins[bestcoin].cnt+1


    if coins[bestcoin].miningNow == False:
        # i.e. if we're not already mining the best coin
        print '=> Switching to %s (running %s)' % (coins[bestcoin].name, coins[bestcoin].command)
        for abbreviation, c in coins.items():
            c.miningNow = False
        coins[bestcoin].miningNow = True
        subprocess.Popen(coins[bestcoin].command)

    # Sell some coins if that's what we're into
    for abbreviation, c in coins.items():
        if c.willingToSell and (c.miningNow or c.merged) and enableBTCE:
            # i.e. if we're willing to sell it AND it's still worth more than BTC -
            # with pool payout delays and wild exchange swings, while it might be
            # profitable to have mined it, we didn't sell it quickly enough. This
            # keeps hold of the coin until you've made a decision.
            sellCoinBTCE(abbreviation, authedAPI)
        # elif c.willingToSell and c.miningNow and enableVircurex:
        if c.willingToSell and enableVircurex and (c.miningNow or c.merged):
            sellCoinVircurex(abbreviation)
        if c.willingToSell and enableCryptsy and (c.miningNow or c.merged):
            sellCoinCryptsy(abbreviation)

    # ...and now save the keyfile in case the script is aborted.
    if enableBTCE:
        handler.setNextNonce(key,time.time()) #Thanks, jsorchik
        handler.save(key_file)

    # create status output strings
    sname = "#        "
    smedian = "# Median:"
    stime = "# Time:  "
    median_all = 0
    cnt_all = 0
    for abbreviation, c in coins.items():
        if c.willingToMine and (not c.merged):
            coins[abbreviation].h, coins[abbreviation].m = divmod(coins[abbreviation].cnt*idletime, 60)
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

    # remove last chars
    sname = sname[:-2]
    smedian = smedian[:-2]
    stime = stime[:-2]

    smedian_all = '# Total Median:%5d' % (median_all)
    stime_all = '# Total Time:%4d:%02d' % (divmod(cnt_all*idletime, 60))

#    # fill strings to screen width and add "#" to the end
#    sname = "%s%s%s" % (sname, " "*(79-len(sname)), "#")
#    smedian = "%s%s%s" % (smedian, " "*(79-len(smedian)), "#")
#    stime = "%s%s%s" % (stime, " "*(79-len(stime)), "#")
#    smedian_all = "%s%s%s" % (smedian_all, " "*(79-len(smedian_all)), "#")
#    stime_all = "%s%s%s" % (stime_all, " "*(79-len(stime_all)), "#")

    # output status strings
#    print "\n", "#"*80+sname+smedian+stime+smedian_all+stime_all+"#"*80
    print "\n", sname
    print smedian
    print stime
    print smedian_all
    print stime_all, "\n"

    # sleep
    print 'Going to sleep...'
    i=0
    while i<idletime*60:
        print "Seconds remaining:", (idletime*60-i), " ", "\r",
        time.sleep(1)
        i+=1
