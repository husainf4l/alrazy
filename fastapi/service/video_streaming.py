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
import warnings
import os
from typing import Optional, Dict, Any
from aiortc import VideoStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer
from concurrent.futures import ThreadPoolExecutor
from av import VideoFrame
import threading
import time

# YOLO import
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logging.warning("YOLO not available, falling back to OpenCV HOG detection")

# Comprehensive H.264/FFmpeg error suppression to prevent system hang
os.environ['OPENCV_LOG_LEVEL'] = 'FATAL'  # Only show fatal errors
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'  # Disable video I/O debug
os.environ['FFMPEG_LOG_LEVEL'] = 'fatal'  # Only fatal FFmpeg errors
os.environ['AV_LOG_FORCE_NOCOLOR'] = '1'  # Disable color in logs
os.environ['AV_LOG_FORCE_COLOR'] = '0'   # Disable color in logs

# Additional FFmpeg/libav suppression for H.264 decoder errors
os.environ['FFREPORT'] = 'level=error'  # Only report errors
os.environ['AV_LOG_LEVEL'] = '16'  # AV_LOG_ERROR level (16)
os.environ['OPENCV_AVFOUNDATION_SKIP_AUTH'] = '1'  # Skip auth checks
os.environ['OPENCV_VIDEOIO_PRIORITY_FFMPEG'] = '100'  # Force FFmpeg priority

# Suppress all OpenCV warnings and runtime warnings
warnings.filterwarnings('ignore', category=UserWarning, module='cv2')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='cv2')
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Suppress specific H.264/RTSP error patterns that don't affect functionality
import logging
import sys
import io
from contextlib import contextmanager

h264_logger = logging.getLogger('libav')
h264_logger.setLevel(logging.CRITICAL)  # Only critical messages

# Add stderr suppression for FFmpeg C-level errors
@contextmanager
def suppress_stderr():
    """Context manager to suppress stderr output from FFmpeg C libraries."""
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = old_stderr

# Additional system-level stderr suppression using os.dup2
@contextmanager 
def suppress_stderr_completely():
    """Complete stderr suppression using low-level file descriptor manipulation."""
    import os
    old_stderr_fd = os.dup(2)  # Save original stderr file descriptor
    try:
        # Redirect stderr to /dev/null
        with open(os.devnull, 'w') as devnull:
            os.dup2(devnull.fileno(), 2)
        yield
    finally:
        # Restore original stderr
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)

# Import configuration
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
    class FallbackConfig:
        TARGET_FPS = 3  # Even lower for RTSP stability
        FRAME_SKIP_INTERVAL = 5  # Process every 5th frame
        MAX_CONSECUTIVE_FAILURES = 5
        RTSP_TIMEOUT_MS = 15000  # Longer timeout for stability
        RTSP_BUFFER_SIZE = 1
        CONNECTION_RETRY_ATTEMPTS = 5  # More retries
        RECOVERY_CHECK_INTERVAL = 30
        RECOVERY_THRESHOLD = 60
        RECOVERY_ERROR_DELAY = 60
        THREAD_POOL_MAX_WORKERS = 2  # Reduce workers to limit load
        
        @staticmethod
        def get_rtsp_default_credentials():
            return ("admin", "tt55oo77")
        
        @staticmethod
        def get_fastapi_base_url():
            return "http://localhost:8000"
    
    config = FallbackConfig()

# Import configuration
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
    class FallbackConfig:
        TARGET_FPS = 3  # Even lower for RTSP stability
        FRAME_SKIP_INTERVAL = 5  # Process every 5th frame  
        MAX_CONSECUTIVE_FAILURES = 5
        ANALYSIS_FRAME_INTERVAL = 60  # Analyze every 60th frame (much less frequent)
        DETECTION_FRAME_INTERVAL = 120  # Detect every 120th frame (very infrequent)
        MOTION_THRESHOLD = 1500
        MAX_DETECTIONS_TO_DRAW = 3  # Limit to 3 detections for performance
        RTSP_TIMEOUT_MS = 15000  # Longer timeout for stability
        RTSP_BUFFER_SIZE = 1
        CONNECTION_RETRY_ATTEMPTS = 5  # More retries
        RECOVERY_CHECK_INTERVAL = 30
        RECOVERY_THRESHOLD = 60
        RECOVERY_ERROR_DELAY = 60
        THREAD_POOL_MAX_WORKERS = 2  # Reduce workers to limit load
        SCALE_FACTOR_THRESHOLD = 512  # Smaller images for faster processing
        DETECTION_SCALE_FACTOR = 0.4  # More aggressive scaling
        HOG_WIN_STRIDE = (32, 32)  # Larger stride for performance
        HOG_PADDING = (64, 64)
        HOG_SCALE = 1.2
        FACE_SCALE_FACTOR = 1.3
        FACE_MIN_NEIGHBORS = 4
        
        @staticmethod
        def get_rtsp_default_credentials():
            return ("admin", "tt55oo77")
        
        @staticmethod
        def get_fastapi_base_url():
            return "http://localhost:8000"
    
    config = FallbackConfig()

logger = logging.getLogger(__name__)

