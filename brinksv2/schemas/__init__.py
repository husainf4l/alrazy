"""
Pydantic Schemas for Brinks V2 People Detection System
"""
from schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from schemas.detection import DetectionCountResponse
from schemas.room import RoomCreate, RoomUpdate, RoomResponse

__all__ = [
    "CameraCreate",
    "CameraUpdate", 
    "CameraResponse",
    "DetectionCountResponse",
    "RoomCreate",
    "RoomUpdate",
    "RoomResponse",
]