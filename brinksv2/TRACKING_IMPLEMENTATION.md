# ByteTrack + DeepSORT ReID Implementation

## Architecture Overview

### Dual-Tracking System
- **ByteTrack**: Primary tracker running at 30 FPS for real-time tracking
- **DeepSORT ReID**: Fallback tracker for uncertain or lost tracks

## Implementation Details

### 1. ByteTrack Configuration (30 FPS)
```python
sv.ByteTrack(
    track_activation_threshold=0.5,  # Higher threshold for activation
    lost_track_buffer=30,            # Keep lost tracks for 1 second (30 frames)
    minimum_matching_threshold=0.8,  # High matching threshold
    frame_rate=30                    # 30 FPS processing
)
```

### 2. DeepSORT ReID Configuration
```python
DeepSort(
    max_age=30,                      # Maximum frames to keep lost tracks
    n_init=3,                        # Min consecutive detections for track init
    nms_max_overlap=0.7,            # Non-max suppression overlap threshold
    max_cosine_distance=0.3,        # Max cosine distance for ReID matching
    nn_budget=100,                  # Max size of appearance descriptor gallery
    embedder="mobilenet",           # Use MobileNet for ReID embeddings
)
```

### 3. Tracking Logic Flow

```
Frame Input (30 FPS)
    ↓
YOLO11m Detection (Person Class Only)
    ↓
ByteTrack Primary Tracking
    ↓
Check Confidence Threshold (0.6)
    ├─ High Confidence → Use ByteTrack Result
    └─ Low Confidence → Apply DeepSORT ReID
        ↓
    Re-identification with MobileNet embeddings
        ↓
    Confirmed Track → Use DeepSORT Result
```

### 4. Track ID System
- **Positive IDs (1, 2, 3...)**: ByteTrack confident tracks
- **Negative IDs (-1, -2, -3...)**: DeepSORT ReID tracks

## Performance Metrics

### Current Status
- **Processing Speed**: 30 FPS per camera
- **Cameras**: 4 simultaneous streams
- **Memory Usage**: ~1.3 GB (with 4 cameras)
- **CPU**: Moderate usage (depends on hardware)

### Detection Results
```json
{
  "camera_id": 2,
  "camera_name": "Store",
  "current_count": 1,
  "average_count": 1.0,
  "active_tracks": 1,
  "last_update": "2025-11-06T02:45:20.970767"
}
```

## Key Features

### 1. Real-Time Tracking
- ByteTrack processes every frame at 30 FPS
- Low latency (~33ms per frame)
- Smooth track continuity

### 2. Intelligent Fallback
- DeepSORT activates when ByteTrack confidence < 0.6
- Re-identification using appearance features
- Handles occlusions and track losses

### 3. Automatic Reconnection
- Auto-reconnect on RTSP stream failure
- Minimal buffer (1 frame) for low latency
- Graceful error handling

### 4. Statistics Logging
Every 10 seconds (300 frames):
```
📊 Camera 2: 1 people | ByteTrack: 250 | DeepSORT: 50
```

## Configuration Parameters

### Adjustable Settings

#### Detection Confidence
```python
conf_threshold=0.5  # YOLO detection threshold
```

#### ByteTrack Confidence
```python
bytetrack_threshold=0.6  # Threshold for ByteTrack certainty
```

#### Processing FPS
```python
process_fps=30  # Frame rate for tracking
```

## Usage

### API Endpoints

#### Get Live Statistics
```bash
GET /detections/live
```

Response includes:
- `current_count`: People count right now
- `average_count`: Average over last 100 frames
- `active_tracks`: Number of tracked individuals
- `last_update`: Timestamp of last update

#### Get Historical Data
```bash
GET /detections/history?camera_id=1&hours=24
```

### Dashboard
Access at: `http://127.0.0.1:8001/dashboard`

Features:
- Live WebRTC video streams
- Real-time people counts
- Auto-refresh every 5 seconds
- Track statistics per camera

## Technical Stack

- **YOLO11m**: Object detection (people only)
- **Supervision**: ByteTrack wrapper
- **DeepSORT Realtime**: ReID implementation
- **OpenCV**: Video stream processing
- **FastAPI**: REST API backend
- **PostgreSQL**: Statistics storage

## Advantages of This Approach

### 1. Speed + Accuracy Balance
- ByteTrack: Fast tracking without appearance features
- DeepSORT: Accurate ReID when needed

### 2. Resource Efficiency
- DeepSORT only runs on uncertain tracks (~20-30% of frames)
- Reduced computational overhead
- Better than running DeepSORT on every frame

### 3. Robustness
- Handles occlusions (DeepSORT)
- Maintains tracks through brief losses (ByteTrack buffer)
- Re-identifies people after long occlusions (DeepSORT embeddings)

## Monitoring

### Check Service Status
```bash
pm2 status brinks-v2
```

### View Logs
```bash
pm2 logs brinks-v2
```

### Test Detection
```bash
curl http://127.0.0.1:8001/detections/live
```

## Troubleshooting

### High CPU Usage
- Reduce `process_fps` (e.g., from 30 to 15)
- Use smaller YOLO model (yolo11s or yolo11n)
- Reduce number of cameras

### Missed Detections
- Lower `conf_threshold` (e.g., from 0.5 to 0.4)
- Lower `bytetrack_threshold` (more DeepSORT usage)

### Track Switching
- Increase `minimum_matching_threshold` in ByteTrack
- Decrease `max_cosine_distance` in DeepSORT

## Future Enhancements

1. **GPU Acceleration**: Use CUDA for YOLO inference
2. **Multi-Threading**: Separate threads for detection and tracking
3. **Adaptive FPS**: Adjust based on scene complexity
4. **Track Analytics**: Heatmaps, paths, dwell time
5. **Alerts**: Crowd detection, loitering detection
