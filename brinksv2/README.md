````markdown
# Brinks V2 - AI-Powered People Detection System

A modern, real-time people detection and tracking system with cross-camera tracking capabilities, built with YOLO11, ByteTrack, and DeepSORT.

## 🚀 Features

- 🎥 **Real-time People Detection** - YOLO11m model with GPU acceleration
- � **Multi-Camera Support** - Monitor multiple RTSP camera streams simultaneously
- 🏃 **ByteTrack Integration** - Fast and accurate single-camera tracking (30 FPS)
- � **DeepSORT ReID** - Advanced re-identification for uncertain tracks
- 🌐 **Cross-Camera Tracking** - Track people across multiple overlapping cameras
- 🏠 **Room Management** - Group cameras by physical location for accurate people counting
- 💎 **Modern UI** - Apple-inspired interface built with Tailwind CSS
- 🚀 **REST API** - Complete FastAPI backend with automatic documentation
- 📊 **Real-time Statistics** - Live person counting and tracking metrics

## 📋 Requirements

- Python 3.12+
- CUDA-capable GPU (recommended, RTX 4070 Ti SUPER or better)
- PostgreSQL database
- RTSP camera streams
- Go 1.25+ (for WebRTC server)

## 🛠️ Installation

### 1. Clone the repository
```bash
cd /home/husain/alrazy/brinksv2
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
# or use UV for faster installation:
uv pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your configuration (database, model paths, etc.)
```

### 5. Download YOLO model
Place `yolo11m.pt` in the project root or specify path in `.env`

### 6. Initialize database
```bash
python -c "from database import init_db; init_db()"
```

### 7. Build WebRTC server
```bash
cd RTSPtoWebRTC
go build -o rtsp-webrtc-server
cd ..
```

## 🚦 Usage

### Start with PM2 (Production)
```bash
pm2 start ecosystem.config.json
pm2 status
pm2 logs
```

### Start manually (Development)
```bash
# Terminal 1: Start FastAPI backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start WebRTC server
cd RTSPtoWebRTC
./rtsp-webrtc-server
```

### Access the application
- **Dashboard**: http://localhost:8001/dashboard
- **Cameras**: http://localhost:8001/cameras-page
- **Rooms**: http://localhost:8001/rooms-page
- **API Docs**: http://localhost:8001/docs

## 📁 Project Structure

```
brinksv2/
├── config.py                 # ✨ Configuration management (NEW)
├── database.py              # ✨ Enhanced database with pooling (IMPROVED)
├── main.py                  # FastAPI application entry point
│
├── models/                  # SQLAlchemy ORM models
│   ├── __init__.py         # ✨ Proper exports (NEW)
│   ├── camera.py           # Camera and DetectionCount models
│   └── room.py             # Room model for grouping cameras
│
├── schemas/                 # Pydantic schemas for validation
│   ├── __init__.py         # ✨ Proper exports (NEW)
│   ├── camera.py
│   ├── detection.py
│   └── room.py
│
├── routes/                  # FastAPI route handlers
│   ├── __init__.py         # ✨ Proper exports (NEW)
│   ├── cameras.py          # Camera CRUD operations
│   ├── dashboard.py        # Dashboard page routing
│   ├── detections.py       # Detection data endpoints
│   ├── visualization.py    # Video stream visualization
│   └── rooms.py            # Room management
│
├── services/                # Business logic layer
│   ├── __init__.py         # ✨ Proper exports (NEW)
│   ├── people_detection.py         # Core detection service
│   └── cross_camera_tracking.py   # Global tracking logic
│
├── utils/                   # ✨ Utility modules (NEW)
│   ├── __init__.py
│   ├── logger.py           # ✨ Centralized logging (NEW)
│   └── decorators.py       # ✨ Retry and timing decorators (NEW)
│
├── templates/               # HTML templates
│   ├── dashboard.html
│   ├── cameras.html
│   └── rooms.html
│
├── scripts/                 # ✨ Utility scripts (ORGANIZED)
│   ├── migrate_add_rooms.py
│   ├── setup_example_room.py
│   ├── fix_cascade_delete.py
│   └── test_all_cameras.py
│
├── docs/                    # ✨ Documentation (ORGANIZED)
│   ├── BYTETRACK_IMPLEMENTATION.md
│   ├── MULTI_CAMERA_TRACKING.md
│   ├── QUICK_START_ROOMS.md
│   ├── TRACKING_IMPLEMENTATION.md
│   └── VISUAL_GUIDE.md
│
├── RTSPtoWebRTC/           # Go WebRTC server
│   ├── main.go
│   ├── database.go
│   └── config.json
│
├── requirements.txt         # ✨ Python dependencies (NEW)
├── .env.example            # ✨ Example environment variables (NEW)
├── .gitignore              # ✨ Comprehensive ignore file (IMPROVED)
├── ecosystem.config.json   # PM2 configuration
└── README.md               # This file
```

