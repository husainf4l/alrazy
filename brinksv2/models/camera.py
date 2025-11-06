from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rtsp_main = Column(String, nullable=False)
    rtsp_sub = Column(String, nullable=False)
    location = Column(String)
    
    # Room assignment for cross-camera tracking
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    
    # Camera positioning and overlap zones
    # Format: {"x": 0, "y": 0, "angle": 0, "fov": 90, "height": 3.0}
    position_config = Column(JSON, nullable=True)
    
    # Overlap zones with other cameras (polygon coordinates)
    # Format: {"camera_id": 2, "zone": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]}
    overlap_zones = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room = relationship("Room", back_populates="cameras")
    detection_counts = relationship("DetectionCount", back_populates="camera", cascade="all, delete-orphan")


class DetectionCount(Base):
    __tablename__ = "detection_counts"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    people_count = Column(Integer, nullable=False)
    average_count = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship to camera
    camera = relationship("Camera", back_populates="detection_counts")

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}', location='{self.location}')>"
