from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import cv2
import numpy as np
import time
import json
import asyncio

# Import routers
from routes.pages import router as pages_router
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.vault_rooms import router as vault_rooms_router

# Import services
from services.yolo_service import YOLOService
from services.tracking_service import TrackingService
from services.camera_service import CameraService
from database import SessionLocal

# Configure centralized logging and settings
from logging_config import setup_logging, get_logger
from config import get_settings

# Setup logging (INFO level for production, DEBUG for development)
setup_logging(log_level="INFO")
logger = get_logger(__name__)
settings = get_settings()

# Global service instances
yolo_service = None
tracking_service = None
camera_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    global yolo_service, tracking_service, camera_service
    
    logger.info("Starting RAZZv4 Backend...")
    
    try:
        # Initialize YOLO service from config (uses .env settings)
        logger.info(f"Initializing YOLO11 service with {settings.YOLO_MODEL}...")
        yolo_service = YOLOService()  # Uses config defaults
        
        # Initialize tracking service (BRINKSv2 style: ByteTrack + DeepSORT)
        # No args needed - it creates trackers per camera automatically
        logger.info("Initializing tracking service...")
        tracking_service = TrackingService()
        
        # Initialize camera service
        logger.info("Initializing camera service...")
        camera_service = CameraService(yolo_service, tracking_service, SessionLocal)
        
        # Start processing all active cameras
        logger.info("Starting camera monitoring...")
        camera_service.start_all_cameras()
        
        logger.info("RAZZv4 Backend started successfully!")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAZZv4 Backend...")
    if camera_service:
        camera_service.stop_all_cameras()
    logger.info("RAZZv4 Backend stopped successfully!")


# Create FastAPI instance with lifespan
app = FastAPI(
    title="RAZZv4 Backend API",
    description="FastAPI backend for RAZZv4 Banking Security System with YOLO11 People Counting",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(vault_rooms_router)

# Mount static files for CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")


# MJPEG Streaming Endpoint - Real-time with tracking visualization!
@app.get("/camera/{camera_id}/stream")
async def camera_mjpeg_stream(camera_id: int, fps: int = 30):
    """
    MJPEG stream endpoint for real-time camera streaming with tracking visualization
    Streams annotated frames with tracking boxes, IDs, and trails
    Much lower latency than WebSocket!
    """
    if not camera_service or camera_id not in camera_service.processors:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    processor = camera_service.processors[camera_id]
    
    def generate_mjpeg():
        """Generate MJPEG stream"""
        frame_interval = 1.0 / min(fps, 30)  # Limit to 30 FPS max
        
        while True:
            start_time = time.time()
            
            try:
                if processor.last_annotated_frame is not None:
                    frame = processor.last_annotated_frame.copy()
                else:
                    # Waiting frame
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, f"Waiting for camera {camera_id}...", (50, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Encode as JPEG (quality 70 for balance)
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
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
                logger.error(f"Error in MJPEG stream for camera {camera_id}: {e}")
                time.sleep(0.1)
    
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# WebSocket endpoint for tracking data only (4-6 FPS from YOLO)
@app.websocket("/ws/tracking/{camera_id}")
async def websocket_tracking_endpoint(websocket: WebSocket, camera_id: int):
    """
    WebSocket endpoint that sends only tracking data (bounding boxes, IDs, etc.)
    This runs at YOLO detection rate (4-6 FPS) and is overlayed on WebRTC video
    
    Data format:
    {
        "camera_id": int,
        "timestamp": float,
        "tracks": [
            {
                "track_id": int,
                "bbox": [x1, y1, x2, y2],
                "confidence": float,
                "center": [x, y],
                "source": str  // "bytetrack" or "deepsort"
            }
        ],
        "stats": {
            "fps": float,
            "active_tracks": int,
            "frame_count": int
        }
    }
    """
    await websocket.accept()
    logger.info(f"WebSocket tracking connection opened for camera {camera_id}")
    
    if not camera_service or camera_id not in camera_service.processors:
        await websocket.send_json({"error": f"Camera {camera_id} not found"})
        await websocket.close()
        return
    
    processor = camera_service.processors[camera_id]
    
    try:
        while True:
            # Send tracking data at YOLO detection rate (4-6 FPS)
            tracks_list = []
            
            if processor.last_tracks:
                for track_id, track_data in processor.last_tracks.items():
                    tracks_list.append({
                        "track_id": int(track_id) if isinstance(track_id, int) else str(track_id),
                        "bbox": track_data.get("bbox", [0, 0, 0, 0]),
                        "confidence": float(track_data.get("confidence", 0.0)),
                        "center": track_data.get("center", [0, 0]),
                        "source": track_data.get("source", "unknown")
                    })
            
            tracking_data = {
                "camera_id": camera_id,
                "timestamp": time.time(),
                "tracks": tracks_list,
                "stats": {
                    "fps": round(processor.fps, 2) if hasattr(processor, 'fps') else 0,
                    "active_tracks": len(tracks_list),
                    "frame_count": processor.frame_count if hasattr(processor, 'frame_count') else 0
                }
            }
            
            await websocket.send_json(tracking_data)
            
            # Send at ~6 FPS (YOLO detection rate)
            await asyncio.sleep(0.16)  # ~6 FPS
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket tracking connection closed for camera {camera_id}")
    except Exception as e:
        logger.error(f"Error in tracking WebSocket for camera {camera_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


# Add endpoint to get service status
@app.get("/api/services/status")
async def get_services_status():
    """Get status of AI services"""
    global yolo_service, tracking_service, camera_service
    
    return {
        "yolo_service": {
            "initialized": yolo_service is not None,
            "model": yolo_service.model_name if yolo_service else None,
            "device": yolo_service.device if yolo_service else None
        },
        "tracking_service": {
            "initialized": tracking_service is not None,
            "statistics": tracking_service.get_statistics() if tracking_service else {}
        },
        "camera_service": {
            "initialized": camera_service is not None,
            "active_cameras": len(camera_service.processors) if camera_service else 0
        }
    }


if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)