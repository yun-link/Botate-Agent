#!/bin/bash
# Install all dependencies for Botate-Agent

SCRIPT_DIR="$(dirname "$0")"

echo "Installing Botate-Agent dependencies..."

# Install backend dependencies
echo "Installing backend dependencies..."
cd "$SCRIPT_DIR/backend"
pip install -r requirements.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
npm install

echo "All dependencies installed successfully!"
