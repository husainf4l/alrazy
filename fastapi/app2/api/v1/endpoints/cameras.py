"""
Camera API endpoints for the Al Razy Pharmacy Security System.
Fully async implementation following best practices.
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import (
    CameraInfo, CameraFrame, MotionDetectionResult,
    CameraInitRequest, CameraInitResponse,
    CameraListResponse, CameraFramesResponse,
    Camera, CameraCreate, CameraUpdate, CameraPublic, CameraTestResult
)
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_camera_service, get_current_active_user
from app.services.camera_crud_service import CameraCRUDService
from app.core.database import get_session

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


# Camera Management CRUD Endpoints
def get_camera_crud_service(session: AsyncSession = Depends(get_session)) -> CameraCRUDService:
    """Get camera CRUD service."""
    return CameraCRUDService(session)


@router.post("/manage", response_model=CameraPublic, status_code=201)
async def add_user_camera(
    camera_create: CameraCreate,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> CameraPublic:
    """Add a new camera for the current user."""
    try:
        # Create camera in database
        camera = await camera_service.create_camera(
            user_id=current_user.id,
            camera_create=camera_create,
            company_id=current_user.company_id
        )
        
        return CameraPublic(**camera.dict())
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to add camera: {str(e)}"
        )


@router.get("/manage", response_model=List[CameraPublic])
async def get_user_cameras(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> List[CameraPublic]:
    """Get all cameras for the current user."""
    cameras = await camera_service.get_user_cameras(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return [CameraPublic(**camera.dict()) for camera in cameras]


@router.get("/manage/{camera_id}", response_model=CameraPublic)
async def get_user_camera(
    camera_id: int,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> CameraPublic:
    """Get a specific camera by ID."""
    camera = await camera_service.get_camera(camera_id, current_user.id)
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return CameraPublic(**camera.dict())


@router.put("/manage/{camera_id}", response_model=CameraPublic)
async def update_user_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> CameraPublic:
    """Update a camera."""
    camera = await camera_service.update_camera(
        camera_id=camera_id,
        user_id=current_user.id,
        camera_update=camera_update
    )
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return CameraPublic(**camera.dict())


@router.delete("/manage/{camera_id}")
async def delete_user_camera(
    camera_id: int,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
):
    """Delete a camera."""
    success = await camera_service.delete_camera(camera_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {"message": "Camera deleted successfully", "camera_id": camera_id}


@router.post("/test-connection", response_model=CameraTestResult)
async def test_camera_connection(
    rtsp_url: str,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> CameraTestResult:
    """Test camera connection before adding it."""
    return await camera_service.test_camera_connection(rtsp_url)


@router.post("/manage/{camera_id}/test", response_model=CameraTestResult)
async def test_existing_camera(
    camera_id: int,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> CameraTestResult:
    """Test connection to an existing camera."""
    camera = await camera_service.get_camera(camera_id, current_user.id)
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    test_result = await camera_service.test_camera_connection(camera.rtsp_url)
    test_result.camera_id = camera_id
    
    return test_result


@router.get("/manage/stats/summary")
async def get_user_camera_stats(
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
):
    """Get camera statistics for the current user."""
    total_cameras = await camera_service.get_camera_count_by_user(current_user.id)
    active_cameras = await camera_service.get_active_cameras_by_user(current_user.id)
    
    return {
        "total_cameras": total_cameras,
        "active_cameras": len(active_cameras),
        "inactive_cameras": total_cameras - len(active_cameras),
        "camera_ids": [camera.id for camera in active_cameras],
        "user_id": current_user.id
    }


@router.post("/manage/{camera_id}/activate")
async def activate_user_camera(
    camera_id: int,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
):
    """Activate a camera."""
    camera_update = CameraUpdate(is_active=True)
    camera = await camera_service.update_camera(camera_id, current_user.id, camera_update)
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {"message": "Camera activated successfully", "camera_id": camera_id}


@router.post("/manage/{camera_id}/deactivate")
async def deactivate_user_camera(
    camera_id: int,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
):
    """Deactivate a camera."""
    camera_update = CameraUpdate(is_active=False)
    camera = await camera_service.update_camera(camera_id, current_user.id, camera_update)
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {"message": "Camera deactivated successfully", "camera_id": camera_id}


@router.post("/add-enterprise", response_model=Dict[str, Any])
async def add_enterprise_camera(
    camera_create: CameraCreate,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> Dict[str, Any]:
    """
    Enterprise camera addition with multi-user access and admin assignment.
    This endpoint supports all the advanced features for camera management.
    
    Features:
    - Camera link (RTSP URL)
    - Camera name and location
    - Multiple user IDs for access
    - Company ID assignment
    - Admin user ID for camera management
    - Automatic connection testing before saving
    """
    try:
        # Step 1: Validate required fields
        if not camera_create.rtsp_url:
            return {
                "success": False,
                "error": "RTSP URL is required",
                "field": "rtsp_url"
            }
        
        if not camera_create.name:
            return {
                "success": False,
                "error": "Camera name is required", 
                "field": "name"
            }
        
        # Step 2: Test camera connection first
        test_result = await camera_service.test_camera_connection(camera_create.rtsp_url)
        
        if not test_result.success:
            return {
                "success": False,
                "step": "connection_test",
                "message": "Camera connection failed - camera not added",
                "test_result": {
                    "rtsp_url": camera_create.rtsp_url,
                    "error": test_result.message,
                    "error_details": test_result.error_details
                },
                "recommendations": [
                    "Check if the RTSP URL is correct",
                    "Verify camera IP address and port", 
                    "Check username/password credentials",
                    "Ensure camera is online and accessible",
                    "Test the URL in VLC or another media player first"
                ]
            }
        
        # Step 3: Validate user access list
        user_ids = camera_create.user_ids or []
        if user_ids:
            # TODO: Add user validation logic here
            # You might want to check if all user IDs exist in the database
            pass
        
        # Step 4: Create camera with all features
        camera = await camera_service.create_camera(
            user_id=current_user.id,
            camera_create=camera_create,
            company_id=current_user.company_id
        )
        
        return {
            "success": True,
            "message": "Enterprise camera added successfully",
            "camera": {
                "id": camera.id,
                "name": camera.name,
                "rtsp_url": camera.rtsp_url,
                "location": camera.location,
                "is_active": camera.is_active,
                "admin_user_id": camera.admin_user_id,
                "user_id": camera.user_id,
                "company_id": camera.company_id,
                "created_at": camera.created_at.isoformat()
            },
            "access_info": {
                "primary_owner": current_user.id,
                "admin_user": camera.admin_user_id,
                "additional_users": user_ids,
                "company_id": current_user.company_id
            },
            "test_result": {
                "connection_successful": True,
                "resolution": test_result.resolution,
                "frame_shape": test_result.frame_shape
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "step": "unexpected_error",
            "message": f"Failed to add enterprise camera: {str(e)}",
            "error": str(e)
        }


@router.post("/add-with-test", response_model=Dict[str, Any])
async def add_camera_with_test(
    camera_create: CameraCreate,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> Dict[str, Any]:
    """
    Test camera connection and add to database only if successful.
    This is the recommended endpoint for adding cameras.
    """
    try:
        # Step 1: Test the camera connection first
        test_result = await camera_service.test_camera_connection(camera_create.rtsp_url)
        
        if not test_result.success:
            return {
                "success": False,
                "step": "connection_test",
                "message": "Camera connection failed - camera not added",
                "test_result": {
                    "rtsp_url": camera_create.rtsp_url,
                    "error": test_result.message,
                    "error_details": test_result.error_details
                },
                "recommendations": [
                    "Check if the RTSP URL is correct",
                    "Verify camera IP address and port",
                    "Check username/password credentials",
                    "Ensure camera is online and accessible",
                    "Test the URL in VLC or another media player first"
                ]
            }
        
        # Step 2: Connection successful, now save to database
        try:
            camera = await camera_service.create_camera(
                user_id=current_user.id,
                camera_create=camera_create,
                company_id=current_user.company_id
            )
            
            return {
                "success": True,
                "step": "camera_added",
                "message": "Camera tested successfully and added to your account",
                "camera": {
                    "id": camera.id,
                    "name": camera.name,
                    "rtsp_url": camera.rtsp_url,
                    "location": camera.location,
                    "is_active": camera.is_active,
                    "created_at": camera.created_at.isoformat()
                },
                "test_result": {
                    "resolution": test_result.resolution,
                    "frame_shape": test_result.frame_shape,
                    "connection_successful": True
                }
            }
            
        except Exception as db_error:
            return {
                "success": False,
                "step": "database_save",
                "message": "Camera connection works but failed to save to database",
                "test_result": {
                    "connection_successful": True,
                    "resolution": test_result.resolution
                },
                "error": str(db_error),
                "recommendation": "Camera connection is working. Please try again or contact support."
            }
            
    except Exception as e:
        return {
            "success": False,
            "step": "unexpected_error",
            "message": "Unexpected error occurred",
            "error": str(e),
            "recommendation": "Please check your request and try again."
        }


@router.post("/test-only")
async def test_camera_only(
    rtsp_url: str,
    current_user: User = Depends(get_current_active_user),
    camera_service: CameraCRUDService = Depends(get_camera_crud_service)
) -> Dict[str, Any]:
    """
    Test camera connection without saving to database.
    Use this to verify your camera settings before adding.
    """
    try:
        test_result = await camera_service.test_camera_connection(rtsp_url)
        
        if test_result.success:
            return {
                "success": True,
                "message": "Camera connection successful",
                "rtsp_url": rtsp_url,
                "test_details": {
                    "resolution": test_result.resolution,
                    "frame_shape": test_result.frame_shape,
                    "can_capture_frames": True
                },
                "next_step": "Use /cameras/add-with-test endpoint to add this camera to your account"
            }
        else:
            return {
                "success": False,
                "message": "Camera connection failed",
                "rtsp_url": rtsp_url,
                "error": test_result.message,
                "error_details": test_result.error_details,
                "troubleshooting": [
                    "Verify the RTSP URL format: rtsp://username:password@ip:port/path",
                    "Check if camera is online and accessible",
                    "Test credentials (username/password)",
                    "Try different ports (554, 8554, 1935)",
                    "Check firewall/network settings"
                ]
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": "Error testing camera connection",
            "error": str(e),
            "rtsp_url": rtsp_url
        }


@router.get("/templates")
async def get_camera_templates() -> Dict[str, Any]:
    """
    Get common camera RTSP URL templates and examples.
    Use this to help format your camera URLs correctly.
    """
    return {
        "common_templates": {
            "hikvision": {
                "template": "rtsp://username:password@ip:554/Streaming/Channels/101",
                "example": "rtsp://admin:password123@192.168.1.100:554/Streaming/Channels/101",
                "ports": [554, 8554]
            },
            "dahua": {
                "template": "rtsp://username:password@ip:554/cam/realmonitor?channel=1&subtype=0",
                "example": "rtsp://admin:password123@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0",
                "ports": [554, 8554]
            },
            "axis": {
                "template": "rtsp://username:password@ip:554/axis-media/media.amp",
                "example": "rtsp://admin:password123@192.168.1.102:554/axis-media/media.amp",
                "ports": [554, 8554]
            },
            "generic_rtsp": {
                "template": "rtsp://username:password@ip:port/stream",
                "example": "rtsp://admin:password123@192.168.1.103:554/stream",
                "ports": [554, 8554, 1935]
            },
            "no_auth": {
                "template": "rtsp://ip:port/stream",
                "example": "rtsp://192.168.1.104:554/stream",
                "ports": [554, 8554]
            }
        },
        "validation_tips": [
            "Always use the format: rtsp://username:password@ip:port/path",
            "Default RTSP port is usually 554",
            "Some cameras use port 8554 or 1935",
            "Test the URL in VLC player first: Media -> Open Network Stream",
            "Make sure camera is on the same network or accessible",
            "Check camera documentation for exact RTSP path"
        ],
        "troubleshooting": {
            "connection_refused": "Check IP address and port",
            "authentication_failed": "Verify username and password",
            "timeout": "Camera might be offline or network issue",
            "invalid_format": "Check RTSP URL format"
        }
    }


@router.post("/validate-url")
async def validate_rtsp_url(
    rtsp_url: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Validate RTSP URL format without testing connection.
    Quick validation before attempting connection test.
    """
    import re
    
    # Basic RTSP URL validation
    rtsp_pattern = r'^rtsp://'
    
    if not re.match(rtsp_pattern, rtsp_url):
        return {
            "valid": False,
            "error": "URL must start with 'rtsp://'",
            "provided_url": rtsp_url,
            "example": "rtsp://admin:password@192.168.1.100:554/stream"
        }
    
    # Check for basic components
    has_credentials = '@' in rtsp_url
    has_port = ':554' in rtsp_url or ':8554' in rtsp_url or ':1935' in rtsp_url
    
    warnings = []
    if not has_credentials:
        warnings.append("No credentials detected - this might be okay if camera doesn't require auth")
    if not has_port:
        warnings.append("No standard port detected - make sure port is specified")
    
    return {
        "valid": True,
        "provided_url": rtsp_url,
        "has_credentials": has_credentials,
        "has_standard_port": has_port,
        "warnings": warnings,
        "next_step": "Use /cameras/test-only to test the actual connection"
    }
