from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    rtspLink: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    rtspLink: Optional[str] = None


class RoomResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    rtspLink: Optional[str] = None
    isActive: Optional[bool] = None
    businessId: Optional[UUID] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class RoomWithCameras(RoomResponse):
    camera_count: int
    cameras: List[Dict[str, Any]] = []


class RoomPersonCount(BaseModel):
    room_id: UUID
    room_name: str
    unique_person_count: int
    active_persons: List[Dict[str, Any]] = []
    timestamp: str
