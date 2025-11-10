"""
Auto-detect and configure overlap zones based on camera FOV
"""

import sys
sys.path.append('/home/husain/alrazy/brinksv2')

from database import SessionLocal
from models import Room, Camera
import math

def calculate_fov_polygon(camera_pos, fov_angle, fov_distance, rotation):
    """Calculate the FOV polygon points for a camera"""
    x, y = camera_pos['x'], camera_pos['y']
    
    # Convert rotation to radians
    rotation_rad = math.radians(rotation)
    half_fov_rad = math.radians(fov_angle / 2)
    
    # Calculate the three points of the FOV triangle
    # Point 1: Camera position
    p1 = {'x': x, 'y': y}
    
    # Point 2: Left edge of FOV
    angle_left = rotation_rad - half_fov_rad
    p2 = {
        'x': x + fov_distance * math.cos(angle_left),
        'y': y + fov_distance * math.sin(angle_left)
    }
    
    # Point 3: Right edge of FOV
    angle_right = rotation_rad + half_fov_rad
    p3 = {
        'x': x + fov_distance * math.cos(angle_right),
        'y': y + fov_distance * math.sin(angle_right)
    }
    
    return [p1, p2, p3]

def polygons_overlap(poly1, poly2):
    """Simple overlap detection - check if any points are close"""
    # This is a simplified check - in production, use proper polygon intersection
    for p1 in poly1:
        for p2 in poly2:
            distance = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
            if distance < 2.0:  # If points are within 2 meters
                return True
    return False

def auto_detect_overlaps(room_id):
    """Auto-detect overlap zones for a room based on camera FOV"""
    db = SessionLocal()
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        print(f"❌ Room {room_id} not found")
        db.close()
        return
    
    print(f"\n{'=' * 80}")
    print(f"AUTO-DETECTING OVERLAPS FOR ROOM: {room.name} (ID: {room_id})")
    print(f"{'=' * 80}\n")
    
    if not room.camera_positions or len(room.camera_positions) < 2:
        print("⚠️  Need at least 2 cameras with positions to detect overlaps")
        db.close()
        return
    
    # Calculate FOV polygons for all cameras
    camera_fovs = {}
    for pos in room.camera_positions:
        camera_id = pos['camera_id']
        polygon = calculate_fov_polygon(
            pos['position'],
            pos['fov_angle'],
            pos['fov_distance'],
            pos['rotation']
        )
        camera_fovs[camera_id] = polygon
        
        print(f"📹 Camera {camera_id}:")
        print(f"   Position: ({pos['position']['x']:.2f}, {pos['position']['y']:.2f})")
        print(f"   Rotation: {pos['rotation']}°")
        print(f"   FOV: {pos['fov_angle']}° at {pos['fov_distance']}m")
        print(f"   FOV Polygon: {len(polygon)} points")
        print()
    
    # Detect overlaps
    overlaps = []
    camera_ids = list(camera_fovs.keys())
    
    for i in range(len(camera_ids)):
        for j in range(i + 1, len(camera_ids)):
            cam1_id = camera_ids[i]
            cam2_id = camera_ids[j]
            
            if polygons_overlap(camera_fovs[cam1_id], camera_fovs[cam2_id]):
                print(f"✅ OVERLAP DETECTED: Camera {cam1_id} ↔ Camera {cam2_id}")
                
                # Create a simple overlap polygon (intersection of both FOVs)
                # For now, use the midpoint area
                poly1 = camera_fovs[cam1_id]
                poly2 = camera_fovs[cam2_id]
                
                # Calculate approximate overlap area
                overlap_polygon = [
                    {'x': (poly1[0]['x'] + poly2[0]['x']) / 2,
                     'y': (poly1[0]['y'] + poly2[0]['y']) / 2},
                    {'x': (poly1[1]['x'] + poly2[1]['x']) / 2,
                     'y': (poly1[1]['y'] + poly2[1]['y']) / 2},
                    {'x': (poly1[2]['x'] + poly2[2]['x']) / 2,
                     'y': (poly1[2]['y'] + poly2[2]['y']) / 2}
                ]
                
                overlaps.append({
                    'camera_ids': [cam1_id, cam2_id],
                    'polygon_points': overlap_polygon
                })
    
    if overlaps:
        # Save overlaps to database
        if not room.overlap_config:
            room.overlap_config = {}
        room.overlap_config['overlaps'] = overlaps
        
        db.commit()
        
        print(f"\n{'=' * 80}")
        print(f"✅ SAVED {len(overlaps)} OVERLAP ZONE(S) TO DATABASE")
        print(f"{'=' * 80}\n")
        
        for idx, overlap in enumerate(overlaps):
            print(f"Overlap Zone {idx + 1}:")
            print(f"  Cameras: {overlap['camera_ids']}")
            print(f"  Polygon: {len(overlap['polygon_points'])} points")
            print()
    else:
        print("\n⚠️  NO OVERLAPS DETECTED - Cameras FOVs don't intersect")
        print("   Consider adjusting camera positions or FOV settings")
    
    db.close()

if __name__ == "__main__":
    # Auto-detect for all rooms
    db = SessionLocal()
    rooms = db.query(Room).all()
    db.close()
    
    for room in rooms:
        auto_detect_overlaps(room.id)
    
    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT: Restart the application to apply overlap zone changes:")
    print("   pm2 restart brinks-v2")
    print("=" * 80)
