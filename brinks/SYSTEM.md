# SafeRoom Detection System

A complete real-time occupancy detection and monitoring system using YOLOv8 + ByteTrack for room safety enforcement.

## System Architecture

```
┌──────────────────┐
│  Cameras (RTSP)  │
└────────┬─────────┘
         │ Frames (JPEG)
         ↓
┌──────────────────────────┐
│  Frame Ingestion Client  │
│  (ingest_frames.py)      │
└────────┬─────────────────┘
         │ HTTP POST /ingest
         ↓
┌──────────────────────────────────┐
│  FastAPI Backend                 │
│  - YOLOv8 Detection              │
│  - ByteTrack Tracking            │
│  - Violation Detection           │
│  - WebSocket Broadcasting        │
└────────┬──────────────────────────┘
         │ 
    ┌────┴─────┐
    ↓          ↓
┌─────────┐  ┌──────────────┐
│  Redis  │  │  WebSocket   │
│ (State) │  │  (Clients)   │
└─────────┘  └──────┬───────┘
                    ↓
            ┌──────────────────┐
            │  Web Dashboard   │
            │  (Real-time View)│
            └──────────────────┘
```

## Features

✅ **Real-time Detection**: YOLOv8 person detection at multiple FPS rates  
✅ **Persistent Tracking**: ByteTrack for consistent ID assignment  
✅ **Violation Alerts**: Immediate alert when occupancy exceeds limit  
✅ **Live Dashboard**: Real-time web interface with camera feed and alerts  
✅ **WebSocket Broadcasting**: Instant updates to all connected clients  
✅ **Redis State Store**: Fast in-memory occupancy tracking  
✅ **Event Logging**: Complete audit trail of all violations  
✅ **Docker Ready**: Complete Docker Compose setup  
✅ **Webhook Actions**: POST violations to external services  

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

**Note**: PyTorch needs to be installed separately. Install from: https://pytorch.org/get-started/locally/

### 2. Start Redis

```bash
# Option A: Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Option B: Using Docker Compose
docker-compose up -d redis
```

### 3. Start the Backend

```bash
# Development mode (with hot reload)
python -m uvicorn backend.main:app --reload

# Production mode
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The backend will start at `http://localhost:8000`

### 4. Start Frame Ingestion

In a new terminal:

```bash
# Ingest from live camera (Room1)
python ingest_frames.py --camera room1 --fps 5

# Ingest from video file
python ingest_frames.py --video /path/to/video.mp4 --fps 10

# Custom settings
python ingest_frames.py --backend http://localhost:8000 --camera room1 --fps 3 --room room_safe
```

### 5. Open Dashboard

Open your browser to: **http://localhost:8000**

## Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Room Settings
ROOM_ID=room_safe
MAX_OCCUPANCY=1
VIOLATION_THRESHOLD=2

# YOLO Model
# Options: yolov8n.pt (fast, ~6GB/s), yolov8s.pt, yolov8m.pt, yolov8l.pt
YOLO_MODEL=yolov8n.pt

# Webhook for violations
VIOLATION_WEBHOOK=https://your-service.com/webhook
```

### Performance Tuning

**For CPU-only systems:**
- Use `yolov8n.pt` (nano model)
- Reduce FPS: `--fps 3`
- Lower resolution: resize frames before sending

**For GPU systems:**
- Use `yolov8m.pt` or `yolov8l.pt` for better accuracy
- Increase FPS: `--fps 15`

## API Reference

### Endpoints

#### POST /ingest
Send a frame for detection and tracking

```bash
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@frame.jpg" \
  -G -d "camera_id=room1" \
  -G -d "room_id=room_safe"
```

Response:
```json
{
  "ok": true,
  "occupancy": 1,
  "objects": [1, 2],
  "count_boxes": 2,
  "status": "ok"
}
```

#### WebSocket /ws
Real-time connection for dashboard updates

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle: frame, violation, init, echo
};
```

#### GET /status
Get current room status

```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "room_id": "room_safe",
  "state": {
    "occupancy": "1",
    "last_update": "1234567890.123"
  },
  "recent_events": [...]
}
```

#### GET /health
Health check

```bash
curl http://localhost:8000/health
```

#### POST /clear_violations
Clear violation log

