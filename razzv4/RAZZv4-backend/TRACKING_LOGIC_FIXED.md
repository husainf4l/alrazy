# Multi-Camera Tracking System - Proper Implementation

## Problem: Previous Implementation Had Fatal Flaws

### ❌ Old Logic Issues:

1. **Global IDs Were Regenerated Every API Call**
   - `get_unique_people_count_across_cameras()` created NEW IDs every time
   - Person got ID 59, then 60, then 61... constantly changing
   - Made editing impossible

2. **Names Regenerated Every API Call**
   - `used_name_index` incremented on every call
   - Even existing tracks got new names
   - Alex → Blake → Casey... cycling forever

3. **Embeddings Stored Wrong**
   - Stored as `{(camera_id, track_id): embedding}`
   - Should be `{global_id: embedding}` for matching against ALL persons

4. **Deduplication Called From API**
   - API endpoint called `get_unique_people_count()` which recreated IDs
   - Should just query existing data

## ✅ New Logic: Best Practice Implementation

### Core Principles

1. **Global Person Database**
   ```python
   self.global_persons = {
       global_id: {
           'embedding': np.ndarray,  # ReID embedding
           'name': str,              # Person's name
           'track_mappings': [(cam, track_id)]  # All tracks this person appears in
       }
   }
   ```

2. **Global ID Assignment Happens ONCE**
   - When embedding is first generated for a new track
   - Compare against ALL existing global persons
   - If similarity > threshold: reuse existing ID
   - If no match: create NEW global ID + name

3. **Names Assigned ONCE**
   - When global_id is created
   - Only changes when user explicitly renames

### Processing Flow

```
1. ByteTrack runs every frame (30 FPS)
   └─> Assigns local track_ids per camera
   └─> Fast, motion-based tracking

2. Every 2 seconds: generate_embeddings_for_camera()
   ├─> Generate DeepSORT embeddings for each track
   ├─> FOR EACH TRACK:
   │   ├─> Check if already has global_id
   │   │   └─> YES: Update embedding, done
   │   └─> NO (new track):
   │       ├─> Compare embedding against ALL global_persons
   │       ├─> Best match > threshold?
   │       │   ├─> YES: Assign existing global_id (same person)
   │       │   └─> NO: Create NEW global_id + name (new person)
   │       └─> Store mapping in camera_track_to_global
   └─> Result: stable global IDs across cameras

3. API: get_people_in_room()
   └─> Simple query: get all tracks with global_ids
   └─> NO ID regeneration
   └─> NO name changes
```

### Key Data Structures

```python
# GLOBAL PERSON DATABASE (persists forever)
global_persons = {
    1: {
        'embedding': [0.12, 0.45, ...],
        'name': 'Alex',
        'track_mappings': [(7, 34), (8, 12)]  # Cameras 7 and 8
    },
    2: {
        'embedding': [0.89, 0.23, ...],
        'name': 'Blake',
        'track_mappings': [(9, 5)]
    }
}

# QUICK LOOKUP (for checking if track already has ID)
camera_track_to_global = {
    (7, 34): 1,  # Camera 7, Track 34 → Person 1 (Alex)
    (8, 12): 1,  # Camera 8, Track 12 → Person 1 (Alex) - SAME PERSON
    (9, 5): 2    # Camera 9, Track 5 → Person 2 (Blake)
}

# CAMERA TRACKS (current state, per camera)
camera_tracks = {
    7: {
        'tracks': {
            34: {
                'bbox': [100, 200, 300, 400],
                'confidence': 0.95,
                'global_id': 1,
                'name': 'Alex'
            }
        }
    }
}
```

### Comparison Example

**Scenario:** Person appears in Camera 7, then walks to Camera 8

#### ❌ Old Logic:
```
Frame 1: Camera 7 Track 34 → API call → global_id=1, name=Alex
Frame 2: Camera 7 Track 34 → API call → global_id=2, name=Blake (WRONG!)
Frame 3: Camera 8 Track 12 → API call → global_id=3, name=Casey (WRONG!)
Result: IDs 1, 2, 3 all for SAME person
```

#### ✅ New Logic:
```
Frame 1: Camera 7 Track 34 detected
  └─> 2 seconds later: embedding generated
      └─> No existing persons → Create global_id=1, name=Alex
      └─> Store: global_persons[1] = {embedding, 'Alex', [(7,34)]}

Frame 20: Same person still in Camera 7 Track 34
  └─> 2 seconds later: embedding generated
      └─> Track (7,34) already in camera_track_to_global → global_id=1
      └─> Update embedding, DONE (no new ID)

Frame 100: Person walks to Camera 8, appears as Track 12
  └─> 2 seconds later: embedding generated
      └─> NEW track (8,12), generate embedding
      └─> Compare against global_persons[1]
      └─> Similarity = 0.92 > threshold (0.75)
      └─> Assign existing global_id=1, name=Alex
      └─> Store: camera_track_to_global[(8,12)] = 1

Result: SAME global_id=1, name=Alex across both cameras ✅
```

## Why This Works

1. **Embeddings stored per person, not per track**
   - Can match new tracks against ALL known persons
   - Cross-camera deduplication works correctly

2. **Global IDs created once, persisted forever**
   - No regeneration in API calls
   - Stable IDs even when person moves between cameras

3. **Names assigned once with global_id**
   - Only changes on explicit user edit
   - No cycling through name pool

4. **Separation of concerns**
   - ByteTrack: Fast per-camera tracking
   - DeepSORT: Periodic ReID embeddings
   - API: Simple data query (no logic)

## Testing

### Expected Behavior:

1. **Single person in Camera 7:**
   - After 2 seconds: "✨ NEW person: Alex (ID: 1) on Camera 7 Track 34"
   - API returns: `{global_id: 1, name: "Alex", camera_id: 7}`
   - Next API call: SAME data (no regeneration)

2. **Same person moves to Camera 8:**
   - After 2 seconds: "👤 Camera 8 Track 12 → Existing person 1 (Alex) [sim=0.92]"
   - API returns: `{global_id: 1, name: "Alex", camera_id: 8}` (deduplicated)

3. **Second person enters Camera 7:**
   - After 2 seconds: "✨ NEW person: Blake (ID: 2) on Camera 7 Track 35"
   - API returns TWO people: Alex (ID 1), Blake (ID 2)

4. **User renames Alex to "John":**
   - POST `/vault-rooms/5/rename-person` with `{global_id: 1, name: "John"}`
   - All future API calls return "John" for person 1
   - Name persists forever (no regeneration)

## References

Based on industry-standard implementations:

- **deep_sort_realtime**: Track objects with embeddings for ReID
- **ByteTrack**: Fast motion-based tracking (30 FPS)
- **Multi-Camera Person Re-Identification**: Embedding similarity matching
- **CVAT**: Professional annotation tool patterns

## Summary

**Old system:** IDs/names regenerated every API call → unusable  
**New system:** IDs/names assigned once on detection → stable and editable

The key insight: **Don't create IDs in API endpoints. Create them when embeddings are generated, store them, and query them later.**
