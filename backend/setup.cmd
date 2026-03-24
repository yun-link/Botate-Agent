@echo off
REM Install backend dependencies

cd /d "%~dp0"
pip install -r requirements.txt
