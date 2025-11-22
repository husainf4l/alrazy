"""
IP Camera Service for connecting and streaming from RTSP cameras with multi-camera tracking
"""
import os
import cv2
import threading
import time
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging
import base64
import numpy as np

# Configure GPU for camera processing
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Use GPU 0
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'
os.environ['TF_GPU_THREAD_PER_CORE'] = '2'

# Try to use NVIDIA GPU for video decoding
try:
    import cuda
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)

# Thread pool for frame encoding (non-blocking)
frame_encoder_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="frame_encoder")

# Multi-camera tracking service (lazy loaded)
_tracking_service = None
_tracking_lock = threading.Lock()
_tracking_initializing = False


def init_tracking_service():
    """
    Initialize the multi-camera tracking service eagerly at application startup.
    This prevents blocking on first API call.
    Best Practice: Initialize heavy services during startup, not on-demand.
    """
    global _tracking_service, _tracking_initializing
    
    if _tracking_service is not None:
        return _tracking_service
    
    with _tracking_lock:
        if _tracking_service is None and not _tracking_initializing:
            _tracking_initializing = True
            try:
                logger.info("🚀 Initializing multi-camera tracking service...")
                from app.services.multi_camera_tracking_service import get_multi_camera_tracking_service
                _tracking_service = get_multi_camera_tracking_service()
                logger.info("✅ Multi-camera tracking service initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize tracking service: {e}")
                raise
            finally:
                _tracking_initializing = False
    
    return _tracking_service


def get_tracking_service():
    """
    Get the multi-camera tracking service.
    The service should be initialized during application startup via init_tracking_service().
    """
    global _tracking_service
    
    if _tracking_service is None:
        # Fallback to lazy initialization if not initialized at startup
        logger.warning("⚠️  Tracking service not initialized at startup, initializing now (may cause delay)...")
        return init_tracking_service()
    
    return _tracking_service


