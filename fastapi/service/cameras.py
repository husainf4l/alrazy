"""
Camera Service Module
Handles camera-related operations for the security camera system.
"""
from typing import List, Dict, Any, Optional
import httpx
import asyncio

# Import configuration
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
    class FallbackConfig:
        @staticmethod
        def get_api_base_url():
            return "http://localhost:4005"
        
        @staticmethod
        def get_auth_credentials():
            return ("husain", "tt55oo77")
    
    config = FallbackConfig()


import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class CameraService:
    """Standalone service for managing camera operations without external backend dependencies."""
    
    def __init__(self):
        self.cameras_db = {}  # In-memory camera database
        self.initialize_cameras()
    
    def initialize_cameras(self):
        """Initialize the in-memory camera database with test data."""
        test_cameras = self.get_test_cameras()
        for camera in test_cameras:
            self.cameras_db[camera["id"]] = camera
        logger.info(f"Initialized {len(self.cameras_db)} cameras in standalone mode")
    
    async def authenticate(self) -> Optional[str]:
        """Mock authentication for standalone mode - always returns success."""
        return "standalone_token"
    
    async def get_headers(self) -> Dict[str, str]:
        """Get headers for standalone mode."""
        return {"Content-Type": "application/json"}
    
    async def fetch_cameras_from_api(self) -> List[Dict[str, Any]]:
        """Return all cameras from in-memory database (standalone mode)."""
        print("🔍 Fetching cameras from standalone database...")
        cameras = list(self.cameras_db.values())
        print(f"✅ Successfully fetched {len(cameras)} cameras from standalone database")
        return cameras
    
    def get_test_cameras(self) -> List[Dict[str, Any]]:
        """Generate test camera data for standalone operation."""
        return [
            {
                "id": 1,
                "name": "Front Door Camera",
                "location": "Front Door",
                "description": "Main entrance security camera",
                "isActive": True,
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/102",  # Sub-stream for faster streaming
                "webrtcUrl": None,
                "status": "offline",
                "lastSeen": None,
                "features": {
                    "nightVision": True,
                    "motionDetection": True,
                    "audioRecording": False,
                    "panTilt": False,
                    "zoom": False
                },
                "settings": {
                    "resolution": "640x480",  # Lower resolution for faster streaming
                    "frameRate": 15,  # Lower frame rate
                    "quality": "medium"
                }
            },
            {
                "id": 2,
                "name": "Back Yard Camera",
                "location": "Back Yard", 
                "description": "Backyard area monitoring",
                "isActive": True,
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/202",  # Sub-stream for faster streaming
                "webrtcUrl": None,
                "status": "offline",
                "lastSeen": None,
                "features": {
                    "nightVision": True,
                    "motionDetection": True,
                    "audioRecording": False,
                    "panTilt": False,
                    "zoom": False
                },
                "settings": {
                    "resolution": "640x480",  # Lower resolution for faster streaming
                    "frameRate": 15,  # Lower frame rate
                    "quality": "medium"
                }
            },
            {
                "id": 3,
                "name": "Garage Camera",
                "location": "Garage",
                "description": "Garage area surveillance",
                "isActive": True,
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/302",  # Sub-stream for faster streaming
                "webrtcUrl": None,
                "status": "offline",
                "lastSeen": None,
                "features": {
                    "nightVision": False,
                    "motionDetection": True,
                    "audioRecording": True,
                    "panTilt": False,
                    "zoom": True
                },
                "settings": {
                    "resolution": "640x480",  # Lower resolution for faster streaming
                    "frameRate": 15,  # Lower frame rate
                    "quality": "medium"
                }
            },
            {
                "id": 4,
                "name": "Side Entrance Camera",
                "location": "Side Entrance",
                "description": "Side door monitoring camera",
                "isActive": True,
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/402",  # Sub-stream for faster streaming
                "webrtcUrl": None,
                "status": "offline",
                "lastSeen": None,
                "features": {
                    "nightVision": True,
                    "motionDetection": True,
                    "audioRecording": False,
                    "panTilt": True,
                    "zoom": False
                },
                "settings": {
                    "resolution": "640x480",  # Lower resolution for faster streaming
                    "frameRate": 15,  # Lower frame rate
                    "quality": "medium"
                }
            }
        ]
    
    async def get_camera_by_id(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """Get a single camera by ID from in-memory database."""
        camera = self.cameras_db.get(camera_id)
        if camera:
            print(f"✅ Successfully fetched camera {camera_id} from standalone database")
            return camera.copy()  # Return a copy to avoid modifications
        else:
            print(f"❌ Camera {camera_id} not found in standalone database")
            return None
    
    def update_camera_webrtc_url(self, camera_id: int, webrtc_url: str) -> bool:
        """Update camera's WebRTC URL in the in-memory database."""
        if camera_id in self.cameras_db:
            self.cameras_db[camera_id]["webrtcUrl"] = webrtc_url
            self.cameras_db[camera_id]["status"] = "online"
            print(f"✅ Successfully updated camera {camera_id} WebRTC URL in standalone database")
            return True
        else:
            print(f"❌ Failed to update camera {camera_id}: Camera not found in standalone database")
            return False
    
    def get_camera_rtsp_url(self, camera_id: int) -> Optional[str]:
        """Get RTSP URL for a camera from the standalone database."""
        camera = self.cameras_db.get(camera_id)
        if camera:
            return camera.get("rtspUrl")
        return None
    
    async def close(self):
        """Cleanup method for compatibility (no-op in standalone mode)."""
        pass

# Global camera service instance
camera_service = CameraService()
