# Quick Start Guide

## ✅ Setup Complete!

Your People Counter API with YOLOv8 is ready to use!

## 📁 Project Structure
```
brinksv3/
├── venv/              # Virtual environment
├── main.py           # FastAPI application
├── detector.py       # YOLO detection logic
├── test_api.py       # API test script
├── viewer.html       # Web-based stream viewer
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variables template
├── .gitignore        # Git ignore rules
├── README.md         # Full documentation
└── yolov8n.pt        # YOLO model (auto-downloaded)
```

## 🚀 Running the Application

### 1. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 2. Start the Server
The server is currently running on: http://localhost:8000

If you need to restart it:
```bash
python main.py
```

## 📚 API Documentation

Visit these URLs in your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Web Viewer**: Open `viewer.html` in your browser

## 🎯 API Endpoints

### 1. Count People (Single Frame)
```bash
curl -X POST "http://localhost:8000/count" \
  -H "Content-Type: application/json" \
  -d '{
    "rtsp_url": "rtsp://your-camera-ip:554/stream",
    "confidence": 0.5
  }'
```

**Response:**
```json
{
  "rtsp_url": "rtsp://your-camera-ip:554/stream",
  "people_count": 3,
  "confidence_threshold": 0.5
}
```

### 2. Stream Video with Detection
```bash
curl -X POST "http://localhost:8000/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "rtsp_url": "rtsp://your-camera-ip:554/stream",
    "confidence": 0.5
  }'
```

Returns an MJPEG stream with bounding boxes and people count overlay.

### 3. Health Check
```bash
curl http://localhost:8000/health
```

## 🎥 Testing with RTSP Stream

### Using the Web Viewer
1. Open `viewer.html` in a web browser
2. Enter your RTSP URL
3. Click "Start Stream" or "Count Once"

### Using Python
```python
import requests

response = requests.post(
    "http://localhost:8000/count",
    json={
        "rtsp_url": "rtsp://your-camera:554/stream",
        "confidence": 0.5
    }
)
print(response.json())
```

### Using the Test Script
```bash
python test_api.py
```

## 🔧 Configuration

### Change YOLO Model
Edit `detector.py` line 15:
- `yolov8n.pt` - Nano (fastest, 6MB)
- `yolov8s.pt` - Small (11MB)
- `yolov8m.pt` - Medium (49MB)
- `yolov8l.pt` - Large (83MB, most accurate)

### Adjust Confidence Threshold
- Lower (0.3-0.5): More detections, may have false positives
- Higher (0.6-0.9): Fewer but more confident detections

## 📝 Common RTSP URL Formats

```
# Generic
rtsp://ip:port/stream

# With authentication
rtsp://username:password@ip:port/stream

# Examples
rtsp://192.168.1.100:554/stream
rtsp://admin:admin123@192.168.1.100:554/h264
rtsp://camera.local:8554/live
```

## 🐛 Troubleshooting

### Can't connect to RTSP stream?
1. Test the stream with VLC or ffplay first
2. Check camera IP and port
3. Verify network connectivity
4. Ensure camera supports RTSP

### Dependencies installation failed?
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Server won't start?
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "python main.py"

# Restart
python main.py
```

## 📊 Features

✅ Real-time people detection
✅ RTSP stream support
✅ REST API endpoints
✅ Video streaming with overlay
✅ Configurable confidence threshold
✅ Web-based viewer
✅ Interactive API docs

## 🎉 You're All Set!

The application is running and ready to detect people from your RTSP streams!

For more details, see the full README.md file.
