#!/bin/bash

# FastAPI Camera Streaming Service Setup Script
# This script sets up the clean FastAPI service that integrates with your NestJS backend

echo "🚀 Setting up FastAPI Camera Streaming Service..."
echo "📊 This service will connect to your NestJS backend database"

# Check if we're in the right directory
if [ ! -f "requirements_streaming.txt" ]; then
    echo "❌ Error: Please run this script from the fastapi directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected files: requirements_streaming.txt"
    exit 1
fi

# Step 1: Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements_streaming.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Step 2: Copy Prisma schema from backend
echo ""
echo "📋 Setting up Prisma schema..."

# Create prisma directory if it doesn't exist
mkdir -p prisma

# Copy schema from backend
if [ -f "../backend/prisma/schema.prisma" ]; then
    cp ../backend/prisma/schema.prisma prisma/
    echo "✅ Copied Prisma schema from backend"
else
    echo "❌ Backend Prisma schema not found at ../backend/prisma/schema.prisma"
    echo "   Please make sure your backend is set up correctly"
    exit 1
fi

# Step 3: Generate Prisma client
echo ""
echo "🔧 Generating Prisma client..."
prisma generate

if [ $? -ne 0 ]; then
    echo "❌ Failed to generate Prisma client"
    echo "   Make sure the schema.prisma file is valid"
    exit 1
fi

# Step 4: Create environment file if it doesn't exist
echo ""
echo "⚙️  Setting up environment..."

if [ ! -f ".env" ]; then
    cat > .env << EOF
# Database URL (same as your NestJS backend)
DATABASE_URL="postgresql://username:password@localhost:5432/alrazy_db"

# Service configuration
SERVICE_NAME="Camera Streaming Service"
SERVICE_PORT=8001
DEBUG=true

# Logging
LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file"
    echo "📝 Please update DATABASE_URL in .env to match your backend database"
else
    echo "✅ .env file already exists"
fi

# Step 5: Create run script
echo ""
echo "🎬 Creating run script..."

cat > run_streaming.py << 'EOF'
#!/usr/bin/env python3
"""
Run script for FastAPI Camera Streaming Service
"""
import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting FastAPI Camera Streaming Service...")
    print("📡 Service: Camera streaming and computer vision")
    print("🔗 Integration: NestJS backend database via Prisma")
    print("🌐 Server: http://0.0.0.0:8001")
    print("📚 API Docs: http://localhost:8001/docs")
    print("📡 WebSocket: ws://localhost:8001/ws/camera-stream")
    print("")
    print("💡 Make sure your NestJS backend is running on port 3000")
    print("💡 Make sure PostgreSQL database is running")
    print("")
    
    # Get configuration from environment
    port = int(os.getenv("SERVICE_PORT", 8001))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    uvicorn.run(
        "app.main_streaming:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info"
    )
EOF

chmod +x run_streaming.py
echo "✅ Created run_streaming.py"

# Step 6: Test database connection
echo ""
echo "🔍 Testing database connection..."

python3 << 'EOF'
import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

async def test_db():
    try:
        from prisma import Prisma
        
        db = Prisma()
        await db.connect()
        
        # Test query
        count = await db.camera.count()
        print(f"✅ Database connection successful!")
        print(f"📊 Found {count} cameras in database")
        
        await db.disconnect()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure:")
        print("   - PostgreSQL is running")
        print("   - DATABASE_URL in .env is correct")
        print("   - Your NestJS backend database is set up")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_db())
    sys.exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo "✅ Database connection test passed"
else
    echo "⚠️  Database connection test failed (this is normal if your backend isn't running yet)"
fi

# Final instructions
echo ""
echo "🎉 FastAPI Camera Streaming Service setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update .env file with your database credentials"
echo "   2. Make sure your NestJS backend is running (port 3000)"
echo "   3. Make sure PostgreSQL database is running"
echo "   4. Run the streaming service:"
echo "      python3 run_streaming.py"
echo ""
echo "🌐 Service will be available at:"
echo "   - Main service: http://localhost:8001"
echo "   - API docs: http://localhost:8001/docs"
echo "   - WebSocket: ws://localhost:8001/ws/camera-stream"
echo ""
echo "🔗 Integration with your NestJS backend:"
echo "   - FastAPI reads camera configs from your backend database"
echo "   - Frontend authenticates with NestJS backend (port 3000)"
echo "   - Frontend sends X-Company-Id header to FastAPI for camera access"
echo "   - FastAPI creates alerts and recordings in your backend database"
echo ""
echo "✅ Ready to stream cameras!"
