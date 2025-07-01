import asyncio
import json
import base64
import time
import logging
from typing import Dict, Set
import cv2
from fastapi import WebSocket, WebSocketDisconnect
from camera_service import cameras, detect_motion_in_frame
from activity_detection import analyze_camera_activity

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for camera streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "camera_streams": set(),
            "motion_detection": set(),
            "system_status": set()
        }
        self.streaming_tasks: Dict[int, asyncio.Task] = {}
        self.motion_tasks: Dict[int, asyncio.Task] = {}
        
    async def connect(self, websocket: WebSocket, connection_type: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if connection_type in self.active_connections:
            self.active_connections[connection_type].add(websocket)
            logger.info(f"New {connection_type} connection: {len(self.active_connections[connection_type])} total")

    def disconnect(self, websocket: WebSocket, connection_type: str):
        """Disconnect a WebSocket client."""
        if connection_type in self.active_connections:
            self.active_connections[connection_type].discard(websocket)
            logger.info(f"Disconnected {connection_type}: {len(self.active_connections[connection_type])} remaining")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_type(self, message: dict, connection_type: str):
        """Broadcast a message to all clients of a specific type."""
        if connection_type not in self.active_connections:
            return
            
        disconnected = set()
        for connection in self.active_connections[connection_type]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_type}: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections[connection_type].discard(conn)

    async def start_camera_streaming(self, camera_id: int, fps: int = 10, max_width: int = 1280, quality: int = 85):
        """Start streaming from a specific camera with configurable resolution and quality."""
        if camera_id in self.streaming_tasks:
            return  # Already streaming
        
        self.streaming_tasks[camera_id] = asyncio.create_task(
            self._stream_camera_frames(camera_id, fps, max_width, quality)
        )
        logger.info(f"Started streaming camera {camera_id} at {fps} FPS, max width {max_width}px, quality {quality}%")

    async def stop_camera_streaming(self, camera_id: int):
        """Stop streaming from a specific camera."""
        if camera_id in self.streaming_tasks:
            self.streaming_tasks[camera_id].cancel()
            del self.streaming_tasks[camera_id]
            logger.info(f"Stopped streaming camera {camera_id}")

    async def start_motion_detection(self, camera_id: int, interval: float = 3.0):
        """Start motion detection for a specific camera (now uses suspicious activity detection)."""
        await self.start_suspicious_activity_detection(camera_id, interval)

    async def stop_motion_detection(self, camera_id: int):
        """Stop motion detection for a specific camera."""
        await self.stop_suspicious_activity_detection(camera_id)

    async def start_suspicious_activity_detection(self, camera_id: int, interval: float = 3.0):
        """Start suspicious activity detection for a specific camera."""
        if camera_id in self.motion_tasks:
            return  # Already running
        
        self.motion_tasks[camera_id] = asyncio.create_task(
            self._detect_suspicious_activity_loop(camera_id, interval)
        )
        logger.info(f"Started suspicious activity detection for camera {camera_id}")

    async def stop_suspicious_activity_detection(self, camera_id: int):
        """Stop suspicious activity detection for a specific camera."""
        if camera_id in self.motion_tasks:
            self.motion_tasks[camera_id].cancel()
            del self.motion_tasks[camera_id]
            logger.info(f"Stopped suspicious activity detection for camera {camera_id}")

    async def _stream_camera_frames(self, camera_id: int, fps: int, max_width: int = 1280, quality: int = 85):
        """Stream frames from a camera at specified FPS with configurable resolution and quality."""
        interval = 1.0 / fps
        
        while True:
            try:
                if not self.active_connections["camera_streams"]:
                    await asyncio.sleep(1)  # No clients, wait
                    continue
                
                # Get frame from camera
                frame = None
                if camera_id in cameras:
                    frame = cameras[camera_id].get_current_frame()
                    if frame is None:
                        frame = cameras[camera_id].capture_single_frame()
                
                if frame is not None:
                    # Resize frame if requested (0 means original size)
                    if max_width > 0:
                        height, width = frame.shape[:2]
                        if width > max_width:
                            scale = max_width / width
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                    
                    # Encode frame with specified quality
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Send to all connected clients
                    message = {
                        "type": "camera_frame",
                        "camera_id": camera_id,
                        "frame": frame_b64,
                        "timestamp": time.time(),
                        "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
                        "quality": quality,
                        "original_size": max_width == 0 or max_width >= 1280
                    }
                    
                    await self.broadcast_to_type(message, "camera_streams")
                    del buffer  # Clean up
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in camera {camera_id} streaming: {e}")
                await asyncio.sleep(interval)

    async def _detect_suspicious_activity_loop(self, camera_id: int, interval: float):
        """Continuously detect suspicious activities for a camera."""
        while True:
            try:
                if not self.active_connections["motion_detection"]:
                    await asyncio.sleep(interval)
                    continue
                
                # Get current frame for analysis
                frame = None
                if camera_id in cameras:
                    frame = cameras[camera_id].get_current_frame()
                    if frame is None:
                        frame = cameras[camera_id].capture_single_frame()
                
                if frame is not None:
                    # Analyze for suspicious activities instead of basic motion
                    suspicious_activities = analyze_camera_activity(camera_id, frame)
                    
                    if suspicious_activities:
                        # Send detailed suspicious activity information
                        for activity in suspicious_activities:
                            message = {
                                "type": "suspicious_activity_detected",
                                "camera_id": camera_id,
                                "activity_type": activity.activity_type.value,
                                "confidence": activity.confidence,
                                "threat_level": activity.threat_level,
                                "description": activity.description,
                                "timestamp": activity.timestamp,
                                "person_id": activity.person_id if hasattr(activity, 'person_id') else None,
                                "location": activity.location if hasattr(activity, 'location') else None
                            }
                            
                            await self.broadcast_to_type(message, "motion_detection")
                            logger.info(f"Suspicious activity detected on camera {camera_id}: {activity.activity_type.value} (confidence: {activity.confidence:.2f})")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in suspicious activity detection for camera {camera_id}: {e}")
                await asyncio.sleep(interval)

    async def broadcast_system_status(self):
        """Broadcast system status to connected clients."""
        try:
            from camera_service import get_all_cameras_info
            
            status = get_all_cameras_info()
            connected_count = sum(1 for info in status.values() if info.get("status") == "connected")
            
            message = {
                "type": "system_status",
                "total_cameras": len(status),
                "connected_cameras": connected_count,
                "cameras": status,
                "timestamp": time.time()
            }
            
            await self.broadcast_to_type(message, "system_status")
            
        except Exception as e:
            logger.error(f"Error broadcasting system status: {e}")

    async def cleanup(self):
        """Clean up all streaming tasks."""
        # Cancel all streaming tasks
        for task in self.streaming_tasks.values():
            task.cancel()
        
        # Cancel all motion detection tasks
        for task in self.motion_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.streaming_tasks:
            await asyncio.gather(*self.streaming_tasks.values(), return_exceptions=True)
        
        if self.motion_tasks:
            await asyncio.gather(*self.motion_tasks.values(), return_exceptions=True)
        
        self.streaming_tasks.clear()
        self.motion_tasks.clear()


