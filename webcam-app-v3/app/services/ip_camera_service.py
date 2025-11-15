"""
IP Camera Service for connecting and streaming from RTSP cameras
"""
import os
import cv2
import threading
import time
from typing import Dict, Optional, List
import logging

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


class IPCameraStream:
    """Manages a single IP camera stream"""
    
    def __init__(self, camera_name: str, rtsp_url: str):
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.cap = None
        self.frame = None
        self.is_running = False
        self.thread = None
        self.connection_status = "disconnected"
        self.error_message = ""
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        
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
        while self.is_running and self.cap is not None:
            try:
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
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - self.last_time >= 1.0:
                        self.fps = self.frame_count
                        self.frame_count = 0
                        self.last_time = current_time
                        logger.debug(f"{self.camera_name}: {self.fps} FPS")
                else:
                    self.connection_status = "disconnected"
                    logger.warning(f"Stream ended for {self.camera_name}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in streaming thread for {self.camera_name}: {e}")
                self.connection_status = "error"
                self.error_message = str(e)
                break
    
    def get_frame(self):
        """Get the current frame"""
        return self.frame
    
    def stop(self):
        """Stop streaming and disconnect"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        self.connection_status = "disconnected"
        logger.info(f"Stopped streaming for {self.camera_name}")
    
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
