"""
Core configuration settings for the RazZ Backend Security System.
"""
import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from functools import lru_cache


class CameraConfig(BaseModel):
    """Camera configuration model."""
    base_ip: str
    username: str
    password: str
    port: str
    cameras: Dict[str, str]


class LLMConfig(BaseModel):
    """LLM configuration model."""
    api_url: str
    api_key: str
    model: str
    max_retries: int = 3
    timeout: int = 30
    enabled: bool = True


class RecordingConfig(BaseModel):
    """Recording configuration model."""
    recordings_dir: str = "recordings"
    buffer_duration: int = 30
    auto_record_on_threat_levels: list = ["HIGH", "CRITICAL"]
    default_recording_duration: int = 60
    max_concurrent_recordings: int = 4


class WebhookConfig(BaseModel):
    """Webhook configuration model."""
    pharmacy_name: str
    webhooks: list = []


class ActivityDetectionConfig(BaseModel):
    """Activity detection configuration model."""
    loiter_threshold: float = 45.0
    movement_threshold: float = 50.0
    rapid_movement_threshold: float = 200.0
    max_people_per_zone: int = 2


class Settings(BaseModel):
    """Application settings."""
    # Application
    app_name: str = "RazZ Backend Security System"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Pharmacy
    pharmacy_name: str = "RazZ Pharmacy"
    
    # Configurations
    camera_config: Optional[CameraConfig] = None
    llm_config: Optional[LLMConfig] = None
    recording_config: Optional[RecordingConfig] = None
    webhook_config: Optional[WebhookConfig] = None
    activity_detection: Optional[ActivityDetectionConfig] = None
    
    # Paths
    config_file: str = "config.json"
    recordings_dir: str = "recordings"
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://husain:tt55oo77@localhost:5432/alrazy")
    
    # JWT Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here-change-this-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def substitute_env_vars(obj: Any) -> Any:
    """Substitute environment variables in configuration."""
    if isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(v) for v in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        return os.getenv(env_var, "")
    else:
        return obj


def load_config_from_file(config_file: str = "config.json") -> Dict[str, Any]:
    """Load configuration from JSON file with environment variable substitution."""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return substitute_env_vars(config)
    except FileNotFoundError:
        print(f"⚠️  Configuration file {config_file} not found")
        return {}
    except Exception as e:
        print(f"⚠️  Error loading {config_file}: {e}")
        return {}


def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        "pharmacy_name": "Al Razy Pharmacy",
        "llm_config": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "",
            "model": "gpt-4o-mini",
            "max_retries": 3,
            "timeout": 30,
            "enabled": False  # Disabled by default if no API key
        },
        "recording_config": {
            "recordings_dir": "recordings",
            "buffer_duration": 30,
            "auto_record_on_threat_levels": ["HIGH", "CRITICAL"],
            "default_recording_duration": 60,
            "max_concurrent_recordings": 4
        },
        "webhook_config": {
            "pharmacy_name": "Al Razy Pharmacy",
            "webhooks": []
        },
        "activity_detection": {
            "loiter_threshold": 45.0,
            "movement_threshold": 50.0,
            "rapid_movement_threshold": 200.0,
            "max_people_per_zone": 2
        },
        "camera_config": {
            "base_ip": "192.168.1.186",
            "username": "admin",
            "password": "password",
            "port": "554",
            "cameras": {
                "1": "/Streaming/Channels/101",
                "2": "/Streaming/Channels/201",
                "3": "/Streaming/Channels/301",
                "4": "/Streaming/Channels/401"
            }
        }
    }


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    config_data = load_config_from_file()
    
    if not config_data:
        config_data = get_default_config()
    
    settings = Settings()
    
    # Parse configurations
    if "camera_config" in config_data:
        settings.camera_config = CameraConfig(**config_data["camera_config"])
    
    if "llm_config" in config_data:
        settings.llm_config = LLMConfig(**config_data["llm_config"])
    
    if "recording_config" in config_data:
        settings.recording_config = RecordingConfig(**config_data["recording_config"])
    
    if "webhook_config" in config_data:
        settings.webhook_config = WebhookConfig(**config_data["webhook_config"])
    
    if "activity_detection" in config_data:
        settings.activity_detection = ActivityDetectionConfig(**config_data["activity_detection"])
    
    if "pharmacy_name" in config_data:
        settings.pharmacy_name = config_data["pharmacy_name"]
    
    return settings


# Create global settings instance
settings = get_settings()
