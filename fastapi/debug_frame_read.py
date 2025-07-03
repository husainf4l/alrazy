#!/usr/bin/env python3

import cv2
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_rtsp_frame_reading():
    """Test RTSP frame reading and diagnose the format issue"""
    
    # Test URL - using one of the cameras (updated with correct IP)
    rtsp_url = "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101"
    
    logger.info(f"Testing frame reading from: {rtsp_url}")
    logger.info(f"OpenCV version: {cv2.__version__}")
    
    # Test with FFmpeg backend (explicit)
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        logger.error("Failed to open RTSP stream")
        return
    
    # Configure minimal settings
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)
    
    logger.info("VideoCapture opened successfully")
    
    # Read several frames to analyze the data
    for i in range(5):
        logger.info(f"\n--- Frame {i+1} ---")
        ret, frame = cap.read()
        
        logger.info(f"ret = {ret}")
        logger.info(f"frame is None: {frame is None}")
        
        if frame is not None:
            logger.info(f"frame type: {type(frame)}")
            logger.info(f"frame shape: {frame.shape}")
            logger.info(f"frame dtype: {frame.dtype}")
            logger.info(f"frame size: {frame.size}")
            logger.info(f"frame ndim: {frame.ndim}")
            
            # Check if it's the raw bytes issue
            if len(frame.shape) == 2 and frame.shape[0] == 1:
                logger.warning(f"ISSUE DETECTED: Frame is reading as raw bytes: {frame.shape}")
                logger.info(f"First 20 bytes: {frame.flat[:20]}")
                
            elif len(frame.shape) == 3:
                logger.info(f"Proper 3D frame detected: H={frame.shape[0]}, W={frame.shape[1]}, C={frame.shape[2]}")
                
            elif len(frame.shape) == 2:
                logger.info(f"2D frame (grayscale): H={frame.shape[0]}, W={frame.shape[1]}")
                
        else:
            logger.error("Frame is None")
    
    cap.release()
    logger.info("Test completed")

if __name__ == "__main__":
    test_rtsp_frame_reading()
