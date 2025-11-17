# Primary Camera System

## Overview
Implemented a **primary camera system** where Camera 10 is designated as the "main" camera that assigns Global IDs to all persons. All other cameras are "support cameras" that can only match against persons already detected by the primary camera.

## Architecture

### Camera Roles

1. **Primary Camera (Camera 10)**
   - **Assigns all Global IDs**
   - Extracts all features (dimensions, colors, embeddings)
   - Source of truth for person identities
   - Every person MUST be seen by primary camera first

2. **Support Cameras (All Others)**
   - **Cannot create new persons**
   - Only match against persons from primary camera
   - Use multi-layer matching (Spatial → Dimension → Color → Re-ID)
   - Wait for primary camera to detect person first

## Workflow

### Primary Camera (Camera 10)

```
Person detected on Camera 10
         ↓
Check if already mapped? → YES → Update existing person
         ↓ NO
Create NEW Global ID
         ↓
Extract features:
  - Dimensions (height × width)
  - Clothing color histogram
  - Skin tone
  - Re-ID embedding (OSNet)
         ↓
Store in memory + database
```

### Support Cameras (Camera 11, 12, etc.)

```
Person detected on Camera 11
         ↓
Check if already mapped? → YES → Update existing person
         ↓ NO
Get primary camera persons
         ↓
Try matching:
  1. Spatial (overlapping views)
  2. Dimension (physical size)
  3. Color (clothing + skin)
  4. Re-ID (OSNet embeddings)
         ↓
Match found? → YES → Assign existing Global ID
         ↓ NO
Return None (wait for primary camera)
```

## Implementation Details

### Initialization

```python
tracker = GlobalPersonTracker(primary_camera_id=10)

# Logs:
# ✅ Global person tracker initialized
#    Primary camera: 10 (assigns IDs)
#    Support cameras: All others (match against primary)
```

### Matching Logic

```python
def match_or_create_person(self, camera_id, ...):
    # Check if already mapped
    if track_already_mapped:
        return existing_global_id
    
    # PRIMARY CAMERA: Always create
    if camera_id == PRIMARY_CAMERA_ID:
        return create_new_person()
    
    # SUPPORT CAMERA: Match only
    primary_persons = filter_by_primary_camera()
    
    if not primary_persons:
        return None  # Wait for primary
    
    # Try multi-layer matching
    match = try_spatial_match(primary_persons)
    if match: return match
    
    match = try_dimension_match(primary_persons)
    if match: return match
    
    match = try_color_match(primary_persons)
    if match: return match
    
    match = try_reid_match(primary_persons)
    if match: return match
    
    return None  # No match, wait for primary
```

### Primary-Only Matching Functions

Created specialized matching functions that only search within primary camera persons:

1. **`_find_best_spatial_match_from_primary()`**
   - Searches only persons from primary camera
   - IoU-based overlap detection

2. **`_find_best_dimension_match_from_primary()`**
   - Matches physical dimensions
   - 80% similarity threshold

3. **`_find_best_color_match_from_primary()`**
   - Matches clothing color + skin tone
   - 70% similarity threshold

4. **`_find_best_face_match_from_primary()`**
   - Matches Re-ID embeddings (OSNet)
   - 50% similarity threshold

## Benefits

### 1. **Single Source of Truth**
- Camera 10 is authoritative for all IDs
- No ID conflicts between cameras
- Consistent numbering across the system

### 2. **Reduced False Positives**
- Support cameras can't create duplicate IDs
- All persons validated by primary camera first

### 3. **Controlled ID Assignment**
- Primary camera in optimal location (entrance, main view)
- Better quality feature extraction from primary
- Support cameras supplement with additional views

### 4. **Simplified Debugging**
- All IDs originate from one camera
- Easy to trace person first appearance
- Clear camera hierarchy

## Configuration

### Change Primary Camera

```python
# Set Camera 12 as primary instead
tracker = GlobalPersonTracker(primary_camera_id=12)
```

### Disable Primary System

To revert to old behavior (any camera can create IDs):
```python
# Set primary_camera_id to None or -1
# Then modify logic to allow all cameras to create
```

## Logging

### Primary Camera Logs

```
🎯 PRIMARY Camera 10: New person Global ID 5 (track 123)
```

### Support Camera Logs

```
📡 Support Camera 11: Searching for match against primary camera persons...
📊 Support Camera 11: Found 3 persons from primary camera (out of 5 total)
✅ Support Camera 11: Dimension match → Global ID 5 (track 456)
```

```
⚠️  Support Camera 11: No persons from primary camera yet!
⚠️  Support Camera 11: No match found for track 789 (waiting for primary camera)
```

## Use Cases

### Scenario 1: Person Enters Through Primary Camera

```
1. Person walks into Camera 10 view
   → Primary camera creates Global ID 1
   → Extracts all features

2. Person moves to Camera 11 view
   → Support camera matches dimensions/color
   → Assigns existing Global ID 1
   → Person tracked across cameras

Result: ✅ Single consistent ID
```

### Scenario 2: Person Enters Through Support Camera

```
1. Person walks into Camera 11 view
   → Support camera tries matching
   → No primary camera persons yet
   → Returns None

2. Person moves to Camera 10 view
   → Primary camera creates Global ID 1
   → Extracts all features

3. Person returns to Camera 11
   → Support camera matches successfully
   → Assigns Global ID 1

Result: ✅ Eventually consistent
```

