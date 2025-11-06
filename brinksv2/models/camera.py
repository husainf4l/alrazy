from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to detection counts with cascade delete
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
