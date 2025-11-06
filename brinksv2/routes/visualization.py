"""
Video Visualization Routes
Serves annotated video frames with tracking overlays
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
import cv2
import numpy as np
from typing import Optional
import time

router = APIRouter()

# Will be injected from main.py
people_detector = None
people_counter = None


def set_detection_service(detector, counter):
    """Set the detection service instances"""
    global people_detector, people_counter
    people_detector = detector
    people_counter = counter


def generate_frame_stream(camera_id: int, fps: int = 10):
    """
    Generate MJPEG stream with annotated frames
    
    Args:
        camera_id: Camera identifier
        fps: Frames per second for the stream
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
                # Get the last processed frame
                frame = people_detector.camera_tracks[camera_id].get('last_frame', None)
                
                if frame is None:
                    # Send waiting frame
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, f"Waiting for camera {camera_id}...", (50, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    # Draw tracking annotations
                    frame = people_detector.draw_tracks(frame, camera_id)
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Error in frame stream for camera {camera_id}: {e}")
            time.sleep(0.1)


@router.get("/visualization/camera/{camera_id}/stream")
async def get_camera_visualization_stream(camera_id: int, fps: Optional[int] = 10):
    """
    Get MJPEG stream with tracking visualization for a camera
    
    Args:
        camera_id: Camera identifier
        fps: Frames per second (default: 10, max: 30)
    
    Returns:
        MJPEG stream
    """
    if people_detector is None:
        raise HTTPException(status_code=503, detail="Detection service not initialized")
    
    # Limit FPS to avoid overload
    fps = min(fps, 30)
    fps = max(fps, 1)
    
    return StreamingResponse(
        generate_frame_stream(camera_id, fps),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/visualization/camera/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: int):
    """
    Get a single annotated snapshot of a camera
    
    Args:
        camera_id: Camera identifier
    
    Returns:
        JPEG image with tracking visualization
    """
    if people_detector is None:
        raise HTTPException(status_code=503, detail="Detection service not initialized")
    
    # Get the last processed frame
    frame = people_detector.camera_tracks[camera_id].get('last_frame', None)
    
    if frame is None:
        raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")
    
    # Draw tracking annotations
    annotated_frame = people_detector.draw_tracks(frame, camera_id)
    
    # Encode as JPEG
    ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    
    return Response(content=buffer.tobytes(), media_type="image/jpeg")
