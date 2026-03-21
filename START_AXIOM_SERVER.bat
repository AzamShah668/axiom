@echo off
:: AXIOM Academy — Auto-starts the pipeline server in a minimized background window.
:: Registered in Windows Task Scheduler by scripts\install_autostart.bat
start "AXIOM Server" /min cmd /k "cd /d "D:\notebook lm" && node core/server.js"
