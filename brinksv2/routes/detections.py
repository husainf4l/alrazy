from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from database import get_db
from models.camera import DetectionCount, Camera
from schemas.detection import DetectionCountResponse, LiveDetectionStats

router = APIRouter(prefix="/detections", tags=["detections"])


@router.get("/live", response_model=List[LiveDetectionStats])
def get_live_detections():
    """
    Get live people detection counts from all cameras
    """
    from main import people_counter
    
    if people_counter is None:
        raise HTTPException(status_code=503, detail="Detection service not running")
    
    stats = people_counter.get_stats()
    
    # Get camera names
    from database import SessionLocal
    db = SessionLocal()
    cameras = {c.id: c.name for c in db.query(Camera).all()}
    db.close()
    
    # Format response
    live_stats = []
    for stat in stats:
        camera_id = stat['camera_id']
        live_stats.append(LiveDetectionStats(
            camera_id=camera_id,
            camera_name=cameras.get(camera_id, f"Camera {camera_id}"),
            current_count=stat['current_count'],
            average_count=stat['average_count'],
            active_tracks=stat['active_tracks'],
            last_update=stat['last_update'],
            history_size=stat['history_size']
        ))
    
    return live_stats


@router.get("/history/{camera_id}", response_model=List[DetectionCountResponse])
def get_detection_history(
    camera_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get historical people detection counts for a specific camera
    
    Args:
        camera_id: Camera ID
        hours: Number of hours to retrieve (default: 24)
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    counts = db.query(DetectionCount).filter(
        DetectionCount.camera_id == camera_id,
        DetectionCount.timestamp >= since
    ).order_by(DetectionCount.timestamp.desc()).all()
    
    return counts


@router.get("/history", response_model=List[DetectionCountResponse])
def get_all_detection_history(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get historical people detection counts for all cameras
    
    Args:
        hours: Number of hours to retrieve (default: 24)
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    counts = db.query(DetectionCount).filter(
        DetectionCount.timestamp >= since
    ).order_by(DetectionCount.timestamp.desc()).all()
    
    return counts


@router.post("/log")
def log_detection_count(camera_id: int, people_count: int, average_count: float = None, db: Session = Depends(get_db)):
    """
    Log a detection count to the database
    
    Args:
        camera_id: Camera ID
        people_count: Current people count
        average_count: Average count (optional)
    """
    detection = DetectionCount(
        camera_id=camera_id,
        people_count=people_count,
        average_count=average_count
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    
    return {"status": "success", "id": detection.id}
