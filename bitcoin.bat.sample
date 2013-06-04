@echo off
::end old cgminer if running
tasklist /FI "IMAGENAME eq cgminer.exe" 2>NUL | find /I /N "cgminer.exe">NUL
if "%ERRORLEVEL%"=="0" taskkill /IM cgminer.exe /F
::start new cgminer
start cmd.exe /C "cgminer\cgminer.exe -o mint.bitminter.com:8332 -u USER -p PASSWORD -I 9 --gpu-reorder -k diablo --worksize 256 --lookup-gap 2 --auto-fan"