@echo off
call conda activate wp_autodesk
python "%~dp0setup.py" build --project-dir "%~1"
