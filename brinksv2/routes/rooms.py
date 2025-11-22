"""
Room Management Routes
Handles room CRUD operations and cross-camera person counting
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from database import SessionLocal
from models import Room, Camera
from schemas.room import (
    RoomCreate, RoomUpdate, RoomResponse, 
    RoomWithCameras, RoomPersonCount
)
from schemas.camera import CameraResponse
from schemas.room_layout import RoomLayout, RoomLayoutUpdate, RoomLayoutResponse

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
        cameras = db.query(Camera).filter(Camera.roomId == room.id).all()
        result.append({
            **room.__dict__,
            'camera_count': len(cameras),
            'cameras': [{'id': c.id, 'name': c.name, 'location': c.location} for c in cameras]
        })
    
    return result


@router.get("/{room_id}", response_model=RoomWithCameras)
def get_room(room_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific room by ID with its cameras
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    cameras = db.query(Camera).filter(Camera.roomId == room_id).all()
    
    return {
        **room.__dict__,
        'camera_count': len(cameras),
        'cameras': [{'id': c.id, 'name': c.name, 'location': c.location} for c in cameras]
    }


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: UUID, 
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
def delete_room(room_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a room (cameras will be unassigned, not deleted)
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Unassign cameras from this room
    db.query(Camera).filter(Camera.roomId == room_id).update({"roomId": None})
    
    db.delete(db_room)
    db.commit()
    
    return {"message": f"Room {room_id} deleted successfully"}


@router.post("/{room_id}/cameras/{camera_id}")
def assign_camera_to_room(
    room_id: UUID, 
    camera_id: UUID, 
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
    
    camera.roomId = room_id
    db.commit()
    
    return {"message": f"Camera {camera_id} assigned to room {room_id}"}


@router.delete("/{room_id}/cameras/{camera_id}")
def remove_camera_from_room(
    room_id: UUID, 
    camera_id: UUID, 
    db: Session = Depends(get_db)
):
    """
    Remove a camera from a room
    """
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.roomId == room_id
    ).first()
    
    if not camera:
        raise HTTPException(
            status_code=404, 
            detail="Camera not found in this room"
        )
    
    camera.roomId = None
    db.commit()
    
    return {"message": f"Camera {camera_id} removed from room {room_id}"}


@router.get("/{room_id}/person-count", response_model=RoomPersonCount)
def get_room_person_count(room_id: UUID, db: Session = Depends(get_db)):
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


@router.put("/{room_id}/person/{global_id}/name")
def set_person_name(room_id: UUID, global_id: int, name: str, db: Session = Depends(get_db)):
    """
    Assign a name to a tracked person in a room
    
    Args:
        room_id: Room ID
        global_id: Global person ID from tracking
        name: Name to assign to the person
    """
    from main import global_person_tracker
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    success = global_person_tracker.set_person_name(room_id, global_id, name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Person not found or no longer active")
    
    return {
        "message": f"Name '{name}' assigned to person {global_id}",
        "room_id": room_id,
        "global_id": global_id,
        "name": name
    }


@router.get("/{room_id}/person/{global_id}")
def get_person_info(room_id: UUID, global_id: int, db: Session = Depends(get_db)):
    """
    Get information about a specific tracked person
    
    Args:
        room_id: Room ID
        global_id: Global person ID from tracking
    """
    from main import global_person_tracker
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    person_info = global_person_tracker.get_person_info(room_id, global_id)
    
    if not person_info:
        raise HTTPException(status_code=404, detail="Person not found or no longer active")
    
    return person_info


@router.get("/{room_id}/layout", response_model=RoomLayoutResponse)
def get_room_layout(room_id: UUID, db: Session = Depends(get_db)):
    """
    Get room layout with camera positions and overlap zones
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        'room_id': room.id,
        'room_name': room.name,
        'dimensions': room.dimensions,
        'camera_positions': room.camera_positions or [],
        'overlap_zones': room.overlap_config.get('overlaps', []) if room.overlap_config else [],
        'floor_plan_image': room.floor_plan_image,
        'scale': room.layout_scale or 100
    }


@router.put("/{room_id}/layout")
def update_room_layout(
    room_id: UUID, 
    layout: RoomLayoutUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update room layout with camera positions and dimensions
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update dimensions
    if layout.dimensions:
        room.dimensions = layout.dimensions.dict()
    
    # Update camera positions
    if layout.camera_positions is not None:
        room.camera_positions = [pos.dict() for pos in layout.camera_positions]
        
        # Also update Camera model position_config
        for pos in layout.camera_positions:
            camera = db.query(Camera).filter(Camera.id == pos.camera_id).first()
            if camera:
                camera.position_config = pos.dict()
    
    # Update overlap zones
    if layout.overlap_zones is not None:
        if not room.overlap_config:
            room.overlap_config = {}
        room.overlap_config['overlaps'] = [zone.dict() for zone in layout.overlap_zones]
        
        # Configure global tracker with new overlap zones
        from main import global_person_tracker
        for zone in layout.overlap_zones:
            if len(zone.camera_ids) == 2:
                global_person_tracker.configure_overlap_zone(
                    room_id,
                    zone.camera_ids[0],
                    zone.camera_ids[1],
                    [{'x': p.x, 'y': p.y} for p in zone.polygon_points]
                )
    
    # Update floor plan image
    if layout.floor_plan_image is not None:
        room.floor_plan_image = layout.floor_plan_image
    
    # Update scale
    if layout.scale is not None:
        room.layout_scale = int(layout.scale)
    
    db.commit()
    db.refresh(room)
    
    return {
        'message': 'Layout updated successfully',
        'room_id': room.id
    }