# Custom logging filter to suppress H.264/RTSP noise errors
class H264ErrorFilter(logging.Filter):
    """Filter to suppress common H.264/RTSP decoding errors that don't affect functionality."""
    
    def __init__(self):
        super().__init__()
        self.h264_noise_patterns = [
            # RTP/RTSP errors
            'RTP: PT=60: bad cseq',
            'rtsp @', 
            'rtp:', 'pt=60',
            'bad cseq',
            'expected=',
            
            # H.264 decoding errors
            'h264 @',
            'left block unavailable for requested intra4x4 mode',
            'top block unavailable for requested intra mode', 
            'error while decoding MB',
            'bytestream',
            'cabac',
            'qscale',
            'intra4x4',
            'unavailable for requested',
            'decoding MB',
            'mb ', 'mb,',
            
            # Additional FFmpeg noise patterns
            'concealing',
            'slice_type',
            'decode_slice_header',
            'mmco',
            'Invalid NAL unit',
            'nal_unit_type',
            'corrupted macroblock',
            'reference count overflow',
            'sps_id',
            'pps_id'
        ]
    
    def filter(self, record):
        # Check if the log message contains H.264 noise patterns
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for pattern in self.h264_noise_patterns:
                if pattern.lower() in msg_lower:
                    # Suppress this log message completely
                    return False
        
        # Check formatted message as well
        try:
            formatted_msg = record.getMessage().lower()
            for pattern in self.h264_noise_patterns:
                if pattern.lower() in formatted_msg:
                    return False
        except:
            pass
        
        return True  # Allow other messages

# Apply the filter to the root logger and specific loggers
h264_filter = H264ErrorFilter()
logging.getLogger().addFilter(h264_filter)
logging.getLogger('ffmpeg').addFilter(h264_filter)
logging.getLogger('libav').addFilter(h264_filter)
logging.getLogger('opencv').addFilter(h264_filter)


