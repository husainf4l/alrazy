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
    
    def __init__(self, rtsp_url: str, enable_analysis: bool = True, executor: ThreadPoolExecutor = None):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.cap = None
        self._frame_rate = config.TARGET_FPS
        self._frame_time = 1.0 / self._frame_rate
        self._timestamp = 0
        self._start_time = None
        # Initialize required attributes for VideoStreamTrack
        self._start = None
        
        # Thread pool for blocking operations
        self.executor = executor or ThreadPoolExecutor(
            max_workers=config.THREAD_POOL_MAX_WORKERS, 
            thread_name_prefix="rtsp_video"
        )
        
        # Connection state
        self._connection_lock = asyncio.Lock()
        self._is_connected = False
        
        # Analysis settings
        self.enable_analysis = enable_analysis
        self.analysis_frame_count = 0
        self.last_analysis_results = {}
        
        # Frame skip counter for performance
        self._frame_skip_counter = 0
        self._frame_skip_interval = config.FRAME_SKIP_INTERVAL
        
        # Add time-based frame rate limiting
        self._last_frame_time = 0
        self._min_frame_interval = 1.0 / config.TARGET_FPS  # Minimum time between frames
        
        # Initialize OpenCV analysis components
        if self.enable_analysis:
            self._init_analysis_models()
        
        # Log OpenCV info at startup for diagnostics
        self.log_opencv_info()
    
    def log_opencv_info(self):
        """Log OpenCV version, build info, and backend/capabilities for diagnostics."""
        try:
            import cv2
            logger.info(f"OpenCV version: {cv2.__version__}")
            try:
                build_info = cv2.getBuildInformation()
                logger.info(f"OpenCV build info:\n{build_info}")
            except Exception as e:
                logger.warning(f"Could not get OpenCV build info: {e}")
            try:
                backends = cv2.videoio_registry.getBackends()
                logger.info(f"Available OpenCV video backends: {backends}")
            except Exception as e:
                logger.warning(f"Could not get OpenCV video backends: {e}")
            try:
                codecs = cv2.videoio_registry.getCameraBackends()
                logger.info(f"Available OpenCV camera backends: {codecs}")
            except Exception as e:
                logger.warning(f"Could not get OpenCV camera backends: {e}")
        except Exception as e:
            logger.error(f"Error logging OpenCV info: {e}")
    
    def _init_analysis_models(self):
        """Initialize OpenCV analysis models with GPU acceleration."""
        try:
            # Check for GPU support
            try:
                gpu_count = cv2.cuda.getCudaEnabledDeviceCount()
                if gpu_count > 0:
                    logger.info(f"CUDA-enabled OpenCV detected with {gpu_count} GPU(s)")
                    self.use_gpu = True
                else:
                    logger.info("No CUDA support detected, using CPU")
                    self.use_gpu = False
            except:
                logger.info("OpenCV compiled without CUDA, using CPU")
                self.use_gpu = False
            
            # Initialize background subtractor for motion detection (optimized for night vision)
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                detectShadows=False,  # Disable shadows for better performance
                varThreshold=150,     # Higher threshold for noisy night vision
                history=200           # Longer history for stable night background
            )
            
            # Initialize HOG descriptor for person detection
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Initialize face cascade classifier with optimized settings
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Analysis counters
            self.motion_detected = False
            self.people_count = 0
            self.faces_count = 0
            
            logger.info(f"OpenCV analysis models initialized successfully (GPU: {self.use_gpu})")
            
        except Exception as e:
            logger.error(f"Failed to initialize analysis models: {e}")
            self.enable_analysis = False
            self.use_gpu = False
        
    async def recv(self):
        """Receive the next video frame with OpenCV analysis."""
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
            
            # Implement frame skipping for better performance
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
            
            # Perform OpenCV analysis on the frame (in BGR format) - run in thread pool
            if self.enable_analysis:
                frame_data = await loop.run_in_executor(
                    self.executor,
                    self._analyze_frame,
                    frame_data
                )
            
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
        """Analyze frame with OpenCV and overlay results."""
        try:
            self.analysis_frame_count += 1
            analyzed_frame = frame.copy()
            
            # Only analyze every 30th frame for much better performance and stability
            if self.analysis_frame_count % config.ANALYSIS_FRAME_INTERVAL == 0:
                # Motion detection optimized for night vision
                try:
                    # Pre-process frame for better night vision motion detection
                    motion_frame = frame.copy()
                    
                    # Check if this looks like night vision footage
                    frame_mean = np.mean(motion_frame)
                    if frame_mean < 80:  # Likely night vision
                        # Apply gentle enhancement for motion detection
                        motion_frame = cv2.convertScaleAbs(motion_frame, alpha=1.2, beta=10)
                        logger.debug("Applied night vision enhancement for motion detection")
                    
                    motion_mask = self.background_subtractor.apply(motion_frame)
                    
                    # Apply morphological operations to reduce noise in motion detection
                    kernel = np.ones((3,3), np.uint8)
                    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
                    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
                    
                    motion_pixels = cv2.countNonZero(motion_mask)
                    # Adjust motion threshold for night vision (higher due to noise)
                    motion_threshold = config.MOTION_THRESHOLD * 1.5 if frame_mean < 80 else config.MOTION_THRESHOLD
                    self.motion_detected = motion_pixels > motion_threshold
                    
                except Exception as motion_error:
                    logger.debug(f"Motion detection error (non-fatal): {motion_error}")
                    # Fallback to simple motion detection
                    motion_mask = self.background_subtractor.apply(frame)
                    motion_pixels = cv2.countNonZero(motion_mask)
                    self.motion_detected = motion_pixels > config.MOTION_THRESHOLD
                
                # Person detection (much less frequent for performance, optimized for night vision)
                if self.analysis_frame_count % config.DETECTION_FRAME_INTERVAL == 0:
                    try:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        
                        # Apply gentle denoising for night vision footage
                        try:
                            # Check if frame is likely night vision (low brightness, high noise)
                            frame_mean = np.mean(gray)
                            frame_std = np.std(gray)
                            
                            if frame_mean < 80 and frame_std > 30:  # Likely night vision
                                # Apply light denoising
                                gray = cv2.bilateralFilter(gray, 5, 20, 20)
                                logger.debug("Applied denoising for night vision analysis")
                        except:
                            pass  # Continue without denoising if it fails
                        
                        # Reduce image size more aggressively for faster processing
                        height, width = gray.shape
                        max_dimension = max(height, width)
                        
                        if max_dimension > 512:  # More aggressive scaling
                            scale_factor = 512.0 / max_dimension
                            new_width = int(width * scale_factor)
                            new_height = int(height * scale_factor)
                            small_gray = cv2.resize(gray, (new_width, new_height))
                        else:
                            small_gray = gray
                            scale_factor = 1.0
                        
                        # Detect people using HOG with very conservative parameters
                        people, _ = self.hog.detectMultiScale(
                            small_gray, 
                            winStride=(32, 32),  # Larger stride for better performance
                            padding=(64, 64),    # Larger padding
                            scale=1.2            # Larger scale steps
                        )
                        
                        # Debug: Log the type and shape of the detection result
                        logger.debug(f"People detection result type: {type(people)}, shape: {getattr(people, 'shape', 'N/A')}")
                        
                        # Convert to numpy array if it's a tuple or ensure it's an array
                        if isinstance(people, tuple):
                            people = np.array(people)
                        elif not isinstance(people, np.ndarray):
                            people = np.array(people)
                        
                        # Ensure it's a proper array and handle empty case
                        if people.size == 0:
                            people = np.empty((0, 4), dtype=int)
                        
                        # Scale coordinates back up if we downscaled
                        if scale_factor < 1.0 and len(people) > 0 and people.size > 0:
                            try:
                                people = people.astype(float)
                                people[:, [0, 2]] = people[:, [0, 2]] / scale_factor  # x, width
                                people[:, [1, 3]] = people[:, [1, 3]] / scale_factor  # y, height
                                people = people.astype(int)
                            except Exception as scale_error:
                                logger.warning(f"Error scaling people detections: {scale_error}")
                                people = np.empty((0, 4), dtype=int)
                        
                        self.people_count = len(people)
                        
                        # Draw rectangles around detected people (limit to 3 for performance)
                        for (x, y, w, h) in people[:3]:
                            cv2.rectangle(analyzed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(analyzed_frame, 'Person', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Face detection with safe parameters
                        faces = self.face_cascade.detectMultiScale(
                            small_gray, 
                            scaleFactor=1.3, 
                            minNeighbors=4,
                            minSize=(40, 40)  # Larger minimum size for better detection
                        )
                        
                        # Debug: Log the type and shape of the detection result
                        logger.debug(f"Face detection result type: {type(faces)}, shape: {getattr(faces, 'shape', 'N/A')}")
                        
                        # Convert to numpy array if it's a tuple or ensure it's an array
                        if isinstance(faces, tuple):
                            faces = np.array(faces)
                        elif not isinstance(faces, np.ndarray):
                            faces = np.array(faces)
                        
                        # Ensure it's a proper array and handle empty case
                        if faces.size == 0:
                            faces = np.empty((0, 4), dtype=int)
                        
                        # Scale coordinates back up if we downscaled
                        if scale_factor < 1.0 and len(faces) > 0 and faces.size > 0:
                            try:
                                faces = faces.astype(float)
                                faces[:, [0, 2]] = faces[:, [0, 2]] / scale_factor  # x, width
                                faces[:, [1, 3]] = faces[:, [1, 3]] / scale_factor  # y, height
                                faces = faces.astype(int)
                            except Exception as scale_error:
                                logger.warning(f"Error scaling face detections: {scale_error}")
                                faces = np.empty((0, 4), dtype=int)
                        
                        self.faces_count = len(faces)
                        
                        # Draw rectangles around detected faces (limit to 3 for performance)
                        for (x, y, w, h) in faces[:3]:
                            cv2.rectangle(analyzed_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            cv2.putText(analyzed_frame, 'Face', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    except Exception as detection_error:
                        logger.warning(f"Detection error (non-fatal): {detection_error}")
                        # Continue with motion detection only
                
                # Update analysis results
                self.last_analysis_results = {
                    "motion_detected": self.motion_detected,
                    "people_count": self.people_count,
                    "faces_count": self.faces_count,
                    "timestamp": self.analysis_frame_count
                }
            
            # Draw analysis overlay (lighter version)
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
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, config.RTSP_BUFFER_SIZE)
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
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer to reduce latency
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
                await self._update_camera_webrtc_url(camera_id, None)
                
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
    
    async def _update_camera_webrtc_url(self, camera_id: str, webrtc_url: Optional[str]) -> Dict[str, Any]:
        """Update camera in NestJS backend with WebRTC URL."""
        try:
            # Import camera service to reuse authentication
            from service.cameras import camera_service
            
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


# Global service instance
video_streaming_service = VideoStreamingService()