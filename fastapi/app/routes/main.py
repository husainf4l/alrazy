"""
Main application routes for RazZ Backend Security System.

Contains core application endpoints like health checks and root endpoint.
"""
import time
from fastapi import APIRouter
from typing import Dict, Any

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

# Import security system globally
security_system = None


def set_security_system(sys):
    """Set the security system instance."""
    global security_system
    security_system = sys


@router.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint that returns comprehensive RazZ Backend Security System status."""
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


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": settings.app_name,
        "version": settings.app_version
    }
