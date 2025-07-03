"""
Auto-Streaming FastAPI Application
Automatically starts WebRTC streams for all cameras on startup
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Dict, Any
from pydantic import BaseModel
import logging
import asyncio
from contextlib import asynccontextmanager

# Import our services
from service.cameras import camera_service
from service.video_streaming import video_streaming_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting FastAPI application with auto-streaming...")
    
    # Auto-initialize all cameras with WebRTC streams
    await auto_initialize_camera_streams()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI application...")
    await video_streaming_service.cleanup_all_streams()
    await camera_service.close()


async def auto_initialize_camera_streams():
    """Automatically initialize WebRTC streams for all cameras and update NestJS backend."""
    try:
        logger.info("🎥 Auto-initializing camera streams...")
        
        # Fetch all cameras from NestJS API
        cameras = await camera_service.fetch_cameras_from_api()
        
        if not cameras:
            logger.warning("⚠️ No cameras found in the database")
            return
        
        logger.info(f"📋 Found {len(cameras)} cameras in database")
        
        # Process each camera
        successful_streams = 0
        failed_streams = 0
        
        for camera in cameras:
            try:
                camera_id = str(camera.get('id'))
                camera_name = camera.get('name', f'Camera {camera_id}')
                
                logger.info(f"🔄 Processing camera {camera_id}: {camera_name}")
                
                # Get RTSP URL for this camera
                rtsp_url = await camera_service.get_rtsp_url(camera_id)
                
                if not rtsp_url:
                    logger.warning(f"⚠️ No RTSP URL found for camera {camera_id}")
                    failed_streams += 1
                    continue
                
                # Create analyzed WebRTC stream
                result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id)
                
                if result["success"]:
                    successful_streams += 1
                    logger.info(f"✅ Successfully created WebRTC stream for camera {camera_id}")
                    logger.info(f"   📡 WebRTC URL: {result['webrtc_url']}")
                    logger.info(f"   🔍 Analysis enabled: {result['analysis_enabled']}")
                    logger.info(f"   💾 Database updated: {result['database_updated']}")
                else:
                    failed_streams += 1
                    logger.error(f"❌ Failed to create stream for camera {camera_id}: {result.get('error')}")
                
                # Small delay between camera processing to avoid overwhelming the system
                await asyncio.sleep(2)
                
            except Exception as e:
                failed_streams += 1
                logger.error(f"❌ Error processing camera {camera.get('id', 'unknown')}: {e}")
        
        # Summary
        logger.info(f"📊 Auto-initialization complete:")
        logger.info(f"   ✅ Successful streams: {successful_streams}")
        logger.info(f"   ❌ Failed streams: {failed_streams}")
        logger.info(f"   📡 Total active WebRTC streams: {len(video_streaming_service.persistent_streams)}")
        
        if successful_streams > 0:
            logger.info("🎉 Camera streaming system is now active with real-time AI analysis!")
            logger.info("🔗 All camera records in NestJS have been updated with WebRTC URLs")
        
    except Exception as e:
        logger.error(f"❌ Critical error in auto-initialization: {e}")


# Create FastAPI application with lifespan events
app = FastAPI(
    title="Auto-Streaming Video API",
    description="FastAPI service that automatically streams all cameras with OpenCV analysis on startup",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for requests
class WebRTCAnswerRequest(BaseModel):
    sdp: str
    type: str


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    active_streams = await video_streaming_service.get_active_streams()
    persistent_streams = await video_streaming_service.get_persistent_streams()
    
    return {
        "message": "Auto-Streaming FastAPI Application",
        "status": "operational",
        "version": "2.0.0",
        "features": [
            "auto_camera_streaming",
            "opencv_analysis", 
            "webrtc_streaming",
            "nestjs_database_integration"
        ],
        "statistics": {
            "active_sessions": active_streams["total_sessions"],
            "persistent_streams": persistent_streams["total_persistent"],
            "analysis_enabled": True
        }
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "auto_streaming": "active"}


@app.get("/test-streaming", response_class=HTMLResponse)
async def test_streaming_page():
    """Serve the test streaming HTML page."""
    try:
        with open("test_streaming.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Test streaming page not found")


# Status and monitoring endpoints
@app.get("/api/status")
async def get_system_status():
    """Get comprehensive system status."""
    try:
        active_streams = await video_streaming_service.get_active_streams()
        persistent_streams = await video_streaming_service.get_persistent_streams()
        cameras = await camera_service.fetch_cameras_from_api()
        
        return {
            "success": True,
            "system_status": "operational",
            "cameras": {
                "total_in_database": len(cameras),
                "with_active_streams": len(persistent_streams["persistent_streams"])
            },
            "streaming": {
                "active_sessions": active_streams["total_sessions"],
                "persistent_streams": persistent_streams["total_persistent"],
                "analysis_enabled": True
            },
            "features": [
                "Real-time OpenCV Analysis",
                "Motion Detection",
                "Person Detection", 
                "Face Detection",
                "WebRTC Streaming",
                "Auto Database Updates"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


@app.get("/api/streams/status")
async def get_streams_status():
    """Get detailed status of all streams."""
    try:
        active_streams = await video_streaming_service.get_active_streams()
        persistent_streams = await video_streaming_service.get_persistent_streams()
        
        return {
            "success": True,
            "active_streams": active_streams,
            "persistent_streams": persistent_streams,
            "message": "All streams initialized automatically on startup"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get streams status: {str(e)}")


@app.get("/api/cameras")
async def get_cameras():
    """Get all cameras from the database."""
    try:
        cameras = await camera_service.fetch_cameras_from_api()
        return {"success": True, "cameras": cameras, "count": len(cameras)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cameras: {str(e)}")


@app.get("/api/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """Get specific camera details."""
    try:
        camera = await camera_service.fetch_camera_by_id_from_api(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        return {"success": True, "camera": camera}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch camera: {str(e)}")


@app.get("/api/streams/{session_id}/analysis")
async def get_stream_analysis(session_id: str):
    """Get real-time analysis results from a video stream."""
    try:
        result = await video_streaming_service.get_stream_analysis(session_id)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "Stream not found"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis: {str(e)}")


# Manual control endpoints (for debugging/manual control)
@app.post("/api/cameras/{camera_id}/stream/restart")
async def restart_camera_stream(camera_id: str):
    """Manually restart a camera stream (for debugging)."""
    try:
        # Stop existing stream if it exists
        if camera_id in video_streaming_service.persistent_streams:
            await video_streaming_service.stop_persistent_stream(camera_id)
            await asyncio.sleep(1)
        
        # Create new analyzed WebRTC stream
        result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id)
        
        if result["success"]:
            return JSONResponse(content={
                **result,
                "message": f"Camera {camera_id} stream restarted successfully"
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to restart stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart stream: {str(e)}")


@app.delete("/api/cameras/{camera_id}/stream")
async def stop_camera_stream(camera_id: str):
    """Manually stop a camera stream."""
    try:
        result = await video_streaming_service.stop_persistent_stream(camera_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop stream: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Auto-Streaming FastAPI Application...")
    print("📺 This will automatically create WebRTC streams for all cameras")
    print("🔍 OpenCV analysis (motion, person, face detection) will be enabled")
    print("💾 Camera records will be updated with WebRTC URLs in NestJS backend")
    print("🌐 Server will start at: http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
