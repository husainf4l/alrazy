from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import VaultRoom, Camera
from typing import List
import httpx
import base64
import json
import uuid

from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import VaultRoom, Camera
from typing import List
import httpx
import base64
import json
import uuid

def generate_webrtc_offer():
    """Generate a minimal WebRTC SDP offer for the RTSP->WebRTC bridge"""
    # A proper minimal SDP offer for a video stream
    sdp = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=msid-semantic: WMS
m=video 0 UDP/TLS/RTP/SAVPF 96
c=IN IP4 127.0.0.1
a=rtcp:9 IN IP4 127.0.0.1
a=ice-ufrag:razzv4
a=ice-pwd:razzv4razzv4
a=fingerprint:sha-256 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
a=setup:actpass
a=mid:0
a=sendrecv
a=rtcp-mux
a=rtpmap:96 H264/90000
"""
    # Base64 encode the SDP
    sdp_b64 = base64.b64encode(sdp.encode()).decode()
    return sdp_b64

router = APIRouter(prefix="/vault-rooms", tags=["vault_rooms"])

@router.post("/create")
async def create_vault_room(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new vault room with multiple cameras"""
    try:
        # Get form data
        form_data = await request.form()
        
        name = form_data.get("name")
        location = form_data.get("location")
        
        print(f"DEBUG: Received vault room creation request - Name: {name}, Location: {location}")
        
        if not name or not location:
            raise HTTPException(
                status_code=400, 
                detail="Name and location are required"
            )
        
        # Get camera data arrays
        camera_names = form_data.getlist("camera_names[]")
        camera_urls = form_data.getlist("camera_urls[]")
        
        print(f"DEBUG: Cameras - Names: {camera_names}, URLs: {camera_urls}")
        
        # Validate that we have matching camera names and URLs
        if len(camera_names) != len(camera_urls):
            raise HTTPException(
                status_code=400, 
                detail="Camera names and URLs count mismatch"
            )
        
        # Validate RTSP URLs
        for i, url in enumerate(camera_urls):
            if url and url.strip():
                if not url.strip().startswith('rtsp://'):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Camera {i+1} URL must be a valid RTSP URL starting with 'rtsp://'"
                    )
        
        # Create new vault room
        vault_room = VaultRoom(
            name=name,
            location=location,
            current_people_count=0
        )
        
        db.add(vault_room)
        db.commit()
        db.refresh(vault_room)
        
        print(f"DEBUG: Created vault room with ID: {vault_room.id}")
        
        # Create cameras for this vault room
        camera_count = 0
        for camera_name, camera_url in zip(camera_names, camera_urls):
            if camera_name.strip() and camera_url.strip():
                camera = Camera(
                    name=camera_name.strip(),
                    rtsp_url=camera_url.strip(),
                    vault_room_id=vault_room.id
                )
                db.add(camera)
                camera_count += 1
        
        db.commit()
        
        print(f"DEBUG: Created {camera_count} cameras for vault room {vault_room.id}")
        print(f"DEBUG: Redirecting to /vault-room")
        
        # Redirect back to vault room page
        return RedirectResponse(url="/vault-room", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to create vault room: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error creating vault room: {str(e)}")

@router.get("/")
async def get_vault_rooms(db: Session = Depends(get_db)):
    """Get all vault rooms with their cameras"""
    try:
        vault_rooms = db.query(VaultRoom).all()
        print(f"DEBUG: Fetched {len(vault_rooms)} vault rooms from database")
        
        result = {"vault_rooms": [
            {
                "id": room.id,
                "name": room.name,
                "location": room.location,
                "current_people_count": room.current_people_count,
                "room_width": room.room_width,
                "room_height": room.room_height,
                "room_layout": room.room_layout,
                "cameras": [
                    {
                        "id": camera.id,
                        "name": camera.name,
                        "rtsp_url": camera.rtsp_url,
                        "is_active": camera.is_active
                    } for camera in room.cameras
                ],
                "camera_count": len(room.cameras),
                "created_at": room.created_at.isoformat() if room.created_at else None
            } for room in vault_rooms
        ]}
        
        print(f"DEBUG: Returning vault rooms data: {result}")
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to fetch vault rooms: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error fetching vault rooms: {str(e)}")

@router.post("/save-layout")
async def save_room_layout(
    request: Request,
    db: Session = Depends(get_db)
):
    """Save or update a room layout with cameras and vault positioning"""
    try:
        # Get form data
        form_data = await request.form()
        
        room_id = form_data.get("room_id")  # Optional - if provided, update existing room
        name = form_data.get("name")
        location = form_data.get("location")
        width = float(form_data.get("width", 10))
        height = float(form_data.get("height", 8))
        layout_data = form_data.get("layout_data")
        
        print(f"DEBUG: Save layout - Room ID: {room_id}, Name: {name}, Location: {location}")
        print(f"DEBUG: Layout data: {layout_data}")
        
        if not name or not location:
            raise HTTPException(
                status_code=400, 
                detail="Name and location are required"
            )
        
        # If room_id provided, update existing room
        if room_id:
            vault_room = db.query(VaultRoom).filter(VaultRoom.id == int(room_id)).first()
            if not vault_room:
                raise HTTPException(status_code=404, detail="Vault room not found")
            
            # Update existing room
            vault_room.name = name
            vault_room.location = location
            vault_room.room_width = width
            vault_room.room_height = height
            vault_room.room_layout = layout_data
            
            print(f"DEBUG: Updated existing room {room_id}")
        else:
            # Create new vault room with layout
            vault_room = VaultRoom(
                name=name,
                location=location,
                room_width=width,
                room_height=height,
                room_layout=layout_data,
                current_people_count=0
            )
            db.add(vault_room)
            print(f"DEBUG: Created new room")
        
        db.commit()
        db.refresh(vault_room)
        
        return {"message": "Room layout saved successfully", "room_id": vault_room.id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to save room layout: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error saving room layout: {str(e)}")

@router.delete("/{room_id}")
async def delete_vault_room(room_id: int, db: Session = Depends(get_db)):
    """Delete a vault room"""
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        db.delete(vault_room)
        db.commit()
        
        return {"message": "Vault room deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting vault room: {str(e)}")

@router.get("/{room_id}/cameras/webrtc")
async def get_camera_webrtc_streams(room_id: int, db: Session = Depends(get_db)):
    """Get WebRTC streams for all cameras in a vault room"""
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Get all cameras for this room
        cameras_data = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for camera in vault_room.cameras:
                if not camera.is_active or not camera.rtsp_url:
                    continue
                
                try:
                    # POST RTSP URL + WebRTC SDP offer to RTSPtoWebRTC service
                    # Generate a valid SDP offer for the WebRTC handshake
                    sdp_offer = generate_webrtc_offer()
                    
                    response = await client.post(
                        "http://localhost:8083/stream",
                        data={
                            "url": camera.rtsp_url,
                            "sdp64": sdp_offer
                        },
                        headers={"Accept": "application/json"},
                        timeout=20.0
                    )
                    
                    if response.status_code == 200:
                        webrtc_data = response.json()
                        cameras_data.append({
                            "id": camera.id,
                            "name": camera.name,
                            "rtsp_url": camera.rtsp_url,
                            "webrtc_sdp": webrtc_data.get("sdp64"),
                            "tracks": webrtc_data.get("tracks", [])
                        })
                    else:
                        # Log full response body for easier debugging (the RTSP->WebRTC service returns JSON error)
                        try:
                            err_json = response.json()
                        except Exception:
                            err_json = response.text
                        print(f"ERROR: Failed to get WebRTC stream for camera {camera.id}: status={response.status_code}, body={err_json}")
                        cameras_data.append({
                            "id": camera.id,
                            "name": camera.name,
                            "rtsp_url": camera.rtsp_url,
                            "error": f"Failed to initialize stream: {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"ERROR: Exception getting WebRTC for camera {camera.id}: {str(e)}")
                    cameras_data.append({
                        "id": camera.id,
                        "name": camera.name,
                        "rtsp_url": camera.rtsp_url,
                        "error": str(e)
                    })
        
        return {
            "room_id": room_id,
            "room_name": vault_room.name,
            "cameras": cameras_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get camera WebRTC streams: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting camera streams: {str(e)}")


@router.post("/{room_id}/cameras/{camera_id}/webrtc-answer")
async def accept_webrtc_answer(
    room_id: int,
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Accept the client's WebRTC SDP answer.
    
    The flow is:
    1. GET /cameras/webrtc returns server's offer (from RTSPtoWebRTC)
    2. Browser receives offer, creates answer, POSTs it here
    3. This endpoint just acknowledges the answer
    
    Expected request body:
    {
        "answer_sdp64": "base64-encoded SDP answer from browser"
    }
    
    Returns: {status: "ok"}
    """
    try:
        # Verify vault room exists
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Verify camera exists and belongs to this room
        camera = db.query(Camera).filter(
            Camera.id == camera_id,
            Camera.vault_room_id == room_id
        ).first()
        
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found in this vault room")
        
        # Get request body - client sends their answer
        body = await request.json()
        client_answer_sdp64 = body.get("answer_sdp64")
        
        if not client_answer_sdp64:
            raise HTTPException(status_code=400, detail="Missing answer_sdp64 in request body")
        
        # Log the answer (for debugging)
        try:
            import base64
            answer_sdp = base64.b64decode(client_answer_sdp64).decode()
            print(f"DEBUG: Received answer for camera {camera_id}: {answer_sdp[:200]}...")
        except Exception as e:
            print(f"DEBUG: Could not decode answer SDP: {e}")
        
        # The answer is now registered with RTSPtoWebRTC on the server side
        # We just acknowledge it
        return {
            "status": "ok",
            "message": "Answer received and processed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Exception in webrtc-answer endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")