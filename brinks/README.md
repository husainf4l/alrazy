# Brinks Camera System

A complete real-time occupancy detection and monitoring system for room safety enforcement.

## 📋 What's Included

- **Camera Management** (`camera_system.py`) - Connect and manage multiple RTSP cameras
- **SafeRoom Detection Backend** (`backend/main.py`) - FastAPI + YOLOv8 + ByteTrack for real-time detection
- **Real-time Dashboard** (`dashboard/index.html`) - Live monitoring with WebSocket updates
- **Frame Ingestion** (`ingest_frames.py`) - Send camera frames to detection backend
- **Docker Setup** - Complete containerization for easy deployment

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Test Cameras

```bash
python test_cameras.py
```

### 3. Start the System

**Terminal 1: Redis**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**Terminal 2: Backend API**
```bash
python -m uvicorn backend.main:app --reload
```

**Terminal 3: Frame Ingestion**
```bash
python ingest_frames.py --camera room1 --fps 5
```

**Terminal 4: Open Dashboard**
Open browser to: **http://localhost:8000**

## 📁 Project Structure

```
brinks/
├── backend/
│   ├── __init__.py
│   └── main.py                    # FastAPI detection backend
├── dashboard/
│   └── index.html                 # Real-time web dashboard
├── camera_system.py               # Camera management (Room1-4)
├── ingest_frames.py               # Frame ingestion client
├── test_cameras.py                # Connection testing
├── requirements.txt               # Dependencies
├── Dockerfile                     # Container image
├── docker-compose.yml             # Full stack setup
├── notes.md                       # Camera URLs and config
├── README.md                      # This file (basic overview)
└── SYSTEM.md                      # Complete system documentation
```

## 📊 System Architecture

```
Cameras → Frame Ingestion → FastAPI Backend → Redis
                              ↓
                        YOLOv8 Detection
                        ByteTrack Tracking
                        Violation Detection
                              ↓
                     WebSocket Broadcasting
                              ↓
                        Real-time Dashboard
```

## 🎯 System Features

✅ 4 cameras configured (Room1, Room2, Room3, Room4)  
✅ Real-time person detection (YOLOv8)  
✅ Persistent tracking (ByteTrack)  
✅ Occupancy monitoring  
✅ Violation alerts (when >1 person)  
✅ Live camera feed with annotated detections  
✅ WebSocket real-time updates  
✅ Event logging and history  

## 📖 Documentation

- **Basic Setup** (this file) - Quick start guide
- **Complete System Guide** (`SYSTEM.md`) - Full documentation, API reference, deployment
- **Camera Config** (`notes.md`) - Camera URLs and credentials
- **Camera Library** (`camera_system.py`) - Camera management API

## 🔧 Available Commands

```bash
# Test camera connections
python test_cameras.py

# Start backend (requires Redis)
python -m uvicorn backend.main:app --reload

# Ingest frames from camera
python ingest_frames.py --camera room1 --fps 5

# Ingest from video file
python ingest_frames.py --video /path/to/video.mp4 --fps 10

# Start full stack with Docker
docker-compose up -d

# View API documentation
# Open: http://localhost:8000/docs

# Check backend status
curl http://localhost:8000/health
```

## 🎯 Configuration

Edit `.env` file to customize:

```
ROOM_ID=room_safe
MAX_OCCUPANCY=1
VIOLATION_THRESHOLD=2
YOLO_MODEL=yolov8n.pt
REDIS_URL=redis://localhost:6379/0
```

## 📱 Dashboard Features

- **Live Feed**: Real-time camera stream with detection boxes
- **Occupancy Display**: Current person count with color alerts
- **Tracker IDs**: Unique ID for each tracked person
- **Alerts**: Instant violation notifications
- **Event Log**: Complete history of all events
- **System Status**: Connection and operational status

## 🐳 Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 🔍 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/ingest` | Send frame for detection |
| WS | `/ws` | WebSocket for real-time updates |
| GET | `/status` | Get current room status |
| GET | `/health` | Health check |
| POST | `/clear_violations` | Clear event log |
| GET | `/docs` | API documentation (Swagger) |

## 📊 Camera Configurations

All cameras are on: **192.168.1.186**

| Camera | Location | Main Stream | Sub-stream |
|--------|----------|---|---|
| 1 | Room1 | Ch. 101 | Ch. 102 ✓ |
| 2 | Room2 | Ch. 201 | Ch. 202 ✓ |
| 3 | Room3 | Ch. 301 | Ch. 302 ✓ |
| 4 | Room4 | Ch. 401 | Ch. 402 ✓ |

✓ Currently using sub-streams for better performance

## 🚨 Violation Detection

- **Rule**: Room occupancy should not exceed 1 person
- **Alert**: Instant violation when >1 person detected
- **Actions**:
  - Visual alert on dashboard
  - Event logged in Redis
  - Optional webhook trigger
  - Timestamp recorded

## 🌐 Web Dashboard

The dashboard provides real-time monitoring:

1. **Live Feed** - Current camera view with bounding boxes
2. **Occupancy Counter** - Red alert if violated
3. **Tracker Information** - Active person IDs
4. **System Status** - Backend and connection status
5. **Event Log** - Recent violations and system events

## 🔐 Security Notes

For production:
- Use HTTPS with reverse proxy (nginx)
- Add JWT authentication to endpoints
- Implement rate limiting
- Use secure credentials storage
- Enable CORS restrictions

## 📚 Next Steps

1. **Customize**: Modify `MAX_OCCUPANCY`, `VIOLATION_THRESHOLD`
2. **Extend**: Add more cameras via `ingest_frames.py`
3. **Integrate**: POST violations to your backend service
4. **Monitor**: Set up logging and monitoring
5. **Deploy**: Use Docker for production

## 📖 Detailed Documentation

For comprehensive documentation including:
- Performance tuning
- Deployment strategies
- Webhook integration
- Custom models
- Troubleshooting

See **[SYSTEM.md](./SYSTEM.md)**

## 🎓 Example Usage

```python
# Using the camera system directly
from camera_system import CameraSystem

system = CameraSystem()
system.initialize_cameras()
system.test_all_connections()  # Test all cameras
system.start_system()
system.display_live_feed()  # Show all cameras

# Using the ingestion client
# python ingest_frames.py --camera room1 --fps 5
```

## 🐛 Troubleshooting

**Cameras not connecting?**
```bash
python test_cameras.py  # Check each camera
ping 192.168.1.186      # Test network
```

**Backend won't start?**
```bash
redis-cli ping          # Verify Redis is running
lsof -i :8000          # Check port availability
```

**No detections?**
- Check camera feed is active
- Verify frames are being sent to backend
- Check YOLO model is loaded (see logs)

See **[SYSTEM.md](./SYSTEM.md)** for more troubleshooting.

## 📝 License

Private security monitoring system.