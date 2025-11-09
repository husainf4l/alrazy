from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    position_x = Column(Integer, nullable=True)  # Camera position in room layout
    position_y = Column(Integer, nullable=True)
    field_of_view = Column(Integer, default=90)  # Field of view in degrees
    direction = Column(Integer, default=0)  # Camera direction in degrees
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    vault_room = relationship("VaultRoom", back_populates="cameras")