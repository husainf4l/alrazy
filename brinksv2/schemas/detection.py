from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DetectionCountCreate(BaseModel):
    camera_id: int
    people_count: int
    average_count: Optional[float] = None


class DetectionCountResponse(BaseModel):
    id: int
    camera_id: int
    people_count: int
    average_count: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class LiveDetectionStats(BaseModel):
    camera_id: int
    camera_name: str
    current_count: int
    average_count: float
    active_tracks: int
    last_update: Optional[str] = None
    history_size: int
