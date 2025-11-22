from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from database import get_db
from models.camera import Camera
from schemas.camera import CameraCreate, CameraUpdate, CameraResponse

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.post("/", response_model=CameraResponse, status_code=201)
async def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    """Create a new camera"""
    db_camera = Camera(
        name=camera.name,
        rtspUrl=camera.rtspUrl,
        description=camera.description,
        roomId=camera.roomId,
        businessId=camera.businessId,
        userId=camera.userId
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera


@router.get("/", response_model=List[CameraResponse])
async def get_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all cameras"""
    cameras = db.query(Camera).offset(skip).limit(limit).all()
    return cameras


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: UUID, db: Session = Depends(get_db)):
    """Get a specific camera by ID"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: UUID, camera_update: CameraUpdate, db: Session = Depends(get_db)):
    """Update a camera"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    if camera_update.name is not None:
        camera.name = camera_update.name
    if camera_update.rtspUrl is not None:
        camera.rtspUrl = camera_update.rtspUrl
    if camera_update.description is not None:
        camera.description = camera_update.description
    if camera_update.roomId is not None:
        camera.roomId = camera_update.roomId
    
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_id}")
async def delete_camera(camera_id: UUID, db: Session = Depends(get_db)):
    """Delete a camera and all its related detection records"""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Delete the camera
    try:
        db.delete(camera)
        db.commit()
        return {"success": True, "message": f"Camera {camera_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete camera: {str(e)}")
