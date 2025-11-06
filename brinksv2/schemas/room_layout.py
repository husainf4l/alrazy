"""
Room Designer Schema - for visual camera positioning
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Point(BaseModel):
    """2D Point coordinates"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class Dimensions(BaseModel):
    """Room dimensions in meters"""
    width: float = Field(..., gt=0, description="Room width in meters")
    height: float = Field(..., gt=0, description="Room height in meters")
    length: float = Field(..., gt=0, description="Room length/depth in meters")


class CameraPosition(BaseModel):
    """Camera position in room with field of view"""
    camera_id: int
    position: Point = Field(..., description="Camera position in room (x, y in meters)")
    rotation: float = Field(default=0, ge=0, lt=360, description="Camera rotation in degrees")
    fov_angle: float = Field(default=90, gt=0, le=180, description="Field of view angle in degrees")
    fov_distance: float = Field(default=10, gt=0, description="Field of view distance in meters")
    height: float = Field(default=2.5, gt=0, description="Camera mounting height in meters")
    tilt_angle: float = Field(default=0, ge=-90, le=90, description="Camera tilt angle in degrees")


class OverlapZone(BaseModel):
    """Overlap zone between cameras"""
    camera_ids: List[int] = Field(..., min_items=2, max_items=2)
    polygon_points: List[Point] = Field(..., min_items=3, description="Polygon defining overlap area")
    confidence_boost: float = Field(default=0.2, ge=0, le=1)


class RoomLayout(BaseModel):
    """Complete room layout with dimensions and camera positions"""
    room_id: int
    dimensions: Dimensions
    camera_positions: List[CameraPosition] = []
    overlap_zones: List[OverlapZone] = []
    floor_plan_image: Optional[str] = Field(None, description="Base64 encoded floor plan image")
    scale: float = Field(default=1.0, gt=0, description="Scale factor: pixels per meter")


class RoomLayoutUpdate(BaseModel):
    """Update room layout"""
    dimensions: Optional[Dimensions] = None
    camera_positions: Optional[List[CameraPosition]] = None
    overlap_zones: Optional[List[OverlapZone]] = None
    floor_plan_image: Optional[str] = None
    scale: Optional[float] = None


class RoomLayoutResponse(BaseModel):
    """Response with complete room layout"""
    room_id: int
    room_name: str
    dimensions: Optional[Dimensions]
    camera_positions: List[CameraPosition]
    overlap_zones: List[OverlapZone]
    floor_plan_image: Optional[str]
    scale: float
    
    class Config:
        from_attributes = True
