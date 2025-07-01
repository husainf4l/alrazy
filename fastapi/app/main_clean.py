"""
Updated main FastAPI application with clean Prisma integration.
Focuses only on camera streaming and computer vision features.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.streaming import router as streaming_router
from app.models.prisma_client import prisma_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    print("🚀 Starting FastAPI Camera Streaming Service...")
    
    # Connect to Prisma database (same as backend)
    try:
        await prisma_manager.connect()
        print("📊 Connected to Prisma database")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("   Make sure your backend database is running")
        raise
    
    print("✅ FastAPI Camera Streaming Service ready!")
    print("📋 Available endpoints:")
    print("   - Camera stream info: GET /api/v1/cameras/stream/info/{camera_id}")
    print("   - Camera frame: GET /api/v1/cameras/stream/frame/{camera_id}")
    print("   - Motion detection: GET /api/v1/cameras/stream/motion/{camera_id}")
    print("   - Initialize camera: POST /api/v1/cameras/stream/initialize/{camera_id}")
    print("   - Start recording: POST /api/v1/cameras/stream/record/{camera_id}")
    print("   - Company cameras: GET /api/v1/cameras/company/{company_id}/cameras")
    print("   - API docs: http://localhost:8001/docs")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down FastAPI Camera Streaming Service...")
    
    # Disconnect from database
    try:
        await prisma_manager.disconnect()
        print("Database connection closed")
    except Exception as e:
        print(f"Error closing database connection: {e}")

# Create FastAPI application
app = FastAPI(
    title="Camera Streaming Service",
    description="FastAPI service for camera streaming, computer vision, and real-time features. Integrates with NestJS backend database.",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(streaming_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Camera Streaming Service",
        "status": "operational",
        "description": "FastAPI service for camera streaming and computer vision",
        "integration": "Connected to NestJS backend database",
        "endpoints": {
            "docs": "/docs",
            "cameras": "/api/v1/cameras/*",
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        prisma = await prisma_manager.get_client()
        # Simple query to test connection
        await prisma.camera.count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "camera_streaming"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,  # Different port from backend
        reload=True
    )
