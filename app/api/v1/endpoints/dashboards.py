"""
Dashboard API endpoints for the Al Razy Pharmacy Security System.
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def main_dashboard():
    """Serve the main dashboard HTML page."""
    return FileResponse("app/static/index.html")


@router.get("/security")
async def security_dashboard():
    """Enhanced security dashboard with advanced features."""
    return FileResponse("app/static/security-dashboard.html")


@router.get("/analytics")
async def analytics_dashboard():
    """Analytics dashboard for security insights."""
    return FileResponse("app/static/analytics-dashboard.html")


@router.get("/streaming")
async def streaming_dashboard():
    """Serve the real-time streaming dashboard."""
    return FileResponse("app/static/streaming-dashboard.html")


@router.get("/multi-camera")
async def multi_camera_dashboard():
    """Serve the multi-camera dashboard HTML page."""
    return FileResponse("app/static/multi-camera.html")


# Legacy endpoints for backward compatibility
@router.get("/security-dashboard")
async def security_dashboard_legacy():
    """Direct access to security dashboard (legacy)."""
    return FileResponse("app/static/security-dashboard.html")


@router.get("/analytics-dashboard")
async def analytics_dashboard_legacy():
    """Direct access to analytics dashboard (legacy)."""
    return FileResponse("app/static/analytics-dashboard.html")


@router.get("/streaming-dashboard")
async def streaming_dashboard_legacy():
    """Direct access to streaming dashboard (legacy)."""
    return FileResponse("app/static/streaming-dashboard.html")


@router.get("/multi-dashboard")
async def multi_dashboard_legacy():
    """Serve the multi-camera dashboard HTML page (legacy)."""
    return FileResponse("app/static/multi-camera.html")