class IPCameraStream:
    """Manages a single IP camera stream with SMOOTH LIVE streaming"""
    
    # Smooth streaming settings
    FRAME_CACHE_TTL = 0.0  # No cache - always fresh frames
    JPEG_QUALITY = 75  # Lower for faster encoding (smooth > perfect)
    JPEG_OPTIMIZE = 0  # Disable optimization for speed
    JPEG_PROGRESSIVE = 0  # Disable progressive for faster decode
    
    def __init__(self, camera_name: str, rtsp_url: str, enable_tracking: bool = True):
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.enable_tracking = enable_tracking  # Enable multi-camera tracking
        self.cap = None
        self.frame = None
        self.current_frame = None  # Frame with tracking annotations
        self.detections = []  # Current detections
        self.global_people_count = 0  # Global count across all cameras
        self.frame_lock = threading.Lock()  # Protect frame access
        self.frame_timestamp = 0  # When frame was captured
        self.cached_frame_b64 = None  # Cache for base64 encoded frame
        self.cache_time = 0  # Time when cache was created
        self.frame_etag = None  # ETag for frame caching
        self.frame_etag_time = 0  # Time when ETag was computed
        self.frame_buffer = []  # Buffer of last few frames for smooth delivery
        self.max_buffer_size = 2  # Keep 2 most recent frames
        self.is_running = False
        self.thread = None
        self.connection_status = "disconnected"
        self.error_message = ""
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.encode_lock = threading.Lock()  # Protect frame encoding
        self.dropped_frames = 0  # Track dropped frames for monitoring
        
    def connect(self):
        """Connect to the IP camera with ultra-low latency settings"""
        try:
            # Use FFMPEG backend for better RTSP handling
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # CRITICAL: Set buffer size to 0 for minimum latency (discard old frames)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
            
            # Request maximum FPS from camera
            self.cap.set(cv2.CAP_PROP_FPS, 60)  # Request 60 FPS (camera will provide max available)
            
            # Enable fastest decoding (trade quality for speed)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            
            # Disable auto-exposure and auto-focus for consistent latency
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            # Set transport protocol hints (if supported)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 second timeout
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
            
            # Test if we can read a frame
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.frame = frame
                    self.frame_timestamp = time.time()
                self.connection_status = "connected"
                self.error_message = ""
                logger.info(f"Connected to {self.camera_name} (Low-latency mode: buffer=0, fast decode)")
                return True
            else:
                self.connection_status = "failed"
                self.error_message = "Could not read frames from camera"
                logger.error(f"Failed to read frames from {self.camera_name}")
                return False
                
        except Exception as e:
            self.connection_status = "error"
            self.error_message = str(e)
            logger.error(f"Error connecting to {self.camera_name}: {e}")
            return False
    
    def start_streaming(self):
        """Start the streaming thread"""
        if self.connection_status == "connected":
            self.is_running = True
            self.thread = threading.Thread(target=self._stream_thread, daemon=True)
            self.thread.start()
            logger.info(f"Started streaming thread for {self.camera_name}")
    
    def _stream_thread(self):
        """Thread that continuously reads frames with ultra-low latency optimization and tracking"""
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        frame_skip_threshold = 2  # Skip old frames if buffer has more than this
        
        # Get tracking service if enabled
        tracking_service = None
        if self.enable_tracking:
            try:
                tracking_service = get_tracking_service()
                logger.info(f"Multi-camera tracking enabled for {self.camera_name}")
            except Exception as e:
                logger.warning(f"Could not initialize tracking for {self.camera_name}: {e}")
                self.enable_tracking = False
        
        while self.is_running:
            try:
                if self.cap is None:
                    break
                
                # Direct read - capture every frame for maximum 30 FPS
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    capture_timestamp = time.time()
                    
                    # Process with multi-camera tracking
                    if self.enable_tracking and tracking_service:
                        try:
                            annotated_frame, detections, global_count = tracking_service.process_frame(
                                frame, self.camera_name
                            )
                            
                            # Update tracking results (thread-safe)
                            with self.frame_lock:
                                self.frame = frame  # Original frame
                                self.current_frame = annotated_frame  # Frame with annotations
                                self.detections = detections
                                self.global_people_count = global_count
                                self.frame_timestamp = capture_timestamp
                        except Exception as e:
                            logger.error(f"Tracking error for {self.camera_name}: {e}")
                            # Fallback to original frame on error
                            with self.frame_lock:
                                self.frame = frame
                                self.current_frame = frame
                                self.frame_timestamp = capture_timestamp
                    else:
                        # No tracking - use original frame
                        with self.frame_lock:
                            self.frame = frame
                            self.current_frame = frame
                            self.frame_timestamp = capture_timestamp
                    
                    self.frame_count += 1
                    reconnect_attempts = 0  # Reset reconnect counter on success
                    
                    # Calculate FPS and latency metrics
                    current_time = time.time()
                    if current_time - self.last_time >= 1.0:
                        self.fps = self.frame_count
                        self.frame_count = 0
                        self.last_time = current_time
                        
                        # Log FPS with tracking info
                        if self.enable_tracking:
                            logger.info(f"{self.camera_name}: {self.fps} FPS | Global People: {self.global_people_count}")
                        else:
                            logger.info(f"{self.camera_name}: {self.fps} FPS")
                else:
                    # Frame read failed - try reconnecting
                    reconnect_attempts += 1
                    if reconnect_attempts >= max_reconnect_attempts:
                        self.connection_status = "disconnected"
                        logger.warning(f"Stream ended for {self.camera_name} after {reconnect_attempts} attempts")
                        break
                    else:
                        # Small delay before retry
                        time.sleep(0.05)  # 50ms delay
                        logger.debug(f"Reconnecting to {self.camera_name} (attempt {reconnect_attempts})")
                
                # NO SLEEP - maximize frame rate and minimize latency
                    
            except Exception as e:
                reconnect_attempts += 1
                if reconnect_attempts >= max_reconnect_attempts:
                    logger.error(f"Error in streaming thread for {self.camera_name}: {e}")
                    self.connection_status = "error"
                    self.error_message = str(e)
                    break
                else:
                    logger.warning(f"Error in streaming thread for {self.camera_name}: {e}, retrying...")
                    time.sleep(0.05)  # Wait before retry
            finally:
                # Ensure proper cleanup on exit
                if not self.is_running or reconnect_attempts >= max_reconnect_attempts:
                    logger.info(f"Streaming thread for {self.camera_name} stopped")
    
    def get_frame(self):
        """Get the current frame (thread-safe) - returns frame with tracking if enabled"""
        with self.frame_lock:
            # Return annotated frame if tracking is enabled, otherwise original
            return self.current_frame if self.current_frame is not None else self.frame
    
    def get_frame_b64(self, quality: int = None):
        """Get the current frame as base64-encoded JPEG with smooth continuous streaming"""
        import base64
        
        with self.frame_lock:
            # Get the most recent frame (no age limit - always serve something)
            # This ensures smooth continuous streaming without gaps
            frame_to_use = self.current_frame if self.current_frame is not None else self.frame
            if frame_to_use is None:
                return None
            
            # Copy frame for encoding (release lock quickly)
            frame_to_encode = frame_to_use.copy()
        
        # Use instance quality if not specified
        if quality is None:
            quality = self.JPEG_QUALITY
        else:
            quality = max(70, min(90, quality))  # Clamp to valid range
        
        try:
            # Ultra-fast JPEG encoding for smooth streaming
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, quality,
                cv2.IMWRITE_JPEG_OPTIMIZE, self.JPEG_OPTIMIZE,  # 0 = faster encoding
                cv2.IMWRITE_JPEG_PROGRESSIVE, 0  # Disable progressive for faster decode
            ]
            
            _, buffer = cv2.imencode('.jpg', frame_to_encode, encode_params)
            
            if buffer is None or len(buffer) == 0:
                logger.error(f"Frame encoding failed for {self.camera_name}: empty buffer")
                return None
            
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            frame_data = f"data:image/jpeg;base64,{frame_b64}"
            
            return frame_data
            
        except Exception as e:
            logger.error(f"Error in get_frame_b64 for {self.camera_name}: {e}")
            return None
    
    def get_frame_etag(self):
        """Get ETag for current frame (hash-based for caching)"""
        import hashlib
        
        if self.frame is None:
            return None
        
        try:
            current_time = time.time()
            
            # Compute ETag if not cached or cache TTL expired
            if not self.frame_etag or (current_time - self.frame_etag_time) >= self.FRAME_CACHE_TTL:
                # Create a hash of frame dimensions and content (fast ETag)
                frame_hash = hashlib.md5(self.frame.tobytes()).hexdigest()
                self.frame_etag = f'"{frame_hash}"'
                self.frame_etag_time = current_time
            
            return self.frame_etag
        except Exception as e:
            logger.error(f"Error computing ETag for {self.camera_name}: {e}")
            return None
    
    def stop(self):
        """Stop streaming and disconnect with proper resource cleanup"""
        try:
            # Signal streaming thread to stop
            self.is_running = False
            
            # Wait for thread to finish (with timeout to prevent hanging)
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
                if self.thread.is_alive():
                    logger.warning(f"Streaming thread for {self.camera_name} did not stop within timeout")
            
            # Release video capture resources
            if self.cap:
                try:
                    self.cap.release()
                except Exception as e:
                    logger.warning(f"Error releasing capture for {self.camera_name}: {e}")
            
            # Clear cached data
            self.frame = None
            self.cached_frame_b64 = None
            self.frame_etag = None
            
            self.connection_status = "disconnected"
            logger.info(f"Stopped streaming for {self.camera_name}")
        except Exception as e:
            logger.error(f"Error stopping streaming for {self.camera_name}: {e}")
    
    def get_status(self) -> Dict:
        """Get camera status including tracking information"""
        status = {
            "name": self.camera_name,
            "status": self.connection_status,
            "error": self.error_message,
            "fps": self.fps,
            "has_frame": self.frame is not None,
            "tracking_enabled": self.enable_tracking,
        }
        
        # Add tracking-specific info
        if self.enable_tracking:
            status["detections_count"] = len(self.detections)
            status["global_people_count"] = self.global_people_count
        
        return status


