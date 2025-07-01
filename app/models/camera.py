"""
Camera models and schemas for the Al Razy Pharmacy Security System.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum


class CameraStatus(str, Enum):
    """Camera status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


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
