#!/usr/bin/env python3
"""
Test script to verify person re-identification when leaving and returning

Scenario:
1. Person enters on Camera 10 (PRIMARY) - gets Global ID 1
2. Person moves to Camera 11 (SUPPORT) - matches to Global ID 1
3. Person leaves all cameras (disappears from view)
4. Person returns to Camera 11 - should still match to Global ID 1
5. Person returns to Camera 10 - should still match to Global ID 1
"""

import sys
import time
import numpy as np
import logging
from services.global_person_tracker import GlobalPersonTracker
import services.global_person_tracker as gpt_module
from database import SessionLocal
from models import DetectedPerson

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def reset_tracker_singleton():
    """Reset the global tracker singleton"""
    gpt_module._global_tracker_instance = None

def create_normalized_embedding():
    """Create a random normalized embedding"""
    emb = np.random.rand(512).astype(np.float32)
    return emb / np.linalg.norm(emb)

def create_test_frame(color_seed=0):
    """Create a test frame with optional color"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    if color_seed > 0:
        frame[:] = (color_seed * 30 % 255, color_seed * 50 % 255, color_seed * 70 % 255)
    return frame

def test_person_leave_and_return():
    """Test that person is recognized when leaving and returning"""
    print("\n" + "="*80)
    print("PERSON LEAVE AND RETURN TEST")
    print("="*80)
    
    # Clear database
    print("\n🗑️  Clearing database...")
    db = SessionLocal()
    try:
        deleted_dp = db.query(DetectedPerson).delete()
        db.commit()
        print(f"✅ Deleted {deleted_dp} DetectedPerson records\n")
    finally:
        db.close()
    
    # Reset tracker
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    
    # Create consistent embedding for same person
    person_embedding = create_normalized_embedding()
    frame = create_test_frame()
    
    # STEP 1: Person enters on PRIMARY camera (Camera 10)
    print("\n" + "="*80)
    print("STEP 1: Person enters on Camera 10 (PRIMARY)")
    print("="*80)
    
    global_id_initial = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        face_embedding=person_embedding.copy(),
        bbox=(100, 100, 200, 400),
        frame=frame
    )
    
    print(f"✅ Camera 10 created: Global ID {global_id_initial}")
    person = tracker.persons[global_id_initial]
    print(f"   Cameras visited: {person.cameras_visited}")
    print(f"   Last seen: {time.time() - person.last_seen:.1f}s ago")
    
    # STEP 2: Person moves to SUPPORT camera (Camera 11)
    print("\n" + "="*80)
    print("STEP 2: Person moves to Camera 11 (SUPPORT)")
    print("="*80)
    
    global_id_camera11 = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=1,
        face_embedding=person_embedding + create_normalized_embedding() * 0.05,  # Slightly noisy
        bbox=(105, 105, 205, 405),  # Similar dimensions
        frame=frame
    )
    
    if global_id_camera11 == global_id_initial:
        print(f"✅ Camera 11 matched to same person: Global ID {global_id_camera11}")
    else:
        print(f"❌ Camera 11 got different ID: {global_id_camera11} (expected {global_id_initial})")
    
    person = tracker.persons[global_id_initial]
    print(f"   Cameras visited: {person.cameras_visited}")
    print(f"   Camera positions: {list(person.camera_positions.keys())}")
    
    # STEP 3: Person leaves all cameras
    print("\n" + "="*80)
    print("STEP 3: Person leaves all cameras (simulating disappearance)")
    print("="*80)
    
    # Clear camera positions (person no longer visible)
    tracker.persons[global_id_initial].camera_positions.clear()
    tracker.persons[global_id_initial].camera_tracks.clear()
    
    print(f"✅ Cleared camera positions")
    person = tracker.persons[global_id_initial]
    print(f"   Cameras visited: {person.cameras_visited} (historical)")
    print(f"   Current positions: {list(person.camera_positions.keys())} (empty)")
    print(f"   Last seen: {time.time() - person.last_seen:.1f}s ago")
    
    # Wait a moment
    time.sleep(1)
    
    # STEP 4: Person returns to SUPPORT camera (Camera 11)
    print("\n" + "="*80)
    print("STEP 4: Person returns to Camera 11 (SUPPORT)")
    print("="*80)
    
    global_id_return_11 = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=2,  # New local track ID
        face_embedding=person_embedding + create_normalized_embedding() * 0.05,
        bbox=(110, 110, 210, 410),  # Similar location/size
        frame=frame
    )
    
    if global_id_return_11 == global_id_initial:
        print(f"✅ Camera 11 recognized returning person: Global ID {global_id_return_11}")
    elif global_id_return_11 is None:
        print(f"⚠️  Camera 11 returned None (waiting for primary camera)")
    else:
        print(f"❌ Camera 11 got different ID: {global_id_return_11} (expected {global_id_initial})")
    
    if global_id_return_11:
        person = tracker.persons[global_id_return_11]
        print(f"   Cameras visited: {person.cameras_visited}")
        print(f"   Current positions: {list(person.camera_positions.keys())}")
    
    # STEP 5: Person returns to PRIMARY camera (Camera 10)
    print("\n" + "="*80)
    print("STEP 5: Person returns to Camera 10 (PRIMARY)")
    print("="*80)
    
    global_id_return_10 = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=2,  # New local track ID
        face_embedding=person_embedding + create_normalized_embedding() * 0.05,
        bbox=(95, 95, 195, 395),
        frame=frame
    )
    
    if global_id_return_10 == global_id_initial:
        print(f"✅ Camera 10 recognized returning person: Global ID {global_id_return_10}")
    else:
        print(f"⚠️  Camera 10 created NEW person: Global ID {global_id_return_10} (expected {global_id_initial})")
        print(f"   This might be expected if primary camera always creates new IDs")
    
    person = tracker.persons[global_id_return_10]
    print(f"   Cameras visited: {person.cameras_visited}")
    print(f"   Current positions: {list(person.camera_positions.keys())}")
    
    # FINAL RESULTS
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    print(f"\nTotal persons tracked: {len(tracker.persons)}")
    for gid, person in tracker.persons.items():
        print(f"\nPerson {gid}:")
        print(f"  Cameras visited: {person.cameras_visited}")
        print(f"  Current positions: {list(person.camera_positions.keys())}")
        print(f"  Last seen: {time.time() - person.last_seen:.1f}s ago")
        print(f"  Total appearances: {person.total_appearances}")
    
    # Verify results
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    success = True
    
    # Check if only one person was tracked
    if len(tracker.persons) == 1:
        print("✅ Only ONE person tracked (correct)")
    else:
        print(f"❌ Multiple persons tracked: {len(tracker.persons)} (should be 1)")
        success = False
    
    # Check if support camera matched after return
    if global_id_return_11 == global_id_initial:
        print("✅ Support camera recognized returning person")
    else:
        print(f"❌ Support camera failed to recognize returning person")
        success = False
    
    # Check primary camera behavior
    if global_id_return_10 == global_id_initial:
        print("✅ Primary camera recognized returning person")
    else:
        print(f"⚠️  Primary camera behavior: Created new ID {global_id_return_10}")
        print("   Note: This depends on implementation - does primary check existing persons?")
    
    print("\n" + "="*80)
    if success:
        print("✅ TEST PASSED: Person re-identification works correctly!")
    else:
        print("❌ TEST FAILED: Issues with person re-identification")
    print("="*80 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(test_person_leave_and_return())
