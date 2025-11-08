#!/usr/bin/env python3
"""
Test script for the People Counter API
This demonstrates how to use the API endpoints
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("=" * 50)
    print("Testing Health Check")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_count_people(rtsp_url):
    """
    Test counting people in a single frame
    
    Args:
        rtsp_url: RTSP stream URL
    """
    print("=" * 50)
    print("Testing People Count (Single Frame)")
    print("=" * 50)
    
    payload = {
        "rtsp_url": rtsp_url,
        "confidence": 0.5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/count",
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    print()


def test_root():
    """Test the root endpoint"""
    print("=" * 50)
    print("Testing Root Endpoint")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def main():
    """Main test function"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "People Counter API - Test Suite" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Test basic endpoints
    test_root()
    test_health_check()
    
    # Example RTSP URLs (replace with your actual RTSP stream)
    # Uncomment and modify the RTSP URL below to test with your camera
    
    # test_rtsp_url = "rtsp://your-camera-ip:554/stream"
    # test_count_people(test_rtsp_url)
    
    print("\n" + "=" * 50)
    print("📝 NOTE: To test people counting, uncomment and set")
    print("   your RTSP URL in the test_api.py file")
    print("=" * 50)
    print()
    
    # Show how to access the interactive docs
    print("=" * 50)
    print("📚 Interactive API Documentation:")
    print(f"   Swagger UI: {BASE_URL}/docs")
    print(f"   ReDoc:      {BASE_URL}/redoc")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
