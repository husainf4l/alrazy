#!/usr/bin/env python3
"""
Simple test script to check video functionality in the FastAPI application
"""
import asyncio
import cv2
import logging
import sys
import base64
from camera_service import RTSPCamera

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_opencv_installation():
    """Test if OpenCV is properly installed and working"""
    try:
        logger.info(f"OpenCV version: {cv2.__version__}")
        
        # Test video capture with a dummy device
        cap = cv2.VideoCapture(0)  # Try webcam
        is_opened = cap.isOpened()
        cap.release()
        
        if is_opened:
            logger.info("✅ OpenCV can access video devices")
        else:
            logger.info("ℹ️ No webcam found, but OpenCV is working")
            
        return True
    except Exception as e:
        logger.error(f"❌ OpenCV test failed: {e}")
        return False

def test_rtsp_camera_simulation():
    """Test RTSP camera class with a simulated URL"""
    try:
        logger.info("🎥 Testing RTSP Camera class...")
        
        # Test with a sample RTSP URL (this will fail connection but test the class)
        rtsp_url = "rtsp://admin:password@192.168.1.100:554/stream"
        camera = RTSPCamera(rtsp_url)
        
        logger.info(f"📡 Testing connection to: {rtsp_url}")
        
        # This will likely fail but should handle gracefully
        success = camera.connect()
        
        if success:
            logger.info("✅ RTSP connection successful")
            camera.disconnect()
        else:
            logger.info("ℹ️ RTSP connection failed (expected if no camera available)")
            
        return True
    except Exception as e:
        logger.error(f"❌ RTSP camera test failed: {e}")
        return False

def test_video_encoding():
    """Test video encoding functionality"""
    try:
        import numpy as np
        
        logger.info("🖼️ Testing video encoding...")
        
        # Create a simple test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 150, 200)  # Fill with a color
        
        # Test JPEG encoding
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, buffer = cv2.imencode('.jpg', test_image, encode_param)
        
        # Test base64 encoding
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        logger.info(f"✅ Successfully encoded test image to base64 ({len(image_b64)} chars)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Video encoding test failed: {e}")
        return False

async def test_async_functionality():
    """Test async functionality"""
    try:
        logger.info("🔄 Testing async functionality...")
        
        # Simple async test
        await asyncio.sleep(0.1)
        
        logger.info("✅ Async functionality working")
        return True
        
    except Exception as e:
        logger.error(f"❌ Async test failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are available"""
    dependencies = {
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'base64': 'Base64 encoding',
        'asyncio': 'Async functionality',
        'logging': 'Logging'
    }
    
    missing_deps = []
    
    for module, name in dependencies.items():
        try:
            __import__(module)
            logger.info(f"✅ {name} is available")
        except ImportError:
            logger.error(f"❌ {name} is missing")
            missing_deps.append(name)
    
    return len(missing_deps) == 0

async def main():
    """Main test function"""
    logger.info("🧪 Starting video functionality tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Dependencies Check", lambda: test_dependencies()),
        ("OpenCV Installation", lambda: test_opencv_installation()),
        ("Video Encoding", lambda: test_video_encoding()),
        ("RTSP Camera Class", lambda: test_rtsp_camera_simulation()),
        ("Async Functionality", test_async_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Video functionality appears to be working.")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Test runner failed: {e}")
        sys.exit(1)
