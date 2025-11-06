from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    floor_level: Optional[str] = None
    capacity: Optional[int] = None
    overlap_config: Optional[Dict[str, Any]] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    floor_level: Optional[str] = None
    capacity: Optional[int] = None
    overlap_config: Optional[Dict[str, Any]] = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    floor_level: Optional[str] = None
    capacity: Optional[int] = None
    overlap_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomWithCameras(RoomResponse):
    camera_count: int
    cameras: List[Dict[str, Any]] = []


class RoomPersonCount(BaseModel):
    room_id: int
    room_name: str
    unique_person_count: int
    active_persons: List[Dict[str, Any]] = []  # Each person now includes 'name' field
    timestamp: str
