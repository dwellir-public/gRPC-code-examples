#!/bin/bash

echo "🚀 Starting Hyperliquid Liquidation Tracker"
echo "=========================================="
echo ""

# Check if .env exists in backend
if [ ! -f backend/.env ]; then
    echo "⚠️  Warning: backend/.env not found!"
    echo "   Please copy backend/.env.example to backend/.env and configure it."
    exit 1
fi

# Start backend in background
echo "📡 Starting backend server..."
cd backend
source venv/bin/activate 2>/dev/null || python -m venv venv && source venv/bin/activate
python server.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services started!"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "📱 Open http://localhost:3000 in your browser"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

wait
