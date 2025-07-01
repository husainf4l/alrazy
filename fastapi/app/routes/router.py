"""
Router configuration for RazZ Backend Security System.

This module combines all route modules and provides a single router
to be included in the main FastAPI application.
"""
from fastapi import APIRouter

from app.routes import main, websocket

# Create main router
router = APIRouter()

# Include all route modules
router.include_router(main.router, tags=["main"])
router.include_router(websocket.router, tags=["websocket"])

# Export individual routers for modular access
main_router = main.router
websocket_router = websocket.router

# Function to set security system for main routes
def set_security_system(security_system):
    """Set the security system instance for main routes."""
    main.set_security_system(security_system)
