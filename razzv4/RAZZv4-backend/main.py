from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import routers
from routes.pages import router as pages_router
from routes.auth import router as auth_router
from routes.health import router as health_router
from routes.vault_rooms import router as vault_rooms_router

# Create FastAPI instance
app = FastAPI(
    title="RAZZv4 Backend API",
    description="FastAPI backend for RAZZv4 Banking Security System",
    version="1.0.0"
)

# Include routers
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(vault_rooms_router)

# Mount static files (you can create this folder later if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)