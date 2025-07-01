"""
Camera API endpoints for the Al Razy Pharmacy Security System.
Fully async implementation following best practices.
"""
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.models.camera import (
    CameraInfo, CameraFrame, MotionDetectionResult,
    CameraInitRequest, CameraInitResponse,
    CameraListResponse, CameraFramesResponse
)
from app.core.dependencies import get_camera_service

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/info", response_model=Dict[str, Any])
async def get_all_cameras_info(camera_service=Depends(get_camera_service)):
    """Get RTSP camera stream information for all cameras."""
    try:
        all_info = await camera_service.get_all_cameras_info()
        available_cameras = camera_service.get_available_cameras()
        
        return {
            "cameras": all_info,
            "total_cameras": len(all_info),
            "available_camera_ids": available_cameras,
            "status": "operational"
        }
    except Exception as e:
        return {
            "cameras": {},
            "total_cameras": 0,
            "available_camera_ids": [],
            "status": "no_cameras_available",
            "message": "No cameras currently available. Use /cameras/initialize to connect cameras.",
            "error": str(e)
        }


@router.get("/info/{camera_id}", response_model=Dict[str, Any])
async def get_camera_info(camera_id: int, camera_service=Depends(get_camera_service)):
    """Get RTSP camera stream information for a specific camera."""
    try:
        info = await camera_service.get_camera_info(camera_id)
        return info
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting camera {camera_id} info: {str(e)}"
        )


@router.get("/frames", response_model=Dict[str, Any])
async def get_all_camera_frames(camera_service=Depends(get_camera_service)):
    """Get current frames from all cameras as base64 encoded images (concurrent)."""
    try:
        available_cameras = camera_service.get_available_cameras()
        
        if not available_cameras:
            return {
                "success": True,
                "cameras": {},
                "total_cameras": 0,
                "timestamp": time.time(),
                "message": "No cameras currently available"
            }
        
        # Get all frames concurrently
        frames_dict = await camera_service.get_all_camera_frames()
        
        results = {}
        for camera_id, frame_b64 in frames_dict.items():
            results[str(camera_id)] = {
                "success": bool(frame_b64),
                "camera_id": camera_id,
                "frame": frame_b64,
                "format": "base64_jpeg",
                "timestamp": time.time()
            }
        
        return {
            "success": True,
            "cameras": results,
            "total_cameras": len(available_cameras),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "cameras": {},
            "total_cameras": 0,
            "error": str(e),
            "message": "Error getting camera frames",
            "timestamp": time.time()
        }


@router.get("/frame/{camera_id}", response_model=Dict[str, Any])
async def get_camera_frame(camera_id: int, camera_service=Depends(get_camera_service)):
    """Get current frame from RTSP camera as base64 encoded image."""
    try:
        frame_b64 = await camera_service.get_camera_frame(camera_id)
        
        return {
            "success": bool(frame_b64),
            "camera_id": camera_id,
            "frame": frame_b64,
            "format": "base64_jpeg",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting camera {camera_id} frame: {str(e)}"
        )


@router.get("/motion/{camera_id}", response_model=Dict[str, Any])
async def detect_motion(camera_id: int, camera_service=Depends(get_camera_service)):
    """Detect motion in the current camera frame."""
    try:
        from app.services.async_camera_service import detect_motion_in_frame
        result = await detect_motion_in_frame(camera_id)
        return {
            "success": True,
            "camera_id": camera_id,
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error detecting motion on camera {camera_id}: {str(e)}"
        )


@router.get("/motion", response_model=Dict[str, Any])
async def detect_motion_all_cameras(camera_service=Depends(get_camera_service)):
    """Detect motion in all cameras concurrently."""
    try:
        results = await camera_service.detect_motion_all_cameras()
        return {
            "success": True,
            "cameras": results,
            "motion_summary": {
                camera_id: result.get("motion_detected", False) 
                for camera_id, result in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error detecting motion on all cameras: {str(e)}"
        )


@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_all_cameras(
    background_tasks: BackgroundTasks,
    camera_service=Depends(get_camera_service)
):
    """Initialize all cameras concurrently."""
    try:
        results = await camera_service.initialize_all_cameras()
        return {
            "message": "Camera initialization completed",
            "results": results,
            "summary": {
                "total": len(results),
                "connected": sum(1 for status in results.values() if status == "connected"),
                "failed": sum(1 for status in results.values() if status != "connected")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error initializing all cameras: {str(e)}"
        )


@router.post("/initialize/{camera_id}", response_model=Dict[str, Any])
async def initialize_camera(camera_id: int, camera_service=Depends(get_camera_service)):
    """Initialize a specific camera."""
    try:
        success = await camera_service.initialize_camera(camera_id)
        status = "connected" if success else "disconnected"
        message = f"Camera {camera_id} {'initialized successfully' if success else 'failed to initialize'}"
        
        return {
            "camera_id": camera_id,
            "status": status,
            "message": message,
            "success": success
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error initializing camera {camera_id}: {str(e)}"
        )


@router.get("/list", response_model=Dict[str, Any])
async def list_cameras(camera_service=Depends(get_camera_service)):
    """Get list of available cameras."""
    try:
        camera_ids = camera_service.get_available_cameras()
        status = "operational" if camera_ids else "no_cameras"
        message = None if camera_ids else "Cameras not initialized. Use /cameras/initialize to connect cameras."
        
        return {
            "available_cameras": camera_ids,
            "total_cameras": len(camera_ids),
            "status": status,
            "message": message
        }
    except Exception as e:
        return {
            "available_cameras": [],
            "total_cameras": 0,
            "status": "error",
            "message": str(e)
        }


@router.get("/test/{camera_id}", response_model=Dict[str, Any])
async def test_camera(camera_id: int, camera_service=Depends(get_camera_service)):
    """Test camera connection and capture a single frame."""
    try:
        # Use the async camera service for testing
        if camera_id not in camera_service.cameras:
            return {
                "success": False,
                "message": f"Camera {camera_id} not found in configuration"
            }
        
        camera = camera_service.cameras[camera_id]
        
        # Test connection
        connected = await camera.connect()
        if not connected:
            return {
                "success": False,
                "message": f"Could not connect to camera {camera_id}"
            }
        
        # Test frame capture
        frame = await camera.capture_single_frame()
        await camera.disconnect()  # Clean up test connection
        
        if frame is not None:
            return {
                "success": True,
                "message": "Camera test successful",
                "frame_shape": list(frame.shape),
                "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
            }
        else:
            return {
                "success": False,
                "message": "Could not read frame from camera"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Camera test failed: {str(e)}"
        }


@router.delete("/cleanup/{camera_id}")
async def cleanup_camera(camera_id: int, camera_service=Depends(get_camera_service)):
    """Cleanup specific camera resources."""
    try:
        await camera_service.cleanup_camera(camera_id)
        return {
            "success": True,
            "message": f"Camera {camera_id} resources cleaned up successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up camera {camera_id}: {str(e)}"
        )


@router.delete("/cleanup")
async def cleanup_all_cameras(camera_service=Depends(get_camera_service)):
    """Cleanup all camera resources."""
    try:
        await camera_service.cleanup_all()
        return {
            "success": True,
            "message": "All camera resources cleaned up successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up all cameras: {str(e)}"
        )
