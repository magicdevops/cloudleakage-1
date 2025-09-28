 this #!/bin/bash

# AWS Cost Optimization Tool - Setup and Run Script
# This script sets up the virtual environment and runs the Flask application

set -e  # Exit on any error

echo "🌟 AWS Cost Optimization Tool Setup"
echo "===================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ All dependencies installed successfully!"
echo ""
echo "🚀 Starting AWS Cost Optimization Tool..."
echo "📍 Server will be available at: http://127.0.0.1:5000"
echo "🎯 Dashboard URL: http://127.0.0.1:5000/dashboard"
echo "⚙️  Press Ctrl+C to stop the server"
echo "===================================="
echo ""

# Set Gemini API Key
export GEMINI_API_KEY="AIzaSyDsUZkA2UgnZ5HuRCM3BKIeFkWzR7K33iI"

# Run the Flask application
python app.py
