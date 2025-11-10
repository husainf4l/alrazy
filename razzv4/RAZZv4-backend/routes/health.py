from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health_check():
    """
    Health check endpoint for API monitoring
    """
    return {"status": "healthy", "message": "RAZZv4 Backend is running"}