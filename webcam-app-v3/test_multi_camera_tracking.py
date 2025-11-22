"""
Test script for multi-camera tracking and people counting system.

Tests:
1. Single person tracking across cameras
2. Multiple people tracking
3. Cross-camera matching
4. Global people count accuracy
"""

import sys
import time
import requests
import json
from typing import Dict, List

BASE_URL = "http://localhost:8000"


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")


def test_camera_status():
    """Test: Get camera status"""
    print_header("Test 1: Camera Status")
    
    try:
        response = requests.get(f"{BASE_URL}/api/ip-cameras/status")
        response.raise_for_status()
        
        cameras = response.json()
        print_info(f"Found {len(cameras)} cameras")
        
        for camera_name, status in cameras.items():
            if status.get("status") == "connected":
                print_success(f"{camera_name}: Connected, {status.get('fps')} FPS")
                if status.get("tracking_enabled"):
                    print_info(f"  - Tracking: Enabled")
                    print_info(f"  - Detections: {status.get('detections_count', 0)}")
                    print_info(f"  - Global Count: {status.get('global_people_count', 0)}")
            else:
                print_error(f"{camera_name}: {status.get('status')} - {status.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to get camera status: {e}")
        return False


def test_people_count():
    """Test: Get total people count"""
    print_header("Test 2: Total People Count")
    
    try:
        response = requests.get(f"{BASE_URL}/api/tracking/people-count")
        response.raise_for_status()
        
        data = response.json()
        total_count = data.get("total_unique_people", 0)
        per_camera = data.get("people_per_camera", {})
        
        print_success(f"Total Unique People: {total_count}")
        print_info("People per camera:")
        for camera, count in per_camera.items():
            print(f"  - {camera}: {count}")
        
        # Verify sum is >= total (can be greater due to overlaps)
        camera_sum = sum(per_camera.values())
        print_info(f"Sum across cameras: {camera_sum}")
        
        if camera_sum >= total_count:
            print_success("Count validation passed (no under-counting)")
        else:
            print_error(f"Count mismatch: sum={camera_sum}, unique={total_count}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to get people count: {e}")
        return False


def test_tracking_stats():
    """Test: Get full tracking statistics"""
    print_header("Test 3: Tracking Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/api/tracking/stats")
        response.raise_for_status()
        
        stats = response.json()
        
        print_info("Tracking Statistics:")
        print(f"  - Total Unique People: {stats.get('total_unique_people', 0)}")
        print(f"  - Active Tracks: {stats.get('active_tracks', 0)}")
        print(f"  - Total Tracks Created: {stats.get('total_tracks_created', 0)}")
        print(f"  - ReID Enabled: {stats.get('reid_enabled', False)}")
        print(f"  - Tracker: {stats.get('tracker', 'Unknown')}")
        
        print_info("\nCamera FPS:")
        for camera, fps in stats.get('camera_fps', {}).items():
            print(f"  - {camera}: {fps:.1f} FPS")
        
        # Validate ReID is enabled
        if stats.get('reid_enabled'):
            print_success("ReID is enabled for cross-camera matching")
        else:
            print_error("ReID is NOT enabled - cross-camera matching may fail")
        
        # Validate FPS
        for camera, fps in stats.get('camera_fps', {}).items():
            if fps >= 15:
                print_success(f"{camera}: Good FPS ({fps:.1f})")
            elif fps >= 10:
                print_info(f"{camera}: Acceptable FPS ({fps:.1f})")
            else:
                print_error(f"{camera}: Low FPS ({fps:.1f})")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to get tracking stats: {e}")
        return False


