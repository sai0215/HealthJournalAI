#!/bin/bash
# Quick launcher for Streamlit Health Assistant

echo "🏥 Starting Health Assistant..."
echo "================================"
echo ""

# Navigate to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv_mac" ]; then
    echo "✓ Activating virtual environment..."
    source venv_mac/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv_mac && pip install -r requirements.txt"
    exit 1
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found!"
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

echo "✓ Starting Streamlit app..."
echo ""
echo "📱 The app will open in your browser at: http://localhost:8501"
echo "🛑 To stop the app, press Ctrl+C"
echo ""
echo "================================"
echo ""

# Run streamlit
streamlit run streamlit_app.py

