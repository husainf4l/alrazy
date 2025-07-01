# RazZ Backend Security System

A comprehensive FastAPI security monitoring system for pharmacies with AI-powered threat detection, real-time camera surveillance, and automated alerts.

## Features

- **Basic API endpoints** - Root, health check, and item CRUD operations
- **RTSP Camera Integration** - Connect to IP cameras via RTSP protocol
- **Real-time Frame Capture** - Get current frames from the camera
- **Motion Detection** - Basic motion detection with bounding box annotations
- **Web Dashboard** - Beautiful HTML interface for camera monitoring
- **Auto-generated API documentation**

## Camera Features

- RTSP stream connection with automatic reconnection
- Real-time frame capture and base64 encoding
- Simple motion detection with configurable sensitivity
- Background subtraction for motion analysis
- Threaded capture for better performance

## API Endpoints

### Basic Endpoints
- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /items/{item_id}` - Get item by ID
- `POST /items/` - Create new item

### Camera Endpoints
- `GET /camera/info` - Get camera stream information
- `GET /camera/frame` - Get current frame as base64 encoded JPEG
- `GET /camera/motion` - Detect motion and return annotated frame
- `POST /camera/initialize` - Initialize or reconnect camera

### Dashboard
- `GET /dashboard` - Web interface for camera monitoring

## RTSP Camera Configuration

The app is configured to connect to:
```
rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101
```

You can modify the RTSP URL in `camera_service.py` if needed.

## How to run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Open your browser and go to:
   - http://127.0.0.1:8000 - API root
   - http://127.0.0.1:8000/dashboard - Camera monitoring dashboard
   - http://127.0.0.1:8000/docs - Interactive API documentation
   - http://127.0.0.1:8000/redoc - Alternative API documentation

## Camera Dashboard

The web dashboard provides:
- Real-time camera status monitoring
- Manual frame capture
- Motion detection with visual alerts
- Auto-refresh functionality for continuous monitoring
- Camera stream information display

## Dependencies

- **FastAPI** - Web framework
- **OpenCV** - Computer vision and video processing
- **NumPy** - Numerical operations
- **Pillow** - Image processing
- **Uvicorn** - ASGI server

## Development

The application runs on port 8000 by default and accepts connections from all interfaces (0.0.0.0) for camera access from other devices on the network.

## Security Notes

- The RTSP URL contains credentials - ensure proper network security
- The camera service runs in a separate thread for non-blocking operation
- Motion detection uses basic background subtraction - adjust thresholds as needed
