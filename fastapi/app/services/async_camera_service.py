"""
Async Camera Service for the Al Razy Pharmacy Security System.
Following async best practices with proper resource management.
"""
import asyncio
import cv2
import numpy as np
import base64
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)


class AsyncRTSPCamera:
    """Async RTSP Camera service with proper resource management."""
    
    def __init__(self, rtsp_url: str, executor: ThreadPoolExecutor = None):
        self.rtsp_url = rtsp_url
        self.executor = executor
        self.cap = None
        self.is_connected = False
        self.current_frame = None
        self.frame_lock = asyncio.Lock()
        self.running = False
        self.capture_task = None
        self.background_frame = None
        self._connection_lock = asyncio.Lock()
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self) -> bool:
        """Connect to the RTSP stream asynchronously."""
        async with self._connection_lock:
            if self.is_connected:
                return True
                
            try:
                # Run blocking opencv operations in thread pool
                loop = asyncio.get_event_loop()
                
                # Clean up any existing connection
                if self.cap is not None:
                    await loop.run_in_executor(self.executor, self.cap.release)
                    self.cap = None
                
                # Try different backends
                backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
                
                for backend in backends:
                    try:
                        # Create video capture in thread pool
                        self.cap = await loop.run_in_executor(
                            self.executor, 
                            self._create_video_capture, 
                            backend
                        )
                        
                        if self.cap and await loop.run_in_executor(
                            self.executor, 
                            self.cap.isOpened
                        ):
                            # Test frame capture
                            test_result = await loop.run_in_executor(
                                self.executor,
                                self._test_frame_capture
                            )
                            
                            if test_result:
                                self.is_connected = True
                                logger.info(f"✅ Connected to RTSP stream: {self.rtsp_url}")
                                return True
                        
                        # Clean up failed attempt
                        if self.cap:
                            await loop.run_in_executor(self.executor, self.cap.release)
                            self.cap = None
                            
                    except Exception as e:
                        logger.warning(f"Backend {backend} failed: {e}")
                        continue
                
                logger.error(f"❌ Failed to connect to RTSP stream: {self.rtsp_url}")
                return False
                
            except Exception as e:
                logger.error(f"Error connecting to RTSP stream: {e}")
                return False
    
    def _create_video_capture(self, backend) -> cv2.VideoCapture:
        """Create video capture with specific backend (runs in thread pool)."""
        cap = cv2.VideoCapture(self.rtsp_url, backend)
        if cap.isOpened():
            # Configure for better RTSP handling
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
        return cap
    
    def _test_frame_capture(self) -> bool:
        """Test frame capture (runs in thread pool)."""
        if not self.cap or not self.cap.isOpened():
            return False
            
        for _ in range(3):
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                logger.info(f"Stream resolution: {frame.shape[1]}x{frame.shape[0]}")
                return True
        return False
    
    async def disconnect(self):
        """Disconnect from the RTSP stream asynchronously."""
        async with self._connection_lock:
            self.running = False
            
            # Cancel capture task
            if self.capture_task and not self.capture_task.done():
                self.capture_task.cancel()
                try:
                    await self.capture_task
                except asyncio.CancelledError:
                    pass
            
            # Release camera in thread pool
            if self.cap:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.cap.release)
                self.cap = None
                
            self.is_connected = False
            self.current_frame = None
            logger.info("🔌 Disconnected from RTSP stream")
    
    async def start_capture(self) -> bool:
        """Start capturing frames asynchronously."""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        if self.capture_task and not self.capture_task.done():
            return True  # Already running
            
        self.running = True
        self.capture_task = asyncio.create_task(self._capture_frames())
        return True
    
    async def _capture_frames(self):
        """Capture frames continuously using asyncio."""
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                if not self.is_connected or not self.cap:
                    logger.warning("📷 Camera disconnected, attempting to reconnect...")
                    if not await self.connect():
                        await asyncio.sleep(2)
                        continue
                
                # Capture frame in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                frame_data = await loop.run_in_executor(
                    self.executor,
                    self._capture_single_frame_sync
                )
                
                if frame_data is not None:
                    async with self.frame_lock:
                        if self.current_frame is not None:
                            del self.current_frame
                        self.current_frame = frame_data.copy()
                    
                    consecutive_failures = 0
                    await asyncio.sleep(0.1)  # ~10 FPS limit
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error("Too many consecutive failures, attempting to reconnect...")
                        self.is_connected = False
                        await self.disconnect()
                        consecutive_failures = 0
                        await asyncio.sleep(2)
                    else:
                        await asyncio.sleep(0.5)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error capturing frame: {e}")
                consecutive_failures += 1
                await asyncio.sleep(1)
    
    def _capture_single_frame_sync(self) -> Optional[np.ndarray]:
        """Capture single frame synchronously (runs in thread pool)."""
        if not self.cap or not self.cap.isOpened():
            return None
            
        try:
            # Skip frames to avoid corrupted data
            for _ in range(3):
                ret, _ = self.cap.read()
                if not ret:
                    break
            
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                if len(frame.shape) == 3 and frame.shape[0] > 0 and frame.shape[1] > 0:
                    return frame
            return None
        except Exception as e:
            logger.error(f"Error in sync frame capture: {e}")
            return None
    
    async def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame asynchronously."""
        async with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    async def capture_single_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame directly from camera."""
        if not self.is_connected or not self.cap:
            if not await self.connect():
                return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._capture_single_frame_sync
        )
    
    async def get_frame_as_base64(self, quality: int = 85) -> Optional[str]:
        """Get current frame as base64 encoded JPEG."""
        frame = await self.get_current_frame()
        if frame is None:
            return None
            
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._encode_frame_to_base64,
            frame,
            quality
        )
    
    def _encode_frame_to_base64(self, frame: np.ndarray, quality: int) -> str:
        """Encode frame to base64 (runs in thread pool)."""
        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            del buffer
            return frame_b64
        except Exception as e:
            logger.error(f"Error encoding frame to base64: {e}")
            return ""
    
    async def detect_motion(self, threshold: int = 25, min_area: int = 1000) -> tuple[bool, Optional[np.ndarray]]:
        """Async motion detection."""
        current_frame = await self.get_current_frame()
        if current_frame is None:
            return False, None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._detect_motion_sync,
            current_frame,
            threshold,
            min_area
        )
    
    def _detect_motion_sync(self, frame: np.ndarray, threshold: int, min_area: int) -> tuple[bool, Optional[np.ndarray]]:
        """Synchronous motion detection (runs in thread pool)."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # Initialize background if not exists
            if self.background_frame is None:
                self.background_frame = gray
                return False, frame
            
            # Compute difference
            frame_delta = cv2.absdiff(self.background_frame, gray)
            thresh = cv2.threshold(frame_delta, threshold, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_detected = False
            annotated_frame = frame.copy()
            
            for contour in contours:
                if cv2.contourArea(contour) > min_area:
                    motion_detected = True
                    # Draw rectangle around motion
                    (x, y, w, h) = cv2.boundingRect(contour)
                    cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Update background
            self.background_frame = cv2.addWeighted(self.background_frame, 0.95, gray, 0.05, 0)
            
            return motion_detected, annotated_frame
            
        except Exception as e:
            logger.error(f"Error in motion detection: {e}")
            return False, frame
    
    async def get_stream_info(self) -> Dict[str, Any]:
        """Get stream information asynchronously."""
        if not self.is_connected or not self.cap:
            return {"status": "disconnected"}
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                self.executor,
                self._get_stream_info_sync
            )
            return info
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_stream_info_sync(self) -> Dict[str, Any]:
        """Get stream info synchronously (runs in thread pool)."""
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
        except Exception:
            return {"status": "error"}


class AsyncCameraManager:
    """Async camera manager with proper resource management."""
    
    def __init__(self, max_workers: int = 4):
        self.cameras: Dict[int, AsyncRTSPCamera] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._manager_lock = asyncio.Lock()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()
        self.executor.shutdown(wait=True)
    
    async def add_camera(self, camera_id: int, rtsp_url: str) -> bool:
        """Add a camera to the manager."""
        async with self._manager_lock:
            if camera_id in self.cameras:
                await self.cameras[camera_id].disconnect()
            
            self.cameras[camera_id] = AsyncRTSPCamera(rtsp_url, self.executor)
            return True
    
    async def initialize_camera(self, camera_id: int) -> bool:
        """Initialize a specific camera."""
        if camera_id not in self.cameras:
            return False
        return await self.cameras[camera_id].start_capture()
    
    async def initialize_all_cameras(self) -> Dict[int, str]:
        """Initialize all cameras concurrently."""
        if not self.cameras:
            return {}
        
        # Use asyncio.gather for concurrent initialization
        tasks = []
        camera_ids = []
        
        for camera_id, camera in self.cameras.items():
            tasks.append(camera.start_capture())
            camera_ids.append(camera_id)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_dict = {}
        for camera_id, result in zip(camera_ids, results):
            if isinstance(result, Exception):
                status_dict[camera_id] = f"error: {str(result)}"
            else:
                status_dict[camera_id] = "connected" if result else "failed"
        
        return status_dict
    
    async def get_camera_frame(self, camera_id: int) -> Optional[str]:
        """Get frame from specific camera as base64."""
        if camera_id not in self.cameras:
            return None
        
        # Try background frame first, then direct capture
        frame_b64 = await self.cameras[camera_id].get_frame_as_base64()
        if frame_b64:
            return frame_b64
        
        # Fallback to direct capture
        frame = await self.cameras[camera_id].capture_single_frame()
        if frame is not None:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self.cameras[camera_id]._encode_frame_to_base64,
                frame,
                85
            )
        
        return None
    
    async def get_all_camera_frames(self) -> Dict[int, Optional[str]]:
        """Get frames from all cameras concurrently."""
        if not self.cameras:
            return {}
        
        tasks = [
            self.get_camera_frame(camera_id) 
            for camera_id in self.cameras.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        frames_dict = {}
        for camera_id, result in zip(self.cameras.keys(), results):
            if isinstance(result, Exception):
                frames_dict[camera_id] = None
            else:
                frames_dict[camera_id] = result
        
        return frames_dict
    
    async def detect_motion_all_cameras(self) -> Dict[int, Dict[str, Any]]:
        """Detect motion in all cameras concurrently."""
        if not self.cameras:
            return {}
        
        tasks = []
        camera_ids = []
        
        for camera_id, camera in self.cameras.items():
            tasks.append(camera.detect_motion())
            camera_ids.append(camera_id)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        motion_dict = {}
        for camera_id, result in zip(camera_ids, results):
            if isinstance(result, Exception):
                motion_dict[camera_id] = {
                    "motion_detected": False,
                    "frame": None,
                    "error": str(result),
                    "timestamp": time.time()
                }
            else:
                motion_detected, annotated_frame = result
                frame_b64 = None
                if annotated_frame is not None:
                    frame_b64 = await self.cameras[camera_id]._encode_frame_to_base64(annotated_frame, 85)
                
                motion_dict[camera_id] = {
                    "motion_detected": motion_detected,
                    "frame": frame_b64,
                    "timestamp": time.time()
                }
        
        return motion_dict
    
    async def get_all_cameras_info(self) -> Dict[int, Dict[str, Any]]:
        """Get info from all cameras concurrently."""
        if not self.cameras:
            return {}
        
        tasks = [
            camera.get_stream_info() 
            for camera in self.cameras.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        info_dict = {}
        for camera_id, result in zip(self.cameras.keys(), results):
            if isinstance(result, Exception):
                info_dict[camera_id] = {"status": "error", "error": str(result)}
            else:
                result["camera_id"] = camera_id
                info_dict[camera_id] = result
        
        return info_dict
    
    async def cleanup_camera(self, camera_id: int):
        """Cleanup specific camera."""
        if camera_id in self.cameras:
            await self.cameras[camera_id].disconnect()
            del self.cameras[camera_id]
    
    async def cleanup_all(self):
        """Cleanup all cameras."""
        tasks = [camera.disconnect() for camera in self.cameras.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.cameras.clear()
    
    def get_available_cameras(self) -> List[int]:
        """Get list of available camera IDs."""
        return list(self.cameras.keys())


# Global async camera manager
_camera_manager: Optional[AsyncCameraManager] = None


async def get_camera_manager() -> AsyncCameraManager:
    """Get the global camera manager instance."""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = AsyncCameraManager()
        
        # Load cameras from config
        from app.core.config import get_settings
        settings = get_settings()
        
        if settings.camera_config:
            for camera_id, path in settings.camera_config.cameras.items():
                rtsp_url = f"rtsp://{settings.camera_config.username}:{settings.camera_config.password}@{settings.camera_config.base_ip}:{settings.camera_config.port}{path}"
                await _camera_manager.add_camera(int(camera_id), rtsp_url)
    
    return _camera_manager


# Async wrapper functions for backward compatibility
async def initialize_camera(camera_id: int) -> bool:
    """Initialize a specific camera."""
    manager = await get_camera_manager()
    return await manager.initialize_camera(camera_id)


async def initialize_all_cameras() -> Dict[int, str]:
    """Initialize all cameras."""
    manager = await get_camera_manager()
    return await manager.initialize_all_cameras()


async def get_camera_frame(camera_id: int) -> Optional[str]:
    """Get camera frame as base64."""
    manager = await get_camera_manager()
    return await manager.get_camera_frame(camera_id)


async def get_camera_info(camera_id: int) -> Dict[str, Any]:
    """Get camera info."""
    manager = await get_camera_manager()
    all_info = await manager.get_all_cameras_info()
    return all_info.get(camera_id, {"status": "not_found", "camera_id": camera_id})


async def get_all_cameras_info() -> Dict[int, Dict[str, Any]]:
    """Get all cameras info."""
    manager = await get_camera_manager()
    return await manager.get_all_cameras_info()


async def detect_motion_in_frame(camera_id: int) -> Dict[str, Any]:
    """Detect motion in specific camera."""
    manager = await get_camera_manager()
    all_motion = await manager.detect_motion_all_cameras()
    return all_motion.get(camera_id, {
        "motion_detected": False,
        "frame": None,
        "timestamp": time.time(),
        "error": f"Camera {camera_id} not found"
    })


async def detect_motion_all_cameras() -> Dict[int, Dict[str, Any]]:
    """Detect motion in all cameras."""
    manager = await get_camera_manager()
    return await manager.detect_motion_all_cameras()


async def cleanup_camera(camera_id: int = None):
    """Cleanup camera resources."""
    manager = await get_camera_manager()
    if camera_id is not None:
        await manager.cleanup_camera(camera_id)
    else:
        await manager.cleanup_all()


async def get_available_cameras() -> List[int]:
    """Get available camera IDs."""
    manager = await get_camera_manager()
    return manager.get_available_cameras()
