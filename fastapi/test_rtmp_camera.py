#!/usr/bin/env python3
"""
Test script for RTMP camera connection
"""
import cv2
import time

def test_rtmp_camera():
    rtmp_url = "rtmp://192.168.1.164:1935/live/mystream"
    print(f"Testing RTMP camera connection: {rtmp_url}")
    
    # Try to connect to the RTMP stream
    cap = cv2.VideoCapture(rtmp_url)
    
    if not cap.isOpened():
        print("❌ Failed to connect to RTMP stream")
        return False
    
    # Get stream properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    backend = cap.get(cv2.CAP_PROP_BACKEND)
    
    print(f"✅ Successfully connected to RTMP stream")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Backend: {backend}")
    
    # Test frame capture
    frame_count = 0
    test_duration = 10  # Test for 10 seconds
    start_time = time.time()
    
    print(f"\nTesting frame capture for {test_duration} seconds...")
    
    while time.time() - start_time < test_duration:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            if frame_count % 30 == 0:  # Print every 30 frames
                elapsed = time.time() - start_time
                print(f"   Captured {frame_count} frames in {elapsed:.1f}s")
        else:
            print("❌ Failed to read frame")
            break
    
    cap.release()
    
    if frame_count > 0:
        actual_fps = frame_count / (time.time() - start_time)
        print(f"\n✅ Test completed successfully!")
        print(f"   Total frames captured: {frame_count}")
        print(f"   Actual FPS: {actual_fps:.2f}")
        return True
    else:
        print("\n❌ No frames captured")
        return False

if __name__ == "__main__":
    success = test_rtmp_camera()
    if success:
        print("\n🎉 RTMP camera is ready to be added to the security system!")
    else:
        print("\n⚠️  RTMP camera connection failed. Please check the stream URL and network connectivity.")
