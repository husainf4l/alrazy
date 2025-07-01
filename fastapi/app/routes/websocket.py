"""
WebSocket routes for RazZ Backend Security System.

Contains all WebSocket endpoints for real-time communication:
- Camera streaming
- Motion detection alerts
- System status updates
"""
import time
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_service import manager, handle_websocket_message

router = APIRouter()


@router.websocket("/ws/camera-streams")
async def camera_streams_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time camera streaming."""
    try:
        await manager.connect(websocket, "camera_streams")
        print(f"✅ Camera streams WebSocket connected")
        
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connection_established",
            "endpoint": "camera_streams",
            "timestamp": time.time()
        }, websocket)
        
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"📥 Camera streams received: {message}")
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        print("🔌 Camera streams WebSocket disconnected")
        manager.disconnect(websocket, "camera_streams")
    except Exception as e:
        print(f"❌ Camera streams WebSocket error: {e}")
        manager.disconnect(websocket, "camera_streams")


@router.websocket("/ws/motion-detection")
async def motion_detection_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time motion detection alerts."""
    try:
        await manager.connect(websocket, "motion_detection")
        print(f"✅ Motion detection WebSocket connected")
        
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connection_established",
            "endpoint": "motion_detection",
            "timestamp": time.time()
        }, websocket)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"📥 Motion detection received: {message}")
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        print("🔌 Motion detection WebSocket disconnected")
        manager.disconnect(websocket, "motion_detection")
    except Exception as e:
        print(f"❌ Motion detection WebSocket error: {e}")
        manager.disconnect(websocket, "motion_detection")


@router.websocket("/ws/system-status")
async def system_status_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time system status updates."""
    try:
        await manager.connect(websocket, "system_status")
        print(f"✅ System status WebSocket connected")
        
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connection_established",
            "endpoint": "system_status",
            "timestamp": time.time()
        }, websocket)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"📥 System status received: {message}")
            await handle_websocket_message(websocket, message)
    except WebSocketDisconnect:
        print("🔌 System status WebSocket disconnected")
        manager.disconnect(websocket, "system_status")
    except Exception as e:
        print(f"❌ System status WebSocket error: {e}")
        manager.disconnect(websocket, "system_status")
