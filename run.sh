#!/bin/bash
# Start both frontend and backend services

SCRIPT_DIR="$(dirname "$0")"

echo "Starting Botate-Agent services..."

# Start backend
echo "Starting backend..."
(
    cd "$SCRIPT_DIR/backend"
    python -m api.agent_api
) &

# Start frontend
echo "Starting frontend..."
(
    cd "$SCRIPT_DIR/frontend"
    npm run dev
) &

echo "All services started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"

# Wait for all background processes
wait
