from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any
import atexit
import json
import asyncio
import os
import time
import time
import concurrent.futures
from camera_service import (
    initialize_camera, 
    get_camera_frame, 
    get_camera_info, 
    detect_motion_in_frame,
    cleanup_camera,
    initialize_all_cameras,
    get_all_cameras_info,
    detect_motion_all_cameras,
    get_available_cameras
)
from websocket_service import manager, handle_websocket_message
from security_orchestrator import (
    initialize_security_system,
    get_security_orchestrator,
    get_default_config
)
from activity_detection import get_pharmacy_risk_assessment
from llm_analysis import get_llm_analyzer
from video_recording import get_recording_service
from webhook_alerts import get_webhook_service, WebhookConfig
import numpy as np

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json with environment variable substitution."""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        # Substitute environment variables
        def substitute_env_vars(obj):
            if isinstance(obj, dict):
                return {k: substitute_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_env_vars(v) for v in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                env_var = obj[2:-1]
                return os.getenv(env_var, "")
            else:
                return obj
        
        return substitute_env_vars(config)
    except FileNotFoundError:
        print("config.json not found, using default configuration")
        return get_default_config()
    except Exception as e:
        print(f"Error loading config.json: {e}, using default configuration")
        return get_default_config()

app = FastAPI(
    title="Security Camera FastAPI App",
    description="A FastAPI application with RTSP camera integration for computer vision security",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize cameras on startup
@app.on_event("startup")
async def startup_event():
    """Initialize all cameras and security system when the app starts."""
    print("🚀 Starting security monitoring application...")
    
    # Skip camera initialization but set up for manual initialization later
    print("📷 Skipping automatic camera initialization...")
    print("   Cameras will be initialized on-demand when accessed")
    print("   Use /cameras/initialize endpoint to manually initialize cameras")
    
    # Initialize security system with graceful fallback
    try:
        config = load_config()
        print(f"⚙️  Loaded configuration with LLM enabled: {config['llm_config'].get('enabled', False)}")
        
        # Try to initialize security system but don't fail if it doesn't work
        try:
            security_system = initialize_security_system(config)
            await security_system.initialize()
            security_system.start()
            print("🔒 Advanced Security System initialized and started")
        except Exception as e:
            print(f"⚠️  Warning: Advanced security system initialization failed: {e}")
            print("   Application will run in basic mode without advanced features")
            
    except Exception as e:
        print(f"⚠️  Warning: Configuration loading failed: {e}")
        print("   Application will run with default settings")
    
    print("✅ Application startup completed - Server is ready!")
    print("📋 Available endpoints:")
    print("   - Main dashboard: http://localhost:8000")
    print("   - Security dashboard: http://localhost:8000/security-dashboard")
    print("   - Multi-camera view: http://localhost:8000/multi-camera")
    print("   - Initialize cameras: POST http://localhost:8000/cameras/initialize")

# Cleanup cameras on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup all cameras and security system when the app shuts down."""
    # Stop security system
    security_system = get_security_orchestrator()
    if security_system:
        security_system.stop()
        print("Security system stopped")
    
    # Cleanup cameras
    cleanup_camera()  # This will clean up all cameras
    print("All camera resources cleaned up")

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint that returns comprehensive Al Razy Pharmacy Security System status."""
    try:
        # Get basic system info
        system_info = {
            "message": "Al Razy Pharmacy Security System",
            "version": "1.0.0",
            "system_status": "online",
            "timestamp": time.time()
        }
        
        # Get pharmacy risk assessment
        try:
            risk_assessment = get_pharmacy_risk_assessment()
            system_info["risk_assessment"] = risk_assessment
        except Exception as e:
            system_info["risk_assessment"] = {"error": str(e), "status": "unavailable"}
        
        # Get camera status
        try:
            available_cameras = get_available_cameras()
            system_info["cameras"] = {
                "total_cameras": len(available_cameras),
                "available_cameras": available_cameras,
                "status": "operational" if available_cameras else "no_cameras"
            }
        except Exception as e:
            system_info["cameras"] = {
                "total_cameras": 0,
                "available_cameras": [],
                "status": "unavailable", 
                "message": "Cameras not initialized. Use /cameras/initialize to connect."
            }
        
        # Get security system status
        try:
            security_system = get_security_orchestrator()
            if security_system:
                security_status = security_system.get_system_status()
                system_info["security_system"] = security_status
            else:
                system_info["security_system"] = {"status": "not_initialized", "basic_mode": True}
        except Exception as e:
            system_info["security_system"] = {"error": str(e), "status": "error"}
        
        # Get LLM status
        try:
            llm_analyzer = get_llm_analyzer()
            system_info["llm_analysis"] = {
                "available": llm_analyzer is not None,
                "status": "active" if llm_analyzer else "disabled"
            }
        except Exception as e:
            system_info["llm_analysis"] = {"error": str(e), "status": "error"}
        
        # Add navigation links
        system_info["dashboards"] = {
            "security_dashboard": "/security-dashboard",
            "streaming_dashboard": "/streaming-dashboard", 
            "multi_camera": "/multi-camera",
            "analytics_dashboard": "/analytics-dashboard"
        }
        
        system_info["api_endpoints"] = {
            "health": "/health",
            "cameras_info": "/cameras/info",
            "security_status": "/security/status",
            "risk_assessment": "/security/risk-assessment",
            "recordings": "/recordings/active",
            "webhooks": "/webhooks/status",
            "test_external_camera": "/camera/test-external"
        }
        
        return system_info
        
    except Exception as e:
        return {
            "message": "Al Razy Pharmacy Security System",
            "status": "error",
            "error": str(e),
            "fallback": "System operational in basic mode"
        }

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "FastAPI App"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None) -> Dict[str, Any]:
    """Get an item by ID with optional query parameter."""
    result = {"item_id": item_id}
    if q:
        result.update({"q": q})
    return result

@app.post("/items/")
async def create_item(name: str, price: float, description: str = None) -> Dict[str, Any]:
    """Create a new item."""
    item = {
        "name": name,
        "price": price,
        "description": description
    }
    return {"message": "Item created successfully", "item": item}

@app.get("/camera/info")
async def get_camera_info_endpoint(camera_id: int = 1) -> Dict[str, Any]:
    """Get RTSP camera stream information for a specific camera."""
    try:
        info = get_camera_info(camera_id)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting camera {camera_id} info: {str(e)}")

@app.get("/cameras/info")
async def get_all_cameras_info_endpoint() -> Dict[str, Any]:
    """Get RTSP camera stream information for all cameras."""
    try:
        # Try to get camera info, but handle gracefully if cameras aren't available
        try:
            all_info = get_all_cameras_info()
            available_cameras = get_available_cameras()
        except Exception as camera_error:
            # If cameras aren't available, return appropriate message
            return {
                "cameras": {},
                "total_cameras": 0,
                "available_camera_ids": [],
                "status": "no_cameras_available",
                "message": "No cameras currently available. Use /cameras/initialize to connect cameras.",
                "error": str(camera_error)
            }
        
        return {
            "cameras": all_info,
            "total_cameras": len(all_info),
            "available_camera_ids": available_cameras,
            "status": "operational"
        }
    except Exception as e:
        return {
            "cameras": {},
            "total_cameras": 0,
            "available_camera_ids": [],
            "status": "error",
            "error": str(e),
            "message": "Error getting camera information"
        }

@app.get("/cameras/frames")
async def get_all_camera_frames_endpoint() -> Dict[str, Any]:
    """Get current frames from all cameras as base64 encoded images."""
    try:
        results = {}
        
        # Try to get available cameras, handle gracefully if none available
        try:
            available_cameras = get_available_cameras()
        except Exception:
            available_cameras = []
        
        if not available_cameras:
            return {
                "success": True,
                "cameras": {},
                "total_cameras": 0,
                "message": "No cameras currently available",
                "timestamp": time.time()
            }
        
        for camera_id in available_cameras:
            try:
                frame_b64 = get_camera_frame(camera_id)
                results[str(camera_id)] = {
                    "success": bool(frame_b64),
                    "camera_id": camera_id,
                    "frame": frame_b64,
                    "format": "base64_jpeg",
                    "timestamp": time.time()
                }
            except Exception as e:
                results[str(camera_id)] = {
                    "success": False,
                    "camera_id": camera_id,
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        return {
            "success": True,
            "cameras": results,
            "total_cameras": len(available_cameras),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "cameras": {},
            "total_cameras": 0,
            "error": str(e),
            "message": "Error getting camera frames",
            "timestamp": time.time()
        }

@app.get("/camera/frame")
async def get_camera_frame_endpoint(camera_id: int = 1) -> Dict[str, Any]:
    """Get current frame from RTSP camera as base64 encoded image."""
    try:
        frame_b64 = get_camera_frame(camera_id)
        if frame_b64:
            return {
                "success": True,
                "camera_id": camera_id,
                "frame": frame_b64,
                "format": "base64_jpeg"
            }
        else:
            return {
                "success": False,
                "camera_id": camera_id,
                "message": f"No frame available from camera {camera_id}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting camera {camera_id} frame: {str(e)}")

@app.get("/camera/motion")
async def detect_motion_endpoint(camera_id: int = 1) -> Dict[str, Any]:
    """Detect motion in the current camera frame."""
    try:
        result = detect_motion_in_frame(camera_id)
        return {
            "success": True,
            "camera_id": result["camera_id"],
            "motion_detected": result["motion_detected"],
            "frame_with_annotations": result["frame"],
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting motion on camera {camera_id}: {str(e)}")

@app.get("/cameras/motion")
async def detect_motion_all_cameras_endpoint() -> Dict[str, Any]:
    """Detect motion in all cameras."""
    try:
        results = detect_motion_all_cameras()
        return {
            "success": True,
            "cameras": results,
            "motion_summary": {
                camera_id: result["motion_detected"] 
                for camera_id, result in results.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting motion on all cameras: {str(e)}")

@app.post("/camera/initialize")
async def initialize_camera_endpoint(camera_id: int = 1) -> Dict[str, str]:
    """Manually initialize or reconnect a specific camera."""
    try:
        success = initialize_camera(camera_id)
        if success:
            return {"message": f"Camera {camera_id} initialized successfully", "status": "connected", "camera_id": camera_id}
        else:
            return {"message": f"Failed to initialize camera {camera_id}", "status": "disconnected", "camera_id": camera_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing camera {camera_id}: {str(e)}")

@app.post("/cameras/initialize")
async def initialize_all_cameras_endpoint() -> Dict[str, Any]:
    """Manually initialize or reconnect all cameras."""
    try:
        results = initialize_all_cameras()
        return {
            "message": "Camera initialization completed",
            "results": results,
            "summary": {
                "total": len(results),
                "connected": sum(1 for status in results.values() if status == "connected"),
                "failed": sum(1 for status in results.values() if status != "connected")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing all cameras: {str(e)}")

@app.get("/cameras/list")
async def list_cameras_endpoint() -> Dict[str, Any]:
    """Get list of available cameras."""
    try:
        try:
            camera_ids = get_available_cameras()
            return {
                "available_cameras": camera_ids,
                "total_cameras": len(camera_ids),
                "status": "operational" if camera_ids else "no_cameras"
            }
        except Exception:
            return {
                "available_cameras": [],
                "total_cameras": 0,
                "status": "not_initialized",
                "message": "Cameras not initialized. Use /cameras/initialize to connect cameras."
            }
    except Exception as e:
        return {
            "available_cameras": [],
            "total_cameras": 0,
            "status": "error",
            "error": str(e)
        }

@app.get("/dashboard")
async def dashboard():
    """Serve the camera dashboard HTML page."""
    return FileResponse("static/index.html")

@app.get("/multi-dashboard")
async def multi_dashboard():
    """Serve the multi-camera dashboard HTML page."""
    return FileResponse("static/multi-camera.html")

@app.get("/camera/test")
async def test_camera_endpoint() -> Dict[str, Any]:
    """Test camera connection and capture a single frame."""
    try:
        import cv2
        cap = cv2.VideoCapture("rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101")
        
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                return {
                    "success": True,
                    "message": "Camera test successful",
                    "frame_shape": list(frame.shape),
                    "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
                }
            else:
                return {
                    "success": False,
                    "message": "Could not read frame from camera"
                }
        else:
            return {
                "success": False,
                "message": "Could not connect to camera"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Camera test failed: {str(e)}"
        }

@app.get("/camera/test-external")
async def test_external_camera_endpoint() -> Dict[str, Any]:
    """Test the new external camera connection (Camera 5)."""
    try:
        import cv2
        camera_url = "rtsp://91.240.87.6:554/user=admin&password=&channel=1&stream=0.sdp"
        
        # Test connection with multiple backends
        backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
        
        for backend in backends:
            try:
                cap = cv2.VideoCapture(camera_url, backend)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret and frame is not None:
                        return {
                            "success": True,
                            "camera_id": 5,
                            "camera_url": camera_url,
                            "backend_used": backend,
                            "message": "External camera connection successful",
                            "frame_shape": list(frame.shape),
                            "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
                        }
                    else:
                        cap.release()
                        continue
                else:
                    cap.release()
                    continue
                    
            except Exception as e:
                continue
        
        return {
            "success": False,
            "camera_id": 5,
            "camera_url": camera_url,
            "message": "Could not connect to external camera with any backend",
            "tested_backends": [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
        }
    except Exception as e:
        return {
            "success": False,
            "camera_id": 5,
            "message": f"External camera test failed: {str(e)}"
        }

@app.websocket("/ws/camera/{camera_id}")
async def websocket_camera_endpoint(websocket: WebSocket, camera_id: int):
    """WebSocket endpoint for real-time camera frame streaming."""
    await manager.connect(websocket, camera_id)
    try:
        while True:
            # Receive message from WebSocket (e.g., for control commands)
            message = await manager.receive_message(websocket)
            if message:
                # Handle the received message (e.g., control camera, change settings)
                await handle_websocket_message(message, camera_id)
            
            # Get the latest frame from the camera
            frame = get_camera_frame(camera_id)
            if frame:
                # Send the frame to the WebSocket client
                await manager.send_frame(websocket, frame)
            await asyncio.sleep(0.1)  # Adjust the rate as needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, camera_id)
    except Exception as e:
        print(f"Error in WebSocket connection for camera {camera_id}: {str(e)}")
        manager.disconnect(websocket, camera_id)

# WebSocket endpoints for real-time streaming
@app.websocket("/ws/camera-streams")
async def camera_streams_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time camera streaming."""
    await manager.connect(websocket, "camera_streams")
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "camera_streams")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, "camera_streams")

