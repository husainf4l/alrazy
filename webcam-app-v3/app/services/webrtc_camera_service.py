"""
WebRTC Camera Service for streaming RTSP cameras using aiortc
Provides low-latency peer-to-peer streaming with best practices
"""
import asyncio
import cv2
import threading
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import aiortc - if fails, provide graceful fallback
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.contrib.media import MediaPlayer
    from av import VideoFrame
    AIORTC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"aiortc not available: {e}. WebRTC features will be limited.")
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    RTCSessionDescription = None
    VideoStreamTrack = None



class RTCVideoStreamTrack:
    """Placeholder video track when aiortc is not available"""
    def __init__(self, rtsp_url: str, camera_name: str):
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name


class RTCVideoStreamTrack_Real(VideoStreamTrack):
    """Custom video track that reads from RTSP camera (only when aiortc available)"""
    
    def __init__(self, rtsp_url: str, camera_name: str):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
        self.cap = None
        self.is_running = False
        self.frame_lock = threading.Lock()
        self.current_frame = None
        self.fps = 0
        self.frame_count = 0
        
    def connect(self) -> bool:
        """Connect to the RTSP camera"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if not self.cap.isOpened():
                logger.error(f"Failed to connect to {self.camera_name}")
                return False
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Start frame capture thread
            self.is_running = True
            thread = threading.Thread(target=self._capture_frames, daemon=True)
            thread.start()
            
            logger.info(f"Connected to {self.camera_name}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to {self.camera_name}: {e}")
            return False
    
    def _capture_frames(self):
        """Background thread that continuously captures frames"""
        import time
        last_time = time.time()
        
        while self.is_running and self.cap:
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.current_frame = frame
                    self.frame_count += 1
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - last_time >= 1.0:
                        self.fps = self.frame_count
                        self.frame_count = 0
                        last_time = current_time
                else:
                    logger.warning(f"Failed to read frame from {self.camera_name}")
                    break
            except Exception as e:
                logger.error(f"Error capturing frame from {self.camera_name}: {e}")
                break
    
    async def recv(self):
        """Receive the next video frame"""
        pts, time_base = await self.next_timestamp()
        
        with self.frame_lock:
            frame = self.current_frame
        
        if frame is None:
            # Return black frame if no frame available
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Resize if needed
        if frame.shape[0] != 480 or frame.shape[1] != 640:
            frame = cv2.resize(frame, (640, 480))
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create video frame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    def stop(self):
        """Stop capturing frames"""
        self.is_running = False
        if self.cap:
            self.cap.release()


class WebRTCCameraSession:
    """Manages a WebRTC peer connection with an RTSP camera"""
    
    def __init__(self, camera_name: str, rtsp_url: str, session_id: str):
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.session_id = session_id
        self.pc: Optional['RTCPeerConnection'] = None
        self.video_track: Optional['RTCVideoStreamTrack'] = None
        self.is_connected = False
        
    async def create_connection(self) -> 'RTCPeerConnection':
        """Create a new peer connection for this camera"""
        try:
            # Create peer connection
            self.pc = RTCPeerConnection()
            
            # Create and connect video track
            self.video_track = RTCVideoStreamTrack_Real(self.rtsp_url, self.camera_name)
            if not self.video_track.connect():
                logger.error(f"Failed to create video track for {self.camera_name}")
                return None
            
            # Add video track to peer connection
            self.pc.addTrack(self.video_track)
            
            # Handle connection state changes
            @self.pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state changed: {self.pc.connectionState}")
                self.is_connected = self.pc.connectionState == "connected"
            
            @self.pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state: {self.pc.iceConnectionState}")
            
            logger.info(f"Created WebRTC connection for {self.camera_name}")
            return self.pc
            
        except Exception as e:
            logger.error(f"Error creating WebRTC connection: {e}")
            return None
    
    async def handle_offer(self, offer: RTCSessionDescription) -> RTCSessionDescription:
        """Handle SDP offer from client"""
        try:
            await self.pc.setRemoteDescription(offer)
            
            # Create and set local description
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            logger.info(f"Created SDP answer for {self.camera_name}")
            return self.pc.localDescription
            
        except Exception as e:
            logger.error(f"Error handling offer: {e}")
            return None
    
    async def add_ice_candidate(self, candidate: Dict):
        """Add ICE candidate from client"""
        try:
            if self.pc:
                await self.pc.addIceCandidate(candidate)
                logger.debug(f"Added ICE candidate for {self.camera_name}")
        except Exception as e:
            logger.error(f"Error adding ICE candidate: {e}")
    
    async def close(self):
        """Close the peer connection"""
        try:
            if self.video_track:
                self.video_track.stop()
            if self.pc:
                await self.pc.close()
            self.is_connected = False
            logger.info(f"Closed WebRTC connection for {self.camera_name}")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


class WebRTCCameraManager:
    """Manages multiple WebRTC camera sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, WebRTCCameraSession] = {}
        self.lock = threading.Lock()
    
    async def create_session(self, session_id: str, camera_name: str, rtsp_url: str) -> Optional[RTCPeerConnection]:
        """Create a new WebRTC session for a camera"""
        try:
            with self.lock:
                # Check if session already exists
                if session_id in self.sessions:
                    logger.warning(f"Session {session_id} already exists")
                    await self.sessions[session_id].close()
                
                # Create new session
                session = WebRTCCameraSession(camera_name, rtsp_url, session_id)
                pc = await session.create_connection()
                
                if pc:
                    self.sessions[session_id] = session
                    logger.info(f"Created WebRTC session {session_id} for {camera_name}")
                    return pc
                
                return None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    async def handle_offer(self, session_id: str, offer: RTCSessionDescription) -> Optional[RTCSessionDescription]:
        """Handle SDP offer for a session"""
        with self.lock:
            if session_id not in self.sessions:
                logger.error(f"Session {session_id} not found")
                return None
            
            session = self.sessions[session_id]
        
        return await session.handle_offer(offer)
    
    async def add_ice_candidate(self, session_id: str, candidate: Dict):
        """Add ICE candidate for a session"""
        with self.lock:
            if session_id not in self.sessions:
                logger.error(f"Session {session_id} not found")
                return
            
            session = self.sessions[session_id]
        
        await session.add_ice_candidate(candidate)
    
    async def close_session(self, session_id: str):
        """Close a specific session"""
        with self.lock:
            if session_id in self.sessions:
                await self.sessions[session_id].close()
                del self.sessions[session_id]
                logger.info(f"Closed WebRTC session {session_id}")
    
    async def close_all(self):
        """Close all sessions"""
        with self.lock:
            sessions_to_close = list(self.sessions.values())
        
        for session in sessions_to_close:
            await session.close()
        
        with self.lock:
            self.sessions.clear()
        
        logger.info("Closed all WebRTC sessions")
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        with self.lock:
            return len(self.sessions)


# Global manager instance
_webrtc_manager = None


async def get_webrtc_manager() -> WebRTCCameraManager:
    """Get or create the global WebRTC camera manager"""
    global _webrtc_manager
    if _webrtc_manager is None:
        _webrtc_manager = WebRTCCameraManager()
    return _webrtc_manager


# Import numpy at end to avoid circular imports
import numpy as np
