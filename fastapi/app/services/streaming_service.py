"""
FastAPI Camera Service that integrates with Prisma backend database.
This service focuses only on camera streaming and computer vision,
while using the backend database for camera management.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from prisma import Prisma
from app.models.prisma_client import get_prisma

logger = logging.getLogger(__name__)

class CameraStreamingService:
    """
    Clean camera service focused only on streaming and computer vision.
    No user management - relies on backend database for camera configs.
    """
    
    def __init__(self):
        self.active_streams: Dict[int, Any] = {}
        self.stream_locks: Dict[int, asyncio.Lock] = {}
    
    async def get_camera_config(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """Get camera configuration from Prisma database."""
        try:
            prisma = await get_prisma()
            camera = await prisma.camera.find_unique(
                where={"id": camera_id},
                include={
                    "company": True,
                    "adminUser": True
                }
            )
            
            if not camera or not camera.isActive:
                return None
            
            return {
                "id": camera.id,
                "name": camera.name,
                "rtsp_url": camera.rtspUrl,
                "username": camera.username,
                "password": camera.password,
                "resolution_width": camera.resolutionWidth,
                "resolution_height": camera.resolutionHeight,
                "fps": camera.fps,
                "enable_motion_detection": camera.enableMotionDetection,
                "enable_recording": camera.enableRecording,
                "company_id": camera.companyId,
                "location": camera.location
            }
        except Exception as e:
            logger.error(f"Error getting camera config {camera_id}: {e}")
            return None
    
    async def get_company_cameras(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all active cameras for a company."""
        try:
            prisma = await get_prisma()
            cameras = await prisma.camera.find_many(
                where={
                    "companyId": company_id,
                    "isActive": True
                },
                include={
                    "company": True
                }
            )
            
            return [
                {
                    "id": camera.id,
                    "name": camera.name,
                    "location": camera.location,
                    "is_online": camera.isOnline,
                    "rtsp_url": camera.rtspUrl,
                    "resolution_width": camera.resolutionWidth,
                    "resolution_height": camera.resolutionHeight,
                    "fps": camera.fps,
                    "enable_motion_detection": camera.enableMotionDetection
                }
                for camera in cameras
            ]
        except Exception as e:
            logger.error(f"Error getting company cameras {company_id}: {e}")
            return []
    
    async def update_camera_status(self, camera_id: int, is_online: bool):
        """Update camera online status in database."""
        try:
            prisma = await get_prisma()
            await prisma.camera.update(
                where={"id": camera_id},
                data={
                    "isOnline": is_online,
                    "lastConnectedAt": None if not is_online else None,
                    "lastHealthCheck": None
                }
            )
        except Exception as e:
            logger.error(f"Error updating camera status {camera_id}: {e}")
    
    async def initialize_camera(self, camera_id: int) -> bool:
        """Initialize camera stream from database config."""
        config = await self.get_camera_config(camera_id)
        if not config:
            logger.error(f"Camera {camera_id} not found or inactive")
            return False
        
        # Initialize camera stream with config
        try:
            # Your existing camera initialization logic here
            # using config['rtsp_url'], config['username'], config['password']
            
            # Update status in database
            await self.update_camera_status(camera_id, True)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize camera {camera_id}: {e}")
            await self.update_camera_status(camera_id, False)
            return False
    
    async def get_camera_frame(self, camera_id: int) -> Optional[str]:
        """Get current frame from camera (base64 encoded)."""
        # Your existing frame capture logic
        pass
    
    async def detect_motion(self, camera_id: int) -> Dict[str, Any]:
        """Detect motion in camera frame."""
        # Your existing motion detection logic
        pass
    
    async def record_activity(self, camera_id: int, trigger_type: str, metadata: Dict[str, Any] = None):
        """Record security activity to database."""
        try:
            prisma = await get_prisma()
            
            # Create recording entry
            recording = await prisma.recording.create(
                data={
                    "cameraId": camera_id,
                    "fileName": f"recording_{camera_id}_{int(asyncio.get_event_loop().time())}.mp4",
                    "filePath": f"/recordings/camera_{camera_id}/",
                    "fileSize": 0,  # Will be updated after recording
                    "duration": 60,  # Default duration
                    "startTime": None,  # Current time
                    "endTime": None,   # Will be set after recording
                    "triggerType": trigger_type.upper(),
                    "metadata": metadata or {}
                }
            )
            
            return recording.id
        except Exception as e:
            logger.error(f"Error creating recording entry: {e}")
            return None
    
    async def create_alert(self, camera_id: int, alert_type: str, severity: str, title: str, description: str = None, metadata: Dict[str, Any] = None):
        """Create security alert in database."""
        try:
            prisma = await get_prisma()
            
            alert = await prisma.alert.create(
                data={
                    "cameraId": camera_id,
                    "type": alert_type.upper(),
                    "severity": severity.upper(),
                    "title": title,
                    "description": description,
                    "metadata": metadata or {},
                    "isRead": False,
                    "isResolved": False
                }
            )
            
            return alert.id
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None

# Global service instance
_camera_service = None

async def get_camera_service() -> CameraStreamingService:
    """Get camera streaming service instance."""
    global _camera_service
    if _camera_service is None:
        _camera_service = CameraStreamingService()
    return _camera_service
