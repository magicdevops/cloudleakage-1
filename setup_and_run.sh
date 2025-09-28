 this #!/bin/bash

# AWS Cost Optimization Tool - Setup and Run Script
# This script sets up the virtual environment and runs the Flask application

set -e  # Exit on any error

echo "🌟 AWS Cost Optimization Tool Setup"
echo "===================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "💡 On Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "💡 On CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv --clear
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Ensure we're using the virtual environment's pip
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
    # Upgrade pip using virtual environment's pip
    echo "⬆️  Upgrading pip..."
    venv/bin/pip install --upgrade pip
    
    # Install requirements
    echo "📚 Installing dependencies..."
    venv/bin/pip install -r requirements.txt
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

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
