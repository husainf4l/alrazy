import cv2
import numpy as np
import base64
import threading
import time
from typing import Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RTSPCamera:
    """RTSP Camera service for computer vision security applications."""
    
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.is_connected = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.capture_thread = None
        
    def connect(self) -> bool:
        """Connect to the RTSP stream."""
        try:
            # Clean up any existing connection
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            # Try with different backends for better H.264 compatibility
            backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    self.cap = cv2.VideoCapture(self.rtsp_url, backend)
                    
                    # Configure for better RTSP handling
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                    self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                    
                    # Additional settings for RTSP streams
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
                    
                    if self.cap.isOpened():
                        # Test multiple frame reads to ensure stability
                        for _ in range(3):
                            ret, test_frame = self.cap.read()
                            if ret and test_frame is not None:
                                self.is_connected = True
                                logger.info(f"Successfully connected to RTSP stream: {self.rtsp_url}")
                                logger.info(f"Stream resolution: {test_frame.shape[1]}x{test_frame.shape[0]}")
                                logger.info(f"Using backend: {backend}")
                                return True
                        
                        # If we get here, frames are not readable
                        self.cap.release()
                        self.cap = None
                    
                except Exception as backend_error:
                    logger.warning(f"Backend {backend} failed: {backend_error}")
                    if self.cap is not None:
                        self.cap.release()
                        self.cap = None
                    continue
            
            logger.error(f"Failed to connect to RTSP stream with any backend: {self.rtsp_url}")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream: {e}")
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            return False
    
    def disconnect(self):
        """Disconnect from the RTSP stream."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join()
        
        if self.cap:
            self.cap.release()
            self.is_connected = False
            logger.info("Disconnected from RTSP stream")
    
    def start_capture(self):
        """Start capturing frames in a separate thread."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        return True
    
    def _capture_frames(self):
        """Internal method to capture frames continuously."""
        consecutive_failures = 0
        max_failures = 5
        frame_skip_count = 0
        
        while self.running:
            try:
                if not self.cap or not self.cap.isOpened():
                    logger.warning("Camera disconnected, attempting to reconnect...")
                    if not self.connect():
                        time.sleep(2)
                        continue
                
                # Skip some frames to avoid corrupted data
                for _ in range(3):
                    ret, _ = self.cap.read()
                    if not ret:
                        break
                
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    # Validate frame dimensions
                    if len(frame.shape) == 3 and frame.shape[0] > 0 and frame.shape[1] > 0:
                        with self.frame_lock:
                            # Clean up previous frame to prevent memory leaks
                            if self.current_frame is not None:
                                del self.current_frame
                            self.current_frame = frame.copy()
                        consecutive_failures = 0
                        time.sleep(0.1)  # ~10 FPS limit to reduce load
                    else:
                        logger.warning(f"Invalid frame dimensions: {frame.shape}")
                        consecutive_failures += 1
                else:
                    consecutive_failures += 1
                    if consecutive_failures <= 3:  # Only log first few failures
                        logger.warning(f"Failed to read frame from RTSP stream (failure {consecutive_failures})")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("Too many consecutive failures, attempting to reconnect...")
                        self.is_connected = False
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                        consecutive_failures = 0
                        time.sleep(2)
                    else:
                        time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error capturing frame: {e}")
                consecutive_failures += 1
                time.sleep(1)
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame from the RTSP stream."""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame directly from the camera (bypassing background thread)."""
        if not self.is_connected or not self.cap or not self.cap.isOpened():
            logger.warning("Camera not connected, attempting to connect...")
            if not self.connect():
                return None
        
        try:
            # Flush buffer by reading multiple frames
            for _ in range(3):
                ret, _ = self.cap.read()
                if not ret:
                    break
            
            # Capture the actual frame
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                if len(frame.shape) == 3 and frame.shape[0] > 0 and frame.shape[1] > 0:
                    logger.info(f"Successfully captured frame: {frame.shape}")
                    return frame.copy()
                else:
                    logger.warning(f"Invalid frame dimensions: {frame.shape}")
            else:
                logger.warning("Failed to capture frame")
            
        except Exception as e:
            logger.error(f"Error capturing single frame: {e}")
        
        return None
    
    def get_frame_as_base64(self) -> Optional[str]:
        """Get the current frame as base64 encoded JPEG."""
        frame = self.get_current_frame()
        if frame is not None:
            try:
                # Encode with lower quality to reduce memory usage
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                # Clean up buffer
                del buffer
                return frame_b64
            except Exception as e:
                logger.error(f"Error encoding frame to base64: {e}")
        return None
    
    def detect_motion(self, threshold: int = 25, min_area: int = 1000) -> Tuple[bool, Optional[np.ndarray]]:
        """Simple motion detection."""
        current_frame = self.get_current_frame()
        if current_frame is None:
            return False, None
        
        # Convert to grayscale
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Initialize background if not exists
        if not hasattr(self, 'background'):
            self.background = gray
            return False, current_frame
        
        # Compute difference
        frame_delta = cv2.absdiff(self.background, gray)
        thresh = cv2.threshold(frame_delta, threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > min_area:
                motion_detected = True
                # Draw rectangle around motion
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(current_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Update background
        self.background = cv2.addWeighted(self.background, 0.95, gray, 0.05, 0)
        
        return motion_detected, current_frame
    
    def get_stream_info(self) -> dict:
        """Get information about the RTSP stream."""
        if not self.is_connected:
            return {"status": "disconnected"}
        
        try:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            return {
                "status": "connected",
                "width": width,
                "height": height,
                "fps": fps,
                "url": self.rtsp_url
            }
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return {"status": "error", "error": str(e)}


# Global camera
cameras = {
    1: RTSPCamera("rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101"),
    2: RTSPCamera("rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/201"),
    3: RTSPCamera("rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/301"),
    4: RTSPCamera("rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/401"),
    5: RTSPCamera("rtsp://91.240.87.6:554/user=admin&password=&channel=1&stream=0.sdp")
}


def initialize_camera(camera_id: int = 1) -> bool:
    """Initialize the RTSP camera connection."""
    if camera_id in cameras:
        return cameras[camera_id].start_capture()
    return False


def initialize_all_cameras() -> dict:
    """Initialize all cameras and return status."""
    results = {}
    for camera_id in cameras:
        try:
            success = cameras[camera_id].start_capture()
            results[camera_id] = "connected" if success else "failed"
            logger.info(f"Camera {camera_id}: {'connected' if success else 'failed'}")
        except Exception as e:
            results[camera_id] = f"error: {str(e)}"
            logger.error(f"Camera {camera_id} error: {e}")
    return results


def get_camera_frame(camera_id: int = 1):
    """Get current camera frame as base64."""
    if camera_id in cameras:
        # Try to get frame from background thread first
        frame = cameras[camera_id].get_current_frame()
        
        # If no frame from background thread, capture directly
        if frame is None:
            frame = cameras[camera_id].capture_single_frame()
        
        if frame is not None:
            try:
                # Encode with lower quality to reduce memory usage
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                # Clean up buffer
                del buffer
                return frame_b64
            except Exception as e:
                logger.error(f"Error encoding frame to base64: {e}")
    return None


def get_camera_info(camera_id: int = 1):
    """Get camera stream information."""
    if camera_id in cameras:
        info = cameras[camera_id].get_stream_info()
        info["camera_id"] = camera_id
        return info
    return {"status": "not_found", "camera_id": camera_id}


def get_all_cameras_info():
    """Get information for all cameras."""
    all_info = {}
    for camera_id in cameras:
        info = cameras[camera_id].get_stream_info()
        info["camera_id"] = camera_id
        all_info[camera_id] = info
    return all_info


def detect_motion_in_frame(camera_id: int = 1):
    """Detect motion and return result with annotated frame."""
    if camera_id not in cameras:
        return {
            "motion_detected": False,
            "frame": None,
            "timestamp": time.time(),
            "error": f"Camera {camera_id} not found"
        }
    
    # Try to get frame from background thread first, then direct capture
    frame = cameras[camera_id].get_current_frame()
    if frame is None:
        frame = cameras[camera_id].capture_single_frame()
    
    if frame is None:
        return {
            "motion_detected": False,
            "frame": None,
            "timestamp": time.time(),
            "error": "No frame available"
        }
    
    try:
        motion_detected, annotated_frame = cameras[camera_id].detect_motion()
        frame_b64 = None
        
        if annotated_frame is not None:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            _, buffer = cv2.imencode('.jpg', annotated_frame, encode_param)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            del buffer
        
        return {
            "camera_id": camera_id,
            "motion_detected": motion_detected,
            "frame": frame_b64,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error in motion detection for camera {camera_id}: {e}")
        return {
            "motion_detected": False,
            "frame": None,
            "timestamp": time.time(),
            "error": str(e)
        }


def detect_motion_all_cameras():
    """Detect motion in all cameras."""
    results = {}
    for camera_id in cameras:
        results[camera_id] = detect_motion_in_frame(camera_id)
    return results


def cleanup_camera(camera_id: int = None):
    """Clean up camera resources."""
    if camera_id is not None and camera_id in cameras:
        cameras[camera_id].disconnect()
    else:
        # Clean up all cameras
        for camera in cameras.values():
            camera.disconnect()


def get_available_cameras():
    """Get list of available camera IDs."""
    return list(cameras.keys())
