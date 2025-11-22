#!/usr/bin/env python3
"""
Quick test to verify multi-camera tracking is working correctly.
Run this while the server is running to check tracking status.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_tracking():
    """Test tracking endpoints without authentication"""
    print("=" * 60)
    print("  Multi-Camera Tracking Test")
    print("=" * 60)
    print()
    
    # Test 1: People Count
    print("📊 Testing People Count Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/tracking/people-count", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"   Total Unique People: {data.get('total_unique_people', 0)}")
            print(f"   People per Camera:")
            for camera, count in data.get('people_per_camera', {}).items():
                print(f"      - {camera}: {count}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 2: Full Tracking Stats
    print("📈 Testing Tracking Statistics Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/tracking/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"   Total Unique People: {data.get('total_unique_people', 0)}")
            print(f"   Active Tracks: {data.get('active_tracks', 0)}")
            print(f"   Total Tracks Created: {data.get('total_tracks_created', 0)}")
            print(f"   ReID Enabled: {data.get('reid_enabled', False)}")
            print(f"   Tracker Type: {data.get('tracker', 'Unknown')}")
            print(f"   Camera FPS:")
            for camera, fps in data.get('camera_fps', {}).items():
                print(f"      - {camera}: {fps:.1f} FPS")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 3: Real-time monitoring (5 seconds)
    print("🔄 Real-time Monitoring (5 seconds)...")
    try:
        for i in range(5):
            response = requests.get(f"{BASE_URL}/api/tracking/people-count", timeout=5)
            if response.status_code == 200:
                data = response.json()
                count = data.get('total_unique_people', 0)
                cameras = len(data.get('people_per_camera', {}))
                print(f"   [{i+1}/5] People: {count} | Active Cameras: {cameras}")
            time.sleep(1)
        print("✅ Monitoring complete!")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    print()
    print("Starting tracking verification test...")
    print("Make sure the server is running on http://localhost:8000")
    print()
    time.sleep(1)
    test_tracking()
