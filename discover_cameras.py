#!/usr/bin/env python3
"""
Script to discover available RTSP camera channels on an IP camera.
This will test various common RTSP path naming conventions.
"""

import cv2
import time
import sys

def test_rtsp_connection(url, timeout=10):
    """Test if an RTSP URL is accessible."""
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
        
        if cap.isOpened():
            # Try to read a frame to verify the stream works
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                cap.release()
                return True, f"{width}x{height}"
            else:
                cap.release()
                return False, "No frames available"
        else:
            cap.release()
            return False, "Cannot open stream"
    except Exception as e:
        return False, str(e)

def discover_camera_channels():
    """Discover available camera channels using common naming conventions."""
    
    base_ip = "192.168.1.186"
    username = "admin"
    password = "tt55oo77"
    port = "554"
    
    # Common RTSP path patterns for IP cameras
    patterns = [
        # Hikvision/Dahua style
        "/Streaming/Channels/{channel}01",
        "/Streaming/Channels/{channel}",
        "/Streaming/channels/{channel}01", 
        "/Streaming/channels/{channel}",
        
        # Generic patterns
        "/cam/realmonitor?channel={channel}&subtype=0",
        "/cam/realmonitor?channel={channel}&subtype=1", 
        "/channel{channel}",
        "/ch{channel:02d}",
        "/stream{channel}",
        "/video{channel}",
        
        # ONVIF style
        "/onvif-media/media.amp?profile=profile_{channel}_h264&sessiontimeout=60&streamtype=unicast",
        "/media/video{channel}",
        
        # Axis style
        "/axis-media/media.amp?videocodec=h264&camera={channel}",
        
        # Foscam style  
        "/videoMain?usr={username}&pwd={password}",
        "/video.cgi?resolution=VGA&usr={username}&pwd={password}",
        
        # Generic numbered patterns
        "/{channel}",
        "/video/{channel}",
        "/live/{channel}",
        "/stream/{channel}",
        "/ch{channel}/stream_1",
        "/ch{channel}/stream_2"
    ]
    
    print(f"🔍 Discovering RTSP camera channels on {base_ip}")
    print("=" * 60)
    
    working_channels = []
    
    # Test channels 1-8 (most cameras have 4-8 channels max)
    for channel in range(1, 9):
        print(f"\n📹 Testing Channel {channel}:")
        print("-" * 30)
        
        for pattern in patterns:
            # Format the pattern with channel number and credentials
            try:
                if "{username}" in pattern or "{password}" in pattern:
                    path = pattern.format(channel=channel, username=username, password=password)
                else:
                    path = pattern.format(channel=channel)
                
                url = f"rtsp://{username}:{password}@{base_ip}:{port}{path}"
                
                print(f"  Testing: {path}", end=" ... ")
                
                success, info = test_rtsp_connection(url, timeout=8)
                
                if success:
                    print(f"✅ SUCCESS ({info})")
                    working_channels.append({
                        'channel': channel,
                        'url': url,
                        'path': path,
                        'resolution': info
                    })
                    break  # Found working channel, move to next
                else:
                    print(f"❌ Failed ({info})")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Small delay between channel tests
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("🎯 DISCOVERY RESULTS")
    print("=" * 60)
    
    if working_channels:
        print(f"✅ Found {len(working_channels)} working camera channels:")
        print()
        
        for cam in working_channels:
            print(f"📹 Channel {cam['channel']}:")
            print(f"   URL: {cam['url']}")
            print(f"   Path: {cam['path']}")
            print(f"   Resolution: {cam['resolution']}")
            print()
        
        # Generate camera service configuration
        print("🔧 Camera Service Configuration:")
        print("-" * 40)
        print("cameras = {")
        for cam in working_channels:
            print(f'    {cam["channel"]}: RTSPCamera("{cam["url"]}"),')
        print("}")
        
    else:
        print("❌ No working camera channels found!")
        print()
        print("💡 Suggestions:")
        print("   - Check if the IP address is correct")
        print("   - Verify username/password credentials") 
        print("   - Ensure the camera is powered on and accessible")
        print("   - Try accessing the camera's web interface first")

if __name__ == "__main__":
    print("🚀 Starting RTSP Camera Channel Discovery...")
    print()
    discover_camera_channels()
