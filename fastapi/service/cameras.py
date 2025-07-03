"""
Camera Service Module
Handles camera-related operations for the security camera system.
"""
from typing import List, Dict, Any, Optional
import httpx
import asyncio

# Import configuration
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
    class FallbackConfig:
        @staticmethod
        def get_api_base_url():
            return "http://localhost:4005"
        
        @staticmethod
        def get_auth_credentials():
            return ("husain", "tt55oo77")
    
    config = FallbackConfig()


class CameraService:
    """Service class for managing security cameras."""
    
    def __init__(self, api_base_url: str = None, username: str = None, password: str = None):
        """Initialize the camera service."""
        self.cameras: Dict[str, Dict[str, Any]] = {}
        
        # Use config if parameters not provided
        if api_base_url is None:
            self.api_base_url = config.get_api_base_url()
        else:
            self.api_base_url = api_base_url
            
        if username is None or password is None:
            self.username, self.password = config.get_auth_credentials()
        else:
            self.username = username
            self.password = password
            
        self.http_client = None
        self.auth_token = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API requests."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=5.0)  # Reduced timeout to 5 seconds
        return self.http_client
    
    async def fetch_cameras_from_api(self) -> List[Dict[str, Any]]:
        """Fetch all cameras from NestJS API."""
        try:
            client = await self._get_http_client()
            headers = await self._get_headers()
            
            print(f"🔍 Fetching cameras from backend API: {self.api_base_url}/api/v1/cameras/all")
            response = await client.get(f"{self.api_base_url}/api/v1/cameras/all", headers=headers)
            
            if response.status_code == 200:
                cameras = response.json()
                print(f"✅ Successfully fetched {len(cameras)} cameras from backend API")
                return cameras
            else:
                print(f"❌ Backend returned status {response.status_code}")
                raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
                
        except httpx.RequestError as e:
            print(f"❌ Network error fetching cameras from API: {e}")
            print("🔄 Falling back to test cameras due to network issues...")
            return self._get_test_cameras()
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error fetching cameras: {e.response.status_code}")
            if e.response.status_code == 401:
                print("🔐 Authentication required - ensure your credentials are correct")
            print("🔄 Falling back to test cameras due to API error...")
            return self._get_test_cameras()
        except Exception as e:
            print(f"❌ Unexpected error fetching cameras: {e}")
            print("🔄 Falling back to test cameras...")
            return self._get_test_cameras()
    
    async def fetch_camera_by_id_from_api(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Fetch specific camera by ID from NestJS API."""
        try:
            client = await self._get_http_client()
            headers = await self._get_headers()
            response = await client.get(f"{self.api_base_url}/api/v1/cameras/{camera_id}", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error fetching camera {camera_id} from API: {e}")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            print(f"HTTP error fetching camera {camera_id}: {e.response.status_code}")
            return None
    
    async def get_rtsp_url(self, camera_id: str) -> Optional[str]:
        """Get RTSP URL for a specific camera from NestJS API."""
        camera_data = await self.fetch_camera_by_id_from_api(camera_id)
        if camera_data:
            rtsp_url = camera_data.get("rtspUrl") or camera_data.get("rtsp_url") or camera_data.get("stream_url")
            
            if rtsp_url:
                # Add authentication credentials if URL doesn't have them
                if "@" not in rtsp_url:
                    # Get credentials from backend data or use defaults
                    username = camera_data.get("username", "admin")
                    password = camera_data.get("password", "tt55oo77")
                    
                    if rtsp_url.startswith("rtsp://"):
                        rtsp_url = f"rtsp://{username}:{password}@{rtsp_url[7:]}"
                
                print(f"🎥 Camera {camera_id} RTSP URL from backend: {rtsp_url}")
                return rtsp_url
        
        # Fallback to test RTSP URL for testing
        print(f"❌ No camera data found for camera {camera_id}, using test URL")
        return self._get_test_rtsp_url(camera_id)
    
    def _get_test_rtsp_url(self, camera_id: str) -> str:
        """Generate a test RTSP URL for development/testing."""
        # Map camera IDs to channel numbers for test
        channel_map = {
            "1": "101",
            "2": "201", 
            "3": "301",
            "4": "401"
        }
        
        channel = channel_map.get(camera_id, "101")
        return f"rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/{channel}"
    
    async def close(self):
        """Close HTTP client connection."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def authenticate(self) -> bool:
        """Authenticate with the NestJS API and get token."""
        try:
            client = await self._get_http_client()
            auth_data = {
                "username": self.username,
                "password": self.password
            }
            
            # Try the correct authentication endpoint
            endpoint = "/api/v1/auth/login"
            response = await client.post(f"{self.api_base_url}{endpoint}", json=auth_data)
            
            if response.status_code == 200:
                auth_response = response.json()
                self.auth_token = auth_response.get("accessToken")
                if self.auth_token:
                    print(f"✅ Successfully authenticated with backend at {endpoint}")
                    return True
            
            print(f"❌ Authentication failed: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        
        # Only authenticate if we don't have a token
        if not self.auth_token:
            auth_success = await self.authenticate()
            if not auth_success:
                print("⚠️ Warning: Authentication failed, proceeding without token")
            
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        return headers
    
    def _get_test_cameras(self) -> List[Dict[str, Any]]:
        """Return test cameras for development when API is not available."""
        return [
            {
                "id": "1",
                "name": "Front Door Camera", 
                "location": "Front Entrance",
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101",
                "description": "Main entrance security camera",
                "status": "active"
            },
            {
                "id": "2", 
                "name": "Back Yard Camera",
                "location": "Rear Garden",
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/201",
                "description": "Backyard surveillance camera",
                "status": "active"
            },
            {
                "id": "3",
                "name": "Garage Camera", 
                "location": "Garage Area",
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/301",
                "description": "Garage monitoring camera",
                "status": "active"
            },
            {
                "id": "4",
                "name": "Side Entrance Camera",
                "location": "Side Door", 
                "rtspUrl": "rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/401",
                "description": "Side entrance security camera",
                "status": "active"
            }
        ]


# Global camera service instance
camera_service = CameraService()
