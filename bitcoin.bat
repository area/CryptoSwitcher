@echo off
::start new cgminer
taskkill /IM cgminer.exe /F
::start new cgminer
start cmd.exe /C "cgminer\cgminer.exe -o mint.bitminter.com:8332 -u l05443.rws -p rs1372 -I 9 --gpu-reorder -k diablo --worksize 256 --lookup-gap 2 --auto-fan --api-network --api-listen --api-allow W:127.0.0.1"