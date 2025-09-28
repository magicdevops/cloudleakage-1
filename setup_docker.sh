#!/bin/bash

# CloudLeakage Docker Setup Script
# This script sets up PostgreSQL in Docker, app runs on host machine

set -e  # Exit on any error

echo "🐳 CloudLeakage Docker Setup (PostgreSQL only)"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker and try again."
    echo "💡 Installation: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    echo "💡 Installation: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose found: $(docker --version)"

# Function to check if Docker daemon is running
check_docker_daemon() {
    if ! docker info &> /dev/null; then
        echo "❌ Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
}

check_docker_daemon

# Navigate to docker directory
cd docker

# Create .env file if it doesn't exist
if [ ! -f ../.env ]; then
    echo "📝 Creating .env file from template..."
    cp ../.env.example ../.env
    echo "✅ .env file created. Please edit it with your specific settings."
    echo "🔧 Important: Update passwords and secrets in .env file before proceeding!"
    read -p "Press Enter after updating .env file..."
fi

# Start only PostgreSQL (and optionally Redis)
echo "🏗️  Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 15

# Check PostgreSQL status
if docker-compose ps postgres | grep -q "Up"; then
    echo "✅ PostgreSQL container is running!"
else
    echo "❌ PostgreSQL container failed to start!"
    echo "🔍 Check logs: docker-compose logs postgres"
    exit 1
fi

# Test database connection
echo "🔗 Testing database connection..."
if docker-compose exec postgres pg_isready -U app_user -d cloudleakage &> /dev/null; then
    echo "✅ PostgreSQL database is ready!"
else
    echo "❌ PostgreSQL database connection failed!"
    echo "🔍 Check logs: docker-compose logs postgres"
    exit 1
fi

echo ""
echo "🚀 PostgreSQL is now running in Docker!"
echo "📍 Database: postgresql://app_user:app_pass@localhost:5432/cloudleakage"
echo ""
echo "🔧 Next steps:"
echo "   1. Run your application locally: python app.py"
echo "   2. The app will automatically connect to PostgreSQL"
echo "   3. Access your app at: http://localhost:5000"
echo ""
echo "📊 Useful commands:"
echo "   docker-compose logs -f postgres    # View database logs"
echo "   docker-compose down                # Stop PostgreSQL"
echo "   docker-compose restart postgres    # Restart database"
echo ""
echo "🎯 Application will run on host, database in container!"
echo "==================================================="
