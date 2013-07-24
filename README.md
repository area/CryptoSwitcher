CryptoSwitcher
==============

A script to switch between mining BTC and altcoins as profitability dictates,
using the powers of http://dustcoin.com.

Dependencies
---
* NumPy
* BeautifulSoup4
* urllib2
* simplejson
* PycURL
* btce-api (included)
* pyvircurex (included)
* PyCryptsy (included)
* cgminer (optional)
* vanityminer (optional)

Usage
---
Edit the scripts such as `bitcoin.sh` so that they start mining the appropriate
coins with your desired settings. I recommend the scripts start the appropriate
miner inside a `screen` session, which the two example scripts I've included
will do. Then poke around in `cryptoSwitcher.config.sample to set everything
up, including which coins you wish to try and mine or merged mine. Then run
    
    git submodule init
    git submodule update

to download the BTC-e, Vircurex, and Cryptsy python APIs. Then rename 
`cryptoSwitcher.config.sample` to `cryptoSwitcher.config` and run
 
    python cryptoSwitcher.py

The script should work out what the best mining option is, and run the
appropriate script. It checks every hour for a change in the situation, and if
the options is enabled it will also sell any coins that have been
auto-withdrawn to BTC-E.  I bear no responsibility for any losses you incur by
using this script to sell your cryptocoins. If you wish to use these options,
set the auto-withdrawal limits at your pools as low as they will go to limit
your exposure to a changing exchange rate. You will also need to add your BTC-E
API key and secret to the file `key.sample` and rename it to `key`.

Thanks
---
Dustcoin and fizzisist, for doing most of the heavy-lifting of the data,
and Alan McIntyre for making the BTC-API used here. sal002 also deserves
thanks for http://www.coinchoose.com.

Tips
---
In hope, not expectation:

* Bitcoin: `1NhathL6LpcgofDnHELSS6Hej6kU9xrVgp`

This couldn't have been made without the work of others; if you feel like
tipping the other people whose work is used here:

* Dustcoin: `1F6fV4U2xnpAuKtmQD6BWpK3EuRosKzF8U` at time of writing, see http://dustcoin.com/donate for latest
* Fizzisist: `122LV3CNADj1yHU2tFPEhcCWR5QbfMzNcm` at time of writing, see http://www.fizzisist.com for latest
* Alan McIntyre : `16vnh6gwFYLGneBa8JUk7NaXpEt3Qojqs1` at time of writing, see https://github.com/alanmcintyre/btce-api
* sal002: Sign up for Vircurex through the referral link on http://www.coinchoose.com
* Scott Alfter: `1TipsGocnz2N5qgAm9f7JLrsMqkb3oXe2` for PyCryptsy
