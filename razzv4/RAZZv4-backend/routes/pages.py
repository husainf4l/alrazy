from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Root endpoint that renders the home template
    """
    return templates.TemplateResponse("index.html", {"request": request, "title": "RAZZv4"})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login page
    """
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login - RAZZv4"})

@router.get("/get-started", response_class=HTMLResponse)
async def get_started_page(request: Request):
    """
    Get started (registration) page
    """
    return templates.TemplateResponse("get-started.html", {"request": request, "title": "Get Started - RAZZv4"})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """
    Dashboard page for authenticated users
    """
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard - RAZZv4"})

@router.get("/vault-room")
async def vault_room_page(request: Request):
    return templates.TemplateResponse("vault-room.html", {"request": request})

@router.get("/test-webrtc")
async def test_webrtc_page(request: Request):
    """Test page for WebRTC camera streaming"""
    return templates.TemplateResponse("test-webrtc.html", {"request": request})

@router.get("/room-designer/{room_id}")
async def room_designer_page(request: Request, room_id: int):
    return templates.TemplateResponse("room-designer.html", {"request": request, "room_id": room_id})