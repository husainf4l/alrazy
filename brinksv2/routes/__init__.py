"""
API Routes for Brinks V2 People Detection System
"""
from routes.cameras import router as cameras_router
from routes.dashboard import router as dashboard_router
from routes.detections import router as detections_router
from routes.visualization import router as visualization_router
from routes.rooms import router as rooms_router

__all__ = [
    "cameras_router",
    "dashboard_router",
    "detections_router",
    "visualization_router",
    "rooms_router",
]