from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/cameras-page", response_class=HTMLResponse)
async def cameras_page(request: Request):
    return templates.TemplateResponse("cameras.html", {"request": request})


@router.get("/rooms-page", response_class=HTMLResponse)
async def rooms_page(request: Request):
    return templates.TemplateResponse("rooms.html", {"request": request})


@router.get("/room-designer", response_class=HTMLResponse)
async def room_designer(request: Request):
    return templates.TemplateResponse("room_designer.html", {"request": request})
