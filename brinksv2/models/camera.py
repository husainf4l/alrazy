from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rtspUrl = Column('rtspUrl', String, nullable=False)
    status = Column(String(11), nullable=False, default='online')
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    isActive = Column('isActive', Boolean, default=True)
    
    # Room assignment for cross-camera tracking
    roomId = Column('roomId', UUID(as_uuid=True), nullable=True)
    businessId = Column('businessId', UUID(as_uuid=True), nullable=True)
    userId = Column('userId', UUID(as_uuid=True), nullable=True)
    
    createdAt = Column('createdAt', DateTime, default=datetime.utcnow)
    updatedAt = Column('updatedAt', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Python properties for backward compatibility
    @property
    def rtsp_main(self):
        return self.rtspUrl
    
    @property
    def rtsp_sub(self):
        return self.rtspUrl  # Using same URL for both main and sub
    
    @property
    def room_id(self):
        return self.roomId
    
    @property
    def created_at(self):
        return self.createdAt
    
    @property
    def updated_at(self):
        return self.updatedAt
    
    @property
    def location(self):
        return self.description


class DetectionCount(Base):
    __tablename__ = "detection_counts"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(UUID(as_uuid=True), nullable=False)  # UUID to match cameras table
    people_count = Column(Integer, nullable=False)
    average_count = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}', location='{self.location}')>"
