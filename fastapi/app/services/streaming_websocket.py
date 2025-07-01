"""
WebSocket service for real-time camera streaming.
Provides live video feeds and real-time alerts.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.services.camera_stream_service import get_camera_service

logger = logging.getLogger(__name__)

class StreamingWebSocketManager:
    """
    Manages WebSocket connections for real-time camera streaming.
    """
    
    def __init__(self):
        # Active connections by company
        self.company_connections: Dict[int, Set[WebSocket]] = {}
        # Camera streams by connection
        self.connection_streams: Dict[WebSocket, Dict[str, Any]] = {}
        # Background tasks
        self.streaming_tasks: Dict[WebSocket, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, company_id: int):
        """Connect a WebSocket client."""
        await websocket.accept()
        
        # Add to company connections
        if company_id not in self.company_connections:
            self.company_connections[company_id] = set()
        self.company_connections[company_id].add(websocket)
        
        # Initialize connection data
        self.connection_streams[websocket] = {
            "company_id": company_id,
            "active_cameras": set(),
            "streaming": False
        }
        
        logger.info(f"📡 WebSocket connected for company {company_id}")
        
        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "company_id": company_id,
            "message": "Connected to camera streaming service"
        })
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        try:
            # Stop streaming task
            if websocket in self.streaming_tasks:
                self.streaming_tasks[websocket].cancel()
                del self.streaming_tasks[websocket]
            
            # Remove from company connections
            if websocket in self.connection_streams:
                company_id = self.connection_streams[websocket]["company_id"]
                if company_id in self.company_connections:
                    self.company_connections[company_id].discard(websocket)
                    if not self.company_connections[company_id]:
                        del self.company_connections[company_id]
                
                del self.connection_streams[websocket]
            
            logger.info("📡 WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def start_camera_stream(self, websocket: WebSocket, camera_id: int, fps: int = 10):
        """Start streaming frames from a camera."""
        if websocket not in self.connection_streams:
            await self.send_personal_message(websocket, {
                "type": "error",
                "message": "WebSocket not properly connected"
            })
            return
        
        # Verify camera access
        company_id = self.connection_streams[websocket]["company_id"]
        camera_service = await get_camera_service()
        config = await camera_service.get_camera_config(camera_id)
        
        if not config or config["company_id"] != company_id:
            await self.send_personal_message(websocket, {
                "type": "error",
                "camera_id": camera_id,
                "message": "Camera not found or access denied"
            })
            return
        
        # Initialize camera if not already done
        if not await camera_service.initialize_camera_stream(camera_id):
            await self.send_personal_message(websocket, {
                "type": "error",
                "camera_id": camera_id,
                "message": "Failed to initialize camera stream"
            })
            return
        
        # Start streaming task
        self.connection_streams[websocket]["active_cameras"].add(camera_id)
        self.connection_streams[websocket]["streaming"] = True
        
        # Cancel existing task if any
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
        
        # Start new streaming task
        self.streaming_tasks[websocket] = asyncio.create_task(
            self._stream_camera_frames(websocket, camera_id, fps, camera_service)
        )
        
        await self.send_personal_message(websocket, {
            "type": "stream_started",
            "camera_id": camera_id,
            "camera_name": config["name"],
            "fps": fps
        })
    
    async def _stream_camera_frames(self, websocket: WebSocket, camera_id: int, fps: int, camera_service):
        """Stream camera frames continuously."""
        frame_interval = 1.0 / fps
        
        try:
            while True:
                # Get frame
                frame = await camera_service.get_camera_frame(camera_id)
                
                if frame:
                    await self.send_personal_message(websocket, {
                        "type": "frame",
                        "camera_id": camera_id,
                        "frame": frame,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                else:
                    await self.send_personal_message(websocket, {
                        "type": "frame_error",
                        "camera_id": camera_id,
                        "message": "Failed to capture frame"
                    })
                
                # Wait for next frame
                await asyncio.sleep(frame_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for camera {camera_id}")
        except Exception as e:
            logger.error(f"Error in camera stream {camera_id}: {e}")

# Global WebSocket manager
_ws_manager = None

def get_websocket_manager() -> StreamingWebSocketManager:
    """Get WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = StreamingWebSocketManager()
    return _ws_manager
