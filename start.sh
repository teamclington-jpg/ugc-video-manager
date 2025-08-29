#!/bin/bash

echo "=========================================="
echo "   UGC Video Manager - Starting..."
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from template..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and settings"
    exit 1
fi

# Clear terminal
clear

echo "╔══════════════════════════════════════════════════╗"
echo "║         UGC Video Manager v1.0.0                 ║"
echo "║                                                   ║"
echo "║  📁 Watching folder for new videos               ║"
echo "║  🤖 AI-powered video analysis                    ║"
echo "║  📊 Smart channel assignment                     ║"
echo "║  🎯 SEO optimization                             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "🌐 Dashboard: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="

# Run the application
python3 main.py