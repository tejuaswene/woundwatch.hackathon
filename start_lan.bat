@echo off
title WoundWatch - LAN launcher
cd /d "%~dp0"
echo.
echo  =====================================================
echo    WoundWatch - starting on your local Wi-Fi network
echo  =====================================================
echo.

REM ---- Build the apps (first time, or when run as:  start_lan.bat rebuild) ----
if /i "%~1"=="rebuild" goto build
if not exist "doctor-app\build\index.html" goto build
if not exist "patient-app\build\index.html" goto build
goto run

:build
echo [1/2] Building doctor app ...
pushd doctor-app
call npm run build
popd
echo [2/2] Building patient app ...
pushd patient-app
call npm run build
popd

:run
REM ---- Start backend + both apps, listening on ALL network interfaces ----
start "WoundWatch Backend :8000" /D "%~dp0backend" cmd /k "(if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) & python -m uvicorn main:app --host 0.0.0.0 --port 8000"
start "WoundWatch Doctor :3001" /D "%~dp0doctor-app" cmd /k "npx --yes serve -s build -l 3001"
start "WoundWatch Patient :3000" /D "%~dp0patient-app" cmd /k "npx --yes serve -s build -l 3000"

REM ---- Find this PC's Wi-Fi / LAN IP (the adapter that has a gateway) ----
set LANIP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1).IPv4Address.IPAddress"`) do set LANIP=%%i
if "%LANIP%"=="" set LANIP=YOUR-PC-IP

timeout /t 4 >nul
echo.
echo  -----------------------------------------------------
echo   Open these on ANY phone / laptop on the same Wi-Fi:
echo.
echo     Patient app :  http://%LANIP%:3000
echo     Doctor site :  http://%LANIP%:3001
echo     Backend API :  http://%LANIP%:8000/docs
echo.
echo   On this PC you can also use http://localhost:3000 / :3001
echo  -----------------------------------------------------
echo   If other devices cannot connect, run allow_firewall.bat
echo   once (right-click ^> Run as administrator).
echo   To stop: close the 3 WoundWatch windows.
echo  -----------------------------------------------------
echo.
pause
