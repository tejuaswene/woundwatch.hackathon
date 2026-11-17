@echo off
title WoundWatch - allow network access
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  Please right-click allow_firewall.bat and choose "Run as administrator".
  echo.
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="WoundWatch LAN" >nul 2>&1
netsh advfirewall firewall add rule name="WoundWatch LAN" dir=in action=allow protocol=TCP localport=3000,3001,8000 profile=any
echo.
echo  Done. Ports 3000 (patient), 3001 (doctor) and 8000 (backend)
echo  are now reachable from other devices on your network.
echo.
echo  To remove this rule after the hackathon, run as administrator:
echo    netsh advfirewall firewall delete rule name="WoundWatch LAN"
echo.
pause
