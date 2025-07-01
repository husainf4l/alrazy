"""
Al Razy Pharmacy Security System - FastAPI Application

A comprehensive security monitoring system for pharmacies with:
- Real-time camera surveillance
- AI-powered threat detection
- Automated recording and alerts
- LLM-enhanced analysis
- WebSocket real-time updates
"""
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.api import api_router
from app.middleware.timeout import TimeoutMiddleware, CameraTimeoutMiddleware
from app.routes.router import router as main_router, set_security_system


# Global variables for services
security_system = None
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    print("🚀 Starting Al Razy Pharmacy Security System...")
    
    # Skip camera initialization but set up for manual initialization later
    print("📷 Cameras will be initialized on-demand when accessed")
    print("   Use /api/v1/cameras/initialize endpoint to manually initialize cameras")
    
    # Initialize async services
    global security_system
    try:
        print(f"⚙️  LLM enabled: {settings.llm_config.enabled if settings.llm_config else False}")
        
        # Initialize async security system
        try:
            from app.services.async_security_service import initialize_async_security_system
            security_system = await initialize_async_security_system(settings.__dict__)
            await security_system.start()
            print("🔒 Async Security System initialized and started")
        except Exception as e:
            print(f"⚠️  Warning: Async security system initialization failed: {e}")
            
            # Fallback to sync version
            try:
                from app.services.security_service import initialize_security_system
                security_system = initialize_security_system(settings)
                await security_system.initialize()
                security_system.start()
                print("🔒 Fallback Security System initialized and started")
            except Exception as e2:
                print(f"⚠️  Warning: Fallback security system initialization failed: {e2}")
                print("   Application will run in basic mode without advanced features")
                
        # Initialize async WebSocket manager
        try:
            from app.services.async_websocket_service import get_async_connection_manager
            websocket_manager = await get_async_connection_manager()
            print("🔌 Async WebSocket manager initialized")
        except Exception as e:
            print(f"⚠️  Warning: WebSocket manager initialization failed: {e}")
            
        # Initialize async recording service
        try:
            from app.services.async_recording_service import initialize_async_recording_service
            recording_config = {
                'recordings_dir': 'recordings',
                'buffer_duration': 30,
                'recording_duration': 60
            }
            recording_service = await initialize_async_recording_service(recording_config)
            print("📹 Async Recording service initialized")
        except Exception as e:
            print(f"⚠️  Warning: Recording service initialization failed: {e}")
            
        # Set security system for routes
        set_security_system(security_system)
            
    except Exception as e:
        print(f"⚠️  Warning: Configuration loading failed: {e}")
        print("   Application will run with default settings")
    
    print("✅ Application startup completed - Server is ready!")
    print("📋 Available endpoints:")
    print("   - Main dashboard: http://localhost:8000")
    print("   - Security dashboard: http://localhost:8000/api/v1/dashboard/security")
    print("   - Multi-camera view: http://localhost:8000/api/v1/dashboard/multi-camera")
    print("   - API docs: http://localhost:8000/docs")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Al Razy Pharmacy Security System...")
    
    # Stop async security system
    if security_system:
        try:
            if hasattr(security_system, 'stop') and asyncio.iscoroutinefunction(security_system.stop):
                await security_system.stop()
            else:
                security_system.stop()
            print("Security system stopped")
        except Exception as e:
            print(f"Error stopping security system: {e}")
    
    # Cleanup async WebSocket manager
    try:
        from app.services.async_websocket_service import cleanup_connection_manager
        await cleanup_connection_manager()
        print("WebSocket manager cleaned up")
    except Exception as e:
        print(f"Error cleaning up WebSocket manager: {e}")
    
    # Cleanup cameras
    try:
        from app.services.camera_service import cleanup_camera
        cleanup_camera()
        print("All camera resources cleaned up")
    except Exception as e:
        print(f"Error cleaning up cameras: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="A comprehensive FastAPI security monitoring system for Al Razy Pharmacy with AI-powered threat detection, real-time camera surveillance, and automated alerts.",
    version=settings.app_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add timeout middleware
app.add_middleware(CameraTimeoutMiddleware, camera_timeout=60)
app.add_middleware(TimeoutMiddleware, timeout=30)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include main routes (health, root, dashboard, websocket)
app.include_router(main_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        reload=settings.debug
    )
