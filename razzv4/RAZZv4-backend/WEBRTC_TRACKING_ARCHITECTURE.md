# WebRTC + WebSocket Tracking Architecture

## Overview
This implementation separates video streaming from tracking data to achieve maximum performance and low latency.

## Architecture Components

### 1. **WebRTC Video Stream (30 FPS)**
- **Purpose**: Raw camera feed at full 30 FPS
- **Source**: RTSPtoWebRTC server (port 8083)
- **Protocol**: WebRTC (peer-to-peer)
- **Latency**: Very low (~100-300ms)
- **Resolution**: 720p
- **Client**: HTML5 `<video>` element

### 2. **WebSocket Tracking Data (4-6 FPS)**
- **Purpose**: Bounding boxes, track IDs, confidence scores
- **Endpoint**: `ws://host/ws/tracking/{camera_id}`
- **Protocol**: WebSocket (JSON messages)
- **Update Rate**: 4-6 FPS (matches YOLO detection rate)
- **Data Format**:
```json
{
  "camera_id": 10,
  "timestamp": 1699545321.123,
  "tracks": [
    {
      "track_id": 1,
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.95,
      "center": [cx, cy],
      "source": "bytetrack"  // or "deepsort"
    }
  ],
  "stats": {
    "fps": 5.2,
    "active_tracks": 2,
    "frame_count": 1523
  }
}
```

### 3. **Canvas Overlay (30 FPS)**
- **Purpose**: Draw tracking boxes on top of WebRTC video
- **Technology**: HTML5 Canvas with requestAnimationFrame
- **Update Rate**: 30 FPS (smooth animation even with 4-6 FPS tracking data)
- **Drawing**: Bounding boxes, labels, confidence scores

## Data Flow

```
RTSP Camera (30 FPS)
    ↓
RTSPtoWebRTC Server (Go) ───────────→ Browser (WebRTC video @ 30 FPS)
    ↓                                        ↓
RAZZv4 Backend                         <video> element
    ↓                                        ↓
YOLO11 Detection (4-6 FPS)            Canvas overlay (30 FPS)
    ↓                                        ↑
ByteTrack + DeepSORT                        │
    ↓                                        │
WebSocket (tracking data @ 4-6 FPS) ────────┘
```

## Performance Characteristics

| Component | FPS | Latency | Bandwidth |
|-----------|-----|---------|-----------|
| WebRTC Video | 30 | ~200ms | ~2-3 Mbps |
| YOLO Detection | 4-6 | N/A | N/A |
| ByteTrack Update | 30 (every frame) | N/A | N/A |
| DeepSORT ReID | On demand | N/A | N/A |
| WebSocket Tracking | 4-6 | ~50ms | ~5 KB/s |
| Canvas Drawing | 30 | Instant | Local |

## Benefits

1. **Low Video Latency**: WebRTC provides near real-time video (~200ms vs 1-2s with MJPEG)
2. **Efficient Bandwidth**: Tracking data is JSON (tiny), video is compressed H.264
3. **Smooth Visualization**: Canvas draws at 30 FPS even when tracking updates at 4-6 FPS
4. **Separation of Concerns**: Video and AI processing are independent
5. **Scalability**: Multiple clients can connect to same WebRTC stream

## Implementation Details

### Backend (`main.py`)
- WebSocket endpoint: `/ws/tracking/{camera_id}`
- Sends tracking data at ~6 FPS (0.16s interval)
- Extracts bbox, confidence, track_id from `camera_processor.last_tracks`

### Camera Service (`camera_service.py`)
- Stores `last_tracks` dict with bbox, confidence, center, source
- Updates `fps` and `frame_count` for monitoring
- Runs YOLO + tracking at 4-6 FPS, stores results

### Frontend (`camera-viewer.html`)
- `initWebRTCWithTracking()`: Sets up WebRTC + WebSocket
- WebRTC connects to `http://127.0.0.1:8083/stream/receiver/{streamId}`
- WebSocket connects to `/ws/tracking/{camera_id}`
- `drawTrackingOverlay()`: Canvas animation loop at 30 FPS
- Scales bounding boxes to match video element size

## Color Coding

- **Green boxes**: ByteTrack (high confidence)
- **Cyan boxes**: DeepSORT (ReID fallback)

## Configuration

### RTSPtoWebRTC Server
- Must be running on port 8083
- Stream IDs: `camera{1,2,3,...}`

### RAZZv4 Backend
- Port 8003 (or configured)
- WebSocket endpoint auto-configured based on hostname

### Camera Setup
- RTSP streams must be accessible to both backend and RTSPtoWebRTC server
- 720p resolution recommended
- H.264 codec required for WebRTC

## Troubleshooting

### No video displayed
- Check RTSPtoWebRTC server is running: `pm2 list`
- Verify stream ID matches camera ID
- Check browser console for WebRTC errors

### No tracking boxes
- Check WebSocket connection in browser console
- Verify `/ws/tracking/{camera_id}` endpoint is accessible
- Check backend logs for tracking service errors

### Boxes not aligned with video
- Canvas auto-scales, but may need adjustment if video aspect ratio changes
- Check `videoElement.videoWidth` and `videoElement.videoHeight` in console

## Future Enhancements

1. **Dynamic Resolution**: Adjust based on network conditions
2. **Multi-camera sync**: Synchronize tracking across cameras
3. **Recording**: Save WebRTC stream with overlayed tracking
4. **Analytics**: Real-time dashboards with tracking statistics
