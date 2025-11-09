from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import logging
import asyncio
import cv2

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        # Initialize YOLO service with medium model (same as brinksv2)
        logger.info("Initializing YOLO11 service...")
        yolo_service = YOLOService(model_name="yolo11m.pt", confidence_threshold=0.5)
        
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

# Mount static files (you can create this folder later if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.websocket("/ws/camera/{camera_id}")
async def websocket_camera_stream(websocket: WebSocket, camera_id: int):
    """
    WebSocket endpoint for real-time camera streaming with tracking visualization
    Streams JPEG frames at 25-30 FPS with baked-in tracking boxes, IDs, and trails
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for camera {camera_id}")
    
    try:
        if not camera_service or camera_id not in camera_service.processors:
            await websocket.send_json({"error": f"Camera {camera_id} not found"})
            await websocket.close()
            return
        
        processor = camera_service.processors[camera_id]
        frame_count = 0
        target_fps = 25  # Slightly lower than processing for smooth streaming
        frame_interval = 1.0 / target_fps
        
        while True:
            try:
                # Get latest annotated frame (with tracking visualization)
                if processor.last_annotated_frame is not None:
                    frame = processor.last_annotated_frame.copy()
                    
                    # Encode as JPEG (quality 80 for balance)
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    
                    # Send as binary data (no base64 overhead)
                    await websocket.send_bytes(buffer.tobytes())
                    frame_count += 1
                    
                    if frame_count % 100 == 0:
                        logger.debug(f"Camera {camera_id}: Sent {frame_count} frames via WebSocket")
                else:
                    # Send placeholder if no frame yet
                    await websocket.send_json({"status": "waiting_for_frame"})
                
                # Sleep to maintain target FPS
                await asyncio.sleep(frame_interval)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for camera {camera_id}")
                break
            except Exception as e:
                logger.error(f"Error streaming camera {camera_id}: {e}")
                await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"WebSocket error for camera {camera_id}: {e}")
    finally:
        logger.info(f"WebSocket closed for camera {camera_id}, sent {frame_count} frames")


if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)