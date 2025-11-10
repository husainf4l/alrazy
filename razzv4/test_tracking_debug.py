#!/usr/bin/env python3
"""
Debug script to test tracking visualization
Run this after starting the main application
"""

import requests
import json
import base64
import cv2
import numpy as np
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_tracking_endpoint(room_id: int, camera_id: int):
    """Test the tracking frame endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing Tracking Endpoint")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/vault-rooms/{room_id}/camera/{camera_id}/tracking-frame"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"   Camera ID: {data['camera_id']}")
            print(f"   Camera Name: {data['camera_name']}")
            print(f"   Frame Size: {data['frame_size']} bytes")
            print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
            
            # Decode and save the frame
            frame_data = base64.b64decode(data['frame'])
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                print(f"   Frame Shape: {frame.shape}")
                output_path = f"/home/husain/alrazy/razzv4/test_tracking_frame_{camera_id}.jpg"
                cv2.imwrite(output_path, frame)
                print(f"   Saved to: {output_path}")
                
                # Check if frame has annotations (look for green pixels)
                green_pixels = np.sum((frame[:,:,1] > 200) & (frame[:,:,0] < 100) & (frame[:,:,2] < 100))
                if green_pixels > 1000:
                    print(f"   ✅ Frame appears to have tracking annotations (found {green_pixels} bright green pixels)")
                else:
                    print(f"   ⚠️  Frame may not have tracking annotations (only {green_pixels} bright green pixels)")
            else:
                print(f"   ❌ Failed to decode frame")
                
        elif response.status_code == 404:
            print(f"❌ NOT FOUND")
            error = response.json()
            print(f"   Detail: {error.get('detail', 'Unknown error')}")
            print(f"   Possible causes:")
            print(f"   - Camera not started")
            print(f"   - No frames processed yet")
            print(f"   - Wrong camera ID or room ID")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR")
        print(f"   Is the server running at {BASE_URL}?")
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")


def test_tracking_stats(room_id: int):
    """Test the tracking stats endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing Tracking Stats Endpoint")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/vault-rooms/{room_id}/tracking-stats"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"   Room ID: {data['room_id']}")
            print(f"   Room Name: {data['room_name']}")
            print(f"   Cameras: {len(data['cameras'])}")
            
            for cam in data['cameras']:
                print(f"\n   Camera {cam['camera_id']}: {cam['camera_name']}")
                print(f"   Tracking Enabled: {cam.get('tracking_enabled', False)}")
                
                if cam.get('tracking_enabled') and 'statistics' in cam:
                    stats = cam['statistics']
                    print(f"   Stats:")
                    print(f"     - Total Frames: {stats.get('total_frames', 0)}")
                    print(f"     - Active Tracks: {stats.get('active_tracks', 0)}")
                    print(f"     - Tracks Created: {stats.get('tracks_created', 0)}")
                    print(f"     - Avg Processing Time: {stats.get('avg_processing_time', 0):.3f}s")
                    
                    if stats.get('total_frames', 0) > 0:
                        print(f"     ✅ Camera is processing frames")
                    else:
                        print(f"     ⚠️  No frames processed yet")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")


def test_camera_list(room_id: int):
    """Test getting camera list"""
    print(f"\n{'='*60}")
    print(f"Testing Camera List Endpoint")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/vault-rooms/{room_id}/cameras/webrtc"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"   Room Name: {data['room_name']}")
            print(f"   Cameras: {len(data['cameras'])}")
            
            for cam in data['cameras']:
                print(f"\n   Camera {cam['id']}: {cam['name']}")
                print(f"     RTSP: {cam['rtsp_url'][:50]}...")
                print(f"     Active: {cam.get('is_active', False)}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("TRACKING VISUALIZATION DEBUG TOOL")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUsage: python test_tracking_debug.py <room_id> [camera_id]")
        print("\nExample:")
        print("  python test_tracking_debug.py 1        # Test room 1, all cameras")
        print("  python test_tracking_debug.py 1 101    # Test room 1, camera 101")
        sys.exit(1)
    
    room_id = int(sys.argv[1])
    camera_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Test camera list
    test_camera_list(room_id)
    
    # Test tracking stats
    test_tracking_stats(room_id)
    
    # Test tracking frame endpoint
    if camera_id:
        test_tracking_endpoint(room_id, camera_id)
    else:
        print("\n⚠️  Specify a camera_id to test tracking frame endpoint")
        print(f"   Example: python test_tracking_debug.py {room_id} 101")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check server logs for any errors")
    print("2. Open browser console on camera-viewer page")
    print("3. Look for '✅ Received tracking frame' messages")
    print("4. Verify canvas overlay is visible (not display:none)")
    print("=" * 60)
