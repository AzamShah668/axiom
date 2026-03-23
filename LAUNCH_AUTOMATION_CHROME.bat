@echo off
echo ==============================================
echo 🚀 AXIOM ACADEMY AUTOMATION LAUNCHER
echo ==============================================
echo.
echo 1. LOG IN TO GOOGLE in the window that just opened.
echo 2. DO NOT CLOSE THIS WINDOW (the black console window).
echo 3. Keep the browser open while the AI is working.
echo.
echo ==============================================
echo.
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%~dp0.automation_profile" --profile-directory="Default" --no-first-run --no-default-browser-check
pause
