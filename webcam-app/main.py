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
from pydantic import BaseModel

app = FastAPI(title="AI Webcam App", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Pydantic models
class UpdateNameRequest(BaseModel):
    name: str

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
