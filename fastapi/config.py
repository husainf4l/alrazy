"""
Configuration settings for the FastAPI Video Streaming Application
"""
import os
from typing import Optional

class VideoStreamingConfig:
    """Configuration class for video streaming settings."""
    
    # Frame processing settings - HEAVILY OPTIMIZED FOR PERFORMANCE
    TARGET_FPS: int = 3  # Even lower FPS for RTSP stability (3 FPS)
    FRAME_SKIP_INTERVAL: int = 5  # Process every 5th frame (maximum reduction)
    MAX_CONSECUTIVE_FAILURES: int = 5
    
    # OpenCV Analysis settings - EXTREMELY INFREQUENT
    ANALYSIS_FRAME_INTERVAL: int = 60  # Analyze every 60th frame (2x less frequent)
    DETECTION_FRAME_INTERVAL: int = 120  # Person/face detection every 120th frame (2x less frequent)
    MOTION_THRESHOLD: int = 1500  # Motion detection threshold
    MAX_DETECTIONS_TO_DRAW: int = 3  # Limit to 3 detections for performance
    
    # RTSP Connection settings - IMPROVED STABILITY
    RTSP_TIMEOUT_MS: int = 15000  # 15 second timeout for stability
    RTSP_BUFFER_SIZE: int = 1  # Minimal buffer for low latency
    CONNECTION_RETRY_ATTEMPTS: int = 5  # More retries for reliability
    
    # WebRTC settings
    ICE_SERVERS = [{"urls": "stun:stun.l.google.com:19302"}]
    
    # Auto-recovery settings
    RECOVERY_CHECK_INTERVAL: int = 30  # Check every 30 seconds
    RECOVERY_THRESHOLD: int = 60  # Recover after 60 seconds of inactivity
    RECOVERY_ERROR_DELAY: int = 60  # Wait 60 seconds on recovery error
    
    # Thread pool settings - REDUCED FOR STABILITY
    THREAD_POOL_MAX_WORKERS: int = 2  # Reduced workers to limit load
    
    # Performance optimization - MORE AGGRESSIVE
    SCALE_FACTOR_THRESHOLD: int = 512  # Scale down images larger than this (more aggressive)
    DETECTION_SCALE_FACTOR: float = 0.4  # More aggressive scaling for detection
    
    # HOG Detection parameters (optimized for performance)
    HOG_WIN_STRIDE = (32, 32)  # Larger stride for better performance
    HOG_PADDING = (64, 64)     # Larger padding
    HOG_SCALE = 1.2  # Larger scale steps for faster processing
    
    # Face detection parameters (optimized for performance)
    FACE_SCALE_FACTOR = 1.3    # Larger scale factor for faster processing
    FACE_MIN_NEIGHBORS = 4     # More neighbors for better stability
    
    @classmethod
    def get_rtsp_default_credentials(cls) -> tuple[str, str]:
        """Get default RTSP credentials."""
        return (
            os.getenv("RTSP_USERNAME", "admin"),
            os.getenv("RTSP_PASSWORD", "tt55oo77")
        )
    
    @classmethod
    def get_api_base_url(cls) -> str:
        """Get API base URL."""
        return os.getenv("API_BASE_URL", "http://localhost:4005")
    
    @classmethod
    def get_fastapi_base_url(cls) -> str:
        """Get FastAPI base URL."""
        return os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
    
    @classmethod
    def get_auth_credentials(cls) -> tuple[str, str]:
        """Get authentication credentials."""
        return (
            os.getenv("AUTH_USERNAME", "husain"),
            os.getenv("AUTH_PASSWORD", "tt55oo77")
        )

# Global config instance
config = VideoStreamingConfig()
