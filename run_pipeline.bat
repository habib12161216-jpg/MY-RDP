@echo off
title Autonomous In-RDP Worker Pipeline
color 0a
cls
echo ========================================================
echo   AUTONOMOUS WORKER PIPELINE INITIATED (C:\Automation)
echo ========================================================
cd /d C:\Automation

rem 1. Guarantee single clean copy of bot.py and proxies.txt on user desktop
if not exist "%USERPROFILE%\Desktop" mkdir "%USERPROFILE%\Desktop" >nul 2>&1
copy /y "C:\Automation\bot.py" "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y "C:\Automation\proxies.txt" "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\bot.py" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\proxies.txt" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\gemini.txt" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\burst_traffic_bot.py" >nul 2>&1

rem 2. Resolve Python Path
set "PY_EXE=python"
python --version >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Python310\python.exe" (
        set "PY_EXE=C:\Program Files\Python310\python.exe"
    ) else if exist "C:\hostedtoolcache\windows\Python\3.10.11\x64\python.exe" (
        set "PY_EXE=C:\hostedtoolcache\windows\Python\3.10.11\x64\python.exe"
    )
)
echo [*] Python executable: %PY_EXE%

rem 3. Verify Python packages
%PY_EXE% -c "import requests, playwright, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing missing Python packages...
    %PY_EXE% -m pip install requests playwright opencv-python numpy pynacl pywin32 uiautomation
    %PY_EXE% -m playwright install chromium
)

rem 4. Resolve and Launch AdsPower Desktop
echo [*] Locating AdsPower Desktop...
set "ADS_EXE="
if exist "C:\Program Files\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files\AdsPower Global\AdsPower Global.exe"
if not defined ADS_EXE if exist "C:\Program Files (x86)\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files (x86)\AdsPower Global\AdsPower Global.exe"
if not defined ADS_EXE if exist "C:\Users\runneradmin\AppData\Local\Programs\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Users\runneradmin\AppData\Local\Programs\AdsPower Global\AdsPower Global.exe"

if not defined ADS_EXE (
    echo [!] AdsPower not found in standard paths. Installing now...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://version.adspower.net/software/win64-global/8.7.23/AdsPower-Global-8.7.23-x64.exe' -OutFile '%TEMP%\ads_setup.exe'; Start-Process '%TEMP%\ads_setup.exe' -ArgumentList '/S','/allusers' -Wait; Remove-Item '%TEMP%\ads_setup.exe' -Force"
    if exist "C:\Program Files\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files\AdsPower Global\AdsPower Global.exe"
)

tasklist /fi "imagename eq AdsPower*" 2>nul | find /i "AdsPower" >nul
if errorlevel 1 (
    if defined ADS_EXE (
        echo [*] Launching AdsPower Desktop: "%ADS_EXE%"
        start "" "%ADS_EXE%" --remote-debugging-port=9222 --disable-features=WebRtcHideLocalIpsWithMdns --disable-component-update --no-default-browser-check
        timeout /t 8 /nobreak >nul
    ) else (
        echo [!] AdsPower executable could not be resolved.
    )
) else (
    echo [*] AdsPower Desktop is already running.
)

rem 5. Automated Mirrored AdsPower GUI Login & Key Injection
echo ========================================================
echo [*] Phase 4: Executing Mirrored AdsPower Login Engine...
echo ========================================================
if exist adspower_login_engine.py (
    %PY_EXE% adspower_login_engine.py
) else if exist adspower_cdp_login.py (
    %PY_EXE% adspower_cdp_login.py
) else if exist drop.py (
    %PY_EXE% drop.py
)

rem Verify authentication before bot launch
echo [*] Verifying AdsPower Local API authentication...
%PY_EXE% -c "import requests, sys; r = requests.get('http://local.adspower.net:50325/api/v1/user/list?page_size=1', timeout=3); sys.exit(0 if r.status_code == 200 and r.json().get('code') == 0 else 1)" >nul 2>&1
if errorlevel 1 (
    echo [!] Warning: Initial API check not ready. Retrying login engine...
    timeout /t 5 /nobreak >nul
    if exist adspower_login_engine.py %PY_EXE% adspower_login_engine.py
)

rem Re-sync patched bot.py to Desktop
copy /y C:\Automation\bot.py "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y C:\Automation\proxies.txt "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
if exist "C:\Users\RDP\Desktop" (
    copy /y C:\Automation\bot.py "C:\Users\RDP\Desktop\bot.py" >nul 2>&1
    copy /y C:\Automation\proxies.txt "C:\Users\RDP\Desktop\proxies.txt" >nul 2>&1
)

rem 6. Launch Main Traffic Bot
echo ========================================================
echo [*] Phase 5: Launching Main Traffic Bot (bot.py)...
echo ========================================================
cd /d "%USERPROFILE%\Desktop"
if exist bot.py (
    %PY_EXE% bot.py
) else if exist "C:\Automation\bot.py" (
    cd /d C:\Automation
    %PY_EXE% bot.py
) else (
    echo [!] Error: bot.py not found!
)

echo.
echo ========================================================
echo   PIPELINE SESSION COMPLETED. WINDOW WILL STAY OPEN.
echo ========================================================
pause
