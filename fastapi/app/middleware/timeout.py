"""
Timeout middleware to prevent long-running requests from blocking the application.
"""
import asyncio
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to handle request timeouts and prevent blocking."""
    
    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request with timeout."""
        start_time = time.time()
        
        try:
            # Wrap the request in a timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
            
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log slow requests
            if process_time > 5.0:
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s"
                )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(
                f"Request timeout: {request.method} {request.url.path} "
                f"exceeded {self.timeout}s"
            )
            return JSONResponse(
                status_code=408,
                content={
                    "error": "Request timeout",
                    "message": f"Request took longer than {self.timeout} seconds",
                    "timeout": self.timeout
                }
            )
        except Exception as e:
            logger.error(f"Request error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e)
                }
            )


class CameraTimeoutMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for camera operations with longer timeouts."""
    
    def __init__(self, app, camera_timeout: int = 60):
        super().__init__(app)
        self.camera_timeout = camera_timeout
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle camera requests with extended timeout."""
        # Check if this is a camera-related endpoint
        is_camera_request = (
            "/api/v1/cameras" in str(request.url.path) or
            "/stream" in str(request.url.path) or
            "/frames" in str(request.url.path)
        )
        
        timeout = self.camera_timeout if is_camera_request else 30
        start_time = time.time()
        
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            if is_camera_request and process_time > 10.0:
                logger.warning(
                    f"Slow camera request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s"
                )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(
                f"Camera request timeout: {request.method} {request.url.path} "
                f"exceeded {timeout}s"
            )
            return JSONResponse(
                status_code=408,
                content={
                    "error": "Camera request timeout",
                    "message": f"Camera operation took longer than {timeout} seconds",
                    "timeout": timeout,
                    "suggestion": "Check camera connectivity and network"
                }
            )
        except Exception as e:
            logger.error(f"Camera request error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Camera operation failed",
                    "message": str(e)
                }
            )
