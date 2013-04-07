#!/bin/bash
#Replace this script with one of your own.

#Send the quit command to any cgminer instances running
echo "{\"command\":\"quit\"}" | nc 127.0.0.1 4028
#Set clocks
export DISPLAY=:0
aticonfig --od-setclocks=850,1000 --adapter=1
aticonfig --od-setclocks=850,1000 --adapter=0
#Start litecoin mining with API access enabled for future instances of the above command
export GPU_USE_SYNC_OBJECTS=1
export GPU_MAX_ALLOC_PERCENT=100
screen -dm ./../cgminer/cgminer -c ~/.cgminer/litecoin.conf  --auto-fan --api-network --api-listen --api-allow W:127.0.0.1
