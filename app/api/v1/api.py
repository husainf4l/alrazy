"""
API v1 router for the Al Razy Pharmacy Security System.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import cameras, security, dashboards

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(cameras.router)
api_router.include_router(security.router)
api_router.include_router(dashboards.router)
