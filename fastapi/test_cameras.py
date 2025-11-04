"""
Test script for camera service
"""
import asyncio
from service.cameras import camera_service


async def test_camera_service():
    """Test the camera service functionality."""
    print("🔍 Testing Camera Service...")
    print(f"📡 API Base URL: {camera_service.api_base_url}")
    
    try:
        # Test fetching all cameras
        print("\n📹 Fetching all cameras...")
        cameras = await camera_service.fetch_cameras_from_api()
        print(f"✅ Found {len(cameras)} cameras")
        
        if cameras:
            print("\n📋 Camera List:")
            for i, camera in enumerate(cameras[:3], 1):  # Show first 3 cameras
                print(f"  {i}. ID: {camera.get('id', 'N/A')}")
                print(f"     Name: {camera.get('name', 'N/A')}")
                print(f"     Location: {camera.get('location', 'N/A')}")
                print(f"     RTSP: {camera.get('rtspUrl', 'N/A')}")
                print()
            
            # Test fetching specific camera
            if cameras:
                first_camera_id = cameras[0].get('id')
                if first_camera_id:
                    print(f"\n🎯 Testing specific camera fetch (ID: {first_camera_id})...")
                    specific_camera = await camera_service.fetch_camera_by_id_from_api(first_camera_id)
                    if specific_camera:
                        print("✅ Successfully fetched specific camera")
                        print(f"   Name: {specific_camera.get('name', 'N/A')}")
                        
                        # Test RTSP URL extraction
                        rtsp_url = await camera_service.get_rtsp_url(first_camera_id)
                        if rtsp_url:
                            print(f"✅ RTSP URL: {rtsp_url}")
                        else:
                            print("❌ No RTSP URL found")
                    else:
                        print("❌ Failed to fetch specific camera")
        else:
            print("❌ No cameras found or API not reachable")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    
    finally:
        # Clean up
        await camera_service.close()
        print("\n🧹 Cleaned up HTTP client")


if __name__ == "__main__":
    asyncio.run(test_camera_service())


