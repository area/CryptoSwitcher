#!/bin/bash
#Replace this script with one of your own.

#Send the quit command to any cgminer instances running
echo "{\"command\":\"quit\"}" | nc 127.0.0.1 4028
#Kill vanityminer - inelegant, but works
killall oclvanityminer
#Start Bitcoin mining with API access enabled for the above command in the future
export DISPLAY=:0
#Set clocks
aticonfig --od-setclocks=930,300 --adapter=1
aticonfig --od-setclocks=850,300 --adapter=0
screen -dm ./../cgminer/cgminer -c ~/.cgminer/bitcoin.conf  --auto-fan --api-network --api-listen --api-allow W:127.0.0.1

