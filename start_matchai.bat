@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python scripts\run_matchai.py
pause
