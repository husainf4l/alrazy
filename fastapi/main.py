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

# Set up loggingtcp link 
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
    
    # Start auto-recovery task for better reliability
    if not video_streaming_service._auto_recovery_started:
        await video_streaming_service.start_auto_recovery()
        video_streaming_service._auto_recovery_started = True
    
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
                camera_id = camera.get('id')  # Keep as integer
                camera_name = camera.get('name', f'Camera {camera_id}')
                
                logger.info(f"🔄 Processing camera {camera_id}: {camera_name}")
                
                # Get RTSP URL for this camera from standalone database
                rtsp_url = camera_service.get_camera_rtsp_url(camera_id)
                
                if not rtsp_url:
                    logger.warning(f"⚠️ No RTSP URL found for camera {camera_id}")
                    failed_streams += 1
                    continue
                
                # Create analyzed WebRTC stream with default live mode for maximum speed
                result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id, "live")
                
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
    """Serve the auto-streaming test HTML page."""
    try:
        import aiofiles
        async with aiofiles.open("test_streaming_auto.html", "r") as f:
            html_content = await f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Auto-streaming test page not found")


@app.get("/test-auto-streaming", response_class=HTMLResponse)
async def test_auto_streaming_page():
    """Serve the auto-streaming test HTML page with WebRTC links."""
    try:
        import aiofiles
        async with aiofiles.open("test_streaming_auto.html", "r") as f:
            html_content = await f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Auto-streaming test page not found")


@app.get("/camera-dashboard", response_class=HTMLResponse)
async def camera_dashboard_page():
    """Serve the camera dashboard HTML page."""
    try:
        import aiofiles
        async with aiofiles.open("camera_dashboard.html", "r") as f:
            html_content = await f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Camera dashboard page not found")


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


@app.get("/api/cameras/{camera_id}/tracking")
async def get_camera_tracking(camera_id: str):
    """Get tracking statistics for a specific camera."""
    try:
        # Find the session for this camera
        if camera_id in video_streaming_service.persistent_streams:
            stream_info = video_streaming_service.persistent_streams[camera_id]
            session_id = stream_info.get("session_id")
            
            if session_id and session_id in video_streaming_service.video_tracks:
                video_track = video_streaming_service.video_tracks[session_id]
                
                tracking_stats = {
                    "success": True,
                    "camera_id": camera_id,
                    "session_id": session_id,
                    "current_people_count": video_track.people_count,
                    "total_tracked_people": video_track.tracked_people_count,
                    "active_track_ids": list(video_track.current_tracked_ids),
                    "track_history_size": len(video_track.track_history),
                    "avg_people_count": sum(video_track.person_count_history) / len(video_track.person_count_history) if video_track.person_count_history else 0,
                    "streaming_mode": stream_info.get("streaming_mode", "unknown"),
                    "analysis_enabled": stream_info.get("analysis_enabled", False)
                }
                
                return JSONResponse(content=tracking_stats)
            else:
                raise HTTPException(status_code=404, detail="Video track not found for camera")
        else:
            raise HTTPException(status_code=404, detail="Camera stream not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tracking stats: {str(e)}")


@app.get("/api/tracking/summary")
async def get_all_tracking_summary():
    """Get tracking summary for all cameras."""
    try:
        summary = {
            "success": True,
            "total_cameras": len(video_streaming_service.persistent_streams),
            "cameras": []
        }
        
        for camera_id, stream_info in video_streaming_service.persistent_streams.items():
            session_id = stream_info.get("session_id")
            
            if session_id and session_id in video_streaming_service.video_tracks:
                video_track = video_streaming_service.video_tracks[session_id]
                
                camera_stats = {
                    "camera_id": camera_id,
                    "current_people": video_track.people_count,
                    "total_tracked": video_track.tracked_people_count,
                    "active_ids": len(video_track.current_tracked_ids),
                    "streaming_mode": stream_info.get("streaming_mode", "unknown"),
                    "analysis_enabled": stream_info.get("analysis_enabled", False)
                }
                
                summary["cameras"].append(camera_stats)
        
        # Calculate totals
        summary["total_current_people"] = sum(c["current_people"] for c in summary["cameras"])
        summary["total_tracked_people"] = sum(c["total_tracked"] for c in summary["cameras"])
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tracking summary: {str(e)}")