```bash
curl -X POST http://localhost:8000/clear_violations
```

## Dashboard Features

### Real-time Monitoring
- Live camera feed with detection boxes
- Tracker IDs for each person
- Current occupancy count
- System status indicator

### Alerts
- Immediate violation notifications
- Visual and textual alerts
- Timestamp logging

### Event Log
- Complete history of all events
- Violation timestamps
- Person count for each event

## Webhook Integration

When a violation occurs, the system can POST to a configured webhook:

```bash
export VIOLATION_WEBHOOK="https://your-service.com/api/alerts"
```

Webhook payload:
```json
{
  "type": "violation",
  "timestamp": "2025-11-05T14:30:00Z",
  "occupants": [1, 2],
  "count": 2,
  "room_id": "room_safe"
}
```

## Camera Integration

### RTSP Cameras
The system connects to cameras via RTSP. Example URLs from your system:

```
rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/102  # Room1 Sub-stream
rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/202  # Room2 Sub-stream
rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/302  # Room3 Sub-stream
rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/402  # Room4 Sub-stream
```

### Adding More Cameras

1. Add camera URLs to `camera_system.py`:
```python
'room5': {
    'name': 'Room5',
    'main_stream': 'rtsp://...',
    'sub_stream': 'rtsp://...',
}
```

2. Create separate ingest processes for each camera:
```bash
python ingest_frames.py --camera room1 --fps 5 &
python ingest_frames.py --camera room2 --fps 5 &
python ingest_frames.py --camera room3 --fps 5 &
```

## Deployment

### Development
```bash
python -m uvicorn backend.main:app --reload
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```bash
docker-compose up -d
```

### Kubernetes
Create deployment manifests for production Kubernetes clusters.

## Troubleshooting

### Backend won't start
```bash
# Check Redis connection
redis-cli ping

# Check port is available
lsof -i :8000
```

### YOLO model not loading
```bash
# Download model manually
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Or use CPU-only:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### No detections from camera
1. Check camera is accessible: `curl rtsp://admin:pass@ip:554/...`
2. Verify frame ingestion: check server logs
3. Adjust YOLO threshold if needed

### High latency/low FPS
- Reduce `--fps` flag
- Use smaller YOLO model (yolov8n)
- Lower frame resolution
- Use GPU instead of CPU

## File Structure

```
brinks/
├── backend/
│   ├── __init__.py
│   └── main.py                 # FastAPI application
├── dashboard/
│   └── index.html              # Web dashboard
├── camera_system.py            # Camera management
├── ingest_frames.py            # Frame ingestion client
├── test_cameras.py             # Camera connection test
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose setup
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Performance Metrics

Typical performance on CPU (Intel i7):

| Model | FPS | Memory | Detection |
|-------|-----|--------|-----------|
| yolov8n | 5-8 | 400MB | ✓ Good |
| yolov8s | 2-4 | 600MB | ✓✓ Better |
| yolov8m | 1-2 | 800MB | ✓✓✓ Best |

With GPU (NVIDIA RTX 3060):

| Model | FPS | Memory | Detection |
|-------|-----|--------|-----------|
| yolov8n | 30+ | 800MB | ✓ Good |
| yolov8s | 25+ | 1.2GB | ✓✓ Better |
| yolov8m | 15+ | 1.8GB | ✓✓✓ Best |

## Security Considerations

For production deployment:

1. **Enable HTTPS**: Use nginx reverse proxy with SSL
2. **Authentication**: Add JWT tokens to `/ingest` and `/ws`
3. **Rate Limiting**: Limit frames per camera per second
4. **CORS**: Restrict to known domains
5. **Secrets**: Use environment variables for credentials
6. **Logging**: Monitor access logs for anomalies

## Contributing

To extend the system:

1. **Custom Detection Model**: Replace YOLOv8 with your model in `backend/main.py`
2. **Tracking Algorithms**: Swap ByteTrack with DeepSORT or other tracker
3. **Action Handlers**: Add custom violation handlers beyond webhooks
4. **Storage**: Connect to PostgreSQL/MongoDB for audit logging
5. **Scaling**: Deploy multiple instances with load balancing

## License

Private project for security monitoring.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check backend logs: `docker-compose logs api`
4. Test camera connection: `python test_cameras.py`