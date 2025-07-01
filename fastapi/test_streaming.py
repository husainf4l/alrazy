"""
Test script to verify FastAPI Camera Streaming Service integration.
"""
import asyncio
import aiohttp
import json

async def test_streaming_service():
    """Test the FastAPI streaming service endpoints."""
    
    base_url = "http://localhost:8001"
    company_id = 1  # Test company ID
    
    print("🧪 Testing FastAPI Camera Streaming Service...")
    print(f"🌐 Base URL: {base_url}")
    print(f"🏢 Test Company ID: {company_id}")
    print("")
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health check
        print("1️⃣ Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Health check passed")
                    print(f"   📊 Database status: {data.get('database', 'unknown')}")
                    print(f"   📹 Cameras in DB: {data.get('cameras_in_db', 'unknown')}")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        print("")
        
        # Test 2: Root endpoint
        print("2️⃣ Testing root endpoint...")
        try:
            async with session.get(f"{base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Root endpoint works")
                    print(f"   📋 Service: {data.get('service', 'unknown')}")
                    print(f"   🔗 Integration: {data.get('integration', {}).get('backend', 'unknown')}")
                else:
                    print(f"   ❌ Root endpoint failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Root endpoint error: {e}")
        
        print("")
        
        # Test 3: Company cameras endpoint
        print("3️⃣ Testing company cameras endpoint...")
        try:
            headers = {"X-Company-Id": str(company_id)}
            async with session.get(f"{base_url}/api/stream/company/{company_id}/cameras", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    cameras = data.get('cameras', [])
                    print(f"   ✅ Company cameras endpoint works")
                    print(f"   📹 Found {len(cameras)} cameras for company {company_id}")
                    
                    if cameras:
                        print(f"   📋 Camera list:")
                        for camera in cameras[:3]:  # Show first 3 cameras
                            print(f"      - ID: {camera.get('id')}, Name: {camera.get('name')}, Online: {camera.get('is_online')}")
                    else:
                        print(f"   📝 No cameras found (this is normal if no cameras are configured)")
                        
                elif response.status == 401:
                    print(f"   ❌ Authentication failed - check X-Company-Id header")
                elif response.status == 403:
                    print(f"   ❌ Access denied - company ID mismatch")
                else:
                    print(f"   ❌ Company cameras failed: {response.status}")
                    text = await response.text()
                    print(f"      Response: {text[:200]}...")
        except Exception as e:
            print(f"   ❌ Company cameras error: {e}")
        
        print("")
        
        # Test 4: Camera info endpoint (if cameras exist)
        print("4️⃣ Testing camera info endpoint...")
        test_camera_id = 1  # Test with camera ID 1
        try:
            headers = {"X-Company-Id": str(company_id)}
            async with session.get(f"{base_url}/api/stream/camera/{test_camera_id}/info", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Camera info endpoint works")
                    print(f"   📹 Camera: {data.get('name', 'unknown')} (ID: {data.get('camera_id')})")
                    print(f"   📍 Location: {data.get('location', 'unknown')}")
                    print(f"   🎥 Resolution: {data.get('resolution', 'unknown')}")
                    print(f"   🔍 Motion detection: {data.get('motion_detection_enabled', False)}")
                elif response.status == 404:
                    print(f"   📝 Camera {test_camera_id} not found (normal if no cameras configured)")
                elif response.status == 403:
                    print(f"   ❌ Access denied to camera {test_camera_id}")
                else:
                    print(f"   ❌ Camera info failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Camera info error: {e}")
        
        print("")
    
    print("🎯 Test Summary:")
    print("   ✅ If health check passed: Service is running and database connected")
    print("   ✅ If company cameras worked: Database integration is working")
    print("   📝 If no cameras found: Add cameras via your NestJS backend first")
    print("")
    print("🔗 Integration Test:")
    print("   1. Create cameras via NestJS backend (port 3000)")
    print("   2. Test streaming via this FastAPI service (port 8001)")
    print("   3. Use frontend to authenticate with backend and stream from FastAPI")

if __name__ == "__main__":
    print("🧪 FastAPI Camera Streaming Service Test")
    print("=" * 50)
    
    try:
        asyncio.run(test_streaming_service())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    
    print("\n✅ Test completed")