@app.get("/api/webrtc/stream/{session_id}")
@app.head("/api/webrtc/stream/{session_id}")
async def get_webrtc_stream_info(session_id: str):
    """Get WebRTC stream information for direct client connection."""
    try:
        # Clean up any closed connections first
        await video_streaming_service._cleanup_closed_connections()
        
        # Check if session exists
        active_streams = await video_streaming_service.get_active_streams()
        if session_id not in active_streams["active_sessions"]:
            # Try to recreate the session
            logger.info(f"Session {session_id} not found, attempting to recreate...")
            recreate_result = await video_streaming_service.recreate_session(session_id)
            
            if recreate_result["success"]:
                new_session_id = recreate_result["new_session_id"]
                logger.info(f"Session recreated: {session_id} -> {new_session_id}")
                
                return {
                    "success": True,
                    "session_recreated": True,
                    "old_session_id": session_id,
                    "new_session_id": new_session_id,
                    "status": "active",
                    "webrtc_endpoints": {
                        "offer": f"/api/streams/{new_session_id}/offer",
                        "answer": f"/api/streams/{new_session_id}/answer", 
                        "ice_candidate": f"/api/streams/{new_session_id}/ice-candidate"
                    },
                    "message": "WebRTC stream recreated and ready for connection"
                }
            
            raise HTTPException(status_code=404, detail="WebRTC stream not found and could not be recreated")
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "active",
            "webrtc_endpoints": {
                "offer": f"/api/streams/{session_id}/offer",
                "answer": f"/api/streams/{session_id}/answer", 
                "ice_candidate": f"/api/streams/{session_id}/ice-candidate"
            },
            "message": "WebRTC stream is active and ready for connection"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stream info: {str(e)}")


@app.post("/api/webrtc/stream/{session_id}/recreate")
async def recreate_webrtc_stream(session_id: str):
    """Recreate a WebRTC stream session if it was closed."""
    try:
        # Extract camera_id from session_id (format: camera_id_session_num)
        camera_id = session_id.split('_')[0]
        
        # Get RTSP URL for this camera from standalone database
        rtsp_url = camera_service.get_camera_rtsp_url(int(camera_id))
        if not rtsp_url:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found or no RTSP URL")
        
        # Clean up old session if it exists
        if session_id in video_streaming_service.peer_connections:
            await video_streaming_service._cleanup_session(session_id)
        
        # Create new WebRTC session
        result = await video_streaming_service.create_webrtc_offer(camera_id, rtsp_url)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to recreate stream: {result.get('error')}")
        
        new_session_id = result["session_id"]
        
        return {
            "success": True,
            "old_session_id": session_id,
            "new_session_id": new_session_id,
            "webrtc_endpoints": {
                "offer": f"/api/streams/{new_session_id}/offer",
                "answer": f"/api/streams/{new_session_id}/answer", 
                "ice_candidate": f"/api/streams/{new_session_id}/ice-candidate"
            },
            "message": "WebRTC stream recreated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recreate stream: {str(e)}")


