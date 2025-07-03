"""
Video Streaming Service Module
Handles video processing with OpenCV and WebRTC streaming.
"""
import asyncio
import cv2
import numpy as np
import logging
import fractions
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any
from aiortc import VideoStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer
from concurrent.futures import ThreadPoolExecutor
import json
from av import VideoFrame
import threading
import time


logger = logging.getLogger(__name__)


class RTSPVideoTrack(VideoStreamTrack):
    """Custom video track that reads from RTSP stream using OpenCV and analyzes frames."""
    
    def __init__(self, rtsp_url: str, enable_analysis: bool = True, executor: ThreadPoolExecutor = None):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.cap = None
        self._frame_rate = 30  # Target frame rate
        self._frame_time = 1.0 / self._frame_rate
        self._timestamp = 0
        self._start_time = None
        # Initialize required attributes for VideoStreamTrack
        self._start = None
        
        # Thread pool for blocking operations
        self.executor = executor or ThreadPoolExecutor(max_workers=2, thread_name_prefix="rtsp_video")
        
        # Connection state
        self._connection_lock = asyncio.Lock()
        self._is_connected = False
        
        # Analysis settings
        self.enable_analysis = enable_analysis
        self.analysis_frame_count = 0
        self.last_analysis_results = {}
        
        # Initialize OpenCV analysis components
        if self.enable_analysis:
            self._init_analysis_models()
    
    def _init_analysis_models(self):
        """Initialize OpenCV analysis models."""
        try:
            # Initialize background subtractor for motion detection
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                detectShadows=True, varThreshold=50
            )
            
            # Initialize HOG descriptor for person detection
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Initialize face cascade classifier
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Analysis counters
            self.motion_detected = False
            self.people_count = 0
            self.faces_count = 0
            
            logger.info("OpenCV analysis models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize analysis models: {e}")
            self.enable_analysis = False
        
    async def recv(self):
        """Receive the next video frame with OpenCV analysis."""
        try:
            # Check if we have too many consecutive failures
            if hasattr(self, '_consecutive_failures') and self._consecutive_failures >= 5:
                logger.warning("Too many consecutive failures, switching to test pattern")
                return self._generate_test_frame()
            
            if self.cap is None or not await self._check_connection():
                try:
                    await self._connect()
                except Exception as e:
                    logger.error(f"Connection failed: {e}")
                    self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
                    return self._generate_test_frame()
            
            # Read frame in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            frame_data = await loop.run_in_executor(
                self.executor,
                self._read_frame_sync
            )
            
            if frame_data is None:
                # Try to reconnect once
                try:
                    await self._connect()
                    frame_data = await loop.run_in_executor(
                        self.executor,
                        self._read_frame_sync
                    )
                    if frame_data is None:
                        raise Exception("Failed to read frame after reconnection")
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                    self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
                    return self._generate_test_frame()
            
            # Reset failure counter on success
            self._consecutive_failures = 0
            
            # Perform OpenCV analysis on the frame (in BGR format) - run in thread pool
            if self.enable_analysis:
                frame_data = await loop.run_in_executor(
                    self.executor,
                    self._analyze_frame,
                    frame_data
                )
            
            # Convert BGR to RGB for WebRTC - run in thread pool
            frame_rgb = await loop.run_in_executor(
                self.executor,
                cv2.cvtColor,
                frame_data,
                cv2.COLOR_BGR2RGB
            )
            
            # Create video frame
            av_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            
            # Set timestamp manually using a simple increment
            av_frame.pts = self._timestamp
            av_frame.time_base = fractions.Fraction(1, self._frame_rate)
            
            self._timestamp += 1
            
            return av_frame
            
        except Exception as e:
            logger.error(f"Error in recv(): {e}")
            self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
            return self._generate_test_frame()
    
    def _generate_test_frame(self):
        """Generate a test pattern frame when camera is unavailable."""
        # Create a test pattern with camera info
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some color and pattern
        test_frame[100:380, 100:540] = (50, 50, 100)  # Dark blue background
        
        # Add text overlay
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(test_frame, "Camera Unavailable", (180, 220), font, 1, (255, 255, 255), 2)
        cv2.putText(test_frame, f"Stream: {getattr(self, 'rtsp_url', 'Unknown')}", (120, 260), font, 0.5, (200, 200, 200), 1)
        cv2.putText(test_frame, "Check camera connection", (160, 290), font, 0.6, (255, 255, 0), 1)
        
        # Convert to RGB and create VideoFrame
        test_frame_rgb = cv2.cvtColor(test_frame, cv2.COLOR_BGR2RGB)
        av_frame = VideoFrame.from_ndarray(test_frame_rgb, format="rgb24")
        
        # Set timestamp
        av_frame.pts = self._timestamp
        av_frame.time_base = fractions.Fraction(1, self._frame_rate)
        self._timestamp += 1
        
        return av_frame
    
    def _analyze_frame(self, frame):
        """Analyze frame with OpenCV and overlay results."""
        try:
            self.analysis_frame_count += 1
            analyzed_frame = frame.copy()
            
            # Only analyze every 5th frame for performance
            if self.analysis_frame_count % 5 == 0:
                # Motion detection
                motion_mask = self.background_subtractor.apply(frame)
                motion_pixels = cv2.countNonZero(motion_mask)
                self.motion_detected = motion_pixels > 1000  # Threshold for motion
                
                # Person detection (every 10th frame for performance)
                if self.analysis_frame_count % 10 == 0:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect people using HOG
                    people, _ = self.hog.detectMultiScale(gray, winStride=(8, 8), padding=(32, 32), scale=1.05)
                    self.people_count = len(people)
                    
                    # Draw rectangles around detected people
                    for (x, y, w, h) in people:
                        cv2.rectangle(analyzed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(analyzed_frame, 'Person', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Face detection
                    faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                    self.faces_count = len(faces)
                    
                    # Draw rectangles around detected faces
                    for (x, y, w, h) in faces:
                        cv2.rectangle(analyzed_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                        cv2.putText(analyzed_frame, 'Face', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # Update analysis results
                self.last_analysis_results = {
                    "motion_detected": self.motion_detected,
                    "people_count": self.people_count,
                    "faces_count": self.faces_count,
                    "timestamp": self.analysis_frame_count
                }
            
            # Draw analysis overlay
            self._draw_analysis_overlay(analyzed_frame)
            
            return analyzed_frame
            
        except Exception as e:
            logger.error(f"Error in frame analysis: {e}")
            return frame
    
    def _draw_analysis_overlay(self, frame):
        """Draw analysis information overlay on frame."""
        try:
            # Create overlay background
            overlay = frame.copy()
            h, w = frame.shape[:2]
            
            # Draw semi-transparent overlay for text background
            cv2.rectangle(overlay, (10, 10), (300, 120), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Draw analysis information
            y_offset = 30
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            color = (255, 255, 255)
            thickness = 1
            
            # Motion status
            motion_text = f"Motion: {'DETECTED' if self.motion_detected else 'None'}"
            motion_color = (0, 255, 0) if self.motion_detected else (128, 128, 128)
            cv2.putText(frame, motion_text, (15, y_offset), font, font_scale, motion_color, thickness)
            y_offset += 25
            
            # People count
            people_text = f"People: {self.people_count}"
            people_color = (0, 255, 0) if self.people_count > 0 else (128, 128, 128)
            cv2.putText(frame, people_text, (15, y_offset), font, font_scale, people_color, thickness)
            y_offset += 25
            
            # Face count
            faces_text = f"Faces: {self.faces_count}"
            faces_color = (255, 0, 0) if self.faces_count > 0 else (128, 128, 128)
            cv2.putText(frame, faces_text, (15, y_offset), font, font_scale, faces_color, thickness)
            y_offset += 25
            
            # Frame counter
            frame_text = f"Frame: {self.analysis_frame_count}"
            cv2.putText(frame, frame_text, (15, y_offset), font, font_scale, color, thickness)
            
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}")
    
    def get_analysis_results(self):
        """Get current analysis results."""
        return self.last_analysis_results
    
    def _read_frame_sync(self):
        """Read frame synchronously (runs in thread pool)."""
        if not self.cap or not self.cap.isOpened():
            return None
        try:
            ret, frame = self.cap.read()
            return frame if ret else None
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return None
    
    async def _check_connection(self):
        """Check if connection is still valid."""
        if not self.cap:
            return False
        try:
            loop = asyncio.get_event_loop()
            is_opened = await loop.run_in_executor(
                self.executor,
                lambda: self.cap.isOpened()
            )
            return is_opened
        except Exception:
            return False
    
    async def _connect(self):
        """Connect to RTSP stream with authentication."""
        async with self._connection_lock:
            try:
                # Release any existing connection first (in thread pool)
                if self.cap:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self.executor, self.cap.release)
                    self.cap = None
                
                # Try to add authentication if missing
                authenticated_url = self._add_rtsp_auth(self.rtsp_url)
                
                logger.info(f"Attempting to connect to RTSP stream: {authenticated_url}")
                
                # Create connection in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self.cap = await loop.run_in_executor(
                    self.executor,
                    self._create_video_capture,
                    authenticated_url
                )
                
                if not self.cap or not await loop.run_in_executor(self.executor, self.cap.isOpened):
                    raise Exception(f"Failed to open RTSP stream: {authenticated_url}")
                    
                # Test reading a frame to ensure the stream is working (in thread pool)
                test_frame = await loop.run_in_executor(
                    self.executor,
                    self._test_frame_read
                )
                
                if test_frame is None:
                    raise Exception(f"Failed to read initial frame from RTSP stream: {authenticated_url}")
                    
                logger.info(f"Successfully connected to RTSP stream, frame size: {test_frame.shape}")
                self._is_connected = True
                
            except Exception as e:
                logger.error(f"Failed to connect to RTSP stream: {e}")
                if self.cap:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self.executor, self.cap.release)
                    self.cap = None
                self._is_connected = False
                raise
    
    def _create_video_capture(self, url: str) -> cv2.VideoCapture:
        """Create video capture object (runs in thread pool)."""
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize delay
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 second timeout
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5 second read timeout
        return cap
    
    def _test_frame_read(self):
        """Test frame reading (runs in thread pool)."""
        if not self.cap or not self.cap.isOpened():
            return None
        try:
            ret, frame = self.cap.read()
            return frame if ret else None
        except Exception as e:
            logger.error(f"Error testing frame read: {e}")
            return None
    
    def _add_rtsp_auth(self, rtsp_url: str) -> str:
        """Add authentication to RTSP URL if missing."""
        # Default credentials - should be configurable
        default_username = "admin"
        default_password = "tt55oo77"
        
        # Check if URL already has authentication
        if "@" in rtsp_url:
            return rtsp_url
            
        # Add authentication
        if rtsp_url.startswith("rtsp://"):
            return f"rtsp://{default_username}:{default_password}@{rtsp_url[7:]}"
        
        return rtsp_url
    
    def stop(self):
        """Stop the video track and release resources."""
        async def _async_stop():
            if self.cap:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.cap.release)
                self.cap = None
        
        # If we're in an async context, schedule the cleanup
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(_async_stop())
        except RuntimeError:
            # Not in async context, release synchronously
            if self.cap:
                self.cap.release()
                self.cap = None


