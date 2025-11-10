from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company")
    vault_rooms = relationship("VaultRoom", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    company = relationship("Company", back_populates="users")

class VaultRoom(Base):
    __tablename__ = "vault_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    current_people_count = Column(Integer, default=0)
    authorized_personnel = Column(Text, nullable=True)  # JSON string of authorized personnel
    
    # Room layout and dimensions
    room_width = Column(Integer, default=10)  # Room width in meters
    room_height = Column(Integer, default=8)  # Room height in meters
    room_layout = Column(Text, nullable=True)  # JSON string of room layout (walls, cameras, vault position)
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="vault_rooms")
    cameras = relationship("Camera", back_populates="vault_room", cascade="all, delete-orphan")

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    vault_room_id = Column(Integer, ForeignKey("vault_rooms.id"), nullable=False)
    current_people_count = Column(Integer, default=0)  # People detected by this camera
    position_x = Column(Integer, nullable=True)  # Camera position in room layout
    position_y = Column(Integer, nullable=True)
    field_of_view = Column(Integer, default=90)  # Field of view in degrees
    direction = Column(Integer, default=0)  # Camera direction in degrees
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    vault_room = relationship("VaultRoom", back_populates="cameras")


class Person(Base):
    """Enrolled persons in the system (gallery)"""
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    employee_id = Column(String(100), nullable=True, index=True)
    department = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", backref="persons")
    face_embeddings = relationship("FaceEmbedding", back_populates="person", cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="person")


class FaceEmbedding(Base):
    """Face embeddings for enrolled persons"""
    __tablename__ = "face_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(Vector(512), nullable=False)  # ArcFace 512-dimensional embedding
    image_path = Column(String(500), nullable=True)  # Path to face image
    quality_score = Column(Float, default=0.0)  # Face quality (0-1)
    source = Column(String(50), default="enrollment")  # "enrollment", "camera", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("Person", back_populates="face_embeddings")


class TrackingEvent(Base):
    """Log of person tracking events (entry, exit, motion)"""
    __tablename__ = "tracking_events"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("vault_rooms.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # "entry", "exit", "motion", "unauthorized"
    track_id = Column(Integer, nullable=True)  # Tracker ID from YOLO
    confidence = Column(Float, nullable=True)  # Recognition confidence (0-1)
    bbox = Column(JSON, nullable=True)  # Bounding box {x, y, w, h}
    event_metadata = Column(JSON, nullable=True)  # Additional event data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    room = relationship("VaultRoom", backref="tracking_events")
    camera = relationship("Camera", backref="tracking_events")
    person = relationship("Person", back_populates="tracking_events")