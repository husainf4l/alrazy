#!/usr/bin/env python3
"""
Entry point for the Al Razy Pharmacy Security System.
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    from app.core.config import get_settings
    
    settings = get_settings()
    
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"🏥 Pharmacy: {settings.pharmacy_name}")
    print(f"🌐 Server: http://{settings.host}:{settings.port}")
    print(f"📋 API Docs: http://{settings.host}:{settings.port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