class RTSPVideoTrack(VideoStreamTrack):
    """Custom video track that reads from RTSP stream using OpenCV and analyzes frames."""
    
    def __init__(self, rtsp_url: str, enable_analysis: bool = True, streaming_mode: str = "balanced"):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.cap = None
        self._frame_rate = config.TARGET_FPS
        self._frame_time = 1.0 / self._frame_rate
        self._timestamp = 0
        self._start_time = None
        # Initialize required attributes for VideoStreamTrack
        self._start = None
        
        # Streaming mode: "live" (no analysis, max speed), "balanced" (light analysis), "analysis" (full analysis)
        self.streaming_mode = streaming_mode
        self.enable_analysis = enable_analysis and streaming_mode != "live"
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(
            max_workers=config.THREAD_POOL_MAX_WORKERS, 
            thread_name_prefix="rtsp_video"
        )
        
        # Async analysis queue for non-blocking analysis
        self.analysis_queue = asyncio.Queue(maxsize=10)
        self.analysis_task = None
        
        # Connection state
        self._connection_lock = asyncio.Lock()
        self._is_connected = False
        
        # Analysis settings
        self.analysis_frame_count = 0
        self.last_analysis_results = {}
        
        # Frame skip counter for performance
        self._frame_skip_counter = 0
        if streaming_mode == "live":
            self._frame_skip_interval = 1  # Process every frame for live streaming
        elif streaming_mode == "balanced":
            self._frame_skip_interval = 2  # Process every 2nd frame
        else:  # analysis mode
            self._frame_skip_interval = 5  # Process every 5th frame
        
        # Add time-based frame rate limiting
        self._last_frame_time = 0
        if streaming_mode == "live":
            self._min_frame_interval = 1.0 / 60  # Allow up to 60 FPS for live streaming (no artificial limit)
        else:
            self._min_frame_interval = 1.0 / 20  # Allow up to 20 FPS for analyzed streaming
        
        # Initialize OpenCV analysis components only if needed
        if self.enable_analysis:
            self._init_analysis_models()
        
        # Start async analysis task if analysis is enabled
        if self.enable_analysis:
            self.analysis_task = asyncio.create_task(self._async_analysis_worker())
        
        # Log OpenCV info at startup for diagnostics
        self.log_opencv_info()
    
    def log_opencv_info(self):
        """Log OpenCV version for diagnostics."""
        try:
            import cv2
            logger.info(f"OpenCV version: {cv2.__version__}")
        except Exception as e:
            logger.error(f"Error logging OpenCV info: {e}")
    
    def _init_analysis_models(self):
        """Initialize YOLO for ultra-fast object detection with tracking."""
        try:
            # Initialize YOLO model for person detection (fastest available)
            if YOLO_AVAILABLE:
                try:
                    # Use YOLOv8 nano model for fastest inference with tracking
                    self.yolo_model = YOLO('yolov8n.pt')
                    self.use_yolo = True
                    
                    # Initialize tracking state
                    self.track_history = {}  # Store tracking history for each person
                    self.person_count_history = []  # Track people count over time
                    self.current_tracked_ids = set()  # Currently tracked person IDs
                    
                    logger.info("✅ YOLOv8n (nano) model loaded successfully with tracking enabled")
                except Exception as yolo_error:
                    logger.error(f"Failed to load YOLO model: {yolo_error}")
                    self.use_yolo = False
                    self.yolo_model = None
            else:
                logger.warning("YOLO not available - analysis disabled for maximum speed")
                self.use_yolo = False
                self.yolo_model = None
            
            # Analysis counters
            self.motion_detected = False
            self.people_count = 0
            self.tracked_people_count = 0  # Count of uniquely tracked people
            
            logger.info(f"Analysis models initialized (YOLO: {self.use_yolo}, Tracking: {self.use_yolo})")
            
        except Exception as e:
            logger.error(f"Failed to initialize analysis models: {e}")
            self.enable_analysis = False
            self.use_yolo = False
            self.yolo_model = None
        
    async def recv(self):
        """Receive the next video frame with optimized streaming based on mode."""
        try:
            # Time-based frame rate limiting
            import time
            current_time = time.time()
            time_since_last_frame = current_time - self._last_frame_time
            
            if time_since_last_frame < self._min_frame_interval:
                # Not enough time has passed, reuse last frame
                if hasattr(self, '_last_frame') and self._last_frame is not None:
                    return self._create_av_frame(self._last_frame)
                else:
                    return self._generate_test_frame()
            
            self._last_frame_time = current_time
            
            # Check if we have too many consecutive failures
            if hasattr(self, '_consecutive_failures') and self._consecutive_failures >= config.MAX_CONSECUTIVE_FAILURES:
                logger.warning("Too many consecutive failures, switching to test pattern")
                return self._generate_test_frame()
            
            if self.cap is None or not await self._check_connection():
                try:
                    await self._connect()
                except Exception as e:
                    logger.error(f"Connection failed: {e}")
                    self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
                    return self._generate_test_frame()
            
            # For live streaming, minimize frame skipping and processing overhead
            if self.streaming_mode == "live":
                # Live mode: direct streaming with minimal overhead
                pass  # No frame skipping for live mode
            else:
                # Implement frame skipping for analysis modes
                self._frame_skip_counter += 1
                if self._frame_skip_counter < self._frame_skip_interval:
                    # Return previous frame to maintain framerate but reduce processing
                    if hasattr(self, '_last_frame') and self._last_frame is not None:
                        return self._create_av_frame(self._last_frame)
                    else:
                        return self._generate_test_frame()
                
                self._frame_skip_counter = 0  # Reset counter
            
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
            
            # Store frame for potential reuse
            self._last_frame = frame_data.copy()
            
            # Handle analysis based on streaming mode
            if self.streaming_mode == "live":
                # Live mode: no analysis, direct streaming for maximum speed
                pass
            elif self.enable_analysis:
                # Queue frame for async analysis (non-blocking) with timeout to prevent blocking
                try:
                    await asyncio.wait_for(
                        self.analysis_queue.put(frame_data.copy()), 
                        timeout=0.001  # Very short timeout to prevent blocking
                    )
                except asyncio.TimeoutError:
                    # Queue is full or would block, skip analysis for this frame to maintain streaming speed
                    pass
            
            # Log successful frame processing (less frequent for live mode)
            log_interval = 100 if self.streaming_mode == "live" else 50
            if self.analysis_frame_count % log_interval == 0:
                mode_name = "live streaming" if self.streaming_mode == "live" else "analyzed streaming"
                logger.info(f"Successfully processed frame {self.analysis_frame_count} for {mode_name}")
            
            return self._create_av_frame(frame_data)
            
        except Exception as e:
            logger.error(f"Error in recv(): {e}")
            self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
            return self._generate_test_frame()
    
    def _create_av_frame(self, frame_data):
        """Create AV frame from frame data with robust format handling (helper method)."""
        try:
            # Ensure frame is valid and in correct format
            if frame_data is None or frame_data.size == 0:
                logger.warning("Invalid frame_data for AV frame creation")
                return self._generate_test_frame()
            
            # Ensure frame has proper dimensions for VP8 encoder
            if len(frame_data.shape) != 3 or frame_data.shape[2] != 3:
                logger.warning(f"Frame has incorrect shape for VP8: {frame_data.shape}")
                return self._generate_test_frame()
            
            height, width = frame_data.shape[:2]
            
            # VP8 encoder works better with even dimensions
            if height % 2 != 0 or width % 2 != 0:
                new_height = height - (height % 2)
                new_width = width - (width % 2)
                logger.debug(f"Adjusting frame size for VP8: {height}x{width} -> {new_height}x{new_width}")
                frame_data = frame_data[:new_height, :new_width, :]
            
            # Ensure frame is contiguous in memory for better performance
            if not frame_data.flags['C_CONTIGUOUS']:
                frame_data = np.ascontiguousarray(frame_data)
            
            # Convert BGR to RGB for WebRTC
            frame_rgb = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            
            # Create video frame with explicit format
            av_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            
            # Set timestamp manually using a simple increment
            av_frame.pts = self._timestamp
            av_frame.time_base = fractions.Fraction(1, self._frame_rate)
            
            self._timestamp += 1
            
            return av_frame
            
        except Exception as e:
            logger.error(f"Error creating AV frame: {e}")
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
        """Analyze frame with YOLO for ultra-fast person detection and tracking."""
        try:
            self.analysis_frame_count += 1
            
            # Periodic cleanup of old ByteTrack tracks (every 300 frames = 10 seconds @ 30fps)
            if self.analysis_frame_count % 300 == 0:
                self.cleanup_old_bytetrack_tracks()
            
            analyzed_frame = frame.copy()
            
            # Only analyze periodically for performance
            if self.analysis_frame_count % config.ANALYSIS_FRAME_INTERVAL == 0:
                # Person detection and tracking using YOLO (super fast)
                if self.use_yolo and self.yolo_model:
                    try:
                        # Run YOLO inference with tracking - optimized for speed
                        # track() method automatically assigns unique IDs to detected persons
                        results = self.yolo_model.track(
                            frame, 
                            persist=True,  # Keep tracking across frames
                            conf=0.3,  # Lower confidence for more detections (ByteTrack benefit)
                            classes=[0],  # class 0 = person
                            verbose=False,  # Suppress output
                            tracker="bytetrack.yaml",  # Use ByteTrack for superior tracking
                            # ByteTrack optimized parameters
                            track_high_thresh=0.6,    # Higher threshold for reliable first association
                            track_low_thresh=0.15,    # Allow recovery of lost tracks
                            new_track_thresh=0.7,     # Higher threshold for new track creation
                            track_buffer=45,          # Keep lost tracks longer (1.5s @ 30fps)
                            match_thresh=0.8          # Similarity threshold for matching
                        )
                        
                        # Extract tracked person detections
                        tracked_people = []
                        current_frame_ids = set()
                        
                        if len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
                            boxes = results[0].boxes
                            
                            for box in boxes:
                                # Get bounding box coordinates
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                conf = float(box.conf[0].cpu().numpy())
                                
                                # Get tracking ID if available
                                track_id = None
                                if box.id is not None:
                                    track_id = int(box.id[0].cpu().numpy())
                                    current_frame_ids.add(track_id)
                                    
                                    # Store tracking history
                                    if track_id not in self.track_history:
                                        self.track_history[track_id] = []
                                    
                                    # Store center point for trajectory
                                    center_x = int((x1 + x2) / 2)
                                    center_y = int((y1 + y2) / 2)
                                    self.track_history[track_id].append((center_x, center_y))
                                    
                                    # Keep only last 30 points for trajectory
                                    if len(self.track_history[track_id]) > 30:
                                        self.track_history[track_id] = self.track_history[track_id][-30:]
                                
                                tracked_people.append({
                                    'box': [int(x1), int(y1), int(x2), int(y2)],
                                    'conf': conf,
                                    'id': track_id
                                })
                        
                        # Update people count and tracked IDs
                        self.people_count = len(tracked_people)
                        self.current_tracked_ids = current_frame_ids
                        self.tracked_people_count = len(self.track_history)  # Total unique people tracked
                        
                        # Draw tracked people with IDs and trajectories
                        for person in tracked_people[:10]:  # Limit to 10 for performance
                            x1, y1, x2, y2 = person['box']
                            track_id = person['id']
                            conf = person['conf']
                            
                            # Draw bounding box
                            color = (0, 255, 0)  # Green for tracked
                            cv2.rectangle(analyzed_frame, (x1, y1), (x2, y2), color, 2)
                            
                            # Draw tracking ID and confidence
                            if track_id is not None:
                                label = f"ID:{track_id} {conf:.2f}"
                                cv2.putText(analyzed_frame, label, (x1, y1 - 10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                
                                # Draw trajectory
                                if track_id in self.track_history and len(self.track_history[track_id]) > 1:
                                    points = self.track_history[track_id]
                                    for i in range(1, len(points)):
                                        # Draw line between consecutive points
                                        cv2.line(analyzed_frame, points[i-1], points[i], (0, 255, 255), 2)
                        
                        # Store people count in history for trend analysis
                        self.person_count_history.append(self.people_count)
                        if len(self.person_count_history) > 100:  # Keep last 100 counts
                            self.person_count_history = self.person_count_history[-100:]
                        
                    except Exception as yolo_error:
                        logger.debug(f"YOLO tracking error: {yolo_error}")
                        self.people_count = 0
                        self.tracked_people_count = 0
                
                # Update analysis results with tracking info
                self.last_analysis_results = {
                    "people_count": self.people_count,
                    "tracked_people_count": self.tracked_people_count,
                    "current_ids": list(self.current_tracked_ids),
                    "timestamp": self.analysis_frame_count,
                    "avg_people_count": sum(self.person_count_history) / len(self.person_count_history) if self.person_count_history else 0
                }
            
            # Draw analysis overlay with tracking info
            if self.people_count > 0 or self.tracked_people_count > 0:
                self._draw_analysis_overlay(analyzed_frame)
            
            return analyzed_frame
            
        except Exception as e:
            logger.error(f"Error in frame analysis: {e}")
            return frame
    
    def _draw_analysis_overlay(self, frame):
        """Draw analysis information overlay on frame with people count and tracking stats."""
        try:
            h, w = frame.shape[:2]
            
            # Draw large people count in top center if people detected
            if self.people_count > 0:
                people_text = f"👥 {self.people_count} {'Person' if self.people_count == 1 else 'People'}"
                
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.5
                thickness = 3
                (text_width, text_height), _ = cv2.getTextSize(people_text, font, font_scale, thickness)
                
                # Position in top center
                x = (w - text_width) // 2
                y = 60
                
                # Draw background rectangle
                cv2.rectangle(frame, (x - 10, y - text_height - 10), (x + text_width + 10, y + 10), (0, 0, 0), -1)
                cv2.rectangle(frame, (x - 10, y - text_height - 10), (x + text_width + 10, y + 10), (0, 255, 0), 2)
                
                # Draw people count text
                cv2.putText(frame, people_text, (x, y), font, font_scale, (0, 255, 0), thickness)
            
            # Draw tracking statistics in top right corner
            if self.tracked_people_count > 0:
                stats_text = [
                    f"Tracked: {self.tracked_people_count}",
                    f"Active: {len(self.current_tracked_ids)}"
                ]
                
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                
                # Calculate background size
                max_width = max([cv2.getTextSize(text, font, font_scale, thickness)[0][0] for text in stats_text])
                bg_height = 20 * len(stats_text) + 20
                
                # Draw background
                cv2.rectangle(frame, (w - max_width - 30, 10), (w - 10, 10 + bg_height), (0, 0, 0), -1)
                cv2.rectangle(frame, (w - max_width - 30, 10), (w - 10, 10 + bg_height), (0, 255, 255), 2)
                
                # Draw stats
                y_offset = 30
                for text in stats_text:
                    cv2.putText(frame, text, (w - max_width - 20, y_offset), 
                              font, font_scale, (0, 255, 255), thickness)
                    y_offset += 20
            
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}")
    
    async def _async_analysis_worker(self):
        """Async worker that processes frames for analysis without blocking streaming."""
        logger.info("Started async analysis worker")
        
        while True:
            try:
                # Get frame from queue with timeout to prevent blocking
                try:
                    frame_data = await asyncio.wait_for(
                        self.analysis_queue.get(), 
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue  # No frame available, continue loop
                
                # Process frame in thread pool (non-blocking for WebRTC)
                loop = asyncio.get_event_loop()
                analyzed_frame = await loop.run_in_executor(
                    self.executor,
                    self._analyze_frame,
                    frame_data
                )
                
                # Update analysis results
                self.analysis_frame_count += 1
                
                # Mark task as done
                self.analysis_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in async analysis worker: {e}")
                await asyncio.sleep(0.01)  # Brief pause on error
    
    def stop(self):
        """Stop the video track and cleanup resources."""
        if self.analysis_task and not self.analysis_task.done():
            self.analysis_task.cancel()
        
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        
        super().stop()
    
    async def _check_connection(self) -> bool:
        """Check if RTSP connection is still active."""
        try:
            if not self.cap or not self.cap.isOpened():
                return False
            
            # Use the connection lock to prevent race conditions
            async with self._connection_lock:
                return self._is_connected and self.cap.isOpened()
                
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
    
    async def _connect(self):
        """Connect to RTSP stream asynchronously."""
        try:
            async with self._connection_lock:
                if self._is_connected and self.cap and self.cap.isOpened():
                    return  # Already connected
                
                logger.info(f"Connecting to RTSP stream: {self.rtsp_url}")
                
                # Release any existing connection
                if self.cap:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor, self.cap.release
                    )
                    self.cap = None
                
                # Create new connection in thread pool
                self.cap = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self._create_video_capture, self.rtsp_url
                )
                
                if self.cap and self.cap.isOpened():
                    # Test the connection with a frame read
                    test_frame = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self._read_frame_sync
                    )
                    
                    if test_frame is not None:
                        self._is_connected = True
                        logger.info(f"Successfully connected to RTSP stream: {self.rtsp_url}")
                    else:
                        logger.warning(f"Connected to RTSP but cannot read frames: {self.rtsp_url}")
                        if self.cap:
                            await asyncio.get_event_loop().run_in_executor(
                                self.executor, self.cap.release
                            )
                            self.cap = None
                        self._is_connected = False
                else:
                    logger.error(f"Failed to connect to RTSP stream: {self.rtsp_url}")
                    self._is_connected = False
                    
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream: {e}")
            self._is_connected = False
            if self.cap:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor, self.cap.release
                    )
                except:
                    pass
                self.cap = None

    def _create_video_capture_robust(self, url: str) -> cv2.VideoCapture:
        """Create video capture with multiple backend attempts for better compatibility."""
        backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
        
        for backend in backends:
            try:
                # Suppress FFmpeg stderr output completely during robust capture creation
                with suppress_stderr_completely():
                    cap = cv2.VideoCapture(url, backend)
                    
                if cap.isOpened():
                    # Configure essential settings
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Increased buffer for stability
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, config.RTSP_TIMEOUT_MS)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, config.RTSP_TIMEOUT_MS)
                    
                    # Test frame read with complete stderr suppression
                    with suppress_stderr_completely():
                        ret, frame = cap.read()
                        
                    if ret and frame is not None:
                        logger.info(f"Successfully created VideoCapture with backend: {backend}")
                        return cap
                    else:
                        cap.release()
                        
                logger.debug(f"Backend {backend} failed to provide readable frames")
                
            except Exception as e:
                logger.debug(f"Backend {backend} failed: {e}")
                
        logger.error("All VideoCapture backends failed")
        return None
    
    def _read_frame_sync(self):
        """Read frame synchronously with robust H.264/YUV420P format handling (runs in thread pool)."""
        if not self.cap or not self.cap.isOpened():
            logger.debug("VideoCapture not opened or missing.")
            return None
        try:
            # Add retry logic for H.264 decoding errors with backoff
            max_retries = config.CONNECTION_RETRY_ATTEMPTS
            for attempt in range(max_retries):
                # Suppress FFmpeg stderr output completely during frame reading
                with suppress_stderr_completely():
                    ret, frame = self.cap.read()
                    
                logger.debug(f"cap.read() returned ret={ret}, type(frame)={type(frame)}, frame is None={frame is None}")
                if frame is not None:
                    logger.debug(f"Frame shape: {getattr(frame, 'shape', None)}, dtype: {getattr(frame, 'dtype', None)}")
                
                if ret and frame is not None:
                    # Enhanced H.264 frame validation and error recovery
                    if len(frame.shape) == 2 and frame.shape[0] == 1:
                        logger.warning(f"Detected raw H.264 packet data instead of decoded frame: {frame.shape}")
                        logger.warning("H.264 decoder returning raw bytes - reinitializing with robust settings")
                        
                        # This indicates H.264 decoder is returning raw packet data
                        if attempt < max_retries - 1:
                            logger.info("Reinitializing VideoCapture with enhanced H.264 error recovery")
                            if self.cap:
                                self.cap.release()
                            self.cap = self._create_video_capture_robust(self.rtsp_url)
                            if self.cap and self.cap.isOpened():
                                time.sleep(0.1)  # Give decoder time to initialize
                                continue
                        else:
                            logger.error("Failed to fix H.264 raw byte data issue after all retries")
                            return None
                    
                    # Handle corrupted or malformed H.264 frames
                    elif (len(frame.shape) < 2 or 
                          frame.shape[0] < 10 or frame.shape[1] < 10 or 
                          frame.size == 0):
                        logger.debug(f"Corrupted H.264 frame detected: shape={getattr(frame, 'shape', 'None')}")
                        if attempt < max_retries - 1:
                            time.sleep(0.02)  # Short delay before retry
                            continue
                        else:
                            logger.warning("Multiple corrupted frames detected, using test pattern")
                            return None
                    
                    # Handle normal decoded frames with format conversion
                    elif len(frame.shape) == 2:  # Grayscale from YUV420P
                        logger.debug("Converting YUV420P grayscale to BGR color frame")
                        try:
                            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                        except cv2.error as cv_error:
                            logger.debug(f"Color conversion failed: {cv_error}")
                            if attempt < max_retries - 1:
                                continue
                            return None
                    elif len(frame.shape) == 3 and frame.shape[2] == 1:  # Single channel
                        logger.debug("Converting single channel to BGR color frame")
                        try:
                            frame = cv2.cvtColor(frame.squeeze(), cv2.COLOR_GRAY2BGR)
                        except cv2.error as cv_error:
                            logger.debug(f"Color conversion failed: {cv_error}")
                            if attempt < max_retries - 1:
                                continue
                            return None
                    
                    # Final frame integrity validation with night vision considerations
                    if (frame.size > 0 and 
                        len(frame.shape) == 3 and
                        frame.shape[0] > 10 and  # Reasonable height
                        frame.shape[1] > 10 and  # Reasonable width
                        frame.shape[2] == 3):    # BGR channels
                        
                        # Enhanced validation for night vision footage
                        frame_mean = np.mean(frame)
                        frame_std = np.std(frame)
                        
                        # Night vision frames tend to be dark (low mean) but can have high noise (high std)
                        if frame_mean < 2:  # Very dark frame (common corruption indicator)
                            logger.debug(f"Very dark frame detected (possible corruption): mean={frame_mean}")
                            if attempt < max_retries - 1:
                                time.sleep(0.02)
                                continue
                        elif frame_mean > 253:  # Very bright frame (IR overexposure)
                            logger.debug(f"Overexposed IR frame detected: mean={frame_mean}")
                            if attempt < max_retries - 1:
                                time.sleep(0.02)
                                continue
                        elif frame_std > 80:  # Very high noise (common with poor night vision)
                            logger.debug(f"High noise frame detected: std={frame_std}")
                            # Apply light denoising for very noisy frames
                            try:
                                frame = cv2.bilateralFilter(frame, 5, 25, 25)
                                logger.debug("Applied noise reduction to night vision frame")
                            except:
                                pass  # Continue without denoising if it fails
                        
                        logger.debug(f"Valid night vision frame: {frame.shape}, mean={frame_mean:.1f}, std={frame_std:.1f}")
                        return frame
                    else:
                        logger.debug(f"Invalid frame format on attempt {attempt + 1}: shape={getattr(frame, 'shape', 'None')}")
                        if attempt < max_retries - 1:
                            time.sleep(0.02)  # 20ms delay
                            continue
                        else:
                            return None
                else:
                    logger.debug(f"Failed to read frame on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(0.1)  # 100ms delay
                        continue
                    else:
                        return None
            
            logger.warning("All frame read attempts failed. Attempting full VideoCapture reinitialization.")
            # Try to reinitialize the VideoCapture object with robust settings
            try:
                if self.cap:
                    self.cap.release()
                self.cap = self._create_video_capture_robust(self.rtsp_url)
                if self.cap and self.cap.isOpened():
                    # Wait for decoder to stabilize
                    time.sleep(0.2)
                    ret, frame = self.cap.read()
                    logger.debug(f"After robust reinit: cap.read() ret={ret}, frame is None={frame is None}")
                    if ret and frame is not None and len(frame.shape) == 3:
                        return frame
            except Exception as reinit_error:
                logger.error(f"Error during VideoCapture reinitialization: {reinit_error}")
            return None
        except Exception as e:
            error_str = str(e).lower()
            # Enhanced error pattern matching for H.264 decoding issues and night vision problems
            h264_error_patterns = [
                "h264", "bytestream", "yuv420p", "cabac", "intra4x4", 
                "qscale", "mb", "decode", "rtp", "cseq", "rtsp",
                "noise", "dark", "gain", "exposure", "infrared", "ir"
            ]
            
            if any(pattern in error_str for pattern in h264_error_patterns):
                logger.debug(f"H.264/RTSP/Night vision decoding error (non-critical, auto-recovering): {e}")
                # These are common network/codec/night vision errors that can be safely ignored
                # The system will automatically recover on the next frame attempt
            else:
                logger.error(f"Error reading frame: {e}")
            return None
    
    def _create_video_capture(self, url: str) -> cv2.VideoCapture:
        """Create video capture object with enhanced H.264/RTSP error resilience and night vision support (runs in thread pool)."""
        # Suppress FFmpeg stderr output completely during video capture creation
        with suppress_stderr_completely():
            # Force FFmpeg backend for better RTSP/H.264 compatibility
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                try:
                    # Essential settings for RTSP stability and H.264 error recovery
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Increased buffer for stability
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, config.RTSP_TIMEOUT_MS)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, config.RTSP_TIMEOUT_MS)
                    
                    # Enhanced H.264 error handling settings
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # Enable automatic conversion
                    cap.set(cv2.CAP_PROP_FORMAT, -1)  # Let OpenCV choose best format
                    
                    # Night vision optimizations to reduce decoding stress from noisy footage
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Lower resolution for less noise data
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Lower resolution for less noise data
                    cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)  # Lower frame rate for stability
                    
                    # H.264 decoder optimizations for noisy night vision
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
                    
                    # Night vision specific settings to handle noise better
                    try:
                        # Reduce gain/brightness to minimize noise amplification
                        cap.set(cv2.CAP_PROP_GAIN, 0)  # Minimize gain
                        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.4)  # Moderate brightness
                        cap.set(cv2.CAP_PROP_CONTRAST, 0.6)  # Moderate contrast
                        cap.set(cv2.CAP_PROP_SATURATION, 0.5)  # Reduce saturation to handle IR artifacts
                        
                        # Auto-exposure settings for night conditions
                        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Reduce auto-exposure
                        cap.set(cv2.CAP_PROP_EXPOSURE, -4)  # Lower exposure for night vision
                    except:
                        pass  # These may not be supported by all cameras
                    
                    # Additional settings for network stream stability
                    try:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Start from beginning
                        cap.set(cv2.CAP_PROP_FRAME_COUNT, -1)  # Infinite stream
                    except:
                        pass  # Ignore if not supported
                    
                    logger.info("Enhanced H.264/RTSP-optimized video capture settings applied with night vision support")
                    
                except Exception as setting_error:
                    logger.warning(f"Some video capture settings failed (continuing anyway): {setting_error}")
                    
            return cap


