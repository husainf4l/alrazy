#!/usr/bin/env python3

import asyncio
import cv2
import numpy as np
import logging
from av import VideoFrame
import fractions

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_vp8_encoding():
    """Test VP8 encoding with different frame formats"""
    
    logger.info("Testing VP8 encoding with aiortc...")
    
    try:
        from aiortc import VideoStreamTrack
        from aiortc.codecs import get_encoder
        
        # Create a test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[100:380, 100:540] = (50, 100, 200)  # Add some color
        
        logger.info(f"Test frame created: shape={test_frame.shape}, dtype={test_frame.dtype}")
        
        # Convert to RGB (WebRTC standard)
        frame_rgb = cv2.cvtColor(test_frame, cv2.COLOR_BGR2RGB)
        logger.info(f"RGB frame: shape={frame_rgb.shape}, dtype={frame_rgb.dtype}")
        
        # Ensure frame is contiguous
        if not frame_rgb.flags['C_CONTIGUOUS']:
            frame_rgb = np.ascontiguousarray(frame_rgb)
            logger.info("Made frame contiguous")
        
        # Create VideoFrame
        av_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        av_frame.pts = 0
        av_frame.time_base = fractions.Fraction(1, 30)
        
        logger.info(f"AV frame created: format={av_frame.format}, width={av_frame.width}, height={av_frame.height}")
        
        # Try to get VP8 encoder
        try:
            encoder = get_encoder("vp8")
            logger.info(f"VP8 encoder available: {encoder}")
        except Exception as encoder_error:
            logger.error(f"VP8 encoder error: {encoder_error}")
            
        logger.info("✅ VP8 encoding test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ VP8 encoding test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vp8_encoding())
