# Quick Fix Reference - Tracking Visualization

## Problem
Tracking bounding boxes and IDs not showing on camera viewer

## Root Cause Analysis
✅ Tracking service working correctly  
✅ Annotated frames being generated  
✅ API endpoint serving frames  
⚠️  Frame skip rate too high (15 = only 2 FPS)  
⚠️  Insufficient debug logging  

## Applied Fixes

### 1. Optimized Frame Rate
```python
# services/camera_service.py:44
self.frame_skip = 5  # Was: 15 (changed to 6 FPS from 2 FPS)
```

### 2. Added Debug Logging
```python
# services/camera_service.py:127-143
logger.debug(f"Camera {self.camera_id}: YOLO detected {len(detections)} people")
logger.debug(f"Camera {self.camera_id}: Stored annotated frame with {person_count} tracked people")
```

### 3. Enhanced Error Handling
```python
# routes/vault_rooms.py:463-466
if not processor.is_running:
    logger.warning(f"Camera {camera_id} processor exists but is not running")
    raise HTTPException(status_code=503, detail="Camera processor not running")
```

### 4. Improved Frontend Logging
```javascript
// templates/camera-viewer.html:377
console.log(`✅ Received tracking frame for camera ${cameraId} (${data.frame_size} bytes)`);
console.log(`Canvas ${videoId} sized to ${width}x${height}`);
```

## Testing

### Quick Test
```bash
cd /home/husain/alrazy/razzv4
python test_tracking_debug.py 1 101
```

### What to Look For
✅ "Frame appears to have tracking annotations"  
✅ Green pixels count > 1000  
✅ Saved JPG file has visible green boxes  

### Browser Console
✅ "📊 Enabled tracking overlay"  
✅ "✅ Received tracking frame"  
✅ "✅ Drew tracking frame on canvas"  

## Files Changed
- `services/camera_service.py` (frame rate + logging)
- `routes/vault_rooms.py` (error handling + logging)
- `templates/camera-viewer.html` (console messages)

## Documentation Added
- `DEBUG_TRACKING.md` (comprehensive debug guide)
- `TRACKING_FIX_SUMMARY.md` (this file's parent)
- `test_tracking_debug.py` (automated test script)

## Status: ✅ COMPLETE

All fixes applied. System ready for testing.
