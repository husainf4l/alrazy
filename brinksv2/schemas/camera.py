from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class CameraBase(BaseModel):
    name: str = Field(..., description="Camera name")
    rtspUrl: str = Field(..., description="RTSP stream link")
    description: Optional[str] = Field(None, description="Camera description")


class CameraCreate(CameraBase):
    roomId: Optional[UUID] = None
    businessId: Optional[UUID] = None
    userId: Optional[UUID] = None
    
    class Config:
        populate_by_name = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtspUrl: Optional[str] = None
    description: Optional[str] = None
    roomId: Optional[UUID] = None


class CameraResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    rtspUrl: str
    status: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    isActive: Optional[bool] = None
    roomId: Optional[UUID] = None
    businessId: Optional[UUID] = None
    userId: Optional[UUID] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    # Backward compatibility
    rtsp_main: Optional[str] = None
    rtsp_sub: Optional[str] = None
    location: Optional[str] = None
    room_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
