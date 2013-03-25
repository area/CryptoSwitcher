CryptoSwitcher
==============

A script to switch between mining LTC and BTC as profitability dictates.

Dependencies
---
*cgminer
*BeautifulSoup4
*urllib2

Usage
---
Edit the `litecoin.sh` and `bitcoin.sh` scripts so that they start mining
Litecoin and Bitcoin with your desired settings. Then just run

    python cryptoSwitcher.py

And you should start mining the most profitable of LTC and BTC. It 
checks every hour for a change in the situation. If you wish to 
change the threshold, then it's clearly marked in `cryptoSwitcher.py`.

Tips
---
In hope, not expectation:

* Bitcoin: 1NhathL6LpcgofDnHELSS6Hej6kU9xrVgp
* Litcoin: LWytTu9JghWMo14bJXcN65Pmf9jafZezHu
