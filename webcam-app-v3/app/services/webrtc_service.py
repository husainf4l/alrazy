"""
Alternative streaming service - uses SSE instead of WebRTC to avoid av library issues.

Since aiortc requires the av library which causes segmentation faults on this system,
we use a simpler HTTP Server-Sent Events (SSE) approach that provides low-latency
frame streaming without av dependency.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import base64
from io import BytesIO

import cv2


logger = logging.getLogger(__name__)
@dataclass
class StreamSession:
    """Represents an active streaming session for a camera."""
    session_id: str
    camera_name: str
    rtsp_url: str
    created_at: str
    cap: Optional[cv2.VideoCapture] = None
    frame_count: int = 0
    is_active: bool = True


class StreamManager:
    """
    Manages video streaming sessions using HTTP SSE instead of WebRTC.
    Provides low-latency streaming without av library dependency.
    """
    
    def __init__(self):
        self.sessions: Dict[str, StreamSession] = {}
        self.camera_rtsp_urls: Dict[str, str] = {}
    
    def set_camera_url(self, camera_name: str, rtsp_url: str):
        """Register RTSP URL for a camera."""
        self.camera_rtsp_urls[camera_name] = rtsp_url
    
    async def create_session(self, session_id: str, camera_name: str) -> StreamSession:
        """Create a new streaming session for a camera."""
        
        if not camera_name in self.camera_rtsp_urls:
            raise ValueError(f"Camera not registered: {camera_name}")
        
        rtsp_url = self.camera_rtsp_urls[camera_name]
        
        # Initialize camera capture
        cap = cv2.VideoCapture(rtsp_url)
        
        # Set connection and read timeouts
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Single frame buffer
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {rtsp_url}")
        
        # Get stream properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Created stream session {session_id} for {camera_name}: {width}x{height} @ {fps}fps")
        
        # Create session
        session = StreamSession(
            session_id=session_id,
            camera_name=camera_name,
            rtsp_url=rtsp_url,
            created_at=datetime.now().isoformat(),
            cap=cap,
            frame_count=0,
            is_active=True
        )
        
        self.sessions[session_id] = session
        return session
    
    async def get_frame(self, session_id: str) -> Optional[bytes]:
        """Get next frame from session as JPEG bytes."""
        
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        try:
            ret, frame = session.cap.read()
            
            if not ret:
                logger.warning(f"Failed to read frame from {session.camera_name}")
                return None
            
            # Encode frame as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if not ret:
                logger.warning(f"Failed to encode frame for {session.camera_name}")
                return None
            
            session.frame_count += 1
            return jpeg.tobytes()
            
        except Exception as e:
            logger.error(f"Error getting frame from {session.camera_name}: {e}")
            return None
    
    async def get_frame_base64(self, session_id: str) -> Optional[str]:
        """Get next frame as base64-encoded JPEG for HTML5."""
        
        frame_bytes = await self.get_frame(session_id)
        
        if frame_bytes is None:
            return None
        
        try:
            b64 = base64.b64encode(frame_bytes).decode('utf-8')
            return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.error(f"Error encoding frame to base64: {e}")
            return None
    
    async def close_session(self, session_id: str) -> None:
        """Close a streaming session."""
        
        if session_id not in self.sessions:
            logger.warning(f"Session not found for closure: {session_id}")
            return
        
        session = self.sessions[session_id]
        
        try:
            if session.cap:
                session.cap.release()
            
            session.is_active = False
            del self.sessions[session_id]
            
            logger.info(f"Closed stream session {session_id} ({session.frame_count} frames)")
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
    
    async def close_all_sessions(self) -> None:
        """Close all active streaming sessions."""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        logger.info(f"Closed {len(session_ids)} streaming sessions")
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session."""
        
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "camera_name": session.camera_name,
            "created_at": session.created_at,
            "is_active": session.is_active,
            "frames_delivered": session.frame_count
        }


# Global manager instance
_stream_manager: Optional[StreamManager] = None


def get_webrtc_manager() -> StreamManager:
    """Get or create the global WebRTC-style streaming manager."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager


def init_webrtc_manager(
    camera_urls: Dict[str, str],
    ice_servers: Optional[List[str]] = None
) -> StreamManager:
    """
    Initialize the streaming manager with camera URLs.
    
    Args:
        camera_urls: Dictionary mapping camera names to RTSP URLs
        ice_servers: Ignored (for API compatibility with WebRTC)
    
    Returns:
        The initialized StreamManager instance
    """
    global _stream_manager
    _stream_manager = StreamManager()
    
    # Register all camera URLs
    for camera_name, rtsp_url in camera_urls.items():
        _stream_manager.set_camera_url(camera_name, rtsp_url)
        logger.info(f"Registered camera: {camera_name}")
    
    return _stream_manager
