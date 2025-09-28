#!/bin/bash
# PostgreSQL initialization script for CloudLeakage

set -e

echo "🚀 Setting up CloudLeakage PostgreSQL database..."

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -p 5432 -U cloudleakage_user; do
  echo "⏳ Waiting for PostgreSQL..."
  sleep 2
done

echo "✅ PostgreSQL is ready!"

# Create the cloudleakage database if it doesn't exist
echo "📦 Creating database and tables..."

# The tables will be created automatically by the application
# This script just ensures the database exists and is accessible

echo "🔐 Setting up database permissions..."

# Grant necessary permissions
psql -v ON_ERROR_STOP=1 --username cloudleakage_user --dbname cloudleakage << EOF
-- Ensure the user has necessary permissions
GRANT ALL PRIVILEGES ON DATABASE cloudleakage TO cloudleakage_user;

-- Create schema if needed (optional)
-- CREATE SCHEMA IF NOT EXISTS cloudleakage;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
EOF

echo "✅ Database initialization completed!"
echo "🎯 CloudLeakage PostgreSQL container is ready!"
echo "📍 Connection: postgresql://cloudleakage_user:cloudleakage_secure_password_123!@localhost:5432/cloudleakage"