# WebRTC Signaling endpoints for actual video streaming
@app.post("/api/streams/{session_id}/offer")
async def create_webrtc_offer(session_id: str):
    """Create WebRTC offer for existing session."""
    try:
        # Clean up any closed connections first
        await video_streaming_service._cleanup_closed_connections()
        
        # Check if session exists
        active_streams = await video_streaming_service.get_active_streams()
        if session_id not in active_streams["active_sessions"]:
            # Try to recreate the session
            logger.info(f"Session {session_id} not found, attempting to recreate...")
            recreate_result = await video_streaming_service.recreate_session(session_id)
            
            if recreate_result["success"]:
                # Use the new session ID
                new_session_id = recreate_result["new_session_id"]
                logger.info(f"Session recreated: {session_id} -> {new_session_id}")
                
                # Get the new peer connection
                if new_session_id in video_streaming_service.peer_connections:
                    pc = video_streaming_service.peer_connections[new_session_id]
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    
                    return {
                        "success": True,
                        "session_recreated": True,
                        "old_session_id": session_id,
                        "new_session_id": new_session_id,
                        "offer": {
                            "type": offer.type,
                            "sdp": offer.sdp
                        }
                    }
            
            raise HTTPException(status_code=404, detail="Session not found and could not be recreated")
        
        # Get the peer connection for this session
        if session_id in video_streaming_service.peer_connections:
            pc = video_streaming_service.peer_connections[session_id]
            
            # Check if connection is still open
            if pc.connectionState in ["closed", "failed"]:
                await video_streaming_service._cleanup_session(session_id)
                raise HTTPException(status_code=410, detail="Connection has been closed, please refresh to create a new session")
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            return {
                "success": True,
                "offer": {
                    "type": offer.type,
                    "sdp": offer.sdp
                }
            }
        else:
            raise HTTPException(status_code=404, detail="Peer connection not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create offer: {str(e)}")

@app.post("/api/streams/{session_id}/answer")
async def handle_webrtc_answer(session_id: str, answer: WebRTCAnswerRequest):
    """Handle WebRTC answer from client."""
    try:
        result = await video_streaming_service.handle_webrtc_answer(
            session_id, 
            {"sdp": answer.sdp, "type": answer.type}
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process answer"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")

@app.post("/api/streams/{session_id}/ice-candidate")
async def handle_ice_candidate(session_id: str, candidate: dict):
    """Handle ICE candidate from client."""
    try:
        result = await video_streaming_service.handle_ice_candidate(session_id, candidate)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process ICE candidate"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process ICE candidate: {str(e)}")


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


@app.post("/api/cameras/{camera_id}/stream/create")
async def create_camera_stream(camera_id: str, streaming_mode: str = "balanced"):
    """Create a camera stream with specified streaming mode."""
    try:
        # Validate streaming mode
        valid_modes = ["live", "balanced", "analysis"]
        if streaming_mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"Invalid streaming mode. Must be one of: {', '.join(valid_modes)}")
        
        # Stop existing stream if it exists
        if camera_id in video_streaming_service.persistent_streams:
            await video_streaming_service.stop_persistent_stream(camera_id)
            await asyncio.sleep(1)
        
        # Create WebRTC stream with specified mode
        result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id, streaming_mode)
        
        if result["success"]:
            return JSONResponse(content={
                **result,
                "message": f"Camera {camera_id} stream created successfully in {streaming_mode} mode"
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create stream: {str(e)}")


@app.post("/api/cameras/{camera_id}/stream/mode")
async def change_streaming_mode(camera_id: str, streaming_mode: str):
    """Change the streaming mode of an existing camera stream."""
    try:
        # Validate streaming mode
        valid_modes = ["live", "balanced", "analysis"]
        if streaming_mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"Invalid streaming mode. Must be one of: {', '.join(valid_modes)}")
        
        # Check if stream exists
        if camera_id not in video_streaming_service.persistent_streams:
            raise HTTPException(status_code=404, detail=f"No active stream found for camera {camera_id}")
        
        # Stop existing stream
        await video_streaming_service.stop_persistent_stream(camera_id)
        await asyncio.sleep(1)
        
        # Create new stream with new mode
        result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id, streaming_mode)
        
        if result["success"]:
            return JSONResponse(content={
                **result,
                "message": f"Camera {camera_id} streaming mode changed to {streaming_mode}"
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to change streaming mode"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change streaming mode: {str(e)}")


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
    print("🔍 YOLO-powered ultra-fast person detection enabled")
    print("💾 Camera records will be updated with WebRTC URLs")
    print("🌐 Server will start at: http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)