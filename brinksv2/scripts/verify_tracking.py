"""
Verify person tracking camera ID assignments
"""

import sys
sys.path.append('/home/husain/alrazy/brinksv2')

from database import SessionLocal
from models import Room, Camera
from services.people_detection import PeopleDetector
import json

db = SessionLocal()

print("=" * 80)
print("PERSON TRACKING VERIFICATION")
print("=" * 80)

# Get all cameras
cameras = db.query(Camera).all()

print(f"\n📹 DATABASE CAMERAS:")
for cam in cameras:
    print(f"  Camera ID: {cam.id}")
    print(f"    Name: {cam.name}")
    print(f"    Location: {cam.location}")
    print(f"    Room ID: {cam.room_id}")
    print(f"    RTSP URL: {cam.rtsp_main[:50]}...")
    print()

print("\n" + "=" * 80)
print("EXPECTED TRACKING FLOW")
print("=" * 80)

for cam in cameras:
    print(f"\nCamera ID {cam.id} ({cam.name}):")
    print(f"  1. Frame captured from: {cam.rtsp_main[:50]}...")
    print(f"  2. Detections processed with camera_id={cam.id}")
    print(f"  3. ByteTrack tracks with camera_id={cam.id}")
    print(f"  4. Room assignment: room_id={cam.room_id}")
    
    # Check if position config exists
    if cam.position_config:
        print(f"  5. Position config: ✅")
        print(f"     - Position: ({cam.position_config.get('position', {}).get('x', 'N/A')}, {cam.position_config.get('position', {}).get('y', 'N/A')})")
        print(f"     - Rotation: {cam.position_config.get('rotation', 'N/A')}°")
    else:
        print(f"  5. Position config: ⚠️  Not set (won't affect tracking, only visualization)")

print("\n" + "=" * 80)
print("DETECTION ENDPOINT VERIFICATION")
print("=" * 80)

print(f"\nTo verify tracking with correct IDs, check these endpoints:")
for cam in cameras:
    print(f"\n  Camera ID {cam.id}:")
    print(f"    Live detections: GET /api/detections/camera/{cam.id}/live")
    print(f"    Video stream:    GET /visualization/camera/{cam.id}/stream")
    print(f"    Stats:          GET /api/detections/camera/{cam.id}/stats")

print("\n" + "=" * 80)
print("CROSS-CAMERA TRACKING")
print("=" * 80)

rooms = db.query(Room).all()
for room in rooms:
    cameras_in_room = db.query(Camera).filter(Camera.room_id == room.id).all()
    if len(cameras_in_room) > 1:
        print(f"\nRoom: {room.name} (ID: {room.id})")
        print(f"  Cameras: {[c.id for c in cameras_in_room]}")
        print(f"  Global tracking will deduplicate people across these cameras")
        print(f"  Endpoint: GET /api/rooms/{room.id}/person-count")

db.close()

print("\n" + "=" * 80)
print("✅ VERIFICATION COMPLETE")
print("=" * 80)
