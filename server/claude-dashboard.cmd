@echo off
rem Double-click: measures the Claude setup and opens the metrics dashboard in your browser.
python "%~dp0_tools\scripts\claude_dashboard.py" %*
if errorlevel 1 pause
