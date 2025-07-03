"""
Clean FastAPI Application - Minimal Security Camera System
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from typing import Dict, Any
from pydantic import BaseModel

# Import our services
from service.cameras import camera_service
from service.video_streaming import video_streaming_service

# Create FastAPI application
app = FastAPI(
    title="Clean FastAPI Application",
    description="A minimal FastAPI application with camera streaming",
    version="1.0.0"
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
    return {
        "message": "Clean FastAPI Application with Camera Streaming",
        "status": "operational",
        "version": "1.0.0",
        "features": ["camera_management", "webrtc_streaming"]
    }

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/test-streaming", response_class=HTMLResponse)
async def test_streaming_page():
    """Serve the test streaming HTML page."""
    try:
        with open("test_streaming.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Test streaming page not found")

# Camera endpoints
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

# WebRTC streaming endpoints
@app.post("/api/cameras/{camera_id}/stream/start")
async def start_camera_stream(camera_id: str):
    """Start WebRTC stream for a camera."""
    try:
        # Get RTSP URL for the camera
        rtsp_url = await camera_service.get_rtsp_url(camera_id)
        if not rtsp_url:
            raise HTTPException(status_code=404, detail="Camera RTSP URL not found")
        
        # Create WebRTC offer
        result = await video_streaming_service.create_webrtc_offer(camera_id, rtsp_url)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to start stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start stream: {str(e)}")

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
    """Handle incoming ICE candidate from client."""
    try:
        # Log incoming candidate data
        print(f"Received ICE candidate for session {session_id}: {candidate}")
        
        result = await video_streaming_service.handle_ice_candidate(session_id, candidate)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            print(f"Error processing ICE candidate for session {session_id}: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process ICE candidate"))
            
    except HTTPException as http_err:
        print(f"HTTPException while processing ICE candidate for session {session_id}: {http_err}")
        raise
    except Exception as e:
        print(f"Unexpected error while processing ICE candidate for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process ICE candidate: {str(e)}")

@app.delete("/api/streams/{session_id}")
async def stop_stream(session_id: str):
    """Stop a WebRTC stream session."""
    try:
        result = await video_streaming_service.stop_stream(session_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop stream: {str(e)}")

@app.get("/api/streams")
async def get_active_streams():
    """Get list of active streaming sessions."""
    try:
        result = await video_streaming_service.get_active_streams()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active streams: {str(e)}")

# Persistent WebRTC streaming endpoints
@app.post("/api/cameras/{camera_id}/webrtc/persistent")
async def create_persistent_webrtc_stream(camera_id: str):
    """Create a persistent WebRTC stream for a camera and update database."""
    try:
        # Get RTSP URL for the camera
        rtsp_url = await camera_service.get_rtsp_url(camera_id)
        if not rtsp_url:
            raise HTTPException(status_code=404, detail="Camera RTSP URL not found")
        
        # Create persistent WebRTC stream
        result = await video_streaming_service.create_persistent_webrtc_stream(camera_id, rtsp_url)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create persistent stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create persistent stream: {str(e)}")

@app.get("/api/webrtc/streams/persistent")
async def get_persistent_streams():
    """Get all persistent WebRTC streams."""
    try:
        result = await video_streaming_service.get_persistent_streams()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get persistent streams: {str(e)}")

@app.delete("/api/cameras/{camera_id}/webrtc/persistent")
async def stop_persistent_webrtc_stream(camera_id: str):
    """Stop a persistent WebRTC stream for a camera."""
    try:
        result = await video_streaming_service.stop_persistent_stream(camera_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop persistent stream: {str(e)}")

@app.get("/api/webrtc/stream/{session_id}")
async def get_webrtc_stream_info(session_id: str):
    """Get WebRTC stream information for direct client connection."""
    try:
        # Check if session exists
        active_streams = await video_streaming_service.get_active_streams()
        if session_id not in active_streams["active_sessions"]:
            raise HTTPException(status_code=404, detail="WebRTC stream not found")
        
        return {
            "success": True,
            "session_id": session_id,
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

# Complete analyzed streaming endpoints
@app.post("/api/cameras/{camera_id}/analyze-and-stream")
async def create_analyzed_webrtc_stream(camera_id: str):
    """
    Complete flow: Get RTSP URL -> Analyze with OpenCV -> Create WebRTC -> Update Camera
    """
    try:
        result = await video_streaming_service.create_analyzed_webrtc_stream(camera_id)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create analyzed stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create analyzed stream: {str(e)}")

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

# Simple HTTP streaming endpoints (as fallback)
@app.get("/api/cameras/{camera_id}/stream/http")
async def get_camera_http_stream(camera_id: str):
    """Get HTTP streaming URL for a camera (simple fallback)."""
    try:
        # Get RTSP URL for the camera
        rtsp_url = await camera_service.get_rtsp_url(camera_id)
        if not rtsp_url:
            raise HTTPException(status_code=404, detail="Camera RTSP URL not found")
        
        return {
            "success": True,
            "camera_id": camera_id,
            "rtsp_url": rtsp_url,
            "message": "RTSP URL retrieved successfully"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stream URL: {str(e)}")

# Simple MJPEG streaming endpoints
@app.post("/api/cameras/{camera_id}/stream/simple/start")
async def start_simple_stream(camera_id: str):
    """Start simple MJPEG stream for a camera."""
    try:
        # Get RTSP URL for the camera
        rtsp_url = await camera_service.get_rtsp_url(camera_id)
        if not rtsp_url:
            raise HTTPException(status_code=404, detail="Camera RTSP URL not found")
        
        # Start simple stream
        result = await simple_streaming_service.start_stream(camera_id, rtsp_url)
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to start stream"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simple stream: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    await video_streaming_service.cleanup_all_streams()
    await camera_service.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
