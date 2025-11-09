# Tracking Visualization Debug Report - RAZZv4

## Issue
Tracking visualization (bounding boxes, IDs) not appearing on camera-viewer.html even though tracking service is running.

## Comparison: brinksv2 vs razzv4

### BRINKSv2 Implementation ✅
```python
# services/people_detection.py - draw_tracks() method
def draw_tracks(self, frame, camera_id):
    # Draws bounding boxes with track IDs
    # Color coding: Green=ByteTrack, Orange=DeepSORT
    # Shows global IDs and names
    # Clean minimal overlay
```

### RAZZv4 Implementation ✅
```python
# services/tracking_service.py - _annotate_frame() method  
def _annotate_frame(self, frame, tracks):
    # Draws bright green bounding boxes
    # Shows track IDs as "ID:X"
    # Includes trajectory trails
    # Stats overlay (top-left)
```

## Data Flow Analysis

### Flow Diagram
```
Camera RTSP Stream
    ↓
CameraProcessor._process_stream()
    ↓
yolo_service.detect_people(frame) → detections_list
    ↓
tracker.update(frame, detections) → (count, track_info, annotated_frame)
    ↓
self.last_annotated_frame = annotated_frame ← STORED HERE
    ↓
vault_rooms.py: get_camera_tracking_frame()
    ↓
processor.last_annotated_frame → encode to JPEG → base64
    ↓
Frontend: updateTrackingOverlay() → draws on canvas
```

## Current Status

### ✅ Working Components
1. **Tracking Service** - `TrackingService._annotate_frame()` properly draws boxes
2. **Storage** - `CameraProcessor.last_annotated_frame` stores the frame
3. **Route** - `/vault-rooms/{room_id}/camera/{camera_id}/tracking-frame` serves the frame
4. **Frontend** - JavaScript polls and draws the frame on canvas overlay

### 🔍 Potential Issues

#### Issue 1: Frame Skip Rate
```python
# camera_service.py line 44
self.frame_skip = 15  # Process every 15th frame (~2 FPS on 30 FPS stream)
```
**Impact**: Only 1 out of every 15 frames is processed
**Fix**: Reduce to 5 for ~6 FPS processing

#### Issue 2: Tracking Not Initialized
```python
# camera_service.py line 34
self.tracker = TrackingService(strategy="bytetrack") if use_tracking else None
```
**Check**: Verify `use_tracking=True` when starting cameras

#### Issue 3: No Detections
**Check**: YOLO detections might be empty (no people in view)
**Fix**: Add debug logging to verify detections

#### Issue 4: Canvas Overlay Not Visible
```html
<!-- camera-viewer.html line 116 -->
<canvas id="${videoId}-overlay" style="display:none;"></canvas>
```
**Issue**: Canvas starts hidden, toggled by button
**Fix**: Already handled by auto-enable after 2 seconds

## Debug Commands

### 1. Check if Camera Service is Running
```python
# In main.py or Python console
from main import camera_service
print(f"Active cameras: {list(camera_service.processors.keys())}")
for cam_id, proc in camera_service.processors.items():
    print(f"Camera {cam_id}: running={proc.is_running}, tracker={proc.tracker is not None}")
```

### 2. Check Last Annotated Frame
```python
processor = camera_service.processors.get(camera_id)
if processor.last_annotated_frame is not None:
    print(f"Frame shape: {processor.last_annotated_frame.shape}")
    print(f"Last update: {processor.last_update_time}")
else:
    print("No annotated frame available")
```

### 3. Check Tracking Stats
```python
if processor.tracker:
    stats = processor.tracker.get_statistics()
    print(f"Stats: {stats}")
```

### 4. Test Endpoint Directly
```bash
curl http://localhost:8000/vault-rooms/1/camera/101/tracking-frame
```

### 5. Frontend Console Logs
```javascript
// In browser console
console.log(trackingOverlayIntervals);
// Should show active intervals for each camera
```

## Recommended Fixes

### Fix 1: Reduce Frame Skip for Better Responsiveness
```python
# camera_service.py line 44
self.frame_skip = 5  # Changed from 15 to 5 (~6 FPS processing)
```

### Fix 2: Add Debug Logging
```python
# camera_service.py after line 136
if self.last_annotated_frame is not None:
    logger.info(f"Camera {self.camera_id}: Stored annotated frame {self.last_annotated_frame.shape}")
else:
    logger.warning(f"Camera {self.camera_id}: No annotated frame (tracker returned None)")
```

### Fix 3: Verify Detections Are Passed Correctly
```python
# camera_service.py line 129
logger.debug(f"Camera {self.camera_id}: {len(detections)} detections from YOLO")
```

### Fix 4: Add Fallback Visualization
If tracking fails, still show YOLO detections:
```python
# camera_service.py after line 139
else:
    # Fallback: annotate with YOLO only
    person_count, annotated = self.yolo_service.process_frame(frame, annotate=True)
    self.last_annotated_frame = annotated
```

## Testing Plan

### Test 1: Verify Frame Generation
1. Start camera service
2. Wait 5 seconds for frames to process
3. Check processor.last_annotated_frame is not None
4. Verify frame shape matches camera resolution

### Test 2: Verify Route Response
1. Open browser dev tools
2. Navigate to camera viewer
3. Check Network tab for `/tracking-frame` requests
4. Verify 200 OK responses with frame data

### Test 3: Verify Canvas Drawing
1. Open camera viewer
2. Check that canvas overlay is visible (display: block)
3. Verify canvas dimensions match video
4. Check console for "Received tracking frame" messages

### Test 4: Verify Tracking Visualization
1. Person walks in front of camera
2. Green bounding box should appear
3. Track ID label should be visible
4. Trajectory trail should follow movement

## Expected Output

### Successful Tracking Visualization
- ✅ Bright green bounding boxes around people
- ✅ "ID:1", "ID:2" labels above boxes
- ✅ Green trajectory trails showing movement
- ✅ Stats overlay: "Tracks: 2 | FPS: 6.3"
- ✅ Smooth updates every 500ms

### Console Logs (Success)
```
INFO: Camera 101: Stored annotated frame (1920, 1080, 3)
INFO: Camera 101: 2 people detected, 2 tracks active
DEBUG: Encoding tracking frame for camera 101, shape: (1920, 1080, 3)
```

### Frontend Console (Success)
```javascript
Received tracking frame for camera 101
Canvas dimensions: 1920x1080
Drawing tracking overlay...
```

## Implementation Differences Summary

| Feature | BRINKSv2 | RAZZv4 | Status |
|---------|----------|---------|--------|
| Tracking Algorithm | ByteTrack + DeepSORT | ByteTrack only | ✅ OK |
| Visualization Method | draw_tracks() | _annotate_frame() | ✅ OK |
| Frame Storage | camera_tracks dict | last_annotated_frame | ✅ OK |
| Serving Method | MJPEG stream | Base64 JSON | ✅ OK |
| Frontend Display | img src stream | Canvas overlay | ✅ OK |
| Update Rate | Continuous stream | 500ms polling | ✅ OK |
| Frame Skip | Per camera config | Fixed 15 frames | ⚠️ Can optimize |

## Conclusion

The implementation is **architecturally sound** and should work. Most likely issues:

1. **Frame skip rate too high** (15 frames = ~0.5 second delay)
2. **No people in camera view** (nothing to track)
3. **Tracker not initialized** (use_tracking=False somewhere)
4. **Canvas overlay not enabled** (but auto-enables after 2 seconds)

**Recommended immediate action**: Reduce frame_skip from 15 to 5 and add debug logging to verify frames are being annotated.
