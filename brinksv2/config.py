"""
Configuration module for Brinks V2 People Detection System
Centralizes all configuration settings with environment variable support
"""
import os
from pathlib import Path
from typing import Optional


# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# ==================== Database Configuration ====================
DATABASE_HOST = os.getenv("DATABASE_HOST", "149.200.251.12")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "razz")
DATABASE_USER = os.getenv("DATABASE_USER", "husain")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "tt55oo77")

# Construct database URL
DATABASE_URL = (
    f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)

# ==================== Application Configuration ====================
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))
APP_DEBUG = os.getenv("APP_DEBUG", "False").lower() == "true"

# ==================== YOLO Model Configuration ====================
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(BASE_DIR / "yolo11m.pt"))
YOLO_CONFIDENCE_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5"))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cuda")  # cuda or cpu

# ==================== ByteTrack Configuration ====================
BYTETRACK_THRESHOLD = float(os.getenv("BYTETRACK_THRESHOLD", "0.6"))
BYTETRACK_FPS = int(os.getenv("BYTETRACK_FPS", "30"))
BYTETRACK_FRAME_RATE = int(os.getenv("BYTETRACK_FRAME_RATE", "30"))

# ==================== Cross-Camera Tracking Configuration ====================
GLOBAL_TRACKER_SIMILARITY_THRESHOLD = float(
    os.getenv("GLOBAL_TRACKER_SIMILARITY_THRESHOLD", "0.6")
)
GLOBAL_TRACKER_TIME_WINDOW = int(
    os.getenv("GLOBAL_TRACKER_TIME_WINDOW", "3")
)  # seconds
GLOBAL_TRACKER_CLEANUP_INTERVAL = int(
    os.getenv("GLOBAL_TRACKER_CLEANUP_INTERVAL", "6")
)  # seconds

# ==================== RTSP Configuration ====================
RTSP_TIMEOUT = int(os.getenv("RTSP_TIMEOUT", "10"))
RTSP_RECONNECT_DELAY = int(os.getenv("RTSP_RECONNECT_DELAY", "5"))

# ==================== WebRTC Configuration ====================
WEBRTC_SERVER_URL = os.getenv("WEBRTC_SERVER_URL", "http://127.0.0.1:8083")

# ==================== API Configuration ====================
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")

# ==================== Detection Service Configuration ====================
DETECTION_SAVE_INTERVAL = int(os.getenv("DETECTION_SAVE_INTERVAL", "300"))  # seconds
DETECTION_HISTORY_SIZE = int(os.getenv("DETECTION_HISTORY_SIZE", "100"))
VISUALIZATION_FPS = int(os.getenv("VISUALIZATION_FPS", "15"))

# ==================== Logging Configuration ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "people_detection.log"))

# ==================== CORS Configuration ====================
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ==================== Feature Flags ====================
ENABLE_DEEPSORT = os.getenv("ENABLE_DEEPSORT", "True").lower() == "true"
ENABLE_GLOBAL_TRACKING = os.getenv("ENABLE_GLOBAL_TRACKING", "True").lower() == "true"
ENABLE_VISUALIZATION = os.getenv("ENABLE_VISUALIZATION", "True").lower() == "true"


class Config:
    """Configuration class for easy access to settings"""
    
    # Database
    DATABASE_URL = DATABASE_URL
    
    # Application
    APP_HOST = APP_HOST
    APP_PORT = APP_PORT
    APP_DEBUG = APP_DEBUG
    
    # YOLO
    YOLO_MODEL_PATH = YOLO_MODEL_PATH
    YOLO_CONFIDENCE_THRESHOLD = YOLO_CONFIDENCE_THRESHOLD
    YOLO_DEVICE = YOLO_DEVICE
    
    # ByteTrack
    BYTETRACK_THRESHOLD = BYTETRACK_THRESHOLD
    BYTETRACK_FPS = BYTETRACK_FPS
    BYTETRACK_FRAME_RATE = BYTETRACK_FRAME_RATE
    
    # Global Tracker
    GLOBAL_TRACKER_SIMILARITY_THRESHOLD = GLOBAL_TRACKER_SIMILARITY_THRESHOLD
    GLOBAL_TRACKER_TIME_WINDOW = GLOBAL_TRACKER_TIME_WINDOW
    GLOBAL_TRACKER_CLEANUP_INTERVAL = GLOBAL_TRACKER_CLEANUP_INTERVAL
    
    # RTSP
    RTSP_TIMEOUT = RTSP_TIMEOUT
    RTSP_RECONNECT_DELAY = RTSP_RECONNECT_DELAY
    
    # WebRTC
    WEBRTC_SERVER_URL = WEBRTC_SERVER_URL
    
    # API
    API_BASE_URL = API_BASE_URL
    
    # Detection
    DETECTION_SAVE_INTERVAL = DETECTION_SAVE_INTERVAL
    DETECTION_HISTORY_SIZE = DETECTION_HISTORY_SIZE
    VISUALIZATION_FPS = VISUALIZATION_FPS
    
    # Logging
    LOG_LEVEL = LOG_LEVEL
    LOG_FORMAT = LOG_FORMAT
    LOG_FILE = LOG_FILE
    
    # CORS
    CORS_ORIGINS = CORS_ORIGINS
    
    # Features
    ENABLE_DEEPSORT = ENABLE_DEEPSORT
    ENABLE_GLOBAL_TRACKING = ENABLE_GLOBAL_TRACKING
    ENABLE_VISUALIZATION = ENABLE_VISUALIZATION


# Export config instance
config = Config()
