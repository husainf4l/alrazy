"""
Verify that camera IDs are correctly used throughout the system
"""

import sys
sys.path.append('/home/husain/alrazy/brinksv2')

from database import SessionLocal
from models import Room, Camera
import json

db = SessionLocal()

print("=" * 80)
print("CAMERA ID VERIFICATION")
print("=" * 80)

# Get all rooms with cameras
rooms = db.query(Room).all()

for room in rooms:
    print(f"\n{'=' * 80}")
    print(f"ROOM: {room.name} (ID: {room.id})")
    print(f"{'=' * 80}")
    
    # Get cameras in this room
    cameras = db.query(Camera).filter(Camera.room_id == room.id).all()
    
    print(f"\n📹 ACTUAL CAMERAS IN DATABASE:")
    for cam in cameras:
        print(f"  ✓ Camera ID: {cam.id}")
        print(f"    Name: {cam.name}")
        print(f"    Location: {cam.location}")
        print(f"    Room ID: {cam.room_id}")
        print()
    
    # Check saved layout
    print(f"\n📐 SAVED LAYOUT CAMERA POSITIONS:")
    if room.camera_positions:
        for pos in room.camera_positions:
            camera_id = pos['camera_id']
            position = pos['position']
            rotation = pos['rotation']
            
            # Find if this camera exists
            camera_exists = any(c.id == camera_id for c in cameras)
            status = "✅ CORRECT" if camera_exists else "❌ MISMATCH"
            
            print(f"  {status} Camera ID: {camera_id}")
            print(f"    Position: ({position['x']:.2f}, {position['y']:.2f})")
            print(f"    Rotation: {rotation}°")
            print(f"    FOV: {pos.get('fov_angle', 'N/A')}°")
            print()
    else:
        print("  ⚠️  No camera positions saved in layout")
    
    # Check overlap zones
    print(f"\n🔄 OVERLAP ZONES:")
    if room.overlap_config and room.overlap_config.get('overlaps'):
        for idx, overlap in enumerate(room.overlap_config['overlaps']):
            cam1_id = overlap.get('camera_id_1', overlap.get('camera_ids', [None, None])[0])
            cam2_id = overlap.get('camera_id_2', overlap.get('camera_ids', [None, None])[1])
            
            cam1_exists = any(c.id == cam1_id for c in cameras)
            cam2_exists = any(c.id == cam2_id for c in cameras)
            
            status1 = "✅" if cam1_exists else "❌"
            status2 = "✅" if cam2_exists else "❌"
            
            print(f"  Overlap Zone {idx + 1}:")
            print(f"    {status1} Camera 1 ID: {cam1_id}")
            print(f"    {status2} Camera 2 ID: {cam2_id}")
            print()
    else:
        print("  ⚠️  No overlap zones configured")

print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

# Check for any mismatches
all_camera_ids = set(c.id for c in db.query(Camera).all())
layout_camera_ids = set()

for room in rooms:
    if room.camera_positions:
        for pos in room.camera_positions:
            layout_camera_ids.add(pos['camera_id'])

mismatches = layout_camera_ids - all_camera_ids
if mismatches:
    print(f"\n❌ FOUND MISMATCHES:")
    print(f"   Camera IDs in layouts but not in database: {mismatches}")
else:
    print(f"\n✅ ALL CAMERA IDS ARE CORRECTLY MAPPED")
    print(f"   Total cameras in database: {len(all_camera_ids)}")
    print(f"   Cameras with saved positions: {len(layout_camera_ids)}")

db.close()
