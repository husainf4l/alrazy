from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Room(Base):
    """
    Room model to group multiple cameras
    Handles cross-camera tracking to prevent double-counting
    """
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    floor_level = Column(String, nullable=True)  # e.g., "Ground Floor", "1st Floor"
    capacity = Column(Integer, nullable=True)  # Maximum room capacity
    
    # Visual layout configuration
    dimensions = Column(JSON, nullable=True)  # Room dimensions: {width, height, length} in meters
    floor_plan_image = Column(Text, nullable=True)  # Base64 encoded floor plan image
    layout_scale = Column(Integer, default=100)  # Scale: pixels per meter
    
    # Camera positioning in room
    camera_positions = Column(JSON, nullable=True)  # Array of camera positions with FOV
    
    # Metadata for cross-camera tracking configuration
    overlap_config = Column(JSON, nullable=True)  # Store overlap zones between cameras
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to cameras
    cameras = relationship("Camera", back_populates="room")
    
    def __repr__(self):
        return f"<Room(id={self.id}, name='{self.name}', cameras={len(self.cameras)})>"
