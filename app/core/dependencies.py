"""
FastAPI dependencies for the Al Razy Pharmacy Security System.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from app.core.config import get_settings, Settings


def get_app_settings() -> Settings:
    """Get application settings."""
    return get_settings()


async def get_camera_service():
    """Get async camera service dependency."""
    try:
        from app.services.async_camera_service import get_camera_manager
        return await get_camera_manager()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera service not available"
        )


async def get_security_service():
    """Get security service dependency."""
    try:
        from app.services.security_service import get_security_orchestrator
        return get_security_orchestrator()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security service not available"
        )


async def get_recording_service():
    """Get recording service dependency."""
    try:
        from app.services.recording_service import get_recording_service
        return get_recording_service()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording service not available"
        )


async def get_webhook_service():
    """Get webhook service dependency."""
    try:
        from app.services.webhook_service import get_webhook_service
        return get_webhook_service()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook service not available"
        )


async def get_llm_service():
    """Get LLM service dependency."""
    try:
        from app.services.llm_service import get_llm_analyzer
        return get_llm_analyzer()
    except ImportError:
        return None  # LLM service is optional
