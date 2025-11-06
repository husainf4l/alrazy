# Brinks V2 - Security Camera System

Modern security camera monitoring system with real-time WebRTC streaming.

## Features

- 🎥 **Real-time Video Streaming** - WebRTC for sub-second latency
- 📊 **Modern Dashboard** - Beautiful responsive UI with Tailwind CSS
- 🗄️ **Database Management** - PostgreSQL for camera configuration
- 🔄 **Dynamic Loading** - Cameras auto-loaded from database
- 🎯 **High Quality** - Main stream with adaptive bitrate
- 🚀 **Production Ready** - PM2 process management

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database for camera configuration
- **SQLAlchemy** - ORM for database operations

### Video Streaming
- **RTSPtoWebRTC** - Go-based RTSP to WebRTC converter
- **WebRTC** - Real-time peer-to-peer streaming
- **RTSP** - Camera protocol support

### Frontend
- **Tailwind CSS** - Modern utility-first CSS
- **Vanilla JavaScript** - Native WebRTC API

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │────────▶│  FastAPI     │────────▶│ PostgreSQL  │
│  Dashboard  │         │  (Port 8001) │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
      │                                                  │
      │ WebRTC                                          │ Queries
      │                                                  │
      ▼                                                  ▼
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   WebRTC    │────────▶│   RTSP       │────────▶│  Cameras    │
│   Server    │         │   Streams    │         │  Database   │
│ (Port 8083) │         │              │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
```

## Setup

### Prerequisites
- Python 3.12+
- Go 1.25+
- PostgreSQL database
- UV package manager (optional, faster than pip)

### Installation

1. **Clone the repository**
   ```bash
   cd /home/husain/alrazy/brinksv2
   ```

2. **Create Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**
   ```bash
   uv pip install fastapi uvicorn sqlalchemy psycopg2-binary jinja2
   # or use pip:
   # pip install fastapi uvicorn sqlalchemy psycopg2-binary jinja2
   ```

4. **Configure database**
   Edit `database.py` with your PostgreSQL credentials:
   ```python
   DATABASE_URL = "postgresql://user:password@host:port/database"
   ```

5. **Build WebRTC server**
   ```bash
   cd RTSPtoWebRTC
   go build -o rtsp-webrtc-server
   ```

### Running with PM2

```bash
# Start all services
pm2 start ecosystem.config.json

# View status
pm2 status

# View logs
pm2 logs

# Restart services
pm2 restart all

# Stop services
pm2 stop all
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
