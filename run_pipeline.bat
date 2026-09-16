@echo off
title Stealth Bot Pipeline — Zero AdsPower
color 0a
cls
echo ================================================================
echo   STEALTH BOT PIPELINE (No AdsPower Required)
echo ================================================================
cd /d C:\Automation

rem 1. Copy bot.py and proxies.txt to user Desktop
if not exist "%USERPROFILE%\Desktop" mkdir "%USERPROFILE%\Desktop" >nul 2>&1
copy /y "C:\Automation\bot.py" "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y "C:\Automation\proxies.txt" "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\orchestrator_config.json" >nul 2>&1

rem Also copy config next to bot.py so load_config() finds it
if not exist "%USERPROFILE%\Desktop\master_orchestrator" mkdir "%USERPROFILE%\Desktop\master_orchestrator" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\master_orchestrator\orchestrator_config.json" >nul 2>&1

rem Clean stale Public Desktop files
del /f /q "C:\Users\Public\Desktop\bot.py" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\proxies.txt" >nul 2>&1
del /f /q "C:\Users\Public\Desktop\gemini.txt" >nul 2>&1

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
echo [*] Python: %PY_EXE%

rem 3. Install stealth engine dependencies
echo [*] Installing stealth engine (camoufox, playwright)...
%PY_EXE% -m pip install --quiet --upgrade pip
%PY_EXE% -m pip install --quiet requests playwright pynacl

rem 4. Download Camoufox Firefox binary (only if not already cached)
echo [*] Fetching Camoufox Firefox binary (if needed)...
%PY_EXE% -c "import camoufox" >nul 2>&1
if errorlevel 1 (
    %PY_EXE% -m pip install --quiet camoufox
)
%PY_EXE% -m camoufox fetch >nul 2>&1

rem Also ensure standard Playwright Chromium is available as fallback
%PY_EXE% -m playwright install chromium >nul 2>&1

rem 5. Re-sync bot.py to Desktop (in case it was updated)
copy /y "C:\Automation\bot.py" "%USERPROFILE%\Desktop\bot.py" >nul 2>&1
copy /y "C:\Automation\proxies.txt" "%USERPROFILE%\Desktop\proxies.txt" >nul 2>&1
copy /y "C:\Automation\master_orchestrator\orchestrator_config.json" "%USERPROFILE%\Desktop\master_orchestrator\orchestrator_config.json" >nul 2>&1

rem 6. Launch Main Traffic Bot
echo ================================================================
echo [*] Launching Stealth Traffic Bot (bot.py)...
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
