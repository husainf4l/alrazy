from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class CameraBase(BaseModel):
    name: str = Field(..., description="Camera name")
    rtsp_main: str = Field(..., description="Main RTSP stream link (high quality)")
    rtsp_sub: str = Field(..., description="Sub RTSP stream link (low quality)")
    location: str = Field(..., description="Camera location")


class CameraCreate(CameraBase):
    room_id: Optional[int] = None
    position_config: Optional[Dict[str, Any]] = None
    overlap_zones: Optional[List[Dict[str, Any]]] = None


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_main: Optional[str] = None
    rtsp_sub: Optional[str] = None
    location: Optional[str] = None
    room_id: Optional[int] = None
    position_config: Optional[Dict[str, Any]] = None
    overlap_zones: Optional[List[Dict[str, Any]]] = None


class CameraResponse(CameraBase):
    id: int
    room_id: Optional[int] = None
    position_config: Optional[Dict[str, Any]] = None
    overlap_zones: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
