"""
Configuration management for RAZZv4 Backend
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "RAZZv4 Backend"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: str = "logs/app.log"
    
    # Database
    DATABASE_URL: str = "sqlite:///./vault_system.db"
    
    # Authentication (optional, from .env)
    SECRET_KEY: Optional[str] = "your-secret-key-here-change-in-production"
    ALGORITHM: Optional[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = 30
    
    # YOLO Detection
    YOLO_MODEL: str = "yolo11m.pt"
    YOLO_CONFIDENCE: float = 0.5
    YOLO_DEVICE: str = "auto"  # auto, cuda, cpu
    
    # Tracking
    BYTETRACK_THRESHOLD: float = 0.6
    DEEPSORT_MAX_AGE: int = 30
    DEEPSORT_APPEARANCE_THRESHOLD: float = 0.3
    
    # Global ID System
    GLOBAL_ID_TIMEOUT: float = 30.0  # seconds
    GLOBAL_ID_SIMILARITY_THRESHOLD: float = 0.5
    GLOBAL_ID_FEATURE_SMOOTHING: float = 0.7  # Running average: 70% old, 30% new
    
    # Deduplication
    DEDUP_SIMILARITY_THRESHOLD: float = 0.5
    DEDUP_DISTANCE_THRESHOLD: int = 300  # pixels
    
    # Camera
    CAMERA_RECONNECT_DELAY: int = 5  # seconds
    CAMERA_FPS: int = 15
    
    # Face Recognition
    FACE_RECOGNITION_ENABLED: bool = True
    FACE_RECOGNITION_TOLERANCE: float = 0.6
    
    # Upload paths
    UPLOAD_DIR: str = "uploads"
    FACE_UPLOAD_DIR: str = "uploads/faces"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
