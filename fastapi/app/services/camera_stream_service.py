"""
Camera Streaming Service for FastAPI.
Focuses only on real-time streaming, computer vision, and WebSocket features.
All camera management is handled by the NestJS backend.
"""
import asyncio
import logging
import base64
import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.database.prisma_client import get_prisma

logger = logging.getLogger(__name__)

class CameraStreamService:
    """
    Clean camera streaming service that integrates with your backend database.
    
    Responsibilities:
    - Real-time camera streaming
    - Motion detection and computer vision
    - WebSocket video feeds
    - Recording triggers
    - Alert creation
    
    Does NOT handle:
    - User authentication (backend handles this)
    - Camera CRUD operations (backend handles this)
    - User management (backend handles this)
    """
    
    def __init__(self):
        self.active_streams: Dict[int, cv2.VideoCapture] = {}
        self.stream_locks: Dict[int, asyncio.Lock] = {}
        self.motion_detectors: Dict[int, cv2.BackgroundSubtractorMOG2] = {}
        self.executor = None
    
    async def initialize(self):
        """Initialize the service."""
        import concurrent.futures
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        logger.info("🎥 Camera streaming service initialized")
    
    async def get_camera_config(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """Get camera configuration from your backend database."""
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
                logger.warning(f"Camera {camera_id} not found or inactive")
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
                "location": camera.location,
                "quality": camera.quality
            }
        except Exception as e:
            logger.error(f"Error getting camera config {camera_id}: {e}")
            return None
    
    async def initialize_camera_stream(self, camera_id: int) -> bool:
        """Initialize camera stream from database configuration."""
        config = await self.get_camera_config(camera_id)
        if not config:
            return False
        
        try:
            # Initialize stream lock if not exists
            if camera_id not in self.stream_locks:
                self.stream_locks[camera_id] = asyncio.Lock()
            
            async with self.stream_locks[camera_id]:
                # Close existing stream if any
                if camera_id in self.active_streams:
                    self.active_streams[camera_id].release()
                    del self.active_streams[camera_id]
                
                # Create new stream
                rtsp_url = config["rtsp_url"]
                
                # Run in thread pool to avoid blocking
                def create_capture():
                    cap = cv2.VideoCapture(rtsp_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, config["fps"])
                    return cap
                
                loop = asyncio.get_event_loop()
                cap = await loop.run_in_executor(self.executor, create_capture)
                
                if cap.isOpened():
                    self.active_streams[camera_id] = cap
                    # Initialize motion detector
                    self.motion_detectors[camera_id] = cv2.createBackgroundSubtractorMOG2(
                        detectShadows=True,
                        varThreshold=50
                    )
                    
                    # Update camera status in database
                    await self.update_camera_status(camera_id, True)
                    logger.info(f"✅ Camera {camera_id} stream initialized")
                    return True
                else:
                    logger.error(f"❌ Failed to open camera {camera_id} stream")
                    await self.update_camera_status(camera_id, False)
                    return False
                    
        except Exception as e:
            logger.error(f"Error initializing camera {camera_id}: {e}")
            await self.update_camera_status(camera_id, False)
            return False
    
    async def get_camera_frame(self, camera_id: int) -> Optional[str]:
        """Get current frame from camera as base64 encoded image."""
        if camera_id not in self.active_streams:
            # Try to initialize if not active
            if not await self.initialize_camera_stream(camera_id):
                return None
        
        try:
            cap = self.active_streams[camera_id]
            
            def capture_frame():
                ret, frame = cap.read()
                if ret:
                    # Resize frame if needed
                    height, width = frame.shape[:2]
                    if width > 640:  # Resize for web streaming
                        scale = 640 / width
                        new_width = 640
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    # Encode as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    return base64.b64encode(buffer).decode()
                return None
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            frame_b64 = await loop.run_in_executor(self.executor, capture_frame)
            return frame_b64
            
        except Exception as e:
            logger.error(f"Error getting frame from camera {camera_id}: {e}")
            return None
    
    async def detect_motion(self, camera_id: int) -> Dict[str, Any]:
        """Detect motion in camera frame."""
        if camera_id not in self.active_streams or camera_id not in self.motion_detectors:
            return {"motion_detected": False, "error": "Camera not initialized"}
        
        try:
            cap = self.active_streams[camera_id]
            detector = self.motion_detectors[camera_id]
            
            def detect():
                ret, frame = cap.read()
                if not ret:
                    return {"motion_detected": False, "error": "Failed to read frame"}
                
                # Apply motion detection
                fg_mask = detector.apply(frame)
                
                # Count motion pixels
                motion_pixels = cv2.countNonZero(fg_mask)
                total_pixels = fg_mask.shape[0] * fg_mask.shape[1]
                motion_ratio = motion_pixels / total_pixels
                
                motion_detected = motion_ratio > 0.01  # 1% threshold
                
                if motion_detected:
                    # Draw motion areas
                    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for contour in contours:
                        if cv2.contourArea(contour) > 500:  # Filter small areas
                            x, y, w, h = cv2.boundingRect(contour)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # Encode annotated frame
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    annotated_frame = base64.b64encode(buffer).decode()
                else:
                    annotated_frame = None
                
                return {
                    "motion_detected": motion_detected,
                    "motion_ratio": motion_ratio,
                    "motion_pixels": motion_pixels,
                    "confidence": min(motion_ratio * 100, 100),
                    "annotated_frame": annotated_frame
                }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, detect)
            return result
            
        except Exception as e:
            logger.error(f"Error detecting motion in camera {camera_id}: {e}")
            return {"motion_detected": False, "error": str(e)}
    
    async def update_camera_status(self, camera_id: int, is_online: bool):
        """Update camera status in your backend database."""
        try:
            prisma = await get_prisma()
            await prisma.camera.update(
                where={"id": camera_id},
                data={
                    "isOnline": is_online,
                    "lastConnectedAt": datetime.now() if is_online else None,
                    "lastHealthCheck": datetime.now()
                }
            )
        except Exception as e:
            logger.error(f"Error updating camera status {camera_id}: {e}")
    
    async def create_alert(self, camera_id: int, alert_type: str, severity: str, title: str, description: str = None, metadata: Dict[str, Any] = None):
        """Create security alert in your backend database."""
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
            
            logger.info(f"📢 Alert created: {title} (ID: {alert.id})")
            return alert.id
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None
    
    async def start_recording(self, camera_id: int, trigger_type: str = "MANUAL", duration: int = 60, metadata: Dict[str, Any] = None):
        """Create recording entry in your backend database."""
        try:
            prisma = await get_prisma()
            
            recording = await prisma.recording.create(
                data={
                    "cameraId": camera_id,
                    "fileName": f"recording_{camera_id}_{int(datetime.now().timestamp())}.mp4",
                    "filePath": f"/recordings/camera_{camera_id}/",
                    "fileSize": 0,  # Will be updated after recording
                    "duration": duration,
                    "startTime": datetime.now(),
                    "endTime": datetime.now(),  # Will be updated
                    "triggerType": trigger_type.upper(),
                    "metadata": metadata or {}
                }
            )
            
            logger.info(f"📹 Recording started: {recording.fileName} (ID: {recording.id})")
            return recording.id
        except Exception as e:
            logger.error(f"Error creating recording entry: {e}")
            return None
    
    async def get_company_cameras(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all active cameras for a company from your backend database."""
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
                    "resolution": f"{camera.resolutionWidth}x{camera.resolutionHeight}",
                    "fps": camera.fps,
                    "motion_detection_enabled": camera.enableMotionDetection,
                    "recording_enabled": camera.enableRecording,
                    "last_connected": camera.lastConnectedAt.isoformat() if camera.lastConnectedAt else None
                }
                for camera in cameras
            ]
        except Exception as e:
            logger.error(f"Error getting company cameras {company_id}: {e}")
            return []
    
    async def cleanup_camera(self, camera_id: int):
        """Clean up camera resources."""
        try:
            if camera_id in self.active_streams:
                self.active_streams[camera_id].release()
                del self.active_streams[camera_id]
            
            if camera_id in self.motion_detectors:
                del self.motion_detectors[camera_id]
            
            if camera_id in self.stream_locks:
                del self.stream_locks[camera_id]
            
            logger.info(f"🧹 Camera {camera_id} resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up camera {camera_id}: {e}")
    
    async def cleanup_all(self):
        """Clean up all camera resources."""
        for camera_id in list(self.active_streams.keys()):
            await self.cleanup_camera(camera_id)
        
        if self.executor:
            self.executor.shutdown(wait=True)

# Global service instance
_camera_service = None

async def get_camera_service() -> CameraStreamService:
    """Get camera streaming service instance."""
    global _camera_service
    if _camera_service is None:
        _camera_service = CameraStreamService()
        await _camera_service.initialize()
    return _camera_service
