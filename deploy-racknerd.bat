@echo off
setlocal DisableDelayedExpansion
title Unwind Africa - RackNerd setup

where ssh >nul 2>nul
if errorlevel 1 (
    echo OpenSSH client was not found. Enable the Windows OpenSSH Client feature and retry.
    pause
    exit /b 1
)
where scp >nul 2>nul
if errorlevel 1 (
    echo SCP was not found. Enable the Windows OpenSSH Client feature and retry.
    pause
    exit /b 1
)

set "TARGET="
set /p "TARGET=Ubuntu VPS SSH destination (example root@192.236.188.32): "
if not defined TARGET (
    echo An SSH destination is required.
    pause
    exit /b 1
)

if not exist "%~dp0ops\deploy_racknerd.sh" (
    echo Could not find ops\deploy_racknerd.sh beside this launcher.
    pause
    exit /b 1
)

echo.
echo Copying the setup script to %TARGET% ...
scp -p "%~dp0ops\deploy_racknerd.sh" "%TARGET%:/tmp/unwindafrica-nginx-setup.sh"
if errorlevel 1 (
    echo Upload failed. Check your SSH destination, key, and network connection.
    pause
    exit /b 1
)

echo.
echo The Ubuntu script will check the app, back up Nginx, configure the domain, and verify HTTPS routes.
echo It will stop without changing Nginx if the upstream checks or certificate checks fail.
echo.
ssh -t "%TARGET%" "sudo bash /tmp/unwindafrica-nginx-setup.sh"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo Setup stopped or failed with exit code %RESULT%. Read the error above; no secrets were requested.
) else (
    echo Setup completed. Open https://unwindafrica.com and verify the website and app API.
)
pause
exit /b %RESULT%
