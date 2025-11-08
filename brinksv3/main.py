from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from typing import Optional
import asyncio

from detector import YOLODetector

app = FastAPI(title="People Counter API", version="1.0.0")

# Initialize YOLO detector
detector = YOLODetector()


class RTSPRequest(BaseModel):
    rtsp_url: str
    confidence: Optional[float] = 0.5


class StreamRequest(BaseModel):
    rtsp_url: str
    confidence: Optional[float] = 0.5


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "People Counter API using YOLO",
        "endpoints": {
            "/count": "POST - Count people from RTSP stream (single frame)",
            "/stream": "POST - Stream processed video with people count",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": "YOLOv8"}


@app.post("/count")
async def count_people(request: RTSPRequest):
    """
    Count people in a single frame from RTSP stream
    
    Args:
        rtsp_url: RTSP stream URL
        confidence: Detection confidence threshold (default: 0.5)
    
    Returns:
        Number of people detected in the frame
    """
    try:
        count = await detector.count_people_single_frame(
            request.rtsp_url,
            confidence=request.confidence
        )
        return {
            "rtsp_url": request.rtsp_url,
            "people_count": count,
            "confidence_threshold": request.confidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream")
async def stream_video(request: StreamRequest):
    """
    Stream processed video with people counting overlay
    
    Args:
        rtsp_url: RTSP stream URL
        confidence: Detection confidence threshold (default: 0.5)
    
    Returns:
        MJPEG video stream
    """
    try:
        return StreamingResponse(
            detector.generate_frames(
                request.rtsp_url,
                confidence=request.confidence
            ),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    detector.cleanup()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