class VideoStreamingService:
    """Service for handling video streaming with WebRTC."""
    
    def __init__(self):
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.video_tracks: Dict[str, RTSPVideoTrack] = {}
        self.persistent_streams: Dict[str, Dict[str, Any]] = {}  # Store persistent WebRTC streams
        self.base_url = "http://localhost:8000"  # FastAPI server URL
    
    async def create_webrtc_offer(self, camera_id: str, rtsp_url: str) -> Dict[str, Any]:
        """Create WebRTC offer for a camera stream."""
        try:
            logger.info(f"Creating WebRTC offer for camera {camera_id} with RTSP URL: {rtsp_url}")
            
            # Clean up any closed connections first
            await self._cleanup_closed_connections()
            
            # Create peer connection
            pc = RTCPeerConnection()
            
            # Create session ID first
            session_id = f"{camera_id}_{len(self.peer_connections)}"
            
            # Add connection state change logging with session_id
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state is {pc.connectionState} for session {session_id}")
                if pc.connectionState in ["failed", "closed"]:
                    await self._cleanup_session(session_id)
            
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state is {pc.iceConnectionState} for session {session_id}")
            
            @pc.on("icegatheringstatechange")
            async def on_icegatheringstatechange():
                logger.info(f"ICE gathering state is {pc.iceGatheringState} for session {session_id}")
            
            # Create video track from RTSP stream with OpenCV analysis enabled
            video_track = RTSPVideoTrack(rtsp_url, enable_analysis=True)
            pc.addTrack(video_track)
            
            # Store references
            self.peer_connections[session_id] = pc
            self.video_tracks[session_id] = video_track
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            logger.info(f"Created WebRTC offer for camera {camera_id}, session {session_id}")
            
            return {
                "session_id": session_id,
                "offer": {
                    "type": offer.type,
                    "sdp": offer.sdp
                },
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to create WebRTC offer for camera {camera_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_webrtc_answer(self, session_id: str, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WebRTC answer from client."""
        try:
            if session_id not in self.peer_connections:
                return {"success": False, "error": "Session not found"}
            
            pc = self.peer_connections[session_id]
            answer = RTCSessionDescription(
                sdp=answer_data["sdp"],
                type=answer_data["type"]
            )
            
            await pc.setRemoteDescription(answer)
            
            logger.info(f"Successfully set remote description for session {session_id}")
            return {"success": True, "message": "Answer processed successfully"}
            
        except Exception as e:
            logger.error(f"Failed to handle WebRTC answer for session {session_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def handle_ice_candidate(self, session_id: str, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming ICE candidate from client."""
        try:
            if session_id not in self.peer_connections:
                return {"success": False, "error": "Session not found"}
            
            pc = self.peer_connections[session_id]
            
            # Handle case where candidate_data might be a string or dict
            if isinstance(candidate_data, str):
                # If it's a string, try to parse it as JSON
                try:
                    import json
                    candidate_data = json.loads(candidate_data)
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid candidate data format"}
            
            # Ensure candidate_data is a dictionary
            if not isinstance(candidate_data, dict):
                return {"success": False, "error": "Candidate data must be a dictionary"}
            
            # Extract the actual candidate data (it's nested under 'candidate' key)
            candidate_info = candidate_data.get("candidate", candidate_data)
            
            # Handle case where candidate_info might also be a string
            if isinstance(candidate_info, str):
                try:
                    candidate_info = json.loads(candidate_info)
                except json.JSONDecodeError:
                    # If it's not JSON, treat it as the candidate string directly
                    candidate_info = {"candidate": candidate_info}
            
            # Parse the candidate string to extract individual components
            candidate_string = ""
            if isinstance(candidate_info, dict):
                candidate_string = candidate_info.get("candidate", "")
            elif isinstance(candidate_info, str):
                candidate_string = candidate_info
                
            if not candidate_string:
                return {"success": False, "error": "No candidate string found"}
            
            # Parse candidate string format: "candidate:foundation component protocol priority ip port typ type ..."
            parts = candidate_string.split()
            if len(parts) < 8:
                return {"success": False, "error": "Invalid candidate format"}
            
            try:
                foundation = parts[0].split(":", 1)[1]  # Remove "candidate:" prefix
                component = int(parts[1])
                protocol = parts[2].lower()
                priority = int(parts[3])
                ip = parts[4]
                port = int(parts[5])
                candidate_type = parts[7]  # After "typ"
                
                # Handle related address and port for relay/reflexive candidates
                related_address = None
                related_port = None
                if "raddr" in parts:
                    raddr_idx = parts.index("raddr")
                    if raddr_idx + 1 < len(parts):
                        related_address = parts[raddr_idx + 1]
                if "rport" in parts:
                    rport_idx = parts.index("rport")
                    if rport_idx + 1 < len(parts):
                        related_port = int(parts[rport_idx + 1])
                
            except (ValueError, IndexError) as parse_error:
                logger.error(f"Failed to parse candidate string '{candidate_string}': {parse_error}")
                return {"success": False, "error": f"Failed to parse candidate: {parse_error}"}
            
            # Create RTCIceCandidate from parsed data
            ice_candidate = RTCIceCandidate(
                component=component,
                foundation=foundation,
                ip=ip,
                port=port,
                priority=priority,
                protocol=protocol,
                type=candidate_type,
                relatedAddress=related_address,
                relatedPort=related_port,
                sdpMLineIndex=candidate_info.get("sdpMLineIndex", 0),
                sdpMid=candidate_info.get("sdpMid", "0")
            )
            
            # Add the ICE candidate to the peer connection
            await pc.addIceCandidate(ice_candidate)
            
            logger.info(f"Successfully added ICE candidate for session {session_id}: {candidate_type} at {ip}:{port}")
            return {"success": True, "message": "ICE candidate processed successfully"}
            
        except Exception as e:
            logger.error(f"Failed to handle ICE candidate for session {session_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_stream(self, session_id: str) -> Dict[str, Any]:
        """Stop a video stream session."""
        try:
            # Stop video track
            if session_id in self.video_tracks:
                self.video_tracks[session_id].stop()
                del self.video_tracks[session_id]
            
            # Close peer connection
            if session_id in self.peer_connections:
                await self.peer_connections[session_id].close()
                del self.peer_connections[session_id]
            
            return {"success": True, "message": f"Stream {session_id} stopped"}
            
        except Exception as e:
            logger.error(f"Failed to stop stream {session_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_active_streams(self) -> Dict[str, Any]:
        """Get list of active streaming sessions."""
        return {
            "active_sessions": list(self.peer_connections.keys()),
            "total_sessions": len(self.peer_connections)
        }
    
    async def cleanup_all_streams(self):
        """Clean up all active streams."""
        for session_id in list(self.peer_connections.keys()):
            await self.stop_stream(session_id)
    
    async def _cleanup_closed_connections(self):
        """Remove closed peer connections from tracking dictionaries."""
        closed_sessions = []
        
        for session_id, pc in self.peer_connections.items():
            if pc.connectionState in ["closed", "failed"]:
                closed_sessions.append(session_id)
        
        for session_id in closed_sessions:
            await self._cleanup_session(session_id)
            logger.info(f"Cleaned up closed session: {session_id}")
    
    async def _cleanup_session(self, session_id: str):
        """Clean up a specific session."""
        try:
            # Stop video track
            if session_id in self.video_tracks:
                self.video_tracks[session_id].stop()
                del self.video_tracks[session_id]
            
            # Remove peer connection (don't close it again if already closed)
            if session_id in self.peer_connections:
                del self.peer_connections[session_id]
            
            # Clean up from persistent streams if exists
            for camera_id, stream_info in list(self.persistent_streams.items()):
                if stream_info.get("session_id") == session_id:
                    # Mark as inactive instead of deleting for recreation
                    stream_info["status"] = "inactive"
                    stream_info["last_cleanup"] = asyncio.get_event_loop().time()
                    logger.info(f"Marked persistent stream {camera_id} as inactive")
                    break
                    
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    async def recreate_session(self, session_id: str) -> Dict[str, Any]:
        """Recreate a session if it was closed."""
        try:
            # Extract camera_id from session_id (format: camera_id_session_num)
            camera_id = session_id.split('_')[0]
            
            # Check if we have persistent stream info for this camera
            if camera_id in self.persistent_streams:
                stream_info = self.persistent_streams[camera_id]
                rtsp_url = stream_info.get("rtsp_url")
                
                if rtsp_url:
                    # Create new WebRTC session
                    result = await self.create_webrtc_offer(camera_id, rtsp_url)
                    
                    if result["success"]:
                        new_session_id = result["session_id"]
                        
                        # Update persistent stream info
                        webrtc_url = f"{self.base_url}/api/webrtc/stream/{new_session_id}"
                        self.persistent_streams[camera_id].update({
                            "session_id": new_session_id,
                            "webrtc_url": webrtc_url,
                            "status": "active",
                            "recreated_at": asyncio.get_event_loop().time()
                        })
                        
                        # Update camera database
                        await self._update_camera_webrtc_url(camera_id, webrtc_url)
                        
                        logger.info(f"Successfully recreated session for camera {camera_id}: {new_session_id}")
                        return {
                            "success": True,
                            "old_session_id": session_id,
                            "new_session_id": new_session_id,
                            "webrtc_url": webrtc_url
                        }
                    
            return {"success": False, "error": "Unable to recreate session"}
            
        except Exception as e:
            logger.error(f"Failed to recreate session {session_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_persistent_webrtc_stream(self, camera_id: str, rtsp_url: str) -> Dict[str, Any]:
        """Create a persistent WebRTC stream and update camera with WebRTC URL."""
        try:
            logger.info(f"Creating persistent WebRTC stream for camera {camera_id}")
            
            # Create WebRTC offer
            result = await self.create_webrtc_offer(camera_id, rtsp_url)
            
            if not result["success"]:
                return result
            
            session_id = result["session_id"]
            
            # Generate WebRTC URL for this stream
            webrtc_url = f"{self.base_url}/api/webrtc/stream/{session_id}"
            
            # Store persistent stream info
            self.persistent_streams[camera_id] = {
                "session_id": session_id,
                "webrtc_url": webrtc_url,
                "rtsp_url": rtsp_url,
                "created_at": asyncio.get_event_loop().time(),
                "status": "active"
            }
            
            # Update camera in NestJS backend with WebRTC URL
            update_result = await self._update_camera_webrtc_url(camera_id, webrtc_url)
            
            if update_result["success"]:
                logger.info(f"Successfully created persistent stream and updated camera {camera_id}")
                return {
                    "success": True,
                    "camera_id": camera_id,
                    "session_id": session_id,
                    "webrtc_url": webrtc_url,
                    "message": "Persistent WebRTC stream created and camera updated"
                }
            else:
                logger.warning(f"Stream created but failed to update camera {camera_id}: {update_result.get('error')}")
                return {
                    "success": True,
                    "camera_id": camera_id,
                    "session_id": session_id,
                    "webrtc_url": webrtc_url,
                    "warning": f"Stream created but camera update failed: {update_result.get('error')}"
                }
                
        except Exception as e:
            logger.error(f"Failed to create persistent WebRTC stream for camera {camera_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_camera_webrtc_url(self, camera_id: str, webrtc_url: Optional[str]) -> Dict[str, Any]:
        """Update camera in NestJS backend with WebRTC URL."""
        try:
            # Import camera service to reuse authentication
            from .cameras import camera_service
            
            # NestJS API endpoint
            api_url = f"http://localhost:4005/api/v1/cameras/{camera_id}"
            
            # Payload for PATCH request
            payload = {
                "webRtcUrl": webrtc_url
            }
            
            # Get authenticated headers from camera service
            client = await camera_service._get_http_client()
            headers = await camera_service._get_headers()
            
            # Make authenticated request using httpx
            response = await client.patch(api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Successfully updated camera {camera_id} with WebRTC URL")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.content else {}
            }
                    
        except Exception as e:
            logger.error(f"Failed to update camera {camera_id} in database: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_persistent_streams(self) -> Dict[str, Any]:
        """Get all persistent WebRTC streams."""
        return {
            "persistent_streams": self.persistent_streams,
            "total_persistent": len(self.persistent_streams)
        }
    
    async def stop_persistent_stream(self, camera_id: str) -> Dict[str, Any]:
        """Stop a persistent WebRTC stream and remove WebRTC URL from camera."""
        try:
            if camera_id not in self.persistent_streams:
                return {"success": False, "error": "Persistent stream not found"}
            
            stream_info = self.persistent_streams[camera_id]
            session_id = stream_info["session_id"]
            
            # Stop the WebRTC session
            stop_result = await self.stop_stream(session_id)
            
            # Remove WebRTC URL from camera
            update_result = await self._update_camera_webrtc_url(camera_id, None)
            
            # Remove from persistent streams
            del self.persistent_streams[camera_id]
            
            logger.info(f"Stopped persistent stream for camera {camera_id}")
            return {
                "success": True,
                "message": f"Persistent stream for camera {camera_id} stopped",
                "stream_stop": stop_result,
                "camera_update": update_result
            }
            
        except Exception as e:
            logger.error(f"Failed to stop persistent stream for camera {camera_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_analyzed_webrtc_stream(self, camera_id: str) -> Dict[str, Any]:
        """
        Complete flow: Get RTSP -> Analyze with OpenCV -> Create WebRTC -> Update Camera
        """
        try:
            logger.info(f"Starting complete analyzed WebRTC flow for camera {camera_id}")
            
            # Step 1: Get RTSP URL from camera endpoint
            from service.cameras import camera_service
            rtsp_url = await camera_service.get_rtsp_url(camera_id)
            
            if not rtsp_url:
                return {
                    "success": False,
                    "error": f"No RTSP URL found for camera {camera_id}"
                }
            
            logger.info(f"Retrieved RTSP URL for camera {camera_id}: {rtsp_url}")
            
            # Step 2: Create WebRTC stream with OpenCV analysis
            webrtc_result = await self.create_webrtc_offer(camera_id, rtsp_url)
            
            if not webrtc_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to create WebRTC stream: {webrtc_result.get('error')}"
                }
            
            session_id = webrtc_result["session_id"]
            
            # Step 3: Generate WebRTC URL
            webrtc_url = f"{self.base_url}/api/webrtc/stream/{session_id}"
            
            # Step 4: Store persistent stream with analysis info
            self.persistent_streams[camera_id] = {
                "session_id": session_id,
                "webrtc_url": webrtc_url,
                "rtsp_url": rtsp_url,
                "created_at": asyncio.get_event_loop().time(),
                "status": "active",
                "analysis_enabled": True,
                "last_analysis": {}
            }
            
            # Step 5: Update camera in database with WebRTC URL
            update_result = await self._update_camera_webrtc_url(camera_id, webrtc_url)
            
            logger.info(f"Completed analyzed WebRTC flow for camera {camera_id}")
            
            return {
                "success": True,
                "camera_id": camera_id,
                "session_id": session_id,
                "rtsp_url": rtsp_url,
                "webrtc_url": webrtc_url,
                "analysis_enabled": True,
                "database_updated": update_result["success"],
                "message": "RTSP stream analyzed with OpenCV and WebRTC URL created",
                "flow_steps": [
                    "✅ Retrieved RTSP URL from camera endpoint",
                    "✅ Created WebRTC stream with OpenCV analysis",
                    "✅ Generated WebRTC URL endpoint", 
                    "✅ Updated camera database with WebRTC URL",
                    "✅ Stream ready with real-time AI analysis"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create analyzed WebRTC stream for camera {camera_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stream_analysis(self, session_id: str) -> Dict[str, Any]:
        """Get current analysis results from a video stream."""
        try:
            if session_id not in self.video_tracks:
                return {"success": False, "error": "Stream not found"}
            
            video_track = self.video_tracks[session_id]
            analysis_results = video_track.get_analysis_results()
            
            return {
                "success": True,
                "session_id": session_id,
                "analysis": analysis_results,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get analysis for session {session_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global video streaming service instance
video_streaming_service = VideoStreamingService()
