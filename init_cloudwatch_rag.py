#!/usr/bin/env python3
"""
Initialize CloudWatch RAG Database
Creates the necessary tables for the CloudWatch RAG system
"""

import sqlite3
import os
from datetime import datetime

def init_database(db_path="cloudleakage.db"):
    """Initialize the CloudWatch RAG database with required tables"""
    
    print(f"Initializing CloudWatch RAG database: {db_path}")
    
    # Read the schema file
    schema_file = "cloudwatch_rag_schema.sql"
    if not os.path.exists(schema_file):
        print(f"Error: Schema file {schema_file} not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read and execute schema
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement.upper().startswith(('CREATE', 'INSERT', 'UPDATE')):
                try:
                    cursor.execute(statement)
                    print(f"✓ Executed: {statement[:50]}...")
                except sqlite3.Error as e:
                    print(f"✗ Failed: {statement[:50]}... - {e}")
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
        print(f"\n✓ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    import subprocess
    import sys
    
    packages = [
        'google-generativeai',
        'python-dotenv'
    ]
    
    print("Installing required packages...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")

def create_env_template():
    """Create a .env template file for configuration"""
    env_template = """# CloudWatch RAG Configuration
# Get your Gemini API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Database configuration
DATABASE_PATH=cloudleakage.db

# AWS Configuration (for data ingestion)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_template)
        print("✓ Created .env template file")
        print("  Please edit .env and add your API keys")
    else:
        print("✓ .env file already exists")

if __name__ == "__main__":
    print("CloudWatch RAG System Initialization")
    print("=" * 50)
    
    # Install dependencies
    install_dependencies()
    
    # Create environment template
    create_env_template()
    
    # Initialize database
    success = init_database()
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 CloudWatch RAG System is ready!")
        print("\nNext steps:")
        print("1. Edit .env file and add your Gemini API key")
        print("2. Start the Flask application: python app.py")
        print("3. Visit /cloudwatch/insights to start querying")
        print("4. Click 'Load Sample Data' to test with sample data")
        print("\nExample queries to try:")
        print("- 'Show me CPU utilization for the last 24 hours'")
        print("- 'What are the most common errors today?'")
        print("- 'Find instances with high CPU usage'")
    else:
        print("\n❌ Initialization failed. Please check the errors above.")
