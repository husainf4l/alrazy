from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid


class Room(Base):
    """
    Room model to group multiple cameras
    Handles cross-camera tracking to prevent double-counting
    """
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rtspLink = Column('rtspLink', String, nullable=True)
    location = Column(String, nullable=True)
    isActive = Column('isActive', Boolean, default=True)
    businessId = Column('businessId', UUID(as_uuid=True), nullable=True)
    
    createdAt = Column('createdAt', DateTime, default=datetime.utcnow)
    updatedAt = Column('updatedAt', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Python properties for backward compatibility
    @property
    def created_at(self):
        return self.createdAt
    
    @property
    def updated_at(self):
        return self.updatedAt
    
    @property
    def overlap_config(self):
        """Return empty overlap config for backward compatibility"""
        return None
    
    def __repr__(self):
        return f"<Room(id={self.id}, name='{self.name}')>"
