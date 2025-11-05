#!/usr/bin/env python3
"""
Quick camera connection test script
"""

import cv2
import sys

# Camera URLs from notes.md
cameras = {
    "Camera 1 - Room1": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/102",
    "Camera 2 - Room2": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/202", 
    "Camera 3 - Room3": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/302",
    "Camera 4 - Room4": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/402"
}

def test_camera(name, url):
    """Test individual camera connection"""
    print(f"Testing {name}...")
    
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Try to read a frame
        ret, frame = cap.read()
        
        if ret and frame is not None:
            h, w = frame.shape[:2]
            print(f"  ✅ Connected - Resolution: {w}x{h}")
            cap.release()
            return True
        else:
            print(f"  ❌ Failed to read frame")
            cap.release()
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Test all cameras"""
    print("🔍 Testing Brinks Camera System Connections\n")
    
    results = {}
    working_count = 0
    
    for name, url in cameras.items():
        results[name] = test_camera(name, url)
        if results[name]:
            working_count += 1
        print()
    
    print(f"📊 Results: {working_count}/{len(cameras)} cameras working")
    
    if working_count == len(cameras):
        print("🎉 All cameras are working perfectly!")
    elif working_count > 0:
        print(f"⚠️  {len(cameras) - working_count} cameras need attention")
    else:
        print("❌ No cameras are working. Check network and credentials.")
    
    return working_count > 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)