@echo off
cd /d "%~dp0"
timeout /t 10 /nobreak
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
