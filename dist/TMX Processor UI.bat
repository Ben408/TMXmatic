@echo off
cd /d "%~dp0"
echo Starting TMX Processing Tool...
timeout /t 2 /nobreak > nul
start http://localhost:5000
TMX_Processing_Tool.exe
if errorlevel 1 (
    echo Error starting the application
    echo Check tmx_tool.log for details
    pause
)