"""
Clean Camera Streaming API endpoints.
Focuses only on streaming, computer vision, and real-time features.
All camera management is handled by your NestJS backend.
"""
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from app.services.camera_stream_service import get_camera_service, CameraStreamService
from app.database.prisma_client import get_prisma

router = APIRouter(prefix="/stream", tags=["camera-streaming"])

async def verify_company_access(x_company_id: int = Header(..., description="Company ID from your frontend/backend")):
    """
    Verify company access from header.
    Your frontend should send this after authenticating with NestJS backend.
    """
    if not x_company_id or x_company_id <= 0:
        raise HTTPException(status_code=401, detail="Valid Company ID required in X-Company-Id header")
    return x_company_id

@router.get("/camera/{camera_id}/info")
async def get_camera_stream_info(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Get camera stream information for streaming purposes."""
    config = await service.get_camera_config(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Camera not found or inactive")
    
    # Verify camera belongs to the company
    if config["company_id"] != company_id:
        raise HTTPException(status_code=403, detail="Access denied - camera belongs to different company")
    
    return {
        "camera_id": camera_id,
        "name": config["name"],
        "location": config["location"],
        "resolution": f"{config['resolution_width']}x{config['resolution_height']}",
        "fps": config["fps"],
        "motion_detection_enabled": config["enable_motion_detection"],
        "recording_enabled": config["enable_recording"],
        "stream_status": "ready"
    }

@router.get("/camera/{camera_id}/frame")
async def get_camera_frame(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Get current frame from camera as base64 encoded image."""
    # Verify camera access
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    frame = await service.get_camera_frame(camera_id)
    if not frame:
        raise HTTPException(status_code=503, detail="Camera not available or failed to capture frame")
    
    return {
        "success": True,
        "camera_id": camera_id,
        "frame": frame,
        "timestamp": time.time(),
        "format": "base64_jpeg"
    }

@router.post("/camera/{camera_id}/initialize")
async def initialize_camera_stream(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Initialize camera stream for real-time video."""
    # Verify camera access
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    success = await service.initialize_camera_stream(camera_id)
    return {
        "success": success,
        "camera_id": camera_id,
        "message": f"Camera {camera_id} {'initialized successfully' if success else 'failed to initialize'}",
        "camera_name": config["name"]
    }

@router.get("/camera/{camera_id}/motion")
async def detect_motion(
    camera_id: int,
    create_alert: bool = Query(default=True, description="Whether to create alert if motion detected"),
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Detect motion in camera feed and optionally create alerts."""
    # Verify camera access
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    if not config["enable_motion_detection"]:
        raise HTTPException(status_code=403, detail="Motion detection disabled for this camera")
    
    result = await service.detect_motion(camera_id)
    
    # Create alert if motion detected and requested
    if result.get("motion_detected") and create_alert:
        alert_id = await service.create_alert(
            camera_id=camera_id,
            alert_type="MOTION_DETECTED",
            severity="LOW" if result.get("confidence", 0) < 50 else "MEDIUM",
            title=f"Motion detected in {config['name']}",
            description=f"Motion detected at {config['location']} with {result.get('confidence', 0):.1f}% confidence",
            metadata={
                "confidence": result.get("confidence", 0),
                "motion_ratio": result.get("motion_ratio", 0),
                "motion_pixels": result.get("motion_pixels", 0)
            }
        )
        result["alert_id"] = alert_id
    
    return {
        **result,
        "camera_id": camera_id,
        "camera_name": config["name"],
        "timestamp": time.time()
    }

@router.post("/camera/{camera_id}/record")
async def start_recording(
    camera_id: int,
    duration: int = Query(default=60, ge=10, le=300, description="Recording duration in seconds"),
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Start manual recording for a camera."""
    # Verify camera access
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    if not config["enable_recording"]:
        raise HTTPException(status_code=403, detail="Recording disabled for this camera")
    
    recording_id = await service.start_recording(
        camera_id=camera_id,
        trigger_type="MANUAL",
        duration=duration,
        metadata={
            "manual_trigger": True,
            "requested_duration": duration,
            "camera_name": config["name"],
            "location": config["location"]
        }
    )
    
    return {
        "success": True,
        "recording_id": recording_id,
        "camera_id": camera_id,
        "camera_name": config["name"],
        "duration": duration,
        "message": f"Recording started for {config['name']}"
    }

@router.get("/company/{company_id}/cameras")
async def get_company_cameras(
    company_id: int,
    verified_company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Get all cameras for a company (for streaming purposes)."""
    if company_id != verified_company_id:
        raise HTTPException(status_code=403, detail="Access denied - company ID mismatch")
    
    cameras = await service.get_company_cameras(company_id)
    return {
        "company_id": company_id,
        "cameras": cameras,
        "total": len(cameras),
        "streaming_service": "ready"
    }

@router.get("/camera/{camera_id}/status")
async def get_camera_status(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Get camera streaming status."""
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    # Check if stream is active
    is_streaming = camera_id in service.active_streams
    
    return {
        "camera_id": camera_id,
        "name": config["name"],
        "location": config["location"],
        "is_streaming": is_streaming,
        "motion_detection_enabled": config["enable_motion_detection"],
        "recording_enabled": config["enable_recording"],
        "status": "online" if is_streaming else "offline"
    }

@router.delete("/camera/{camera_id}/cleanup")
async def cleanup_camera(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamService = Depends(get_camera_service)
):
    """Clean up camera streaming resources."""
    # Verify camera access
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    await service.cleanup_camera(camera_id)
    return {
        "success": True,
        "camera_id": camera_id,
        "message": f"Camera {camera_id} resources cleaned up"
    }
