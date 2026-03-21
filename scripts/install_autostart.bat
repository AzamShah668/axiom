@echo off
echo ================================================
echo  AXIOM Academy — Install Auto-Start
echo ================================================
echo.
echo This will register a Windows Task Scheduler task
echo so the AXIOM server starts automatically every
echo time you log in to Windows.
echo.
echo Run this script ONCE. You can run it again later
echo to update the registration if needed.
echo.

schtasks /create ^
  /tn "AXIOM Academy Server" ^
  /tr "\"D:\notebook lm\START_AXIOM_SERVER.bat\"" ^
  /sc ONLOGON ^
  /ru "%USERNAME%" ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Task registered successfully!
    echo      The server will now start automatically on every login.
    echo.
    echo To verify: schtasks /query /tn "AXIOM Academy Server"
    echo To remove: schtasks /delete /tn "AXIOM Academy Server" /f
) else (
    echo.
    echo [ERROR] Task registration failed. Try running as Administrator.
)

echo.
pause
