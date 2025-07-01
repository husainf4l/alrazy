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
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any

from app.core.config import get_settings
from app.api.v1.api import api_router


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

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint that returns comprehensive Al Razy Pharmacy Security System status."""
    try:
        # Get basic system info
        system_info = {
            "message": settings.app_name,
            "version": settings.app_version,
            "pharmacy": settings.pharmacy_name,
            "system_status": "online",
            "timestamp": time.time()
        }
        
        # Get pharmacy risk assessment
        try:
            from app.services.activity_service import get_pharmacy_risk_assessment
            risk_assessment = get_pharmacy_risk_assessment()
            system_info["risk_assessment"] = risk_assessment
        except Exception as e:
            system_info["risk_assessment"] = {"error": str(e), "status": "unavailable"}
        
        # Get camera status
        try:
            from app.services.camera_service import get_available_cameras
            available_cameras = get_available_cameras()
            system_info["cameras"] = {
                "total_cameras": len(available_cameras),
                "available_cameras": available_cameras,
                "status": "operational" if available_cameras else "no_cameras"
            }
        except Exception as e:
            system_info["cameras"] = {
                "total_cameras": 0,
                "available_cameras": [],
                "status": "unavailable", 
                "message": "Cameras not initialized. Use /api/v1/cameras/initialize to connect."
            }
        
        # Get security system status
        global security_system
        try:
            if security_system:
                security_status = security_system.get_system_status()
                system_info["security_system"] = security_status
            else:
                system_info["security_system"] = {"status": "not_initialized", "basic_mode": True}
        except Exception as e:
            system_info["security_system"] = {"error": str(e), "status": "error"}
        
        # Get LLM status
        try:
            from app.services.llm_service import get_llm_analyzer
            llm_analyzer = get_llm_analyzer()
            system_info["llm_analysis"] = {
                "available": llm_analyzer is not None,
                "status": "active" if llm_analyzer else "disabled"
            }
        except Exception as e:
            system_info["llm_analysis"] = {"error": str(e), "status": "error"}
        
        # Add navigation links
        system_info["dashboards"] = {
            "security_dashboard": "/api/v1/dashboard/security",
            "streaming_dashboard": "/api/v1/dashboard/streaming", 
            "multi_camera": "/api/v1/dashboard/multi-camera",
            "analytics_dashboard": "/api/v1/dashboard/analytics"
        }
        
        system_info["api_endpoints"] = {
            "health": "/health",
            "cameras_info": "/api/v1/cameras/info",
            "security_status": "/api/v1/security/status",
            "risk_assessment": "/api/v1/security/risk-assessment",
            "api_docs": "/docs",
            "openapi": "/openapi.json"
        }
        
        return system_info
        
    except Exception as e:
        return {
            "message": settings.app_name,
            "status": "error",
            "error": str(e),
            "fallback": "System operational in basic mode"
        }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": settings.app_name,
        "version": settings.app_version
    }


# Legacy endpoints for backward compatibility
@app.get("/security-dashboard")
async def security_dashboard_legacy():
    """Direct access to security dashboard (legacy)."""
    return FileResponse("app/static/security-dashboard.html")


@app.get("/multi-camera")
async def multi_camera_legacy():
    """Direct access to multi-camera view (legacy)."""
    return FileResponse("app/static/multi-camera.html")


@app.get("/streaming-dashboard")
async def streaming_dashboard_legacy():
    """Direct access to streaming dashboard (legacy)."""
    return FileResponse("app/static/streaming-dashboard.html")


@app.get("/analytics-dashboard")
async def analytics_dashboard_legacy():
    """Direct access to analytics dashboard (legacy)."""
    return FileResponse("app/static/analytics-dashboard.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        reload=settings.debug
    )
