"""
WebSocket endpoints for real-time camera streaming.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.streaming_websocket import get_websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/camera-stream")
async def websocket_camera_stream(
    websocket: WebSocket,
    company_id: int = Query(..., description="Company ID for authentication")
):
    """
    WebSocket endpoint for real-time camera streaming.
    
    Usage from frontend:
    const ws = new WebSocket('ws://localhost:8001/ws/camera-stream?company_id=1');
    
    Send messages:
    - {"type": "start_stream", "camera_id": 1, "fps": 10}
    - {"type": "stop_stream"}
    - {"type": "motion_detection", "camera_id": 1}
    - {"type": "ping"}
    """
    manager = get_websocket_manager()
    
    try:
        await manager.connect(websocket, company_id)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle the message
            await manager.handle_message(websocket, message)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except json.JSONDecodeError:
        logger.error("Invalid JSON received from WebSocket client")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Invalid JSON format"
        }))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)
