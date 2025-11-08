# People Counter API with YOLO

A FastAPI application that uses YOLOv8 to detect and count people from RTSP video streams in real-time.

## Features

- 🎥 Process RTSP video streams
- 👥 Count people in real-time using YOLOv8
- 📊 REST API endpoints for easy integration
- 🎬 Video streaming with detection overlay
- ⚡ Fast and efficient detection

## Prerequisites

- Python 3.8+
- RTSP camera stream or test RTSP URL

## Installation

1. **Activate the virtual environment:**

```bash
source venv/bin/activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

The first time you run the application, YOLOv8 will automatically download the model weights (~6MB for yolov8n).

## Usage

### Start the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. **Count People (Single Frame)**

Get the count of people in a single frame from the RTSP stream.

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

#### 2. **Stream Video with Detection**

Stream the video with bounding boxes and people count overlay.

```bash
curl -X POST "http://localhost:8000/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "rtsp_url": "rtsp://your-camera-ip:554/stream",
    "confidence": 0.5
  }'
```

You can view the stream in a browser or video player:
- Open `http://localhost:8000/docs` for the interactive API documentation
- Use the `/stream` endpoint to get an MJPEG stream

#### 3. **Health Check**

```bash
curl http://localhost:8000/health
```

### Testing with Sample RTSP Stream

If you don't have an RTSP camera, you can use public test streams:

```python
# Example using Python requests
import requests

response = requests.post(
    "http://localhost:8000/count",
    json={
        "rtsp_url": "rtsp://your-test-stream-url",
        "confidence": 0.5
    }
)
print(response.json())
```

## Configuration

### Adjust Detection Confidence

The `confidence` parameter (0.0 to 1.0) controls the detection threshold:
- Lower values (0.3-0.5): More detections, may include false positives
- Higher values (0.6-0.8): Fewer but more confident detections

### Change YOLO Model

In `detector.py`, you can change the model for different performance/accuracy tradeoffs:

```python
# Nano (fastest, least accurate)
detector = YOLODetector(model_name="yolov8n.pt")

# Small
detector = YOLODetector(model_name="yolov8s.pt")

# Medium (balanced)
detector = YOLODetector(model_name="yolov8m.pt")

# Large (slowest, most accurate)
detector = YOLODetector(model_name="yolov8l.pt")
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
brinksv3/
├── venv/               # Virtual environment
├── main.py            # FastAPI application
├── detector.py        # YOLO detection logic
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Troubleshooting

### RTSP Connection Issues

If you can't connect to the RTSP stream:
1. Verify the RTSP URL is correct
2. Check network connectivity to the camera
3. Ensure the camera supports RTSP
4. Try testing the stream with VLC or ffplay first

### Performance Issues

- Use a smaller YOLO model (yolov8n.pt)
- Increase the sleep time in `generate_frames()` to reduce frame rate
- Reduce the input resolution in OpenCV

### Dependencies Issues

If opencv-python fails to install, try:
```bash
pip install opencv-python-headless
```

## License

MIT License

## Support

For issues or questions, please check the documentation or create an issue in the repository.