# Global connection manager
manager = ConnectionManager()


async def handle_websocket_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages."""
    try:
        msg_type = message.get("type")
        
        if msg_type == "start_stream":
            camera_id = message.get("camera_id", 1)
            fps = message.get("fps", 10)
            max_width = message.get("max_width", 1280)  # 0 = original size
            quality = message.get("quality", 85)
            await manager.start_camera_streaming(camera_id, fps, max_width, quality)
            
            await manager.send_personal_message({
                "type": "stream_started",
                "camera_id": camera_id,
                "fps": fps,
                "max_width": max_width,
                "quality": quality
            }, websocket)
            
        elif msg_type == "stop_stream":
            camera_id = message.get("camera_id", 1)
            await manager.stop_camera_streaming(camera_id)
            
            await manager.send_personal_message({
                "type": "stream_stopped",
                "camera_id": camera_id
            }, websocket)
            
        elif msg_type == "start_motion_detection":
            camera_id = message.get("camera_id", 1)
            interval = message.get("interval", 3.0)  # Use 3 seconds for suspicious activity detection
            await manager.start_motion_detection(camera_id, interval)
            
            await manager.send_personal_message({
                "type": "motion_detection_started",
                "camera_id": camera_id,
                "interval": interval,
                "detection_type": "suspicious_activity"
            }, websocket)
            
        elif msg_type == "stop_motion_detection":
            camera_id = message.get("camera_id", 1)
            await manager.stop_motion_detection(camera_id)
            
            await manager.send_personal_message({
                "type": "motion_detection_stopped",
                "camera_id": camera_id
            }, websocket)
            
        elif msg_type == "get_status":
            await manager.broadcast_system_status()
            
        elif msg_type == "start_all_streams":
            fps = message.get("fps", 15)  # Default to 15 FPS for smooth streaming
            max_width = message.get("max_width", 1280)
            quality = message.get("quality", 85)
            for camera_id in cameras.keys():
                await manager.start_camera_streaming(camera_id, fps, max_width, quality)
            
            await manager.send_personal_message({
                "type": "all_streams_started",
                "fps": fps,
                "max_width": max_width,
                "quality": quality
            }, websocket)
            
        elif msg_type == "stop_all_streams":
            for camera_id in list(manager.streaming_tasks.keys()):
                await manager.stop_camera_streaming(camera_id)
            
            await manager.send_personal_message({
                "type": "all_streams_stopped"
            }, websocket)
            
        elif msg_type == "start_all_motion_detection":
            interval = message.get("interval", 3.0)
            for camera_id in cameras.keys():
                await manager.start_motion_detection(camera_id, interval)
            
            await manager.send_personal_message({
                "type": "all_motion_detection_started",
                "interval": interval,
                "detection_type": "suspicious_activity"
            }, websocket)
            
        elif msg_type == "stop_all_motion_detection":
            for camera_id in list(manager.motion_tasks.keys()):
                await manager.stop_motion_detection(camera_id)
            
            await manager.send_personal_message({
                "type": "all_motion_detection_stopped"
            }, websocket)
            
        else:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }, websocket)
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": str(e)
        }, websocket)
