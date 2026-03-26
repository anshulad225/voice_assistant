#!/usr/bin/env python3
"""
Quick setup script for Dental Clinic Voice Intake System
"""
import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("   Creating from .env.example...")
        
        example = Path(".env.example")
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print("✅ .env file created")
            print("   Please edit .env and add your credentials")
            return False
        else:
            print("❌ .env.example not found!")
            return False
    
    # Check for placeholder values
    content = env_file.read_text()
    
    issues = []
    if "your_google_api_key_here" in content or "your_openai_api_key" in content:
        issues.append("GOOGLE_API_KEY needs to be set")
    
    if "your_twilio" in content.lower():
        issues.append("Twilio credentials need to be set")
    
    if issues:
        print("⚠️  .env file exists but has placeholder values:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n📖 See GET_API_KEY.md for instructions")
        return False
    
    print("✅ .env file configured")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import fastapi
        import google.generativeai
        import sqlalchemy
        import twilio
        print("✅ Dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("   Run: pip install -r requirements.txt")
        return False

def init_database():
    """Initialize the database"""
    try:
        from app.database import init_db
        print("🔄 Initializing database...")
        init_db()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Dental Clinic Voice Intake System - Setup")
    print("=" * 60)
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check .env file
    if not check_env_file():
        print("\n📝 Next steps:")
        print("   1. Get Google AI API key from: https://aistudio.google.com/")
        print("   2. Add it to .env file")
        print("   3. Run this script again: python setup.py")
        sys.exit(1)
    
    # Initialize database
    if not init_database():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("🚀 Next steps:")
    print("   1. Start server: python run_dev.py")
    print("   2. Expose with ngrok: ngrok http 8000")
    print("   3. Configure Twilio webhook")
    print("   4. Make a test call!")
    print()
    print("📚 Documentation:")
    print("   - QUICKSTART.md - Full setup guide")
    print("   - TESTING.md - Testing procedures")
    print("   - QUICK_REFERENCE.md - Common commands")

if __name__ == "__main__":
    main()
