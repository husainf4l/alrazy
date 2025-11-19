#!/usr/bin/env python3
"""
Script to check actual FPS and stream properties from IP cameras
"""
import cv2
import json

def check_camera_stream(name, url):
    """Check camera stream properties"""
    print(f"\n{'='*60}")
    print(f"Camera: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    try:
        cap = cv2.VideoCapture(url)
        
        if not cap.isOpened():
            print("❌ Failed to open stream")
            return
        
        # Get stream properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        backend = cap.getBackendName()
        
        print(f"Backend: {backend}")
        print(f"Resolution: {int(width)}x{int(height)}")
        print(f"Codec: {codec}")
        print(f"Reported FPS: {fps}")
        
        # Test actual FPS by capturing frames
        print("\nTesting actual capture rate...")
        import time
        frame_count = 0
        start_time = time.time()
        test_duration = 3.0  # Test for 3 seconds
        
        while (time.time() - start_time) < test_duration:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed = time.time() - start_time
        actual_fps = frame_count / elapsed
        
        print(f"Captured {frame_count} frames in {elapsed:.2f} seconds")
        print(f"✅ Actual FPS: {actual_fps:.2f}")
        
        cap.release()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Load camera config
    with open('config/cameras.json', 'r') as f:
        config = json.load(f)
    
    cameras = config['streams']
    
    print("Checking camera stream properties...")
    print("This will take about 15 seconds (3 seconds per camera)")
    
    for name, settings in cameras.items():
        check_camera_stream(name, settings['url'])
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    print("\nIf FPS is low (5-6), you need to:")
    print("1. Login to NVR web interface")
    print("   - http://192.168.1.186 (cameras 2,3,4)")
    print("   - http://192.168.1.219 (cameras 5,6)")
    print("2. Go to: Configuration → Video/Audio → Video")
    print("3. Increase Frame Rate to 25 or 30 FPS")
    print("4. Set I-Frame Interval to 30")
    print("5. Apply and Save")