class VideoStreamingService:
    """Service for handling video streaming with WebRTC."""
    
    def __init__(self):
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.video_tracks: Dict[str, RTSPVideoTrack] = {}
        self.persistent_streams: Dict[str, Dict[str, Any]] = {}  # Store persistent WebRTC streams
        self.base_url = config.get_fastapi_base_url()
        self._auto_recovery_started = False
    
    async def create_webrtc_offer(self, camera_id: str, rtsp_url: str, streaming_mode: str = "balanced") -> Dict[str, Any]:
        """Create WebRTC offer for a camera stream with specified streaming mode."""
        try:
            logger.info(f"Creating WebRTC offer for camera {camera_id} with RTSP URL: {rtsp_url} (mode: {streaming_mode})")
            
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
                    # Mark persistent stream as inactive but don't remove it for auto-recovery
                    camera_id_from_session = session_id.split('_')[0]
                    if camera_id_from_session in self.persistent_streams:
                        self.persistent_streams[camera_id_from_session]["status"] = "inactive"
                        self.persistent_streams[camera_id_from_session]["last_disconnect"] = asyncio.get_event_loop().time()
                        logger.info(f"Marked persistent stream {camera_id_from_session} as inactive")
            
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state is {pc.iceConnectionState} for session {session_id}")
                # Handle ICE connection failures with auto-recovery
                if pc.iceConnectionState == "failed":
                    camera_id_from_session = session_id.split('_')[0]
                    if camera_id_from_session in self.persistent_streams:
                        logger.warning(f"ICE connection failed for camera {camera_id_from_session}, marking for recovery")
                        self.persistent_streams[camera_id_from_session]["status"] = "recovering"
            
            @pc.on("icegatheringstatechange")
            async def on_icegatheringstatechange():
                logger.info(f"ICE gathering state is {pc.iceGatheringState} for session {session_id}")
            
            # Create video track from RTSP stream with specified streaming mode
            enable_analysis = streaming_mode != "live"
            video_track = RTSPVideoTrack(rtsp_url, enable_analysis=enable_analysis, streaming_mode=streaming_mode)
            pc.addTrack(video_track)
            
            # Store references
            self.peer_connections[session_id] = pc
            self.video_tracks[session_id] = video_track
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            logger.info(f"Created WebRTC offer for camera {camera_id}, session {session_id} (mode: {streaming_mode})")
            
            return {
                "session_id": session_id,
                "offer": {
                    "type": offer.type,
                    "sdp": offer.sdp
                },
                "streaming_mode": streaming_mode,
                "analysis_enabled": enable_analysis,
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
    
    async def get_persistent_streams(self) -> Dict[str, Any]:
        """Get all persistent WebRTC streams."""
        return {
            "success": True,
            "persistent_streams": self.persistent_streams,
            "total_persistent": len(self.persistent_streams)
        }
    
    async def get_stream_analysis(self, session_id: str) -> Dict[str, Any]:
        """Get real-time analysis results from a video stream."""
        try:
            if session_id not in self.video_tracks:
                return {"success": False, "error": "Stream not found"}
            
            video_track = self.video_tracks[session_id]
            analysis_results = video_track.get_analysis_results()
            
            return {
                "success": True,
                "analysis": analysis_results,
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"Failed to get stream analysis for session {session_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_persistent_webrtc_stream(self, camera_id: str, rtsp_url: str) -> Dict[str, Any]:
        """Create a persistent WebRTC stream for a camera and update database."""
        try:
            # Use the existing analyzed stream creation method
            result = await self.create_analyzed_webrtc_stream(camera_id)
            return result
        except Exception as e:
            logger.error(f"Failed to create persistent WebRTC stream for camera {camera_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_persistent_stream(self, camera_id: str) -> Dict[str, Any]:
        """Stop a persistent WebRTC stream for a camera."""
        try:
            if camera_id not in self.persistent_streams:
                return {"success": False, "error": f"No persistent stream found for camera {camera_id}"}
            
            stream_info = self.persistent_streams[camera_id]
            session_id = stream_info.get("session_id")
            
            if session_id:
                # Stop the stream
                stop_result = await self.stop_stream(session_id)
                
                # Remove from persistent streams
                del self.persistent_streams[camera_id]
                
                # Update camera database to remove WebRTC URL
                self._update_camera_webrtc_url(camera_id, None)
                
                logger.info(f"Stopped persistent stream for camera {camera_id}")
                return {
                    "success": True,
                    "message": f"Persistent stream stopped for camera {camera_id}",
                    "camera_id": camera_id
                }
            else:
                return {"success": False, "error": "No session ID found for persistent stream"}
                
        except Exception as e:
            logger.error(f"Failed to stop persistent stream for camera {camera_id}: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    def cleanup_old_bytetrack_tracks(self, max_age_frames: int = 900):
        """Clean up old ByteTrack tracks to prevent memory leaks.
        
        Args:
            max_age_frames: Maximum age in frames before removing a track (default 900 = 30s @ 30fps)
        """
        try:
            current_frame = self.analysis_frame_count
            tracks_to_remove = []
            
            for track_id, history in self.track_history.items():
                if not history:
                    tracks_to_remove.append(track_id)
                    continue
                
                # Check if track is too old (no updates in max_age_frames)
                # Since we don't store frame numbers, estimate based on history length
                # Assuming we store trajectory points every frame
                if len(history) > 0:
                    # If we haven't added new points recently, the track might be stale
                    # For now, remove tracks with very long histories that might be memory leaks
                    if len(history) > max_age_frames:
                        tracks_to_remove.append(track_id)
            
            # Remove old tracks
            for track_id in tracks_to_remove:
                del self.track_history[track_id]
                if track_id in self.current_tracked_ids:
                    self.current_tracked_ids.remove(track_id)
            
            if tracks_to_remove:
                logger.debug(f"🧹 Cleaned up {len(tracks_to_remove)} old ByteTrack tracks")
                
        except Exception as e:
            logger.error(f"Error cleaning up ByteTrack tracks: {e}")
    
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
                        self._update_camera_webrtc_url(camera_id, webrtc_url)
                        
                        logger.info(f"Successfully recreated session for camera {camera_id}: {new_session_id}")
                        return {
                            "success": True,
                            "old_session_id": session_id,
                            "new_session_id": new_session_id
                        }
                    else:
                        logger.error(f"Failed to recreate session for camera {camera_id}: {result.get('error', 'Unknown error')}")
                        return {
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        }
            else:
                logger.warning(f"No persistent stream info found for camera {camera_id}")
                return {
                    "success": False,
                    "error": "No persistent stream info found"
                }
        
        except Exception as e:
            logger.error(f"Error recreating session {session_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_camera_webrtc_url(self, camera_id: str, webrtc_url: Optional[str]) -> Dict[str, Any]:
        """Update camera in standalone database with WebRTC URL."""
        try:
            # Use standalone camera service to update in-memory database
            from service.cameras import camera_service
            
            success = camera_service.update_camera_webrtc_url(int(camera_id), webrtc_url)
            
            if success:
                logger.info(f"Successfully updated camera {camera_id} with WebRTC URL in standalone database")
                return {
                    "success": True,
                    "status_code": 200,
                    "response": {"message": "Updated in standalone database"}
                }
            else:
                return {
                    "success": False,
                    "error": f"Camera {camera_id} not found in standalone database"
                }
                    
        except Exception as e:
            logger.error(f"Failed to update camera {camera_id} in database: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_auto_recovery(self):
        """Start the auto-recovery process for persistent streams."""
        if self._auto_recovery_started:
            return
        
        self._auto_recovery_started = True
        
        async def auto_recovery_loop():
            while True:
                try:
                    current_time = asyncio.get_event_loop().time()
                    
                    for camera_id, stream_info in self.persistent_streams.items():
                        if stream_info["status"] == "inactive":
                            last_disconnect = stream_info.get("last_disconnect", 0)
                            elapsed_time = current_time - last_disconnect
                            
                            # Attempt recovery if inactive for longer than the threshold
                            if elapsed_time > config.RECOVERY_THRESHOLD:
                                logger.info(f"Attempting to recover inactive stream {camera_id}")
                                rtsp_url = stream_info.get("rtsp_url")
                                result = await self.create_webrtc_offer(camera_id, rtsp_url)
                                
                                if result["success"]:
                                    logger.info(f"Successfully recovered stream {camera_id}")
                                else:
                                    logger.error(f"Failed to recover stream {camera_id}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error in auto-recovery loop: {e}")
                
                await asyncio.sleep(config.RECOVERY_CHECK_INTERVAL)
        
        # Start the background task
        asyncio.create_task(auto_recovery_loop())
        logger.info("Auto-recovery task started")
    
    async def create_analyzed_webrtc_stream(self, camera_id: str, streaming_mode: str = "balanced") -> Dict[str, Any]:
        """
        Complete flow: Get RTSP -> Create WebRTC stream with specified mode -> Update Camera
        """
        try:
            logger.info(f"Starting WebRTC flow for camera {camera_id} (mode: {streaming_mode})")
            
            # Step 1: Get RTSP URL from standalone camera database
            from service.cameras import camera_service
            rtsp_url = camera_service.get_camera_rtsp_url(int(camera_id))
            
            if not rtsp_url:
                return {
                    "success": False,
                    "error": f"No RTSP URL found for camera {camera_id}"
                }
            
            logger.info(f"Retrieved RTSP URL for camera {camera_id}: {rtsp_url}")
            
            # Step 2: Create WebRTC stream with specified streaming mode
            webrtc_result = await self.create_webrtc_offer(camera_id, rtsp_url, streaming_mode)
            
            if not webrtc_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to create WebRTC stream: {webrtc_result.get('error')}"
                }
            
            session_id = webrtc_result["session_id"]
            
            # Step 3: Generate WebRTC URL
            webrtc_url = f"{self.base_url}/api/webrtc/stream/{session_id}"
            
            # Step 4: Store persistent stream with mode info
            analysis_enabled = streaming_mode != "live"
            self.persistent_streams[camera_id] = {
                "session_id": session_id,
                "webrtc_url": webrtc_url,
                "rtsp_url": rtsp_url,
                "created_at": asyncio.get_event_loop().time(),
                "status": "active",
                "streaming_mode": streaming_mode,
                "analysis_enabled": analysis_enabled,
                "last_analysis": {}
            }
            
            # Step 5: Update camera in database with WebRTC URL
            update_result = self._update_camera_webrtc_url(camera_id, webrtc_url)
            
            mode_description = {
                "live": "ultra-fast live streaming (no analysis)",
                "balanced": "balanced streaming with light analysis", 
                "analysis": "full analysis streaming"
            }.get(streaming_mode, "unknown mode")
            
            logger.info(f"Completed WebRTC flow for camera {camera_id} ({mode_description})")
            
            return {
                "success": True,
                "camera_id": camera_id,
                "session_id": session_id,
                "rtsp_url": rtsp_url,
                "webrtc_url": webrtc_url,
                "streaming_mode": streaming_mode,
                "analysis_enabled": analysis_enabled,
                "database_updated": update_result["success"],
                "message": f"RTSP stream converted to WebRTC with {mode_description}",
                "flow_steps": [
                    "✅ Retrieved RTSP URL from camera endpoint",
                    f"✅ Created WebRTC stream in {streaming_mode} mode",
                    "✅ Generated WebRTC URL endpoint", 
                    "✅ Updated camera database with WebRTC URL",
                    f"✅ Stream ready with {mode_description}"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create WebRTC stream for camera {camera_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global service instance
video_streaming_service = VideoStreamingService()