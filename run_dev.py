#!/usr/bin/env python3
"""
Development server runner with environment validation
"""
import os
import sys
from pathlib import Path

def check_env():
    """Validate required environment variables"""
    required = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN", 
        "GOOGLE_API_KEY",
        "DATABASE_URL"
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nCopy .env.example to .env and fill in your values.")
        sys.exit(1)
    
    print("✓ Environment variables configured")

def main():
    # Load .env if it exists
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    check_env()
    
    print("\n🚀 Starting Dental Voice Intake System...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📊 Health check: http://localhost:8000/health")
    print("📋 Intakes API: http://localhost:8000/intakes\n")
    
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
