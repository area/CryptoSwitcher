#!/bin/bash
#This exit is deliberately included so that people don't just download
#and run this script and somehow ruin their mining setup with
#the clocks below, which are appropriate for my rig
#Remove it and adjust the script below, or replace this whole script
#with one of your own.
exit
#Send the quit command to any cgminer instances running
echo "{\"command\":\"quit\"}" | nc 127.0.0.1 4028
#Set clocks
export DISPLAY=:0
aticonfig --od-setclocks=850,1000 --adapter=1
aticonfig --od-setclocks=850,1000 --adapter=0
#Start litecoin mining with API access enabled for future instances of the above command
export GPU_USE_SYNC_OBJECTS=1
export GPU_MAX_ALLOC_PERCENT=100
screen -dm ./cgminer/cgminer -c ~/.cgminer/litecoin.conf  --auto-fan --api-network --api-listen --api-allow W:127.0.0.1
