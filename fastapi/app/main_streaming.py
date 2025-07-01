"""
Clean FastAPI Camera Streaming Service
Integrates with your NestJS backend database via Prisma.

This service focuses ONLY on:
- Real-time camera streaming
- Computer vision (motion detection)
- WebSocket video feeds
- Recording triggers
- Alert creation

It does NOT handle:
- User authentication (your NestJS backend does this)
- Camera CRUD operations (your NestJS backend does this)
- User management (your NestJS backend does this)
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our clean services
from app.database.prisma_client import prisma_manager
from app.api.streaming_api import router as streaming_router
from app.api.websocket_api import router as websocket_router
from app.services.camera_stream_service import get_camera_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - startup and shutdown."""
    
    # === STARTUP ===
    logger.info("🚀 Starting FastAPI Camera Streaming Service...")
    
    try:
        # Connect to your backend database (same as NestJS)
        await prisma_manager.connect()
        logger.info("📊 Connected to backend database via Prisma")
        
        # Initialize camera streaming service
        camera_service = await get_camera_service()
        logger.info("🎥 Camera streaming service initialized")
        
        logger.info("✅ FastAPI Camera Streaming Service is ready!")
        logger.info("📋 Available endpoints:")
        logger.info("   🎬 Stream camera info: GET /api/stream/camera/{id}/info")
        logger.info("   📸 Get camera frame: GET /api/stream/camera/{id}/frame")
        logger.info("   🔍 Motion detection: GET /api/stream/camera/{id}/motion")
        logger.info("   📹 Start recording: POST /api/stream/camera/{id}/record")
        logger.info("   🏢 Company cameras: GET /api/stream/company/{id}/cameras")
        logger.info("   📡 WebSocket stream: ws://localhost:8001/ws/camera-stream?company_id=X")
        logger.info("   📚 API docs: http://localhost:8001/docs")
        
    except Exception as e:
        logger.error(f"❌ Failed to start service: {e}")
        raise
    
    yield  # Application is running
    
    # === SHUTDOWN ===
    logger.info("🛑 Shutting down FastAPI Camera Streaming Service...")
    
    try:
        # Clean up camera resources
        camera_service = await get_camera_service()
        await camera_service.cleanup_all()
        logger.info("🧹 Camera resources cleaned up")
        
        # Disconnect from database
        await prisma_manager.disconnect()
        logger.info("📊 Database connection closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title="Camera Streaming Service",
    description="""
    🎥 FastAPI service for camera streaming and computer vision.
    
    **Integrates with your NestJS backend database.**
    
    ## Features
    - Real-time camera streaming via WebSocket
    - Motion detection with OpenCV
    - Alert creation in your backend database
    - Recording triggers
    - Multi-company support
    
    ## Authentication
    Send `X-Company-Id` header with requests (obtained from your NestJS backend after user authentication).
    
    ## Integration
    This service reads camera configurations from your NestJS backend database and provides streaming functionality.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware (configure based on your frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(streaming_router, prefix="/api")
app.include_router(websocket_router)

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "FastAPI Camera Streaming Service",
        "version": "2.0.0",
        "status": "operational",
        "description": "Real-time camera streaming and computer vision service",
        "integration": {
            "backend": "NestJS with Prisma",
            "database": "PostgreSQL (shared with backend)",
            "authentication": "Via NestJS backend (X-Company-Id header)"
        },
        "features": [
            "Real-time camera streaming",
            "Motion detection with OpenCV",
            "WebSocket video feeds",
            "Alert creation",
            "Recording triggers",
            "Multi-company support"
        ],
        "endpoints": {
            "docs": "/docs",
            "camera_streaming": "/api/stream/camera/*",
            "websocket": "/ws/camera-stream",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        prisma = prisma_manager.get_client()
        
        # Simple query to test connection
        camera_count = await prisma.camera.count()
        
        return {
            "status": "healthy",
            "service": "camera_streaming",
            "database": "connected",
            "cameras_in_db": camera_count,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "camera_streaming", 
            "database": "disconnected",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting FastAPI Camera Streaming Service on port 8001")
    logger.info("📡 Make sure your NestJS backend is running on port 3000")
    logger.info("📊 Make sure PostgreSQL database is running")
    
    uvicorn.run(
        "app.main_streaming:app",  # This file
        host="0.0.0.0", 
        port=8001,  # Different port from your NestJS backend (3000)
        reload=True,
        log_level="info"
    )
