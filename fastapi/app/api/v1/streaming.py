"""
Clean Camera API endpoints for FastAPI streaming service.
Focuses only on camera streaming, computer vision, and real-time features.
All camera management is handled by the NestJS backend.
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header
from app.services.streaming_service import get_camera_service, CameraStreamingService
from app.models.prisma_client import get_prisma

router = APIRouter(prefix="/cameras", tags=["camera-streaming"])

async def verify_company_access(company_id: int = Header(..., alias="x-company-id")):
    """Verify company access from header (set by your backend)."""
    if not company_id:
        raise HTTPException(status_code=401, detail="Company ID required")
    return company_id

@router.get("/stream/info/{camera_id}")
async def get_camera_stream_info(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Get camera stream information."""
    config = await service.get_camera_config(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Camera not found or inactive")
    
    if config["company_id"] != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "camera_id": camera_id,
        "name": config["name"],
        "location": config["location"],
        "resolution": f"{config['resolution_width']}x{config['resolution_height']}",
        "fps": config["fps"],
        "motion_detection_enabled": config["enable_motion_detection"],
        "recording_enabled": config["enable_recording"]
    }

@router.get("/stream/frame/{camera_id}")
async def get_camera_frame(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Get current frame from camera as base64."""
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    frame = await service.get_camera_frame(camera_id)
    if not frame:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    return {
        "success": True,
        "camera_id": camera_id,
        "frame": frame,
        "timestamp": time.time(),
        "format": "base64_jpeg"
    }

@router.post("/stream/initialize/{camera_id}")
async def initialize_camera_stream(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Initialize camera stream."""
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    success = await service.initialize_camera(camera_id)
    return {
        "success": success,
        "camera_id": camera_id,
        "message": f"Camera {camera_id} {'initialized successfully' if success else 'failed to initialize'}"
    }

@router.get("/stream/motion/{camera_id}")
async def detect_motion(
    camera_id: int,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Detect motion in camera feed."""
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    if not config["enable_motion_detection"]:
        raise HTTPException(status_code=403, detail="Motion detection disabled for this camera")
    
    result = await service.detect_motion(camera_id)
    
    # Create alert if motion detected
    if result.get("motion_detected"):
        await service.create_alert(
            camera_id=camera_id,
            alert_type="MOTION_DETECTED",
            severity="LOW",
            title=f"Motion detected in {config['name']}",
            description=f"Motion detected at {config['location']}",
            metadata={"confidence": result.get("confidence", 0.0)}
        )
    
    return result

@router.get("/company/{company_id}/cameras")
async def get_company_cameras(
    company_id: int,
    verified_company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Get all cameras for a company."""
    if company_id != verified_company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    cameras = await service.get_company_cameras(company_id)
    return {
        "company_id": company_id,
        "cameras": cameras,
        "total": len(cameras)
    }

@router.post("/stream/record/{camera_id}")
async def start_recording(
    camera_id: int,
    duration: int = 60,
    company_id: int = Depends(verify_company_access),
    service: CameraStreamingService = Depends(get_camera_service)
):
    """Start manual recording."""
    config = await service.get_camera_config(camera_id)
    if not config or config["company_id"] != company_id:
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    if not config["enable_recording"]:
        raise HTTPException(status_code=403, detail="Recording disabled for this camera")
    
    recording_id = await service.record_activity(
        camera_id=camera_id,
        trigger_type="MANUAL",
        metadata={"duration": duration, "manual_trigger": True}
    )
    
    return {
        "success": True,
        "recording_id": recording_id,
        "camera_id": camera_id,
        "duration": duration,
        "message": "Recording started"
    }
