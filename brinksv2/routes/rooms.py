"""
Room Management Routes
Handles room CRUD operations and cross-camera person counting
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import SessionLocal
from models import Room, Camera
from schemas.room import (
    RoomCreate, RoomUpdate, RoomResponse, 
    RoomWithCameras, RoomPersonCount
)
from schemas.camera import CameraResponse

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=RoomResponse)
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    """
    Create a new room for grouping cameras
    """
    # Check if room name already exists
    existing = db.query(Room).filter(Room.name == room.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists")
    
    db_room = Room(**room.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


@router.get("/", response_model=List[RoomWithCameras])
def get_rooms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all rooms with their camera counts
    """
    rooms = db.query(Room).offset(skip).limit(limit).all()
    
    result = []
    for room in rooms:
        cameras = db.query(Camera).filter(Camera.room_id == room.id).all()
        result.append({
            **room.__dict__,
            'camera_count': len(cameras),
            'cameras': [{'id': c.id, 'name': c.name, 'location': c.location} for c in cameras]
        })
    
    return result


@router.get("/{room_id}", response_model=RoomWithCameras)
def get_room(room_id: int, db: Session = Depends(get_db)):
    """
    Get a specific room by ID with its cameras
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    cameras = db.query(Camera).filter(Camera.room_id == room_id).all()
    
    return {
        **room.__dict__,
        'camera_count': len(cameras),
        'cameras': [{'id': c.id, 'name': c.name, 'location': c.location} for c in cameras]
    }


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int, 
    room_update: RoomUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update a room's information
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update only provided fields
    for field, value in room_update.dict(exclude_unset=True).items():
        setattr(db_room, field, value)
    
    db.commit()
    db.refresh(db_room)
    return db_room


@router.delete("/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    """
    Delete a room (cameras will be unassigned, not deleted)
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Unassign cameras from this room
    db.query(Camera).filter(Camera.room_id == room_id).update({"room_id": None})
    
    db.delete(db_room)
    db.commit()
    
    return {"message": f"Room {room_id} deleted successfully"}


@router.post("/{room_id}/cameras/{camera_id}")
def assign_camera_to_room(
    room_id: int, 
    camera_id: int, 
    db: Session = Depends(get_db)
):
    """
    Assign a camera to a room
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    camera.room_id = room_id
    db.commit()
    
    return {"message": f"Camera {camera_id} assigned to room {room_id}"}


@router.delete("/{room_id}/cameras/{camera_id}")
def remove_camera_from_room(
    room_id: int, 
    camera_id: int, 
    db: Session = Depends(get_db)
):
    """
    Remove a camera from a room
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.room_id == room_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=404, 
            detail="Camera not found in this room"
        )
    
    camera.room_id = None
    db.commit()
    
    return {"message": f"Camera {camera_id} removed from room {room_id}"}


@router.get("/{room_id}/person-count", response_model=RoomPersonCount)
def get_room_person_count(room_id: int, db: Session = Depends(get_db)):
    """
    Get unique person count in a room (cross-camera tracking)
    This prevents double-counting when cameras overlap
    """
    from main import global_person_tracker
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Get room statistics from global tracker
    stats = global_person_tracker.get_room_stats(room_id)
    
    return {
        'room_id': room_id,
        'room_name': room.name,
        **stats
    }
