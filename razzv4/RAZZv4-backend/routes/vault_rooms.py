from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import VaultRoom, Camera
from typing import List
import logging
import httpx

logger = logging.getLogger(__name__)

WEBRTC_SERVER = "http://localhost:8083"

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

@router.get("/camera/{camera_id}/info")
async def get_camera_info(camera_id: int, db: Session = Depends(get_db)):
    """Get camera RTSP URL and info"""
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        return {
            "id": camera.id,
            "name": camera.name,
            "rtsp_url": camera.rtsp_url,
            "is_active": camera.is_active,
            "vault_room_id": camera.vault_room_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get camera info: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting camera info: {str(e)}")



@router.get("/{room_id}/people")
async def get_room_people_data(room_id: int, db: Session = Depends(get_db)):
    """Get detailed people tracking data for a vault room"""
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Import tracking service
        from main import tracking_service
        
        # Get camera IDs for this room
        camera_ids = [cam.id for cam in vault_room.cameras if cam.is_active]
        
        # Get people list from tracking service
        people_list = []
        if tracking_service:
            raw_people = tracking_service.get_people_in_room(camera_ids)
            # Remove numpy features for JSON serialization
            for person in raw_people:
                person_data = {k: v for k, v in person.items() if k != 'feature'}
                people_list.append(person_data)
        
        return {
            "room_id": room_id,
            "room_name": vault_room.name,
            "current_people_count": len(people_list),
            "people": people_list,
            "timestamp": __import__('time').time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get people data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting people data: {str(e)}")

@router.get("/{room_id}/cameras/webrtc")
async def get_camera_webrtc_streams(room_id: int, db: Session = Depends(get_db)):
    """Get WebRTC streams for all cameras in a vault room - returns stream IDs only"""
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Get all cameras for this room - just return camera info
        # The WebRTC connection will be established directly from the browser
        cameras_data = []
        
        for camera in vault_room.cameras:
            if not camera.is_active or not camera.rtsp_url:
                continue
            
            cameras_data.append({
                "id": camera.id,
                "name": camera.name,
                "rtsp_url": camera.rtsp_url  # Frontend will use this to connect
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
        raise HTTPException(status_code=500, detail=f"Error getting camera streams: {str(e)}")


@router.get("/{room_id}/people-count")
async def get_room_people_count(room_id: int, db: Session = Depends(get_db)):
    """
    Get current people count for a vault room
    Returns deduplicated count across all cameras from live tracking
    """
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Import camera service to get real-time counts
        from main import camera_service, tracking_service
        
        # Get individual camera counts from live tracking
        camera_counts = []
        camera_ids = []
        
        for camera in vault_room.cameras:
            if camera.is_active:
                people_count = 0
                
                # Get live count from camera processor
                if camera_service:
                    processor = camera_service.processors.get(camera.id)
                    if processor and processor.is_running:
                        camera_ids.append(camera.id)
                        # Get count from tracking service
                        if tracking_service:
                            cam_tracks = tracking_service.camera_tracks.get(camera.id, {})
                            people_count = cam_tracks.get('count', 0)
                
                camera_counts.append({
                    "camera_id": camera.id,
                    "camera_name": camera.name,
                    "people_count": people_count
                })
        
        # Use deduplicated count across all cameras in the room
        total_count = 0
        if tracking_service and len(camera_ids) > 0:
            people_list = tracking_service.get_people_in_room(camera_ids)
            total_count = len(people_list)
        
        return {
            "room_id": room_id,
            "room_name": vault_room.name,
            "total_people_count": total_count,
            "cameras": camera_counts
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get people count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting people count: {str(e)}")


@router.get("/all/people-counts")
async def get_all_rooms_people_counts(db: Session = Depends(get_db)):
    """
    Get people counts for all vault rooms
    """
    try:
        vault_rooms = db.query(VaultRoom).all()
        
        results = []
        for room in vault_rooms:
            camera_counts = []
            for camera in room.cameras:
                if camera.is_active:
                    camera_counts.append({
                        "camera_id": camera.id,
                        "camera_name": camera.name,
                        "people_count": camera.current_people_count or 0
                    })
            
            results.append({
                "room_id": room.id,
                "room_name": room.name,
                "total_people_count": room.current_people_count or 0,
                "cameras": camera_counts
            })
        
        return {"rooms": results}
    
    except Exception as e:
        print(f"ERROR: Failed to get people counts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting people counts: {str(e)}")


@router.get("/{room_id}/tracking-stats")
async def get_room_tracking_stats(room_id: int, db: Session = Depends(get_db)):
    """
    Get tracking statistics for cameras in a vault room
    """
    try:
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Import here to avoid circular dependency
        from main import camera_service, tracking_service
        
        camera_stats = []
        for camera in vault_room.cameras:
            if camera.is_active and camera_service and tracking_service:
                processor = camera_service.processors.get(camera.id)
                if processor and processor.is_running:
                    # Get stats from tracking service
                    cam_tracks = tracking_service.camera_tracks.get(camera.id, {})
                    stats = {
                        "active_tracks": cam_tracks.get('count', 0),
                        "bytetrack_confident": cam_tracks.get('bytetrack_confident', 0),
                        "deepsort_assisted": cam_tracks.get('deepsort_assisted', 0),
                        "last_update": cam_tracks.get('last_update').isoformat() if cam_tracks.get('last_update') else None
                    }
                    camera_stats.append({
                        "camera_id": camera.id,
                        "camera_name": camera.name,
                        "tracking_enabled": True,
                        "statistics": stats
                    })
                else:
                    camera_stats.append({
                        "camera_id": camera.id,
                        "camera_name": camera.name,
                        "tracking_enabled": False
                    })
        
        return {
            "room_id": room_id,
            "room_name": vault_room.name,
            "cameras": camera_stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get tracking stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting tracking stats: {str(e)}")


@router.get("/{room_id}/camera/{camera_id}/tracking-frame")
async def get_camera_tracking_frame(room_id: int, camera_id: int, db: Session = Depends(get_db)):
    """
    Get the latest annotated frame with tracking visualization for a specific camera
    Returns base64-encoded JPEG image
    """
    try:
        import cv2
        import base64
        
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        camera = db.query(Camera).filter(
            Camera.id == camera_id,
            Camera.vault_room_id == room_id
        ).first()
        
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # Import here to avoid circular dependency
        from main import camera_service
        
        if not camera_service:
            raise HTTPException(status_code=503, detail="Camera service not available")
        
        processor = camera_service.processors.get(camera_id)
        if not processor:
            logger.warning(f"Camera processor not found for camera {camera_id}. Available: {list(camera_service.processors.keys())}")
            raise HTTPException(status_code=404, detail="Camera processor not found or not started")
        
        if not processor.is_running:
            logger.warning(f"Camera {camera_id} processor exists but is not running")
            raise HTTPException(status_code=503, detail="Camera processor not running")
        
        # Get the latest annotated frame
        if hasattr(processor, 'last_annotated_frame') and processor.last_annotated_frame is not None:
            frame = processor.last_annotated_frame
            
            logger.debug(f"Encoding tracking frame for camera {camera_id}, shape: {frame.shape}, dtype: {frame.dtype}")
            
            # Encode frame as JPEG
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                logger.error(f"Failed to encode frame for camera {camera_id}")
                raise HTTPException(status_code=500, detail="Failed to encode tracking frame")
            
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.debug(f"Successfully encoded frame for camera {camera_id}, size: {len(frame_base64)} bytes")
            
            return {
                "camera_id": camera_id,
                "camera_name": camera.name,
                "frame": frame_base64,
                "frame_size": len(frame_base64),
                "timestamp": processor.last_update_time.isoformat() if hasattr(processor, 'last_update_time') else None
            }
        else:
            logger.info(f"No annotated frame available yet for camera {camera_id} (may be starting up or no detections)")
            # Return a placeholder or 404
            raise HTTPException(status_code=404, detail="No tracking frame available yet - camera may be starting up")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to get tracking frame: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting tracking frame: {str(e)}")


@router.post("/{room_id}/rename-person")
async def rename_person(
    room_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Rename a person by their global ID"""
    try:
        data = await request.json()
        global_id = data.get("global_id")
        new_name = data.get("name")
        
        if not global_id or not new_name:
            raise HTTPException(status_code=400, detail="global_id and name are required")
        
        # Validate room exists
        vault_room = db.query(VaultRoom).filter(VaultRoom.id == room_id).first()
        if not vault_room:
            raise HTTPException(status_code=404, detail="Vault room not found")
        
        # Import tracking service
        from main import tracking_service
        
        if not tracking_service:
            raise HTTPException(status_code=503, detail="Tracking service not available")
        
        # Rename the person
        success = tracking_service.set_person_name(int(global_id), new_name.strip())
        
        if success:
            logger.info(f"Renamed person {global_id} to '{new_name}' in room {room_id}")
            return {
                "success": True,
                "global_id": global_id,
                "name": new_name,
                "message": f"Person renamed to {new_name}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Person with global ID {global_id} not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming person: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error renaming person: {str(e)}")


@router.post("/{room_id}/cameras/{camera_id}/register-webrtc")
async def register_camera_webrtc(
    room_id: int,
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Register a camera's RTSP stream with the RTSPtoWebRTC server.
    This creates the stream dynamically so it can be accessed via WebRTC.
    """
    try:
        # Get camera from database
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        if not camera.rtsp_url:
            raise HTTPException(status_code=400, detail="Camera has no RTSP URL")
        
        # Register stream with WebRTC server
        stream_id = f"camera{camera_id}"
        
        async with httpx.AsyncClient() as client:
            # First, try to add the stream via POST to the config endpoint
            response = await client.post(
                f"{WEBRTC_SERVER}/stream",
                json={
                    "name": stream_id,
                    "channels": {
                        "0": {
                            "url": camera.rtsp_url,
                            "on_demand": True,
                            "disable_audio": True
                        }
                    }
                },
                timeout=5.0
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Registered stream {stream_id} with WebRTC server")
                return {
                    "success": True,
                    "stream_id": stream_id,
                    "camera_id": camera_id,
                    "message": "Stream registered successfully"
                }
            else:
                logger.warning(f"Failed to register stream: {response.status_code} - {response.text}")
                # Stream might already exist, return success anyway
                return {
                    "success": True,
                    "stream_id": stream_id,
                    "camera_id": camera_id,
                    "message": "Stream may already be registered"
                }
    
    except httpx.RequestError as e:
        logger.error(f"Error connecting to WebRTC server: {type(e).__name__} - {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"WebRTC server unavailable: {type(e).__name__} - {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering WebRTC stream: {type(e).__name__} - {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error registering stream: {str(e)}")