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
from io import BytesIO
from typing import List, Dict, Optional

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
                        
                        print(f"DEBUG: Match result = {match_result}")  # Debug log
                        
                        if match_result and match_result.get("similarity"):
                            faces.append({
                                "person_name": match_result.get("name", "Unknown"),
                                "person_id": match_result.get("person_id"),
                                "match_confidence": match_result.get("similarity", 0),
                                "detection_count": 0,
                                "x": 0,
                                "y": 0,
                                "width": 0,
                                "height": 0
                            })
                        else:
                            print("DEBUG: No match found or match below threshold")
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


# ============= APPLICATION LIFECYCLE =============

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    print("🚀 Application started")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    print("👋 Application shutdown")
