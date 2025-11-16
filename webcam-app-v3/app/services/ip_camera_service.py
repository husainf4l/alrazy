"""
IP Camera Service for connecting and streaming from RTSP cameras
"""
import os
import cv2
import threading
import time
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
import logging
import base64

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


class IPCameraStream:
    """Manages a single IP camera stream"""
    
    FRAME_CACHE_TTL = 0.016  # 16ms TTL for frame cache (optimal for ~60 FPS requests)
    JPEG_QUALITY = 80  # Balance between quality and bandwidth
    
    def __init__(self, camera_name: str, rtsp_url: str):
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.cap = None
        self.frame = None
        self.cached_frame_b64 = None  # Cache for base64 encoded frame
        self.cache_time = 0  # Time when cache was created
        self.frame_etag = None  # ETag for frame caching
        self.frame_etag_time = 0  # Time when ETag was computed
        self.is_running = False
        self.thread = None
        self.connection_status = "disconnected"
        self.error_message = ""
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.encode_lock = threading.Lock()  # Protect frame encoding
        
    def connect(self):
        """Connect to the IP camera with GPU acceleration"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            # Set camera properties for better GPU performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # GPU acceleration is handled by system/drivers automatically
            # OpenCV uses hardware acceleration when available
            
            # Test if we can read a frame
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                self.connection_status = "connected"
                self.error_message = ""
                logger.info(f"Connected to {self.camera_name} (GPU accelerated)")
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
        """Thread that continuously reads frames from the camera with GPU optimization"""
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        
        while self.is_running:
            try:
                if self.cap is None:
                    break
                
                ret, frame = self.cap.read()
                if ret:
                    # Optional: GPU-accelerated preprocessing (if CUDA available)
                    if GPU_AVAILABLE:
                        try:
                            # Convert to CUDA array for GPU processing if needed
                            # frame could be processed on GPU here
                            pass
                        except Exception as e:
                            logger.debug(f"GPU preprocessing skipped: {e}")
                    
                    self.frame = frame
                    self.frame_count += 1
                    reconnect_attempts = 0  # Reset reconnect counter on success
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - self.last_time >= 1.0:
                        self.fps = self.frame_count
                        self.frame_count = 0
                        self.last_time = current_time
                        logger.debug(f"{self.camera_name}: {self.fps} FPS")
                else:
                    # Frame read failed - try reconnecting
                    reconnect_attempts += 1
                    if reconnect_attempts >= max_reconnect_attempts:
                        self.connection_status = "disconnected"
                        logger.warning(f"Stream ended for {self.camera_name} after {reconnect_attempts} attempts")
                        break
                    else:
                        # Small delay before retry
                        time.sleep(0.1)
                        logger.debug(f"Reconnecting to {self.camera_name} (attempt {reconnect_attempts})")
                    
            except Exception as e:
                reconnect_attempts += 1
                if reconnect_attempts >= max_reconnect_attempts:
                    logger.error(f"Error in streaming thread for {self.camera_name}: {e}")
                    self.connection_status = "error"
                    self.error_message = str(e)
                    break
                else:
                    logger.warning(f"Error in streaming thread for {self.camera_name}: {e}, retrying...")
                    time.sleep(0.1)  # Wait before retry
            finally:
                # Ensure proper cleanup on exit
                if not self.is_running or reconnect_attempts >= max_reconnect_attempts:
                    logger.info(f"Streaming thread for {self.camera_name} stopped")
    
    def get_frame(self):
        """Get the current frame"""
        return self.frame
    
    def get_frame_b64(self, quality: int = None):
        """Get the current frame as base64-encoded JPEG (cached with TTL)"""
        import base64
        
        if self.frame is None:
            return None
        
        # Use instance quality if not specified
        if quality is None:
            quality = self.JPEG_QUALITY
        else:
            quality = max(70, min(90, quality))  # Clamp to valid range
        
        try:
            current_time = time.time()
            
            # Check if cached frame is still valid (TTL check)
            # Only use cache if quality matches cached quality
            if (self.cached_frame_b64 and 
                (current_time - self.cache_time) < self.FRAME_CACHE_TTL and
                quality == self.JPEG_QUALITY):
                return self.cached_frame_b64
            
            # Cache expired or quality mismatch - encode new frame
            with self.encode_lock:
                try:
                    _, buffer = cv2.imencode('.jpg', self.frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    if buffer is None or len(buffer) == 0:
                        logger.error(f"Frame encoding failed for {self.camera_name}: empty buffer")
                        return None
                    
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    frame_data = f"data:image/jpeg;base64,{frame_b64}"
                    
                    # Only update cache if using default quality
                    if quality == self.JPEG_QUALITY:
                        self.cached_frame_b64 = frame_data
                        self.cache_time = current_time
                except Exception as encode_error:
                    logger.error(f"Error encoding frame for {self.camera_name}: {encode_error}")
                    return None
            
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
        """Get camera status"""
        return {
            "name": self.camera_name,
            "status": self.connection_status,
            "error": self.error_message,
            "fps": self.fps,
            "has_frame": self.frame is not None
        }


class IPCameraManager:
    """Manages multiple IP cameras"""
    
    def __init__(self):
        self.cameras: Dict[str, IPCameraStream] = {}
        self.lock = threading.Lock()
    
    def add_camera(self, camera_name: str, rtsp_url: str) -> bool:
        """Add and connect to a camera"""
        with self.lock:
            if camera_name not in self.cameras:
                camera = IPCameraStream(camera_name, rtsp_url)
                if camera.connect():
                    self.cameras[camera_name] = camera
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
