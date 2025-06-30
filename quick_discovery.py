#!/usr/bin/env python3
"""Quick RTSP camera channel discovery script."""

import cv2
import sys

def test_channel(channel_num, path_format):
    """Test a specific channel path."""
    url = f"rtsp://admin:tt55oo77@192.168.1.186:554{path_format.format(channel_num)}"
    print(f"Testing Channel {channel_num}: {path_format.format(channel_num)}")
    
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 second timeout
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                print(f"  ✅ SUCCESS: {width}x{height}")
                cap.release()
                return True, f"{width}x{height}"
        
        cap.release()
        print(f"  ❌ Failed")
        return False, None
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False, None

def main():
    print("🔍 Quick Camera Discovery")
    print("=" * 40)
    
    # Test the patterns we know work plus common variations
    patterns = [
        "/Streaming/Channels/{}01",  # We know this works for 1 and 2
        "/Streaming/Channels/{}",     # Try without the 01 suffix
        "/Streaming/channels/{}01",   # lowercase variant
        "/cam/realmonitor?channel={}&subtype=0",  # Dahua style
        "/channel{}",                 # Simple pattern
        "/stream{}"                   # Another simple pattern
    ]
    
    working_channels = []
    
    # Test channels 1-8
    for channel in range(1, 9):
        print(f"\n📹 Channel {channel}:")
        
        for pattern in patterns:
            success, resolution = test_channel(channel, pattern)
            if success:
                working_channels.append({
                    'channel': channel,
                    'pattern': pattern,
                    'resolution': resolution,
                    'url': f"rtsp://admin:tt55oo77@192.168.1.186:554{pattern.format(channel)}"
                })
                break  # Found working pattern for this channel
    
    print("\n" + "=" * 40)
    print("📋 RESULTS:")
    print("=" * 40)
    
    if working_channels:
        for cam in working_channels:
            print(f"Channel {cam['channel']}: {cam['pattern'].format(cam['channel'])} ({cam['resolution']})")
    else:
        print("No additional channels found beyond 1 and 2")

if __name__ == "__main__":
    main()
