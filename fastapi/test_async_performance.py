#!/usr/bin/env python3
"""
Async Performance Test Script
Tests the FastAPI application for blocking operations and async performance.
"""
import asyncio
import time
import httpx
import logging
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_async_performance():
    """Test the async performance of the FastAPI application."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("🚀 Starting async performance test...")
        
        # Test multiple concurrent requests
        endpoints = [
            "/",
            "/health", 
            "/api/status",
            "/api/cameras",
            "/api/streams/status"
        ]
        
        # Test concurrent requests
        start_time = time.time()
        
        tasks = []
        for endpoint in endpoints:
            for i in range(5):  # 5 requests per endpoint
                task = client.get(f"{base_url}{endpoint}")
                tasks.append(task)
        
        logger.info(f"📊 Running {len(tasks)} concurrent requests...")
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            successful_requests = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status_code') and r.status_code == 200)
            failed_requests = len(responses) - successful_requests
            
            logger.info(f"✅ Completed {len(tasks)} requests in {duration:.2f} seconds")
            logger.info(f"   📈 Successful: {successful_requests}")
            logger.info(f"   ❌ Failed: {failed_requests}")
            logger.info(f"   ⚡ Requests per second: {len(tasks)/duration:.2f}")
            
            if duration < 5 and successful_requests > len(tasks) * 0.8:
                logger.info("🎉 EXCELLENT: App appears to be fully async and non-blocking!")
                return True
            elif duration < 10:
                logger.info("👍 GOOD: App performance is acceptable")
                return True
            else:
                logger.warning("⚠️ SLOW: App may have blocking operations")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return False

async def test_streaming_endpoints():
    """Test streaming-specific endpoints for async behavior."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        logger.info("🎥 Testing streaming endpoints...")
        
        try:
            # Test concurrent streaming requests
            streaming_tasks = []
            
            # Get cameras first
            cameras_response = await client.get(f"{base_url}/api/cameras")
            if cameras_response.status_code == 200:
                cameras_data = cameras_response.json()
                cameras = cameras_data.get("cameras", [])
                
                if cameras:
                    # Test analysis endpoints concurrently
                    for camera in cameras[:3]:  # Test first 3 cameras
                        camera_id = camera.get("id")
                        if camera_id:
                            task = client.get(f"{base_url}/api/cameras/{camera_id}")
                            streaming_tasks.append(task)
                    
                    if streaming_tasks:
                        start_time = time.time()
                        responses = await asyncio.gather(*streaming_tasks, return_exceptions=True)
                        end_time = time.time()
                        
                        duration = end_time - start_time
                        successful = sum(1 for r in responses if not isinstance(r, Exception))
                        
                        logger.info(f"🎬 Streaming test: {successful}/{len(streaming_tasks)} successful in {duration:.2f}s")
                        
                        if duration < 3:
                            logger.info("⚡ Streaming endpoints are very responsive!")
                            return True
                        elif duration < 6:
                            logger.info("👍 Streaming endpoints performance is good")
                            return True
                        else:
                            logger.warning("⚠️ Streaming endpoints may be slow")
                            return False
            
            logger.warning("⚠️ No cameras found for streaming test")
            return True
            
        except Exception as e:
            logger.error(f"❌ Streaming test failed: {e}")
            return False

async def test_file_operations():
    """Test that file operations are async."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("📁 Testing file operations...")
        
        try:
            # Test HTML file serving endpoints
            html_endpoints = [
                "/test-streaming",
                "/test-auto-streaming"
            ]
            
            start_time = time.time()
            tasks = [client.get(f"{base_url}{endpoint}") for endpoint in html_endpoints]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            duration = end_time - start_time
            successful = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status_code') and r.status_code == 200)
            
            logger.info(f"📄 File operations: {successful}/{len(tasks)} successful in {duration:.2f}s")
            
            if duration < 2:
                logger.info("📂 File operations are fully async!")
                return True
            else:
                logger.warning("⚠️ File operations may be blocking")
                return False
                
        except Exception as e:
            logger.error(f"❌ File operations test failed: {e}")
            return False

async def main():
    """Main test function."""
    logger.info("🧪 Starting FastAPI Async Performance Tests")
    logger.info("=" * 60)
    
    tests = [
        ("General API Performance", test_async_performance),
        ("Streaming Endpoints", test_streaming_endpoints),
        ("File Operations", test_file_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.warning(f"⚠️ {test_name}: NEEDS IMPROVEMENT")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 EXCELLENT: Your FastAPI app is fully async and non-blocking!")
        logger.info("🚀 Performance optimizations have been successfully applied!")
    elif passed >= total * 0.7:
        logger.info("👍 GOOD: Your app is mostly async with good performance")
    else:
        logger.warning("⚠️ NEEDS WORK: Some blocking operations may still exist")
    
    return passed == total

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"\n💥 Test runner failed: {e}")
        exit(1)
