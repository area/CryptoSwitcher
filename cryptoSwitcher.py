from bs4 import BeautifulSoup
import urllib2
import time
import subprocess

#LTC / BTC switcher
#You should have scripts that stop all other forms of mining, set 
#your clocks and environment variables appropriately, and start
#either LTC or BTC mining. I have these called 'litecoin.sh' 
#and 'bitcoin.sh', but edit and/or replace these as you see fit.

#TipJar:
#BTC: 1NhathL6LpcgofDnHELSS6Hej6kU9xrVgp
#LTC: LWytTu9JghWMo14bJXcN65Pmf9jafZezHu

#Set the threshold where we move from BTC to LTC
threshold = 105
#In an ideal world, this would be 100 i.e. when it's just as profitable
#to mine LTC as BTC, mine BTC. With a threshold of 105, BTC gets a little
#extra edge - when you take into account fees at BTC-e, the time spent
#selling LTC for BTC and the extra electricity used, BTC should get a little
#extra.


#-----------
#Hopefully nothing below this needs editing.
#-----------

url = 'http://dustcoin.com/mining'

btcMining = False
ltcMining = False
while True:
    #get data from the incredible dustcoin
    usock = urllib2.urlopen(url)
    data = usock.read()
    usock.close()
    soup = BeautifulSoup(data)

    coins = soup.findAll('tr',{ "class":"coin" })

    #This is assuming that row 1 is litecoin. Get relative profit of LTC vs BTC
    coinName, profit = coins[1].find('strong',text=True).text, coins[1].find('td',{"id":"profit1"}).text.replace('%','')
    print time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), coinName, profit

    if profit > threshold and ltcMining == False:
        ltcMining = True
        btcMining = False
        subprocess.Popen(['./litecoin.sh'])
    elif profit <=threshold and btcMining ==False:
        ltcMining = False
        btcMining = True
        subprocess.Popen(['./bitcoin.sh'])
    time.sleep(3600)
