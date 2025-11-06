"""
Example script showing how to create rooms and configure cross-camera tracking
Run this after migration to set up your first room
"""

import requests

BASE_URL = "http://localhost:8000"

def create_example_room():
    """Create an example room with 2 cameras"""
    
    print("🏢 Creating example room setup...\n")
    
    # Step 1: Create a room
    print("1️⃣ Creating 'Main Lobby' room...")
    room_data = {
        "name": "Main Lobby",
        "description": "Main entrance area with 2 overlapping cameras",
        "floor_level": "Ground Floor",
        "capacity": 50
    }
    
    response = requests.post(f"{BASE_URL}/api/rooms/", json=room_data)
    if response.status_code == 200:
        room = response.json()
        room_id = room['id']
        print(f"   ✅ Room created with ID: {room_id}\n")
    else:
        print(f"   ❌ Failed to create room: {response.text}")
        return
    
    # Step 2: Get available cameras
    print("2️⃣ Fetching available cameras...")
    response = requests.get(f"{BASE_URL}/api/cameras/")
    if response.status_code == 200:
        cameras = response.json()
        print(f"   Found {len(cameras)} cameras\n")
        
        # Display cameras
        for cam in cameras[:5]:  # Show first 5
            print(f"   📹 Camera {cam['id']}: {cam['name']} ({cam['location']})")
        
        if len(cameras) < 2:
            print("\n   ⚠️ Need at least 2 cameras to demonstrate cross-camera tracking")
            print("   Create cameras first using /cameras-page\n")
            return
    else:
        print(f"   ❌ Failed to fetch cameras: {response.text}")
        return
    
    # Step 3: Assign first 2 cameras to the room
    print("\n3️⃣ Assigning cameras to room...")
    for i in range(min(2, len(cameras))):
        camera_id = cameras[i]['id']
        response = requests.post(f"{BASE_URL}/api/rooms/{room_id}/cameras/{camera_id}")
        if response.status_code == 200:
            print(f"   ✅ Camera {camera_id} assigned to room")
        else:
            print(f"   ❌ Failed to assign camera {camera_id}")
    
    # Step 4: Configure overlap zone (example coordinates)
    if len(cameras) >= 2:
        print("\n4️⃣ Configuring overlap zone...")
        camera_1_id = cameras[0]['id']
        camera_2_id = cameras[1]['id']
        
        overlap_config = {
            "overlap_config": {
                "overlaps": [
                    {
                        "camera_id_1": camera_1_id,
                        "camera_id_2": camera_2_id,
                        "polygon": [
                            [200, 200],  # Top-left
                            [600, 200],  # Top-right
                            [600, 400],  # Bottom-right
                            [200, 400]   # Bottom-left
                        ]
                    }
                ]
            }
        }
        
        response = requests.put(f"{BASE_URL}/api/rooms/{room_id}", json=overlap_config)
        if response.status_code == 200:
            print(f"   ✅ Overlap zone configured between cameras {camera_1_id} and {camera_2_id}")
            print(f"   📍 Zone coordinates: [200,200] to [600,400]")
        else:
            print(f"   ❌ Failed to configure overlap: {response.text}")
    
    # Step 5: Get room person count
    print("\n5️⃣ Testing room person count...")
    response = requests.get(f"{BASE_URL}/api/rooms/{room_id}/person-count")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Room: {data['room_name']}")
        print(f"   👥 Unique Person Count: {data['unique_person_count']}")
        print(f"   ⏰ Timestamp: {data['timestamp']}")
    else:
        print(f"   ❌ Failed to get person count: {response.text}")
    
    print("\n" + "="*60)
    print("🎉 Setup complete!")
    print("="*60)
    print(f"\n📋 Next steps:")
    print(f"1. Visit: http://localhost:8000/rooms-page")
    print(f"2. View room '{room_data['name']}' with {min(2, len(cameras))} cameras")
    print(f"3. Monitor real-time person count (cross-camera tracking active)")
    print(f"4. Configure additional rooms as needed")
    print()

if __name__ == "__main__":
    try:
        create_example_room()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the application is running:")
        print("   pm2 restart all")
        print("   Or check: http://localhost:8000/health")
    except Exception as e:
        print(f"❌ Error: {e}")
