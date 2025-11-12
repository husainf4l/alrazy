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
from fastapi.responses import HTMLResponse, JSONResponse
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
from pydantic import BaseModel
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
        status = manager.get_all_cameras_status()
        
        return JSONResponse(content={"cameras": status})
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        return JSONResponse(content={"error": str(e), "cameras": {}}, status_code=500)


@app.post("/api/ip-cameras/initialize")
async def initialize_ip_cameras(request: Request):
    """Initialize IP cameras from configuration"""
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
        
        # Initialize cameras
        initialized_cameras = {}
        for camera_name, camera_info in config.get("streams", {}).items():
            rtsp_url = camera_info.get("url", "")
            success = manager.add_camera(camera_name, rtsp_url)
            initialized_cameras[camera_name] = {
                "success": success,
                "url": rtsp_url
            }
        
        return JSONResponse(content={
            "message": "Cameras initialized",
            "cameras": initialized_cameras
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error initializing cameras: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/ip-cameras/frame/{camera_name}")
async def get_ip_camera_frame(camera_name: str):
    """Get current frame from a specific IP camera"""
    try:
        from app.services.ip_camera_service import get_camera_manager
        import base64
        
        manager = get_camera_manager()
        frame = manager.get_frame(camera_name)
        
        if frame is None:
            return JSONResponse(
                content={"error": f"No frame available from {camera_name}"},
                status_code=404
            )
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return JSONResponse(content={
            "camera": camera_name,
            "frame": f"data:image/jpeg;base64,{frame_b64}"
        })
        
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


# ============= WEBRTC CAMERA ROUTES =============

# Pydantic models for WebRTC
class WebRTCOfferRequest(BaseModel):
    offer: str  # SDP offer as JSON string
    camera_name: str

class WebRTCAnswerResponse(BaseModel):
    answer: str
    session_id: str

class WebRTCIceCandidateRequest(BaseModel):
    session_id: str
    candidate: Dict


@app.post("/api/webrtc/create-session")
async def create_webrtc_session(request: Request, current_user = Depends(get_current_user)):
    """Create a new WebRTC session and get offer"""
    try:
        # Lazy import to avoid startup issues
        import uuid
        from app.services.webrtc_camera_service import get_webrtc_manager
        
        data = await request.json()
        camera_name = data.get("camera_name", "")
        rtsp_url = data.get("rtsp_url", "")
        
        if not camera_name or not rtsp_url:
            return JSONResponse(
                content={"error": "Missing camera_name or rtsp_url"},
                status_code=400
            )
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        # Create WebRTC connection
        pc = await manager.create_session(session_id, camera_name, rtsp_url)
        if not pc:
            return JSONResponse(
                content={"error": "Failed to create WebRTC connection"},
                status_code=500
            )
        
        # Create offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        return JSONResponse(content={
            "session_id": session_id,
            "offer": {
                "type": pc.localDescription.type,
                "sdp": pc.localDescription.sdp
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating WebRTC session: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/webrtc/handle-answer")
async def handle_webrtc_answer(request: Request, current_user = Depends(get_current_user)):
    """Handle SDP answer from client"""
    try:
        # Lazy import to avoid startup issues
        from app.services.webrtc_camera_service import get_webrtc_manager
        from aiortc import RTCSessionDescription
        
        data = await request.json()
        session_id = data.get("session_id", "")
        answer_sdp = data.get("answer", {})
        
        if not session_id or not answer_sdp:
            return JSONResponse(
                content={"error": "Missing session_id or answer"},
                status_code=400
            )
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        # Get session
        with manager.lock:
            if session_id not in manager.sessions:
                return JSONResponse(
                    content={"error": "Session not found"},
                    status_code=404
                )
            
            session = manager.sessions[session_id]
            pc = session.pc
        
        # Set remote description
        answer = RTCSessionDescription(
            sdp=answer_sdp.get("sdp", ""),
            type=answer_sdp.get("type", "answer")
        )
        await pc.setRemoteDescription(answer)
        
        logger.info(f"WebRTC answer handled for session {session_id}")
        
        return JSONResponse(content={"success": True})
        
    except Exception as e:
        logger.error(f"Error handling WebRTC answer: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/webrtc/add-ice-candidate")
async def add_ice_candidate(request: Request, current_user = Depends(get_current_user)):
    """Add ICE candidate for WebRTC connection"""
    try:
        # Lazy import to avoid startup issues
        from app.services.webrtc_camera_service import get_webrtc_manager
        
        data = await request.json()
        session_id = data.get("session_id", "")
        candidate = data.get("candidate", {})
        
        if not session_id or not candidate:
            return JSONResponse(
                content={"error": "Missing session_id or candidate"},
                status_code=400
            )
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        # Add ICE candidate
        await manager.add_ice_candidate(session_id, candidate)
        
        return JSONResponse(content={"success": True})
        
    except Exception as e:
        logger.error(f"Error adding ICE candidate: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/webrtc/close-session")
async def close_webrtc_session(request: Request, current_user = Depends(get_current_user)):
    """Close a WebRTC session"""
    try:
        # Lazy import to avoid startup issues
        from app.services.webrtc_camera_service import get_webrtc_manager
        
        data = await request.json()
        session_id = data.get("session_id", "")
        
        if not session_id:
            return JSONResponse(
                content={"error": "Missing session_id"},
                status_code=400
            )
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        # Close session
        await manager.close_session(session_id)
        
        return JSONResponse(content={"success": True})
        
    except Exception as e:
        logger.error(f"Error closing WebRTC session: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/webrtc/close-all")
async def close_all_webrtc_sessions(current_user = Depends(get_current_user)):
    """Close all WebRTC sessions"""
    try:
        # Lazy import to avoid startup issues
        from app.services.webrtc_camera_service import get_webrtc_manager
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        # Close all sessions
        await manager.close_all()
        
        return JSONResponse(content={"success": True})
        
    except Exception as e:
        logger.error(f"Error closing all WebRTC sessions: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/webrtc/stats")
async def get_webrtc_stats(current_user = Depends(get_current_user)):
    """Get WebRTC connection statistics"""
    try:
        # Lazy import to avoid startup issues
        from app.services.webrtc_camera_service import get_webrtc_manager
        
        # Get WebRTC manager
        manager = await get_webrtc_manager()
        
        return JSONResponse(content={
            "active_sessions": manager.get_session_count()
        })
        
    except Exception as e:
        logger.error(f"Error getting WebRTC stats: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# ============= APPLICATION LIFECYCLE =============

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    print("🚀 Application started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    print("👋 Application shutdown")
