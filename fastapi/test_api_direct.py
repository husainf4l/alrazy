"""
Direct API test to check raw response
"""
import asyncio
import httpx
import json


async def test_api_direct():
    """Test the API directly to see raw responses."""
    api_base_url = "http://localhost:4005"
    username = "husain"
    password = "tt55oo77"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: Test authentication
            print("🔐 Testing Authentication...")
            auth_data = {"username": username, "password": password}
            
            auth_response = await client.post(
                f"{api_base_url}/api/v1/auth/login", 
                json=auth_data
            )
            
            print(f"Auth Status Code: {auth_response.status_code}")
            print(f"Auth Response: {json.dumps(auth_response.json(), indent=2)}")
            
            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                access_token = auth_data.get("accessToken")
                
                if access_token:
                    print(f"\n✅ Got access token: {access_token[:50]}...")
                    
                    # Step 2: Test cameras endpoint
                    print("\n📹 Testing Cameras Endpoint...")
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    
                    cameras_response = await client.get(
                        f"{api_base_url}/api/v1/cameras/all",
                        headers=headers
                    )
                    
                    print(f"Cameras Status Code: {cameras_response.status_code}")
                    print(f"Cameras Response: {json.dumps(cameras_response.json(), indent=2)}")
                    
                else:
                    print("❌ No access token in response")
            else:
                print("❌ Authentication failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api_direct())
