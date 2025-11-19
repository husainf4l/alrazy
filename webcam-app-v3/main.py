import os
import sys

# ==================== CRITICAL: Configure TensorFlow and GPU before imports ====================
# Set environment variables BEFORE importing TensorFlow/DeepFace
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TensorFlow logging (0=all, 1=info, 2=warning, 3=error)
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # Allow GPU memory to grow gradually instead of allocating all at once
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'  # GPU thread mode optimization
os.environ['TF_GPU_THREAD_PER_CORE'] = '2'  # Threads per GPU core
os.environ['TF_AUTOGRAPH_VERBOSITY'] = '0'  # Disable verbose autograph logging

# Fix CUDA libdevice issue
cuda_path = '/usr/local/cuda'
if os.path.exists(cuda_path):
    os.environ['XLA_FLAGS'] = f'--xla_gpu_cuda_data_dir={cuda_path}'
    os.environ['CUDA_HOME'] = cuda_path

# Disable JIT compilation to avoid libdevice errors (use eager execution instead)
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'

# ==================== END GPU Configuration ====================

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
from app.models.database import create_tables, get_db
from app.models.schemas import LoginRequest, Token
from app.services.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    init_users,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.face_recognition import get_face_service
from app.services.webcam_processor import get_webcam_processor
from app.services.multi_angle_capture import get_multi_angle_service
from app.services.webrtc_service import get_webrtc_manager, init_webrtc_manager
from pydantic import BaseModel
import uuid
import json
import base64
import cv2
import numpy as np
import time
import logging
from io import BytesIO
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Webcam App", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Pydantic models
class UpdateNameRequest(BaseModel):
    name: str

class MultiAngleCaptureRequest(BaseModel):
    person_name: str
    front_image: Optional[str] = None
    left_image: Optional[str] = None
    right_image: Optional[str] = None
    back_image: Optional[str] = None

class WebRTCSessionRequest(BaseModel):
    camera_name: str

class WebRTCOfferRequest(BaseModel):
    session_id: str
    offer: str

class WebRTCCandidateRequest(BaseModel):
    session_id: str
    candidate: Dict

class WebRTCCloseRequest(BaseModel):
    session_id: str

# Initialize database
try:
    create_tables()
    init_users()
    print("🚀 Application initialized successfully!")
except Exception as e:
    print(f"⚠️  Warning: Database initialization failed: {e}")
    print("📋 Please run the database setup commands manually")

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "AI Webcam App is running"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_model=Token)
async def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_request.email, login_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard HTML page (client-side auth check)"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/webcam", response_class=HTMLResponse)
async def webcam_page(request: Request):
    """Serve the webcam HTML page (client-side auth check)"""
    return templates.TemplateResponse("webcam.html", {"request": request})

@app.get("/faces", response_class=HTMLResponse)
async def faces_page(request: Request):
    """Serve the face management HTML page"""
    return templates.TemplateResponse("faces.html", {"request": request})

@app.get("/person/{person_id}", response_class=HTMLResponse)
async def person_detail_page(request: Request, person_id: str):
    """Serve the person detail HTML page"""
    return templates.TemplateResponse("person_detail.html", {"request": request, "person_id": person_id})

@app.get("/api/faces")
async def get_faces():
    """Get all detected faces"""
    try:
        service = get_face_service()
        faces = service.get_all_faces()
        return JSONResponse(content=faces)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/person/{person_id}")
async def get_person_detail(person_id: str):
    """Get detailed information about a specific person"""
    try:
        service = get_face_service()
        person = service.get_person_detail(person_id)
        if person:
            return JSONResponse(content=person)
        else:
            raise HTTPException(status_code=404, detail="Person not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/faces/{face_id}/name")
async def update_face_name(face_id: str, request: UpdateNameRequest):
    """Update face name"""
    try:
        service = get_face_service()
        success = service.update_face_name(face_id, request.name)
        if success:
            return JSONResponse(content={"success": True, "message": "Name updated"})
        else:
            raise HTTPException(status_code=404, detail="Face not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/faces/{face_id}")
