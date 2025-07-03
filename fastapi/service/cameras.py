"""
Camera Service Module
Handles camera-related operations for the security camera system.
"""
from typing import List, Dict, Any, Optional
import httpx
import asyncio


class CameraService:
    """Service class for managing security cameras."""
    
    def __init__(self, api_base_url: str = "http://localhost:4005", username: str = "husain", password: str = "tt55oo77"):
        """Initialize the camera service."""
        self.cameras: Dict[str, Dict[str, Any]] = {}
        self.api_base_url = api_base_url
        self.username = username
        self.password = password
        self.http_client = None
        self.auth_token = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API requests."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client
    
    async def fetch_cameras_from_api(self) -> List[Dict[str, Any]]:
        """Fetch all cameras from NestJS API."""
        try:
            client = await self._get_http_client()
            headers = await self._get_headers()
            response = await client.get(f"{self.api_base_url}/api/v1/cameras/all", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error fetching cameras from API: {e}")
            print("🔄 Falling back to test cameras...")
            return self._get_test_cameras()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching cameras: {e.response.status_code}")
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
            
            # Add authentication if URL doesn't have it
            if rtsp_url and "@" not in rtsp_url:
                # Default camera credentials
                username = "admin"
                password = "tt55oo77"
                
                if rtsp_url.startswith("rtsp://"):
                    rtsp_url = f"rtsp://{username}:{password}@{rtsp_url[7:]}"
            
            print(f"🎥 Camera {camera_id} RTSP URL: {rtsp_url}")
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
            
            # Try common authentication endpoints
            auth_endpoints = [
                "/api/v1/auth/login",
                "/api/auth/login", 
                "/auth/login",
                "/login"
            ]
            
            for endpoint in auth_endpoints:
                try:
                    response = await client.post(f"{self.api_base_url}{endpoint}", json=auth_data)
                    if response.status_code == 200:
                        auth_response = response.json()
                        self.auth_token = auth_response.get("accessToken") or auth_response.get("access_token") or auth_response.get("token")
                        if self.auth_token:
                            print(f"✅ Successfully authenticated at {endpoint}")
                            return True
                except httpx.HTTPStatusError:
                    continue
                    
            print("❌ Failed to authenticate with any endpoint")
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


# Global camera service instance
camera_service = CameraService()
