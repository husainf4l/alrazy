# 🎥 FastAPI + NestJS Backend Integration - Complete Guide

## 🎯 What We've Built

A **clean separation** between your NestJS backend and FastAPI streaming service:

```
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Frontend      │    │   NestJS Backend    │    │  FastAPI Stream  │
│                 │◄──►│   (Port 3000)       │    │   (Port 8001)    │
│ - Authentication│    │                     │    │                  │
│ - Dashboard     │    │ - User Management   │    │ - Camera Streams │
│ - Camera CRUD   │    │ - Camera CRUD       │    │ - Motion Detection│
│                 │    │ - Companies         │    │ - Real-time Video│
│                 │    │ - JWT Auth          │    │ - Computer Vision│
│                 │    │ - Business Logic    │    │ - WebSocket Feeds│
└─────────────────┘    └─────────────────────┘    └──────────────────┘
                                 │                           │
                                 └──────────────┬────────────┘
                                    Same PostgreSQL Database
                                      (Prisma Schema)
```

## 🚀 Quick Setup

### 1. Set Up the Clean FastAPI Service

```bash
cd /home/husain/alrazy/fastapi

# Run the setup script
./setup_streaming.sh

# This will:
# - Install clean dependencies  
# - Copy Prisma schema from backend
# - Generate Prisma client
# - Create .env file
# - Test database connection
```

### 2. Configure Environment

Edit `/home/husain/alrazy/fastapi/.env`:

```env
# Same database as your NestJS backend
DATABASE_URL="postgresql://username:password@localhost:5432/alrazy_db"

SERVICE_NAME="Camera Streaming Service"
SERVICE_PORT=8001
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Start Services

```bash
# Terminal 1: Start NestJS Backend (if not running)
cd /home/husain/alrazy/backend
npm run start:dev

# Terminal 2: Start FastAPI Streaming Service  
cd /home/husain/alrazy/fastapi
python3 run_streaming.py
```

### 4. Test Integration

```bash
cd /home/husain/alrazy/fastapi
python3 test_streaming.py
```

## 📋 API Integration

### NestJS Backend (Port 3000) - Camera Management

```typescript
// Create a camera
POST /api/cameras
Authorization: Bearer JWT_TOKEN
Content-Type: application/json

{
  "name": "Front Door Camera",
  "rtspUrl": "rtsp://admin:password@192.168.1.100:554/stream",
  "location": "Main Entrance",
  "resolutionWidth": 1920,
  "resolutionHeight": 1080,
  "fps": 30,
  "enableMotionDetection": true,
  "enableRecording": true
}
```

### FastAPI Streaming (Port 8001) - Camera Streaming

```typescript
// Get camera stream info
GET /api/stream/camera/1/info
X-Company-Id: 1

// Get current frame
GET /api/stream/camera/1/frame  
X-Company-Id: 1

// Detect motion
GET /api/stream/camera/1/motion
X-Company-Id: 1

// Start recording
POST /api/stream/camera/1/record?duration=60
X-Company-Id: 1
```

## 📡 WebSocket Streaming

### Frontend Implementation

```typescript
// Connect to streaming WebSocket
const ws = new WebSocket('ws://localhost:8001/ws/camera-stream?company_id=1');

ws.onopen = () => {
  console.log('Connected to camera streaming');
  
  // Start streaming camera 1 at 10 FPS
  ws.send(JSON.stringify({
    type: 'start_stream',
    camera_id: 1,
    fps: 10
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'frame':
      // Update video display
      const img = document.getElementById('camera-feed');
      img.src = `data:image/jpeg;base64,${data.frame}`;
      break;
      
    case 'motion_result':
      if (data.motion_detected) {
        showMotionAlert(data.camera_id, data.confidence);
      }
      break;
      
    case 'stream_started':
      console.log(`Stream started for ${data.camera_name}`);
      break;
  }
};

// Detect motion
function detectMotion(cameraId) {
  ws.send(JSON.stringify({
    type: 'motion_detection',
    camera_id: cameraId
  }));
}

// Stop streaming
function stopStream() {
  ws.send(JSON.stringify({
    type: 'stop_stream'
  }));
}
```

## 🔗 Integration Workflow

### 1. User Authentication Flow

```typescript
// Step 1: User logs in via NestJS backend
const response = await fetch('http://localhost:3000/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email, password})
});

const {access_token, user} = await response.json();

// Step 2: Get user's cameras from backend
const camerasResponse = await fetch('http://localhost:3000/api/cameras', {
  headers: {'Authorization': `Bearer ${access_token}`}
});

const cameras = await camerasResponse.json();

// Step 3: Stream cameras via FastAPI
for (const camera of cameras) {
  const frameResponse = await fetch(`http://localhost:8001/api/stream/camera/${camera.id}/frame`, {
    headers: {'X-Company-Id': user.companyId.toString()}
  });
  
  const {frame} = await frameResponse.json();
  // Display frame...
}
```

### 2. Camera Management Flow

```typescript
// Frontend → Backend: Create camera
async function createCamera(cameraData) {
  const response = await fetch('http://localhost:3000/api/cameras', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(cameraData)
  });
  
  return response.json();
}