## API Endpoints

### FastAPI (Port 8001)

- `GET /` - API info
- `GET /health` - Health check
- `GET /dashboard` - Main dashboard UI
- `GET /cameras-page` - Camera management page
- `GET /cameras/` - List all cameras
- `POST /cameras/` - Add new camera
- `GET /cameras/{id}` - Get camera by ID
- `PUT /cameras/{id}` - Update camera
- `DELETE /cameras/{id}` - Delete camera
- `GET /docs` - API documentation (Swagger)

### WebRTC Server (Port 8083)

- `GET /stream/player/{stream_id}` - View stream
- `GET /stream/codec/{stream_id}` - Get codec info
- `POST /stream/receiver/{stream_id}` - WebRTC signaling

## Database Schema

### Camera Table
```sql
CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    rtsp_main VARCHAR NOT NULL,
    rtsp_sub VARCHAR NOT NULL,
    location VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Configuration

### ecosystem.config.json
```json
{
  "apps": [
    {
      "name": "brinks-v2",
      "script": "venv/bin/uvicorn",
      "args": "main:app --host 0.0.0.0 --port 8001"
    },
    {
      "name": "rtsp-webrtc-server",
      "script": "./rtsp-webrtc-server",
      "cwd": "./RTSPtoWebRTC"
    }
  ]
}
```

### RTSPtoWebRTC/config.json
```json
{
  "server": {
    "http_port": ":8083",
    "ice_servers": ["stun:stun.l.google.com:19302"]
  }
}
```

Note: Cameras are loaded dynamically from the database, no manual configuration needed!

## Usage

1. **Access Dashboard**
   ```
   http://localhost:8001/dashboard
   ```

2. **Add Cameras**
   - Go to http://localhost:8001/cameras-page
   - Fill in camera details (name, RTSP URLs, location)
   - Click "Add Camera"

3. **View Live Streams**
   - Dashboard automatically loads all cameras from database
   - WebRTC provides real-time streaming with adaptive quality
   - Click fullscreen icon for fullscreen view

4. **Restart After Adding Cameras**
   ```bash
   pm2 restart rtsp-webrtc-server
   ```

## Development

### Project Structure
```
brinksv2/
├── main.py                 # FastAPI application entry
├── database.py             # Database configuration
├── models/
│   └── camera.py          # Camera SQLAlchemy model
├── schemas/
│   └── camera.py          # Pydantic schemas
├── routes/
│   ├── dashboard.py       # Dashboard routes
│   └── cameras.py         # Camera API endpoints
├── templates/
│   ├── dashboard.html     # Main dashboard UI
│   └── cameras.html       # Camera management UI
├── RTSPtoWebRTC/
│   ├── main.go            # Go WebRTC server
│   ├── database.go        # PostgreSQL integration
│   ├── config.go          # Configuration handler
│   └── stream.go          # RTSP stream handler
└── ecosystem.config.json  # PM2 configuration
```

## Troubleshooting

### Cameras not loading
```bash
# Check database connection
psql -h host -U user -d database

# Restart WebRTC server
pm2 restart rtsp-webrtc-server

# Check logs
pm2 logs rtsp-webrtc-server
```

### Stream unavailable
- Verify RTSP URLs are correct
- Check camera network connectivity
- Ensure firewall allows RTSP traffic (port 554)

### Port already in use
```bash
# Check what's using the port
lsof -i :8001
lsof -i :8083

# Kill process or change port in config
```

## License

Private project - All rights reserved

## Credits

- **FastAPI** - https://fastapi.tiangolo.com/
- **RTSPtoWebRTC** - https://github.com/deepch/RTSPtoWebRTC
- **Tailwind CSS** - https://tailwindcss.com/