@app.websocket("/ws/motion-detection")
async def motion_detection_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time motion detection alerts."""
    await manager.connect(websocket, "motion_detection")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "motion_detection")
    except Exception as e:
        print(f"Motion detection WebSocket error: {e}")
        manager.disconnect(websocket, "motion_detection")

@app.websocket("/ws/system-status")
async def system_status_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time system status updates."""
    await manager.connect(websocket, "system_status")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "system_status")
    except Exception as e:
        print(f"System status WebSocket error: {e}")
        manager.disconnect(websocket, "system_status")

# Streaming dashboard
@app.get("/streaming-dashboard")
async def streaming_dashboard():
    """Serve the real-time streaming dashboard."""
    return FileResponse("static/streaming-dashboard.html")

# Advanced Security System Endpoints

@app.get("/security/status")
async def get_security_status() -> Dict[str, Any]:
    """Get comprehensive security system status."""
    try:
        security_system = get_security_orchestrator()
        if security_system:
            return security_system.get_system_status()
        else:
            return {
                "message": "Security system not initialized",
                "basic_motion_detection": True,
                "advanced_features": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting security status: {str(e)}")

@app.get("/security/risk-assessment")
async def get_risk_assessment() -> Dict[str, Any]:
    """Get current pharmacy risk assessment."""
    try:
        risk_assessment = get_pharmacy_risk_assessment()
        return {
            "success": True,
            "risk_assessment": risk_assessment
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting risk assessment: {str(e)}")

@app.get("/security/events")
async def get_security_events(hours: int = 24) -> Dict[str, Any]:
    """Get recent security events."""
    try:
        security_system = get_security_orchestrator()
        if security_system:
            events = security_system.get_recent_events(hours)
            return {
                "success": True,
                "events": events,
                "total_events": len(events),
                "time_period_hours": hours
            }
        else:
            return {
                "success": False,
                "message": "Security system not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting security events: {str(e)}")

@app.get("/security/analytics")
async def get_security_analytics() -> Dict[str, Any]:
    """Get security analytics and insights."""
    try:
        security_system = get_security_orchestrator()
        if security_system:
            analytics = security_system.get_security_analytics()
            return {
                "success": True,
                "analytics": analytics
            }
        else:
            return {
                "success": False,
                "message": "Security system not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting security analytics: {str(e)}")

@app.post("/security/process-frame")
async def process_security_frame(camera_id: int) -> Dict[str, Any]:
    """Manually trigger security analysis on current camera frame."""
    try:
        security_system = get_security_orchestrator()
        if not security_system:
            raise HTTPException(status_code=503, detail="Security system not initialized")
        
        # Get current frame from camera
        from camera_service import cameras
        if camera_id not in cameras:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        
        frame = cameras[camera_id].get_current_frame()
        if frame is None:
            raise HTTPException(status_code=404, detail=f"No frame available from camera {camera_id}")
        
        # Process frame for suspicious activities
        activities = await security_system.process_camera_frame(camera_id, frame)
        
        return {
            "success": True,
            "camera_id": camera_id,
            "activities_detected": len(activities),
            "activities": [
                {
                    "activity_type": activity.activity_type.value,
                    "confidence": activity.confidence,
                    "description": activity.description,
                    "location": activity.location
                }
                for activity in activities
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing security frame: {str(e)}")

# Recording System Endpoints

@app.get("/recordings/active")
async def get_active_recordings() -> Dict[str, Any]:
    """Get information about active recordings."""
    try:
        recording_service = get_recording_service()
        if recording_service:
            active_recordings = recording_service.get_active_recordings()
            return {
                "success": True,
                "active_recordings": active_recordings,
                "count": len(active_recordings)
            }
        else:
            return {
                "success": False,
                "message": "Recording service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting active recordings: {str(e)}")

@app.get("/recordings/history")
async def get_recording_history(hours: int = 24) -> Dict[str, Any]:
    """Get recording history."""
    try:
        recording_service = get_recording_service()
        if recording_service:
            history = recording_service.get_recording_history(hours)
            return {
                "success": True,
                "recordings": history,
                "count": len(history),
                "time_period_hours": hours
            }
        else:
            return {
                "success": False,
                "message": "Recording service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recording history: {str(e)}")

@app.get("/recordings/statistics")
async def get_recording_statistics() -> Dict[str, Any]:
    """Get recording system statistics."""
    try:
        recording_service = get_recording_service()
        if recording_service:
            stats = recording_service.get_recording_statistics()
            return {
                "success": True,
                "statistics": stats
            }
        else:
            return {
                "success": False,
                "message": "Recording service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recording statistics: {str(e)}")

@app.post("/recordings/stop/{incident_id}")
async def stop_recording(incident_id: str) -> Dict[str, Any]:
    """Stop a specific recording."""
    try:
        recording_service = get_recording_service()
        if recording_service:
            success = recording_service.stop_recording(incident_id)
            return {
                "success": success,
                "incident_id": incident_id,
                "message": "Recording stopped" if success else "Recording not found or already stopped"
            }
        else:
            return {
                "success": False,
                "message": "Recording service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping recording: {str(e)}")

# Webhook System Endpoints

@app.get("/webhooks/status")
async def get_webhook_status() -> Dict[str, Any]:
    """Get webhook system status and statistics."""
    try:
        webhook_service = get_webhook_service()
        if webhook_service:
            stats = webhook_service.get_webhook_statistics()
            return {
                "success": True,
                "webhook_statistics": stats
            }
        else:
            return {
                "success": False,
                "message": "Webhook service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting webhook status: {str(e)}")

@app.post("/webhooks/test")
async def test_webhooks(webhook_name: str = None) -> Dict[str, Any]:
    """Send test alert to webhooks."""
    try:
        webhook_service = get_webhook_service()
        if webhook_service:
            async with webhook_service:
                results = await webhook_service.send_test_alert(webhook_name)
            
            successful = sum(1 for r in results if r.success)
            return {
                "success": True,
                "test_results": [
                    {
                        "webhook_name": r.webhook_name,
                        "success": r.success,
                        "status_code": r.status_code,
                        "error_message": r.error_message
                    }
                    for r in results
                ],
                "successful_deliveries": successful,
                "total_webhooks": len(results)
            }
        else:
            return {
                "success": False,
                "message": "Webhook service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing webhooks: {str(e)}")

@app.post("/webhooks/add")
async def add_webhook(webhook_config: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new webhook endpoint."""
    try:
        webhook_service = get_webhook_service()
        if webhook_service:
            # Validate required fields
            required_fields = ["name", "url"]
            for field in required_fields:
                if field not in webhook_config:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            # Create webhook config
            webhook = WebhookConfig(**webhook_config)
            webhook_service.add_webhook(webhook)
            
            return {
                "success": True,
                "message": f"Webhook '{webhook.name}' added successfully",
                "webhook_name": webhook.name
            }
        else:
            return {
                "success": False,
                "message": "Webhook service not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding webhook: {str(e)}")

# LLM Analysis Endpoints

@app.get("/llm/status")
async def get_llm_status() -> Dict[str, Any]:
    """Get LLM analysis service status."""
    try:
        llm_analyzer = get_llm_analyzer()
        if llm_analyzer:
            stats = llm_analyzer.get_analysis_statistics()
            return {
                "success": True,
                "llm_available": True,
                "analysis_statistics": stats
            }
        else:
            return {
                "success": True,
                "llm_available": False,
                "message": "LLM analyzer not initialized - using fallback analysis"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting LLM status: {str(e)}")

# Testing Endpoints
@app.post("/security/test-llm")
async def test_llm_analysis():
    """Test LLM analysis functionality."""
    try:
        from activity_detection import SuspiciousActivity, SuspiciousActivityType
        import time
        import numpy as np
        
        # Create a test suspicious activity
        test_activity = SuspiciousActivity(
            activity_type=SuspiciousActivityType.LOITERING,
            location=(100, 200),
            confidence=0.85,
            description="Person standing in the same location for 60 seconds",
            person_id=1,
            camera_id=1,
            timestamp=time.time(),
            evidence_frame=None  # No image for this test
        )
        
        # Get LLM analyzer
        from llm_analysis import get_llm_analyzer
        llm_analyzer = get_llm_analyzer()
        
        if not llm_analyzer:
            return {"success": False, "error": "LLM analyzer not available"}
        
        # Test context
        context = {
            "total_people": 2,
            "risk_level": "MEDIUM", 
            "recent_activities": 1,
            "business_hours": "8:00 AM - 10:00 PM"
        }
        
        # Analyze with LLM
        result = await llm_analyzer.analyze_suspicious_activity(test_activity, context, include_image=False)
        
        if result:
            return {
                "success": True,
                "llm_enabled": True,
                "analysis": {
                    "is_confirmed_suspicious": result.is_confirmed_suspicious,
                    "confidence_score": result.confidence_score,
                    "reasoning": result.reasoning,
                    "threat_level": result.threat_level,
                    "recommended_action": result.recommended_action
                }
            }
        else:
            return {"success": False, "error": "LLM analysis returned no result"}
            
    except Exception as e:
        return {"success": False, "error": f"LLM test failed: {str(e)}"}

# Dashboard Endpoints (Enhanced)

@app.get("/security-dashboard")
async def security_dashboard_direct():
    """Direct access to security dashboard."""
    return FileResponse("static/security-dashboard.html")

@app.get("/analytics-dashboard") 
async def analytics_dashboard_direct():
    """Direct access to analytics dashboard."""
    return FileResponse("static/analytics-dashboard.html")

@app.get("/streaming-dashboard")
async def streaming_dashboard_direct():
    """Direct access to streaming dashboard."""
    return FileResponse("static/streaming-dashboard.html")

@app.get("/multi-camera")
async def multi_camera_direct():
    """Direct access to multi-camera view."""
    return FileResponse("static/multi-camera.html")

@app.get("/dashboard/security")
async def security_dashboard():
    """Enhanced security dashboard with advanced features."""
    return FileResponse("static/security-dashboard.html")

@app.get("/dashboard/analytics")
async def analytics_dashboard():
    """Analytics dashboard for security insights."""
    return FileResponse("static/analytics-dashboard.html")

@app.get("/cameras/frames")
async def get_all_camera_frames_endpoint() -> Dict[str, Any]:
    """Get current frames from all cameras as base64 encoded images."""
    try:
        camera_ids = get_available_cameras()
        frames = {}
        
        for camera_id in camera_ids:
            try:
                frame_b64 = get_camera_frame(camera_id)
                frames[camera_id] = {
                    "success": True,
                    "frame": frame_b64,
                    "timestamp": time.time()
                }
            except Exception as e:
                frames[camera_id] = {
                    "success": False,
                    "error": str(e),
                    "frame": None,
                    "timestamp": time.time()
                }
        
        return {
            "success": True,
            "cameras": frames,
            "total_cameras": len(frames)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting all camera frames: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
