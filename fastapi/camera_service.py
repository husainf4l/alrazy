import cv2
import logging

logger = logging.getLogger(__name__)

class RTSPCamera:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.is_connected = False

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
                    
            logger.error(f"Failed to connect to RTSP stream with any backend: {self.rtsp_url}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream: {e}")
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            return False