// Frontend → FastAPI: Stream camera  
async function streamCamera(cameraId, companyId) {
  const response = await fetch(`http://localhost:8001/api/stream/camera/${cameraId}/frame`, {
    headers: {'X-Company-Id': companyId.toString()}
  });
  
  return response.json();
}
```

## 📁 Clean File Structure

Your FastAPI is now clean and focused:

```
fastapi/
├── app/
│   ├── api/
│   │   ├── streaming_api.py         # Camera streaming endpoints
│   │   └── websocket_api.py         # WebSocket endpoints
│   ├── database/
│   │   └── prisma_client.py         # Database connection
│   ├── services/
│   │   ├── camera_stream_service.py # Camera streaming logic
│   │   └── streaming_websocket.py   # WebSocket management
│   └── main_streaming.py            # Clean FastAPI app
├── prisma/
│   └── schema.prisma               # Copied from backend
├── requirements_streaming.txt       # Clean dependencies
├── setup_streaming.sh              # Setup script
├── run_streaming.py                # Run script
├── test_streaming.py               # Test script
└── .env                           # Configuration
```

## 🎯 Benefits of This Architecture

### ✅ **Clear Separation**
- **NestJS Backend**: Authentication, CRUD, business logic
- **FastAPI**: Real-time streaming, computer vision, performance

### ✅ **Shared Database**
- Single source of truth
- Consistent data across services
- No data synchronization issues

### ✅ **Scalability**
- Scale streaming service independently
- Add more FastAPI instances for load
- Backend handles authentication once

### ✅ **Development Efficiency**  
- Clean, focused codebases
- No duplicate user management
- Easy to maintain and extend

### ✅ **Security**
- Authentication in one place (backend)
- FastAPI only handles authorized requests
- Company-based access control

## 🛠️ Development Workflow

### Adding New Cameras

1. **Via Backend** (NestJS):
```bash
# Add camera via your backend API
curl -X POST http://localhost:3000/api/cameras \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Camera",
    "rtspUrl": "rtsp://admin:pass@192.168.1.200:554/stream",
    "location": "Back Office"
  }'
```

2. **Stream via FastAPI**:
```bash
# Stream the camera
curl -X GET http://localhost:8001/api/stream/camera/1/frame \
  -H "X-Company-Id: 1"
```

### Adding New Features

**For camera management** → Add to NestJS backend
**For streaming/CV features** → Add to FastAPI

### Testing

```bash
# Test backend
cd /home/husain/alrazy/backend
npm test

# Test FastAPI streaming
cd /home/husain/alrazy/fastapi  
python3 test_streaming.py
```

## 🚨 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test backend database connection
cd /home/husain/alrazy/backend
npm run db:migrate

# Test FastAPI database connection  
cd /home/husain/alrazy/fastapi
python3 test_streaming.py
```

### Camera Access Issues

1. **404 Camera not found**: Camera doesn't exist in database
2. **403 Access denied**: Wrong company ID or camera belongs to different company
3. **503 Camera not available**: RTSP stream failed to connect

### Service Communication

- **Backend**: http://localhost:3000
- **FastAPI**: http://localhost:8001  
- **Database**: PostgreSQL on configured port

## 🎉 Next Steps

1. **Clean up old FastAPI files** (keep only the new clean structure)
2. **Update your frontend** to use both services
3. **Test the integration** with real cameras
4. **Add more computer vision features** to FastAPI
5. **Scale services** as needed

You now have a **production-ready, scalable architecture** with clear separation of concerns! 🚀
