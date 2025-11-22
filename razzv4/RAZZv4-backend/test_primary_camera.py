#!/usr/bin/env python3
"""
Test script for Primary Camera System

Tests the functionality of the primary/support camera architecture.
"""

import sys
import numpy as np
import logging
from services.global_person_tracker import GlobalPersonTracker
import services.global_person_tracker as gpt_module

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def reset_tracker_singleton():
    """Reset the global tracker singleton to force fresh instance"""
    gpt_module._global_tracker_instance = None

def create_normalized_embedding():
    """Create a random normalized embedding (like OSNet output)"""
    emb = np.random.rand(512).astype(np.float32)
    return emb / np.linalg.norm(emb)  # Normalize to unit length

def create_dissimilar_embeddings(n=2):
    """Create n embeddings that are orthogonal (dissimilar)"""
    embeddings = []
    for i in range(n):
        emb = np.zeros(512, dtype=np.float32)
        # Place different values in non-overlapping regions
        start_idx = (i * 512 // n)
        end_idx = ((i + 1) * 512 // n)
        emb[start_idx:end_idx] = 1.0
        emb = emb / np.linalg.norm(emb)  # Normalize
        embeddings.append(emb)
    return embeddings if n > 1 else embeddings[0]

def create_test_frame(color_seed=0):
    """Create a dummy frame for testing with varying colors"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some color variation based on seed
    if color_seed > 0:
        frame[:] = (color_seed * 30 % 255, color_seed * 50 % 255, color_seed * 70 % 255)
    return frame

def test_primary_creates_person():
    """Test that primary camera creates new persons"""
    print("\n" + "="*60)
    print("TEST 1: Primary Camera Creates Person")
    print("="*60)
    
    reset_tracker_singleton()
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Primary camera should create
    global_id = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        face_embedding=create_normalized_embedding(),
        bbox=(100, 100, 200, 400),
        frame=frame
    )
    
    print(f"✅ Primary camera created Global ID: {global_id}")
    assert global_id is not None, "Primary camera should create person"
    
    person = tracker.persons.get(global_id)
    assert person is not None, "Person should exist"
    assert 10 in person.cameras_visited, "Person should have visited camera 10"
    
    print(f"✅ Person {global_id} cameras visited: {person.cameras_visited}")
    print("✅ TEST 1 PASSED\n")
    
    return tracker, global_id

def test_support_waits_for_primary():
    """Test that support camera waits for primary"""
    print("\n" + "="*60)
    print("TEST 2: Support Camera Waits for Primary")
    print("="*60)
    
    reset_tracker_singleton()
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Support camera sees person first (should return None)
    global_id = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=1,
        face_embedding=create_normalized_embedding(),
        bbox=(100, 100, 200, 400),
        frame=frame
    )
    
    if global_id is None:
        print(f"✅ Support camera correctly returned None (waiting for primary)")
    else:
        print(f"❌ Support camera should return None, got Global ID {global_id}")
    
    assert global_id is None, "Support camera should not create person"
    print("✅ TEST 2 PASSED\n")

def test_support_matches_primary():
    """Test that support camera matches person from primary"""
    print("\n" + "="*60)
    print("TEST 3: Support Camera Matches Primary Person")
    print("="*60)
    
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Primary camera creates person
    embedding = create_normalized_embedding()
    primary_id = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        face_embedding=embedding.copy(),
        bbox=(100, 100, 200, 400),
        frame=frame
    )
    
    print(f"✅ Primary camera created Global ID: {primary_id}")
    
    # Support camera sees same person (similar embedding and bbox)
    support_id = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=1,
        face_embedding=embedding + create_normalized_embedding() * 0.1,  # Similar
        bbox=(105, 105, 205, 405),  # Similar dimensions
        frame=frame
    )
    
    if support_id == primary_id:
        print(f"✅ Support camera matched to same Global ID: {support_id}")
    else:
        print(f"❌ Support camera should match to {primary_id}, got {support_id}")
    
    assert support_id == primary_id, "Support camera should match primary person"
    
    person = tracker.persons[primary_id]
    print(f"✅ Person {primary_id} now on cameras: {person.cameras_visited}")
    assert 11 in person.cameras_visited, "Person should have visited camera 11"
    print("✅ TEST 3 PASSED\n")

def test_support_no_match():
    """Test that support camera returns None for different person"""
    print("\n" + "="*60)
    print("TEST 4: Support Camera No Match (Different Person)")
    print("="*60)
    
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Create two truly dissimilar embeddings
    emb1, emb2 = create_dissimilar_embeddings(2)
    
    # Primary camera creates person
    primary_id = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        face_embedding=emb1,
        bbox=(100, 100, 200, 400),
        frame=frame
    )
    
    print(f"✅ Primary camera created Global ID: {primary_id}")
    
    # Support camera sees completely different person (different dimensions AND different color)
    frame2 = create_test_frame(color_seed=5)  # Different colored frame
    support_id = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=2,
        face_embedding=emb2,  # Completely different (orthogonal)
        bbox=(500, 100, 650, 500),  # Different location AND size (width=150, height=400)
        frame=frame2
    )
    
    if support_id is None:
        print(f"✅ Support camera correctly returned None (no match)")
    else:
        print(f"❌ Support camera should return None, got Global ID {support_id}")
    
    assert support_id is None, "Support camera should not match different person"
    print("✅ TEST 4 PASSED\n")

def test_dimension_matching():
    """Test dimension-based matching between cameras"""
    print("\n" + "="*60)
    print("TEST 5: Dimension-Based Matching")
    print("="*60)
    
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Primary camera creates person with specific dimensions
    primary_id = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        face_embedding=create_normalized_embedding(),
        bbox=(100, 100, 200, 400),  # Width: 100, Height: 300
        frame=frame
    )
    
    print(f"✅ Primary camera created Global ID: {primary_id}")
    person = tracker.persons[primary_id]
    print(f"   Dimensions: width={person.avg_width:.1f}, height={person.avg_height:.1f}")
    
    # Support camera sees person with similar dimensions
    support_id = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=1,
        face_embedding=create_normalized_embedding(),  # Different embedding
        bbox=(300, 150, 405, 455),  # Similar dimensions: Width: 105, Height: 305
        frame=frame
    )
    
    if support_id == primary_id:
        print(f"✅ Support camera matched by dimensions to Global ID: {support_id}")
    else:
        print(f"❌ Support camera should match by dimensions to {primary_id}, got {support_id}")
    
    assert support_id == primary_id, "Should match by dimensions"
    print("✅ TEST 5 PASSED\n")

def test_multiple_persons():
    """Test tracking multiple persons across cameras"""
    print("\n" + "="*60)
    print("TEST 6: Multiple Persons Across Cameras")
    print("="*60)
    
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Primary camera creates 3 persons
    embeddings = [create_normalized_embedding() for _ in range(3)]
    bboxes = [
        (100, 100, 200, 400),  # Person 1
        (300, 100, 400, 400),  # Person 2
        (500, 100, 600, 400),  # Person 3
    ]
    
    primary_ids = []
    for i, (embedding, bbox) in enumerate(zip(embeddings, bboxes)):
        gid = tracker.match_or_create_person(
            camera_id=10,
            local_track_id=i+1,
            face_embedding=embedding,
            bbox=bbox,
            frame=frame
        )
        primary_ids.append(gid)
        print(f"✅ Primary camera created Person {i+1}: Global ID {gid}")
    
    print(f"\n✅ Total persons from primary: {len(primary_ids)}")
    
    # Support camera sees all 3 persons (should match all)
    support_ids = []
    for i, (embedding, bbox) in enumerate(zip(embeddings, bboxes)):
        gid = tracker.match_or_create_person(
            camera_id=11,
            local_track_id=i+1,
            face_embedding=embedding + create_normalized_embedding() * 0.05,
            bbox=(bbox[0]+10, bbox[1]+10, bbox[2]+10, bbox[3]+10),
            frame=frame
        )
        support_ids.append(gid)
        if gid == primary_ids[i]:
            print(f"✅ Support camera matched Person {i+1}: Global ID {gid}")
        else:
            print(f"❌ Support camera should match to {primary_ids[i]}, got {gid}")
    
    assert support_ids == primary_ids, "All persons should match"
    print("\n✅ TEST 6 PASSED\n")

def test_primary_persons_filter():
    """Test that primary persons filter works correctly"""
    print("\n" + "="*60)
    print("TEST 7: Primary Persons Filter")
    print("="*60)
    
    reset_tracker_singleton()
    tracker = GlobalPersonTracker(primary_camera_id=10)
    frame = create_test_frame()
    
    # Create persons on different cameras
    # Primary creates 2 persons
    id1 = tracker.match_or_create_person(
        camera_id=10, local_track_id=1,
        face_embedding=create_normalized_embedding(),
        bbox=(100, 100, 200, 400), frame=frame
    )
    id2 = tracker.match_or_create_person(
        camera_id=10, local_track_id=2,
        face_embedding=create_normalized_embedding(),
        bbox=(300, 100, 400, 400), frame=frame
    )
    
    print(f"✅ Primary camera created: Global IDs {id1}, {id2}")
    
    # Check primary persons
    primary_persons = {
        gid: p for gid, p in tracker.persons.items()
        if tracker.PRIMARY_CAMERA_ID in p.cameras_visited
    }
    
    print(f"✅ Primary persons: {list(primary_persons.keys())}")
    print(f"   Total persons: {list(tracker.persons.keys())}")
    
    assert len(primary_persons) == 2, "Should have 2 primary persons"
    assert id1 in primary_persons, "Person 1 should be in primary"
    assert id2 in primary_persons, "Person 2 should be in primary"
    
    print("✅ TEST 7 PASSED\n")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PRIMARY CAMERA SYSTEM TEST SUITE")
    print("="*80)
    
    # Clear database before testing
    print("\n🗑️  Clearing database...")
    try:
        from database import SessionLocal
        from models import Person, DetectedPerson
        
        db = SessionLocal()
        try:
            deleted_dp = db.query(DetectedPerson).delete()
            deleted_p = db.query(Person).delete()
            db.commit()
            print(f"✅ Deleted {deleted_dp} DetectedPerson + {deleted_p} Person records\n")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️  Could not clear database: {e}\n")
    
    try:
        test_primary_creates_person()
        test_support_waits_for_primary()
        test_support_matches_primary()
        test_support_no_match()
        test_dimension_matching()
        test_multiple_persons()
        test_primary_persons_filter()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80 + "\n")
        return 0
        
    except AssertionError as e:
        print("\n" + "="*80)
        print(f"❌ TEST FAILED: {e}")
        print("="*80 + "\n")
        return 1
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