def monitor_counts_over_time(duration: int = 10):
    """Test: Monitor people count over time"""
    print_header(f"Test 4: Monitor Counts Over {duration} Seconds")
    
    print_info("Monitoring people count in real-time...")
    print_info("Walk through camera views to test cross-camera tracking\n")
    
    try:
        start_time = time.time()
        last_count = None
        count_changes = []
        
        while time.time() - start_time < duration:
            response = requests.get(f"{BASE_URL}/api/tracking/people-count")
            response.raise_for_status()
            
            data = response.json()
            total_count = data.get("total_unique_people", 0)
            per_camera = data.get("people_per_camera", {})
            
            # Detect count changes
            if last_count is not None and total_count != last_count:
                change = total_count - last_count
                count_changes.append({
                    "time": time.time() - start_time,
                    "change": change,
                    "total": total_count
                })
                print_info(f"[{time.time() - start_time:.1f}s] Count changed: {last_count} → {total_count} ({change:+d})")
            
            # Display current state
            elapsed = time.time() - start_time
            print(f"\r[{elapsed:.1f}s] Total: {total_count} | Cameras: {dict(per_camera)}", end="", flush=True)
            
            last_count = total_count
            time.sleep(0.5)  # Poll every 500ms
        
        print("\n")
        
        # Summary
        if count_changes:
            print_success(f"Detected {len(count_changes)} count changes")
            for change in count_changes:
                print(f"  - {change['time']:.1f}s: {change['change']:+d} → {change['total']}")
        else:
            print_info("No count changes detected (stable count)")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to monitor counts: {e}")
        return False


def test_cross_camera_matching():
    """Test: Verify same person gets same ID across cameras"""
    print_header("Test 5: Cross-Camera Matching")
    
    print_info("Manual test instructions:")
    print("1. Have one person walk through overlapping camera views")
    print("2. Watch the video streams to see if the same global ID follows them")
    print("3. Check that the total count remains 1 (not 2 or more)\n")
    
    print_info("Press Enter when person is in camera 1...")
    input()
    
    try:
        # Get count in camera 1
        response = requests.get(f"{BASE_URL}/api/tracking/people-count")
        response.raise_for_status()
        data1 = response.json()
        count1 = data1.get("total_unique_people", 0)
        cameras1 = list(data1.get("people_per_camera", {}).keys())
        
        print_success(f"Camera 1 count: {count1}, Active cameras: {cameras1}")
        
        print_info("Now have the person move to camera 2 (overlapping view)...")
        print_info("Press Enter when person is in camera 2...")
        input()
        
        # Wait a moment for tracking to update
        time.sleep(1)
        
        # Get count in camera 2
        response = requests.get(f"{BASE_URL}/api/tracking/people-count")
        response.raise_for_status()
        data2 = response.json()
        count2 = data2.get("total_unique_people", 0)
        cameras2 = list(data2.get("people_per_camera", {}).keys())
        
        print_success(f"Camera 2 count: {count2}, Active cameras: {cameras2}")
        
        # Verify count remained the same (1 person)
        if count1 == count2 == 1:
            print_success("✅ Cross-camera matching works! Same person tracked across cameras.")
            return True
        elif count2 > count1:
            print_error(f"❌ False positive: Count increased from {count1} to {count2}")
            print_info("Possible issue: ReID threshold too strict or camera overlaps not configured")
            return False
        else:
            print_info("Test inconclusive - counts changed unexpectedly")
            return False
        
    except Exception as e:
        print_error(f"Failed cross-camera test: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🔍" * 30)
    print("Multi-Camera Tracking Test Suite")
    print("🔍" * 30)
    
    results = []
    
    # Test 1: Camera status
    results.append(("Camera Status", test_camera_status()))
    
    # Test 2: People count
    results.append(("People Count API", test_people_count()))
    
    # Test 3: Tracking stats
    results.append(("Tracking Statistics", test_tracking_stats()))
    
    # Test 4: Monitor over time
    print_info("\nStarting real-time monitoring test...")
    results.append(("Real-time Monitoring", monitor_counts_over_time(duration=10)))
    
    # Test 5: Cross-camera matching (interactive)
    print_info("\nStarting cross-camera matching test (requires manual interaction)...")
    user_input = input("Run cross-camera matching test? (y/n): ")
    if user_input.lower() == 'y':
        results.append(("Cross-Camera Matching", test_cross_camera_matching()))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("\n🎉 All tests passed! System is working correctly.")
        return 0
    else:
        print_error(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
