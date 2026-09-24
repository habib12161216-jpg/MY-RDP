@echo off
title AdsPower SunBrowser Traffic Pipeline
color 0a
cls
echo ================================================================
echo   ADSPOWER SUNBROWSER PIPELINE (In-RDP Full Automation)
echo ================================================================
cd /d C:\Automation

rem 1. Copy files to user Desktop
if not exist "%USERPROFILE%\Desktop" mkdir "%USERPROFILE%\Desktop" >nul 2>&1
copy /y "C:\Automation\bot.py" "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y "C:\Automation\proxies.txt" "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
copy /y "C:\Automation\adspower_accounts_combos.txt" "%USERPROFILE%\Desktop\adspower_accounts_combos.txt" >nul 2>&1
copy /y "C:\Automation\adspower_login_engine.py" "%USERPROFILE%\Desktop\adspower_login_engine.py" >nul 2>&1

rem Copy config next to bot.py
if not exist "%USERPROFILE%\Desktop\master_orchestrator" mkdir "%USERPROFILE%\Desktop\master_orchestrator" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\master_orchestrator\orchestrator_config.json" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\orchestrator_config.json" >nul 2>&1

rem Clean stale Public Desktop files
del /f /q "C:\Users\Public\Desktop\gemini.txt" >nul 2>&1

rem 2. Resolve Python Path
set "PY_EXE=python"
python --version >nul 2>&1
if errorlevel 1 (
    for /d %%D in (C:\hostedtoolcache\windows\Python\3.*\x64) do (
        if exist "%%D\python.exe" set "PY_EXE=%%D\python.exe"
    )
    if not exist "%PY_EXE%" (
        if exist "C:\Program Files\Python310\python.exe" set "PY_EXE=C:\Program Files\Python310\python.exe"
    )
)
echo [*] Python: %PY_EXE%

rem 3. Install required dependencies
echo [*] Checking dependencies (requests, playwright, opencv, numpy)...
%PY_EXE% -m pip install --quiet --upgrade pip
%PY_EXE% -m pip install --quiet requests playwright opencv-python numpy pynacl pywin32 uiautomation
%PY_EXE% -m playwright install chromium >nul 2>&1

rem 4. Locate and Launch AdsPower Global Desktop
echo [*] Locating AdsPower Global Desktop...
set "ADS_EXE="
if exist "C:\Program Files\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files\AdsPower Global\AdsPower Global.exe"
if not defined ADS_EXE if exist "C:\Program Files (x86)\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files (x86)\AdsPower Global\AdsPower Global.exe"
if not defined ADS_EXE if exist "%LOCALAPPDATA%\Programs\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=%LOCALAPPDATA%\Programs\AdsPower Global\AdsPower Global.exe"
if not defined ADS_EXE if exist "C:\Users\runneradmin\AppData\Local\Programs\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Users\runneradmin\AppData\Local\Programs\AdsPower Global\AdsPower Global.exe"

if not defined ADS_EXE (
    echo [!] AdsPower not found. Downloading official installer...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://version.adspower.net/software/win64-global/8.7.23/AdsPower-Global-8.7.23-x64.exe' -OutFile '%TEMP%\ads_setup.exe'; Start-Process '%TEMP%\ads_setup.exe' -ArgumentList '/S','/allusers' -Wait; Remove-Item '%TEMP%\ads_setup.exe' -Force"
    if exist "C:\Program Files\AdsPower Global\AdsPower Global.exe" set "ADS_EXE=C:\Program Files\AdsPower Global\AdsPower Global.exe"
)

tasklist /fi "imagename eq AdsPower*" 2>nul | find /i "AdsPower" >nul
if errorlevel 1 (
    if defined ADS_EXE (
        echo [*] Launching AdsPower Desktop: "%ADS_EXE%"
        start "" "%ADS_EXE%" --remote-debugging-port=9222
        timeout /t 6 /nobreak >nul
    ) else (
        echo [!] Warning: AdsPower executable could not be resolved automatically.
    )
) else (
    echo [*] AdsPower Desktop is already running.
)

rem 5. Auto-Login AdsPower via CDP
if exist "%USERPROFILE%\Desktop\adspower_login_engine.py" (
    echo [*] Logging into AdsPower & Ingesting API Key...
    cd /d "%USERPROFILE%\Desktop"
    %PY_EXE% adspower_login_engine.py
) else if exist "C:\Automation\adspower_login_engine.py" (
    echo [*] Logging into AdsPower & Ingesting API Key...
    cd /d C:\Automation
    %PY_EXE% adspower_login_engine.py
)

rem 6. Re-sync patched bot.py to Desktop
copy /y "C:\Automation\bot.py" "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y "C:\Automation\proxies.txt" "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\master_orchestrator\orchestrator_config.json" >nul 2>&1

rem 7. Launch Main Traffic Bot
echo ================================================================
echo [*] Launching AdsPower SunBrowser Traffic Bot (bot.py)...
echo ================================================================
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
echo ================================================================
echo   PIPELINE SESSION COMPLETED. WINDOW WILL STAY OPEN.
echo ================================================================
pause
