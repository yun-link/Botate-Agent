@echo off
REM Start both frontend and backend services

echo Starting Botate-Agent services...

REM Start backend in a new window
echo Starting backend...
start "Backend" cmd /k "cd /d "%~dp0backend" && python -m api.agent_api"

REM Start frontend in a new window
echo Starting frontend...
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo All services started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