class IPCameraManager:
    """Manages multiple IP cameras"""
    
    def __init__(self):
        self.cameras: Dict[str, IPCameraStream] = {}
        self.lock = threading.Lock()
    
    def add_camera(self, camera_name: str, rtsp_url: str, connect_async: bool = True) -> bool:
        """
        Add and connect to a camera.
        
        Args:
            camera_name: Name of the camera
            rtsp_url: RTSP URL
            connect_async: If True, connect in background (non-blocking, best practice for startup)
        """
        with self.lock:
            if camera_name not in self.cameras:
                camera = IPCameraStream(camera_name, rtsp_url)
                self.cameras[camera_name] = camera
                
                if connect_async:
                    # Connect in background thread (non-blocking for startup)
                    def connect_and_start():
                        try:
                            if camera.connect():
                                camera.start_streaming()
                                logger.info(f"✅ Camera {camera_name} connected and streaming")
                            else:
                                logger.error(f"❌ Failed to connect camera {camera_name}")
                        except Exception as e:
                            logger.error(f"❌ Error starting camera {camera_name}: {e}")
                    
                    connect_thread = threading.Thread(target=connect_and_start, daemon=True)
                    connect_thread.start()
                    return True
                else:
                    # Synchronous connection (blocks, use only when necessary)
                    if camera.connect():
                        camera.start_streaming()
                        return True
                    else:
                        return False
            return True
    
    def remove_camera(self, camera_name: str):
        """Remove a camera"""
        with self.lock:
            if camera_name in self.cameras:
                self.cameras[camera_name].stop()
                del self.cameras[camera_name]
    
    def get_frame(self, camera_name: str) -> Optional[any]:
        """Get frame from a specific camera"""
        with self.lock:
            if camera_name in self.cameras:
                return self.cameras[camera_name].get_frame()
        return None
    
    def get_all_cameras_status(self) -> Dict:
        """Get status of all cameras"""
        with self.lock:
            return {
                name: camera.get_status() 
                for name, camera in self.cameras.items()
            }
    
    def get_global_tracking_stats(self) -> Dict:
        """Get global tracking statistics across all cameras"""
        try:
            tracking_service = get_tracking_service()
            return tracking_service.get_statistics()
        except Exception as e:
            logger.error(f"Error getting global tracking stats: {e}")
            return {
                "error": str(e),
                "total_unique_people": 0,
                "people_per_camera": {},
            }
    
    def stop_all(self):
        """Stop all cameras"""
        with self.lock:
            for camera in self.cameras.values():
                camera.stop()
            self.cameras.clear()


# Global camera manager instance
_camera_manager = None


def get_camera_manager() -> IPCameraManager:
    """Get or create the global camera manager"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = IPCameraManager()
    return _camera_manager
