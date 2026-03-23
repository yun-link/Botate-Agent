@echo off
REM Install all dependencies for Botate-Agent

echo Installing Botate-Agent dependencies...

REM Install backend dependencies
echo Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt

REM Install frontend dependencies
echo Installing frontend dependencies...
cd /d "%~dp0frontend"
npm install

echo All dependencies installed successfully!
