# Services Module

This module contains the AI and business logic services for RAZZv4.

## Architecture

### YOLOService (`yolo_service.py`)
Handles YOLO11 model initialization and person detection.

**Features:**
- Uses Ultralytics YOLO11 (latest version)
- Configurable model size (nano, small, medium, large, extra-large)
- Person detection with confidence thresholding
- Frame annotation capabilities
- Optimized for real-time processing

**Models Available:**
- `yolo11n.pt` - Nano (fastest, lowest accuracy) - **Default**
- `yolo11s.pt` - Small
- `yolo11m.pt` - Medium
- `yolo11l.pt` - Large
- `yolo11x.pt` - Extra Large (slowest, highest accuracy)

### CameraService (`camera_service.py`)
Manages RTSP camera streams and coordinates people counting.

**Features:**
- Multi-threaded camera processing
- Automatic reconnection on stream failure
- Frame skipping for performance optimization (processes ~2 FPS)
- Real-time database updates
- Aggregates counts across multiple cameras per vault room

**Architecture:**
- `CameraProcessor`: Handles individual camera streams in separate threads
- `CameraService`: Manages multiple camera processors
- Automatic startup of all active cameras on application start

## Usage

### Starting the Services

Services are automatically started when the FastAPI application launches:

```python
# In main.py
yolo_service = YOLOService(model_name="yolo11n.pt", confidence_threshold=0.5)
camera_service = CameraService(yolo_service, SessionLocal)
camera_service.start_all_cameras()
```

### API Endpoints

**Get People Count for a Room:**
```
GET /vault-rooms/{room_id}/people-count
```

Response:
```json
{
  "room_id": 1,
  "room_name": "Main Vault",
  "total_people_count": 3,
  "cameras": [
    {
      "camera_id": 1,
      "camera_name": "Entrance Camera",
      "people_count": 2
    },
    {
      "camera_id": 2,
      "camera_name": "Interior Camera",
      "people_count": 1
    }
  ]
}
```

**Get People Counts for All Rooms:**
```
GET /vault-rooms/all/people-counts
```

**Check Service Status:**
```
GET /api/services/status
```

## Performance Considerations

### Frame Processing
- Default: Processes every 15th frame (~2 FPS on 30 FPS streams)
- Adjustable via `frame_skip` parameter in `CameraProcessor`
- Balance between accuracy and CPU usage

### Model Selection
- **Production**: Use `yolo11n.pt` (nano) for multiple cameras
- **High Accuracy**: Use `yolo11m.pt` or `yolo11l.pt` for critical areas
- **Testing**: Use `yolo11s.pt` (small) for balance

### Resource Usage
- Each camera runs in a separate thread
- YOLO model shared across all cameras (memory efficient)
- GPU acceleration automatic if CUDA available
- CPU fallback available

## Configuration

### Environment Variables
No additional environment variables required. Configuration is done via code.

### Adjusting Performance

**Reduce CPU Usage:**
```python
# In camera_service.py, increase frame_skip
self.frame_skip = 30  # Process every 30th frame (~1 FPS)
```

**Increase Accuracy:**
```python
# In main.py, use larger model
yolo_service = YOLOService(model_name="yolo11m.pt", confidence_threshold=0.5)
```

**Adjust Confidence Threshold:**
```python
yolo_service = YOLOService(model_name="yolo11n.pt", confidence_threshold=0.6)  # More strict
```

## Database Integration

### Models Updated
- `Camera.current_people_count` - People detected by this camera
- `VaultRoom.current_people_count` - Aggregated count from all cameras

### Update Frequency
- Database updated only when count changes
- Reduces database load
- Real-time accuracy maintained

## Troubleshooting

### Camera Connection Issues
- Check RTSP URL format: `rtsp://username:password@ip:port/path`
- Verify network connectivity to cameras
- Check camera authentication credentials
- Review logs for connection errors

### Low Detection Accuracy
- Increase confidence threshold
- Use larger YOLO model
- Ensure good lighting conditions
- Check camera angle and field of view

### High CPU Usage
- Increase `frame_skip` value
- Use smaller YOLO model (nano)
- Reduce number of active cameras
- Enable GPU acceleration

## Logging

All services use Python logging:
```python
import logging
logger = logging.getLogger(__name__)
```

Log levels:
- INFO: Service initialization, camera start/stop, count updates
- DEBUG: Frame processing details, detection counts
- WARNING: Connection failures, retries
- ERROR: Critical errors, exceptions

## Future Enhancements

- [ ] Person tracking across frames (reduce false positives)
- [ ] Historical people count data storage
- [ ] Alert system for unusual activity
- [ ] Zone-based counting (specific areas in room)
- [ ] Person re-identification across cameras
- [ ] Heat maps of movement patterns
