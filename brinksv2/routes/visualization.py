"""
Video Visualization Routes - Optimized for Low Latency
Serves annotated video frames with tracking overlays
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
import cv2
import numpy as np
from typing import Optional
from uuid import UUID
import time
from threading import Lock

router = APIRouter()

# Will be injected from main.py
people_detector = None
people_counter = None

# Per-camera frame cache with timestamp
_frame_cache = {}
_frame_lock = Lock()


def set_detection_service(detector, counter):
    """Set the detection service instances"""
    global people_detector, people_counter
    people_detector = detector
    people_counter = counter


def get_latest_frame(camera_id: UUID, use_cache: bool = True):
    """
    Get the latest annotated frame efficiently
    
    Args:
        camera_id: Camera identifier
        use_cache: Use cached frame to reduce repeated annotation overhead
    
    Returns:
        Annotated frame or None
    """
    if people_detector is None:
        return None
    
    try:
        # Get raw frame
        frame = people_detector.camera_tracks[camera_id].get('last_frame', None)
        if frame is None:
            return None
        
        # Use cached annotated frame if available and recent
        if use_cache:
            with _frame_lock:
                cache_key = f"camera_{camera_id}_annotated"
                cached_frame, cached_time = _frame_cache.get(cache_key, (None, 0))
                current_time = time.time()
                
                # Reuse cached frame if less than 100ms old
                if cached_frame is not None and (current_time - cached_time) < 0.1:
                    return cached_frame
        
        # Annotate frame (minimal overhead)
        annotated = people_detector.draw_tracks(frame, camera_id)
        
        # Cache the annotated frame
        if use_cache:
            with _frame_lock:
                cache_key = f"camera_{camera_id}_annotated"
                _frame_cache[cache_key] = (annotated, time.time())
        
        return annotated
    except Exception as e:
        print(f"Error getting frame for camera {camera_id}: {e}")
        return None


def generate_frame_stream(camera_id: UUID, fps: int = 10, quality: int = 80):
    """
    Generate optimized MJPEG stream with annotated frames
    
    Args:
        camera_id: Camera identifier
        fps: Frames per second for the stream
        quality: JPEG quality (1-100, lower = faster but lower quality)
    """
    frame_interval = 1.0 / fps
    
    while True:
        start_time = time.time()
        
        try:
            if people_detector is None:
                # Send a blank error frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Detection service not ready", (50, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # Get annotated frame (with caching)
                frame = get_latest_frame(camera_id, use_cache=True)
                
                if frame is None:
                    # Send waiting frame
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, f"Waiting for camera {camera_id}...", (50, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Encode frame as JPEG with optimized quality
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' + 
                   frame_bytes + b'\r\n')
            
            # Control frame rate with minimal overhead
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            
            # Adaptive sleep: don't sleep if we're already behind
            if sleep_time > 0:
                time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Error in frame stream for camera {camera_id}: {e}")
            time.sleep(0.1)


@router.get("/visualization/camera/{camera_id}/stream")
async def get_camera_visualization_stream(camera_id: UUID, fps: Optional[int] = 10, quality: Optional[int] = 80):
    """
    Get MJPEG stream with tracking visualization for a camera
    Optimized for low latency
    
    Args:
        camera_id: Camera identifier
        fps: Frames per second (default: 10, max: 30)
        quality: JPEG quality 1-100 (default: 80, higher = better quality but larger size)
    
    Returns:
        MJPEG stream
    """
    if people_detector is None:
        raise HTTPException(status_code=503, detail="Detection service not initialized")
    
    # Limit FPS to avoid overload
    fps = min(fps, 30)
    fps = max(fps, 1)
    
    # Quality constraints
    quality = max(30, min(quality, 100))
    
    return StreamingResponse(
        generate_frame_stream(camera_id, fps, quality),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/visualization/camera/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: UUID, quality: Optional[int] = 90):
    """
    Get a single annotated snapshot of a camera
    
    Args:
        camera_id: Camera identifier
        quality: JPEG quality 1-100 (default: 90)
    
    Returns:
        JPEG image with tracking visualization
    """
    if people_detector is None:
        raise HTTPException(status_code=503, detail="Detection service not initialized")
    
    # Get annotated frame
    annotated_frame = get_latest_frame(camera_id, use_cache=False)
    
    if annotated_frame is None:
        raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")
    
    # Quality constraints
    quality = max(30, min(quality, 100))
    
    # Encode as JPEG
    ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    
    return Response(content=buffer.tobytes(), media_type="image/jpeg")
