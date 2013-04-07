CryptoSwitcher
==============

A script to switch between mining BTC and altcoins as profitability dictates.

Dependencies
---
* cgminer
* vanityminer
* BeautifulSoup4
* urllib2

Usage
---
Edit the scripts such as `bitcoin.sh` so that they start mining
the appropriate coins with your desired settings. Then poke around
in the header of `cryptoSwitcher.py` to set everything up, including
which coins you wish to try and mine or merged mine. Then just run

    python cryptoSwitcher.py

And you should start mining the most profitable coin. It 
checks every hour for a change in the situation. 

Thanks
---
Dustcoin and fizzisist, for doing most of the heavy-lifting of the data.

Tips
---
In hope, not expectation:

* Bitcoin: 1NhathL6LpcgofDnHELSS6Hej6kU9xrVgp