async def delete_face(face_id: str):
    """Delete a face and its associated data"""
    try:
        service = get_face_service()
        success = service.delete_face(face_id)
        if success:
            return JSONResponse(content={"success": True, "message": "Face deleted successfully"})
        else:
            raise HTTPException(status_code=404, detail="Face not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Protected API endpoint to get current user info"""
    return {"email": current_user.email, "id": current_user.id}

@app.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}, this is a protected route!"}

# ============ WEBCAM PROCESSING ENDPOINTS ============

@app.post("/api/process-frame")
async def process_frame(request: Request):
    """
    Process a single frame from webcam
    Expects: {"frame": "base64_encoded_image"}
    Returns: Detection results with locations and logs
    """
    try:
        data = await request.json()
        frame_b64 = data.get("frame", "")
        
        if not frame_b64:
            raise HTTPException(status_code=400, detail="No frame data provided")
        
        # Decode base64 frame
        frame_data = base64.b64decode(frame_b64)
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid frame data")
        
        # Process frame
        processor = get_webcam_processor(fps_limit=2)
        result = processor.process_frame(frame)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        print(f"Error processing frame: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/webcam-status")
async def get_webcam_status():
    """Get webcam processor status"""
    try:
        processor = get_webcam_processor(fps_limit=2)
        status_data = processor.get_status()
        return JSONResponse(content=status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-image")
async def process_image(request: Request):
    """
    Process a static image for testing
    Expects: {"image": "base64_encoded_image"}
    """
    try:
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Use CPU
        
        data = await request.json()
        image_b64 = data.get("image", "")
        
        if not image_b64:
            raise HTTPException(status_code=400, detail="No image data provided")
        
        # Remove data URL prefix if present
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Process image
        processor = get_webcam_processor(fps_limit=2)
        result = processor.process_frame(image)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        print(f"Error processing image: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============= MULTI-ANGLE FACE CAPTURE =============

@app.post("/api/capture-multi-angle")
async def capture_multi_angle(
    request: MultiAngleCaptureRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Capture face from multiple angles (front, left, right, back)
    Stores multiple embeddings for better recognition from any viewpoint
    """
    try:
        images = {}
        
        # Decode each angle image if provided
        for angle in ["front", "left", "right", "back"]:
            image_b64 = getattr(request, f"{angle}_image")
            if image_b64:
                # Decode base64
                image_data = base64.b64decode(image_b64.split(',')[1] if ',' in image_b64 else image_b64)
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is not None:
                    images[angle] = image
        
        if len(images) < 2:
            return JSONResponse(content={
                "success": False,
                "error": "Need at least 2 angle images (front, left, right, or back)"
            })
        
        # Process multi-angle capture
        multi_angle_service = get_multi_angle_service()
        result = multi_angle_service.capture_multi_angle_face(images, request.person_name)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        print(f"Multi-angle capture error: {e}")
        traceback.print_exc()
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })


@app.get("/test-webcam", response_class=HTMLResponse)
async def test_webcam_page(request: Request):
    """Test webcam page for face recognition testing"""
    return templates.TemplateResponse("test_webcam.html", {"request": request})


@app.post("/api/test-face-recognition")
async def test_face_recognition(request: Request):
    """
    Direct face recognition for testing (relaxed validation)
    Expects: {"image": "base64_encoded_image"}
    """
    try:
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Use CPU
        
        data = await request.json()
        image_b64 = data.get("image", "")
        
        if not image_b64:
            raise HTTPException(status_code=400, detail="No image data provided")
        
        # Remove data URL prefix if present
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Direct face detection and matching using face matching service
        from app.services.face_matching import FaceMatchingService
        from deepface import DeepFace
        
        start_time = time.time()
        
        # Extract faces using DeepFace
        try:
            face_objs = DeepFace.extract_faces(
                img_path=image,
                detector_backend="retinaface",
                enforce_detection=False,
                align=True,
                expand_percentage=35
            )
        except:
            face_objs = []
        
        faces = []
        
        if face_objs:
            matching_service = FaceMatchingService()
            
            for face_obj in face_objs:
                try:
                    # Extract embedding
                    embedding_objs = DeepFace.represent(
                        img_path=face_obj["face"] * 255,
                        model_name="ArcFace",
                        detector_backend="skip",
                        enforce_detection=False
                    )
                    
                    if embedding_objs:
                        embedding = embedding_objs[0]["embedding"]
                        
                        # Match against database
                        match_result = matching_service.get_best_match(embedding)
                        
                        if match_result:  # match_result is not None when match found
                            faces.append({
                                "person_name": match_result["name"],
                                "person_id": match_result["face_id"],
                                "match_confidence": match_result["similarity"],
                                "detection_count": match_result.get("detection_count", 0),
                                "x": 0,
                                "y": 0,
                                "width": 0,
                                "height": 0
                            })
                        else:
                            faces.append({
                                "person_name": "Unknown",
                                "person_id": None,
                                "match_confidence": 0,
                                "detection_count": 0,
                                "x": 0,
                                "y": 0,
                                "width": 0,
                                "height": 0
                            })
                except Exception as e:
                    print(f"Error processing face: {e}")
                    continue
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return JSONResponse(content={
            "faces": faces,
            "processing_time": f"{processing_time}ms",
            "message": f"Found {len(faces)} face(s)" if faces else "No faces detected. Make sure your face is clearly visible."
        })
        
    except Exception as e:
        import traceback
        print(f"Error in test face recognition: {e}")
        traceback.print_exc()
        return JSONResponse(content={
            "faces": [],
            "error": str(e),
            "message": "Error processing image"
        })


# ============= ADVANCED TEST / IP CAMERA ROUTES =============

@app.get("/advanced_test", response_class=HTMLResponse)
async def advanced_test_page(request: Request):
    """Advanced testing page with IP camera streams"""
    return templates.TemplateResponse("advanced_test.html", {"request": request})


@app.get("/api/ip-cameras/status")
async def get_ip_cameras_status():
    """Get status of all IP cameras"""
    try:
        from app.services.ip_camera_service import get_camera_manager
        import json
        
        manager = get_camera_manager()
        
        # Return camera status with timeout
        cameras = {}
        for name, camera in manager.cameras.items():
            try:
                cameras[name] = camera.get_status()
            except Exception as e:
                cameras[name] = {
                    "name": name,
                    "status": "error",
                    "error": str(e),
                    "fps": 0,
                    "has_frame": False
                }
        
        return JSONResponse(content={"cameras": cameras})
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        return JSONResponse(content={"error": str(e), "cameras": {}}, status_code=500)


@app.post("/api/ip-cameras/initialize")
async def initialize_ip_cameras(request: Request):
    """Initialize IP cameras from configuration (non-blocking)"""
    try:
        import json
        import os
        from app.services.ip_camera_service import get_camera_manager
        
        # Load camera configuration
        config_path = os.path.join(os.path.dirname(__file__), "config", "cameras.json")
        
        if not os.path.exists(config_path):
            return JSONResponse(
                content={"error": "Camera configuration not found"},
                status_code=404
            )
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        manager = get_camera_manager()
        
        # Initialize cameras in background (non-blocking)
        initialized_cameras = {}
        for camera_name, camera_info in config.get("streams", {}).items():
            rtsp_url = camera_info.get("url", "")
            # Just register the camera name without waiting for connection
            try:
                manager.add_camera(camera_name, rtsp_url)
                initialized_cameras[camera_name] = {
                    "success": True,
                    "url": rtsp_url
                }
            except Exception as e:
                initialized_cameras[camera_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return JSONResponse(content={
            "message": "Cameras initialized",
            "cameras": initialized_cameras
        }, status_code=200)
        
    except Exception as e:
        import traceback
        logger.error(f"Error initializing cameras: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/ip-cameras/frame/{camera_name}")
async def get_ip_camera_frame(camera_name: str, quality: int = 75):
    """Get current frame from a specific IP camera (ULTRA-LOW LATENCY - NO CACHE)"""
    try:
        request_start = time.time()
        from app.services.ip_camera_service import get_camera_manager
        import json
        
        # Clamp quality to valid range (lower default for speed)
        quality = max(70, min(90, quality))
        
        manager = get_camera_manager()
        camera = manager.cameras.get(camera_name)
        
        if camera is None:
            return JSONResponse(
                content={"error": f"Camera not found: {camera_name}"},
                status_code=404
            )
        
        # Get fresh frame (no caching)
        frame_fetch_start = time.time()
        frame_b64 = camera.get_frame_b64(quality=quality)
        frame_fetch_time = (time.time() - frame_fetch_start) * 1000  # ms
        
        if frame_b64 is None:
            return JSONResponse(
                content={"error": f"No frame available from {camera_name}"},
                status_code=404
            )
        
        # Calculate total request time and frame age
        total_request_time = (time.time() - request_start) * 1000  # ms
        frame_age = (time.time() - camera.frame_timestamp) * 1000 if camera.frame_timestamp else 0  # ms
        
        # Create JSON response data with debug timestamps
        response_data = {
            "camera": camera_name,
            "frame": frame_b64,
            "timestamp": time.time(),  # Server timestamp
            "debug": {
                "frame_age_ms": round(frame_age, 1),  # How old is the frame
                "encode_time_ms": round(frame_fetch_time, 1),  # JPEG encoding time
                "total_time_ms": round(total_request_time, 1)  # Total API latency
            }
        }
        
        # Log significant delays (>200ms only - optimized)
        if frame_age > 200:
            logger.warning(f"{camera_name}: HIGH DELAY - Frame age={frame_age:.1f}ms (Encode={frame_fetch_time:.1f}ms)")
        
        # Return with NO-CACHE headers for live streaming
        return Response(
            content=json.dumps(response_data),
            media_type="application/json",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Error getting camera frame: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/ip-cameras/stop-all")
async def stop_all_cameras():
    """Stop all IP camera streams"""
    try:
        from app.services.ip_camera_service import get_camera_manager
        
        manager = get_camera_manager()
        manager.stop_all()
        
        return JSONResponse(content={"message": "All cameras stopped"})
        
    except Exception as e:
        logger.error(f"Error stopping cameras: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/tracking/stats")
async def get_tracking_statistics():
    """Get global multi-camera tracking statistics"""
    try:
        from app.services.ip_camera_service import get_camera_manager
        
        manager = get_camera_manager()
        stats = manager.get_global_tracking_stats()
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Error getting tracking stats: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/tracking/people-count")
async def get_total_people_count():
    """Get total unique people count across all cameras"""
    try:
        from app.services.ip_camera_service import get_camera_manager
        
        manager = get_camera_manager()
        stats = manager.get_global_tracking_stats()
        
        return JSONResponse(content={
            "total_unique_people": stats.get("total_unique_people", 0),
            "people_per_camera": stats.get("people_per_camera", {}),
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting people count: {e}")
        return JSONResponse(
            content={"error": str(e), "total_unique_people": 0},
            status_code=500
        )


# ============= WEBRTC STREAMING =============

@app.get("/advanced-test", response_class=HTMLResponse)
async def advanced_test_page(request: Request):
    """Serve the advanced test page with WebRTC camera streaming"""
    return templates.TemplateResponse("advanced_test.html", {"request": request})


@app.post("/api/webrtc/create-session")
async def create_webrtc_session(
    request: WebRTCSessionRequest,
    current_user = Depends(get_current_user)
):
    """Create a new WebRTC session for a camera"""
    try:
        manager = get_webrtc_manager()
        session_id = str(uuid.uuid4())
        
        await manager.create_session(session_id, request.camera_name)
        
        return JSONResponse(
            content={
                "session_id": session_id,
                "camera_name": request.camera_name,
                "message": "WebRTC session created"
            },
            status_code=201
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating WebRTC session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.post("/api/webrtc/handle-offer")
async def handle_webrtc_offer(
    request: WebRTCOfferRequest,
    current_user = Depends(get_current_user)
):
    """Handle SDP offer and return answer"""
    try:
        manager = get_webrtc_manager()
        answer_sdp = await manager.handle_offer(request.session_id, request.offer)
        
        return JSONResponse(
            content={
                "session_id": request.session_id,
                "answer": answer_sdp
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling SDP offer: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle offer")


@app.post("/api/webrtc/add-ice-candidate")
async def add_ice_candidate(
    request: WebRTCCandidateRequest,
    current_user = Depends(get_current_user)
):
    """Add ICE candidate"""
    try:
        manager = get_webrtc_manager()
        candidate_json = json.dumps(request.candidate)
        await manager.add_ice_candidate(request.session_id, candidate_json)
        
        return JSONResponse(
            content={
                "session_id": request.session_id,
                "message": "ICE candidate added"
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding ICE candidate: {e}")
        raise HTTPException(status_code=500, detail="Failed to add candidate")


@app.post("/api/webrtc/close-session")
async def close_webrtc_session(
    request: WebRTCCloseRequest,
    current_user = Depends(get_current_user)
):
    """Close a WebRTC session"""
    try:
        manager = get_webrtc_manager()
        await manager.close_session(request.session_id)
        
        return JSONResponse(
            content={
                "session_id": request.session_id,
                "message": "Session closed"
            }
        )
    
    except Exception as e:
        logger.error(f"Error closing WebRTC session: {e}")
        raise HTTPException(status_code=500, detail="Failed to close session")


@app.get("/api/webrtc/sessions")
async def get_webrtc_sessions(current_user = Depends(get_current_user)):
    """Get all active WebRTC sessions"""
    try:
        manager = get_webrtc_manager()
        sessions_stats = []
        
        for session_id in manager.sessions.keys():
            stats = manager.get_session_stats(session_id)
            sessions_stats.append(stats)
        
        return JSONResponse(content={"sessions": sessions_stats})
    
    except Exception as e:
        logger.error(f"Error getting WebRTC sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")


@app.post("/api/webrtc/close-all")
async def close_all_webrtc_sessions(current_user = Depends(get_current_user)):
    """Close all WebRTC sessions"""
    try:
        manager = get_webrtc_manager()
        count = len(manager.sessions)
        await manager.close_all_sessions()
        
        return JSONResponse(
            content={
                "message": f"Closed {count} sessions"
            }
        )
    
    except Exception as e:
        logger.error(f"Error closing all WebRTC sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to close sessions")


# ============= APPLICATION LIFECYCLE =============

@app.on_event("startup")
async def startup_event():
    """
    Application startup - Initialize all services eagerly (best practice).
    Cameras connect asynchronously in background to prevent blocking the server.
    """
    try:
        print("🚀 Starting application initialization...")
        
        # Initialize multi-camera tracking service FIRST (before cameras start streaming)
        # This prevents API endpoints from blocking on first call
        from app.services.ip_camera_service import init_tracking_service
        try:
            init_tracking_service()
            print("✅ Multi-camera tracking service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tracking service: {e}")
            print(f"⚠️  Tracking service initialization failed: {e}")
        
        # Load camera configuration
        config_path = "config/cameras.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Initialize IP camera manager (non-blocking)
            from app.services.ip_camera_service import get_camera_manager
            manager = get_camera_manager()
            
            # Add cameras with async connection (non-blocking, best practice)
            for camera_name, camera_config in config.get("streams", {}).items():
                rtsp_url = camera_config.get("url")
                if rtsp_url:
                    # connect_async=True means cameras connect in background
                    manager.add_camera(camera_name, rtsp_url, connect_async=True)
            
            print(f"✅ IP camera manager initialized with {len(config.get('streams', {}))} cameras (connecting in background)")
            
            # Initialize WebRTC manager with camera URLs
            camera_urls = {}
            for camera_name, camera_config in config.get("streams", {}).items():
                rtsp_url = camera_config.get("url")
                if rtsp_url:
                    camera_urls[camera_name] = rtsp_url
            
            ice_servers = config.get("server", {}).get("ice_servers", 
                                                       ["stun:stun.l.google.com:19302"])
            
            init_webrtc_manager(camera_urls, ice_servers)
            print(f"✅ WebRTC manager initialized with {len(camera_urls)} cameras")
        else:
            print("⚠️  Camera configuration not found")
    
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        print(f"⚠️  Initialization failed: {e}")
    
    print("🚀 Application ready - Server is now responsive (cameras connecting in background)")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    try:
        # Clean up IP cameras
        from app.services.ip_camera_service import get_camera_manager
        manager = get_camera_manager()
        manager.stop_all()
        print("✅ Stopped all IP camera streams")
    except Exception as e:
        logger.error(f"Error stopping IP cameras: {e}")
    
    try:
        # Clean up WebRTC sessions
        manager = get_webrtc_manager()
        await manager.close_all_sessions()
        print("✅ Closed all WebRTC sessions")
    except Exception as e:
        logger.error(f"Error closing WebRTC sessions: {e}")
    
    print("👋 Application shutdown")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
