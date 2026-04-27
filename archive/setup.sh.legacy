#!/bin/bash

echo "🚀 Setting up FinTrack..."

# Backend setup
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "✅ Backend ready!"

# Frontend setup
echo "📦 Setting up frontend..."
cd ../frontend
npm install

echo "✅ Frontend ready!"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run the app:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source venv/bin/activate && python run.py"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000"
