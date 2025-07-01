"""
Camera models and schemas for the Al Razy Pharmacy Security System.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel, HttpUrl
from enum import Enum


class CameraStatus(str, Enum):
    """Camera status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"
    INACTIVE = "inactive"


class CameraType(str, Enum):
    """Camera type enumeration."""
    RTSP = "rtsp"
    HTTP = "http"
    USB = "usb"
    IP = "ip"


# Database Models
class CameraBase(SQLModel):
    """Base camera model with common fields."""
    name: str = Field(min_length=1, max_length=100)
    rtsp_url: str = Field(min_length=1, max_length=500)
    camera_type: CameraType = Field(default=CameraType.RTSP)
    username: Optional[str] = Field(default=None, max_length=50)
    password: Optional[str] = Field(default=None, max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    port: Optional[int] = Field(default=554, ge=1, le=65535)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    # New fields for advanced camera management
    admin_user_id: Optional[int] = Field(default=None, foreign_key="users.id", description="Admin user responsible for this camera")
    
    # Camera settings
    last_connected_at: Optional[datetime] = Field(default=None)
    resolution_width: Optional[int] = Field(default=1920)
    resolution_height: Optional[int] = Field(default=1080)
    fps: Optional[int] = Field(default=30)
    quality: Optional[int] = Field(default=80, ge=1, le=100)
    
    # Security settings
    enable_motion_detection: bool = Field(default=True)
    enable_recording: bool = Field(default=True)
    recording_duration: int = Field(default=60, ge=10, le=3600)  # seconds


class Camera(CameraBase, table=True):
    """Camera database model."""
    __tablename__ = "cameras"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", description="Primary owner of the camera")
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class CameraUserAccess(SQLModel, table=True):
    """Junction table for camera-user many-to-many relationship."""
    __tablename__ = "camera_user_access"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    camera_id: int = Field(foreign_key="cameras.id")
    user_id: int = Field(foreign_key="users.id")
    access_level: str = Field(default="viewer", description="Access level: viewer, operator, admin")
    granted_by: Optional[int] = Field(default=None, foreign_key="users.id", description="User who granted access")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class CameraCreate(CameraBase):
    """Camera creation schema."""
    # Additional fields for creation
    user_ids: Optional[List[int]] = Field(default=None, description="List of user IDs to grant access")
    admin_user_id: Optional[int] = Field(default=None, description="Admin user ID for this camera")


class CameraUpdate(SQLModel):
    """Camera update schema."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    rtsp_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    camera_type: Optional[CameraType] = None
    username: Optional[str] = Field(default=None, max_length=50)
    password: Optional[str] = Field(default=None, max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    admin_user_id: Optional[int] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    fps: Optional[int] = None
    quality: Optional[int] = Field(default=None, ge=1, le=100)
    enable_motion_detection: Optional[bool] = None
    enable_recording: Optional[bool] = None
    recording_duration: Optional[int] = Field(default=None, ge=10, le=3600)


class CameraPublic(CameraBase):
    """Public camera schema (excluding sensitive data)."""
    id: int
    user_id: int
    company_id: Optional[int]
    admin_user_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    last_connected_at: Optional[datetime]
    resolution_width: Optional[int]
    resolution_height: Optional[int]
    fps: Optional[int]
    quality: Optional[int]
    enable_motion_detection: bool
    enable_recording: bool
    recording_duration: int
    
    # Mask sensitive data
    password: Optional[str] = Field(default="***", exclude=True)


# API Response Models
class CameraInfo(BaseModel):
    """Camera information schema."""
    camera_id: int
    status: CameraStatus
    rtsp_url: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    is_recording: bool = False
    last_frame_time: Optional[float] = None
    error_message: Optional[str] = None


class CameraFrame(BaseModel):
    """Camera frame schema."""
    camera_id: int
    frame: Optional[str] = None  # Base64 encoded image
    format: str = "base64_jpeg"
    timestamp: float
    success: bool
    error_message: Optional[str] = None


class MotionDetectionResult(BaseModel):
    """Motion detection result schema."""
    camera_id: int
    motion_detected: bool
    confidence: float
    frame: Optional[str] = None  # Base64 encoded annotated image
    timestamp: float
    motion_areas: List[Dict[str, Any]] = []


class CameraInitRequest(BaseModel):
    """Camera initialization request schema."""
    camera_id: Optional[int] = None
    rtsp_url: Optional[str] = None
    timeout: int = 30


class CameraInitResponse(BaseModel):
    """Camera initialization response schema."""
    camera_id: int
    status: CameraStatus
    message: str
    rtsp_url: Optional[str] = None


class CameraListResponse(BaseModel):
    """Camera list response schema."""
    available_cameras: List[int]
    total_cameras: int
    status: str
    message: Optional[str] = None


class CameraFramesResponse(BaseModel):
    """Multiple camera frames response schema."""
    success: bool
    cameras: Dict[str, CameraFrame]
    total_cameras: int
    timestamp: float
    message: Optional[str] = None


class CameraTestResult(BaseModel):
    """Camera connection test result."""
    success: bool
    camera_id: Optional[int] = None
    rtsp_url: str
    message: str
    resolution: Optional[str] = None
    frame_shape: Optional[List[int]] = None
    error_details: Optional[str] = None
