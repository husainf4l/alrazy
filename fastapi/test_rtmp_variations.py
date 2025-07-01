#!/usr/bin/env python3
"""
Test script for RTMP camera connection with different URL variations
"""
import cv2
import time

def test_rtmp_url(url, timeout=10):
    print(f"\n🔍 Testing: {url}")
    
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Wait a bit for connection
        start_time = time.time()
        connected = False
        
        while time.time() - start_time < timeout:
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✅ SUCCESS: Connected and got frame")
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"   Resolution: {width}x{height}")
                    connected = True
                    break
            time.sleep(0.5)
        
        cap.release()
        
        if not connected:
            print(f"❌ FAILED: Timeout after {timeout}s")
        
        return connected
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🔍 Testing RTMP camera with different URL variations...")
    
    base_ip = "192.168.1.164"
    port = "1935"
    
    # Common RTMP URL patterns
    urls_to_test = [
        f"rtmp://{base_ip}:{port}/live/test",
        f"rtmp://{base_ip}:{port}/live/stream",
        f"rtmp://{base_ip}:{port}/live",
        f"rtmp://{base_ip}:{port}/test",
        f"rtmp://{base_ip}:{port}/stream",
        f"rtmp://{base_ip}:{port}/",
        f"rtmp://{base_ip}:{port}/rtmp/live",
        f"rtmp://{base_ip}:{port}/live/cam1",
        f"rtmp://{base_ip}:{port}/cam1",
    ]
    
    successful_urls = []
    
    for url in urls_to_test:
        if test_rtmp_url(url, timeout=5):
            successful_urls.append(url)
    
    print(f"\n{'='*50}")
    if successful_urls:
        print(f"🎉 Found {len(successful_urls)} working RTMP URL(s):")
        for url in successful_urls:
            print(f"   ✅ {url}")
    else:
        print("❌ No working RTMP URLs found")
        print("\n💡 Troubleshooting suggestions:")
        print("   1. Check if the RTMP server is running")
        print("   2. Verify the correct stream path/key")
        print("   3. Check firewall settings")
        print("   4. Try accessing from the device itself")
        print("   5. Check server logs for connection attempts")

if __name__ == "__main__":
    main()