### Scenario 3: Person Only Visible on Support Camera

```
1. Person only visible on Camera 11
   → Support camera cannot create ID
   → Person not tracked

Workaround: Ensure primary camera has good coverage,
or use multiple primary cameras in different zones
```

## Best Practices

### 1. **Primary Camera Placement**
- Place at main entrance/exit
- Maximize coverage of person entry points
- Ensure good lighting and angle

### 2. **Support Camera Tuning**
- Adjust matching thresholds if too strict
- Monitor "No match" warnings
- Ensure overlap with primary camera view

### 3. **Multi-Zone Systems**
- For large areas, consider multiple primary cameras
- Each zone has its own primary camera
- Implement zone-based matching

### 4. **Fallback Strategy**
- If primary camera fails, promote support camera
- Implement automatic failover
- Log primary camera downtime

## Performance

### Matching Speed

| Layer | Primary Camera | Support Camera |
|-------|---------------|----------------|
| Track lookup | ~0.01ms | ~0.01ms |
| Spatial | N/A | ~0.5ms |
| Dimension | N/A | ~0.1ms |
| Color | ~5ms | ~5ms |
| Re-ID | ~10ms | ~10ms |
| **Total** | ~15ms | ~15ms |

### Memory Usage

- Primary camera persons only: Minimal overhead
- Filtering is O(n) where n = total persons
- Typically < 100 persons active at once

## Limitations

### 1. **Primary Camera Dependency**
- System cannot function if primary camera fails
- Support cameras become useless without primary
- **Mitigation**: Monitor primary camera health

### 2. **Entry Point Coverage**
- Persons not seen by primary are invisible
- Creates "blind spots" in support cameras
- **Mitigation**: Ensure primary covers all entries

### 3. **Temporal Delays**
- Person must reach primary camera first
- Brief period where support cameras can't match
- **Mitigation**: Acceptable for most use cases

### 4. **Single Point of ID Assignment**
- Primary camera becomes bottleneck
- High traffic may overwhelm primary
- **Mitigation**: Use high-performance primary camera

## Future Enhancements

### 1. **Multiple Primary Cameras**
```python
PRIMARY_CAMERA_IDS = [10, 12, 14]  # Multiple primaries
# Each can create IDs independently
# Need conflict resolution between primaries
```

### 2. **Primary Camera Failover**
```python
if primary_camera_down:
    promote_support_to_primary(camera_11)
    log_failover_event()
```

### 3. **Zone-Based System**
```python
ZONES = {
    'entrance': {'primary': 10, 'support': [11, 12]},
    'lobby': {'primary': 13, 'support': [14, 15]},
    'exit': {'primary': 16, 'support': [17]}
}
```

### 4. **Confidence-Based Creation**
```python
# Allow support camera to create if very confident
if matching_confidence > 0.95:
    allow_support_creation = True
```

## Testing

### Unit Test Example

```python
def test_primary_camera_system():
    tracker = GlobalPersonTracker(primary_camera_id=10)
    
    # Primary creates
    id1 = tracker.match_or_create_person(
        camera_id=10,
        local_track_id=1,
        bbox=(100, 100, 200, 400)
    )
    assert id1 is not None
    
    # Support matches
    id2 = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=1,
        bbox=(105, 105, 205, 405)  # Similar
    )
    assert id2 == id1  # Same person
    
    # Support cannot create
    id3 = tracker.match_or_create_person(
        camera_id=11,
        local_track_id=2,
        bbox=(500, 100, 600, 400)  # Different
    )
    assert id3 is None  # No match, waits for primary
```

### Integration Test

```bash
# Start system with Camera 10 as primary
python3 main.py

# Monitor logs
tail -f logs/tracking.log | grep -E "(PRIMARY|Support)"

# Expected output:
# 🎯 PRIMARY Camera 10: New person Global ID 1
# 📡 Support Camera 11: Searching for match...
# ✅ Support Camera 11: Dimension match → Global ID 1
```

## Troubleshooting

### Issue: Support camera not matching

**Symptoms**: `⚠️  No match found (waiting for primary camera)`

**Causes**:
1. Thresholds too strict
2. Primary camera features not extracted yet
3. Person appearance changed between cameras

**Solutions**:
1. Lower matching thresholds (dimension: 0.80 → 0.70)
2. Wait for embeddings to extract (3+ frames)
3. Check lighting differences between cameras

### Issue: No persons from primary camera

**Symptoms**: `⚠️  No persons from primary camera yet!`

**Causes**:
1. Primary camera not detecting anyone
2. Primary camera offline
3. Wrong primary_camera_id configured

**Solutions**:
1. Check primary camera feed
2. Verify YOLO detection on primary
3. Confirm `PRIMARY_CAMERA_ID = 10` is correct

### Issue: Wrong camera set as primary

**Symptoms**: All IDs from wrong camera

**Solution**:
```python
tracker = GlobalPersonTracker(primary_camera_id=10)  # Change this
```

## Summary

The primary camera system creates a **hierarchical architecture** where:
- **Camera 10 = Boss** (assigns all IDs)
- **Other cameras = Workers** (match against boss's persons)

This ensures **consistent IDs** and **single source of truth** for person identities across the entire multi-camera system.

---

**Status**: ✅ Implemented  
**Primary Camera**: Camera 10 (configurable)  
**Version**: 1.0  
**Date**: November 10, 2025
