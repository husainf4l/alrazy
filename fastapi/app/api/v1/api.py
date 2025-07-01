"""
API v1 router for the RazZ Backend Security System.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import cameras, security, auth, enterprise_cameras

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(cameras.router)
api_router.include_router(enterprise_cameras.router)
api_router.include_router(security.router)
