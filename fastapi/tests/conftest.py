"""
Test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Settings fixture."""
    return get_settings()


@pytest.fixture
def mock_camera_service():
    """Mock camera service fixture."""
    class MockCameraService:
        def get_available_cameras(self):
            return [1, 2, 3, 4]
        
        def get_camera_frame(self, camera_id):
            return "mock_base64_frame_data"
        
        def initialize_camera(self, camera_id):
            return True
    
    return MockCameraService()


@pytest.fixture
def mock_security_service():
    """Mock security service fixture."""
    class MockSecurityService:
        def get_system_status(self):
            return {
                "system_status": "operational",
                "active_cameras": 4,
                "total_events_today": 5,
                "current_threat_level": "LOW"
            }
    
    return MockSecurityService()
