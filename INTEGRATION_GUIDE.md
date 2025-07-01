# FastAPI + NestJS Backend Integration Guide

## Overview

This guide shows how to clean up your FastAPI service and connect it properly with your NestJS backend database using Prisma.

## Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Frontend      │    │   NestJS Backend    │    │  FastAPI Stream  │
│   (Next.js)     │◄──►│   (Port 3000)       │    │   (Port 8001)    │
│                 │    │                     │    │                  │
│ - User Auth     │    │ - User Management   │    │ - Camera Streams │
│ - Dashboard     │    │ - Camera CRUD       │    │ - Motion Detection│
│ - Management    │    │ - Companies         │    │ - Real-time Video│
└─────────────────┘    │ - JWT Auth          │    │ - Computer Vision│
                       │ - API Management    │    │ - WebSocket      │
                       └─────────────────────┘    └──────────────────┘
                                 │                           │
                                 └───────────────────────────┘
                                    Same PostgreSQL Database
                                      (Prisma Schema)
```

## Step 1: Set up Database Connection

### 1.1 Install Prisma in FastAPI

```bash
cd /home/husain/alrazy/fastapi
pip install prisma
```

### 1.2 Copy Prisma Schema

Copy your schema from backend to FastAPI:

```bash
cp /home/husain/alrazy/backend/prisma/schema.prisma /home/husain/alrazy/fastapi/prisma/
```

### 1.3 Generate Prisma Client

```bash
cd /home/husain/alrazy/fastapi
prisma generate
```

### 1.4 Set Environment Variables

Create `/home/husain/alrazy/fastapi/.env`:

```env
# Same database URL as your backend
DATABASE_URL="postgresql://username:password@localhost:5432/alrazy_db"
```

## Step 2: Clean Up FastAPI Structure

### 2.1 Remove Unnecessary Files

```bash
cd /home/husain/alrazy/fastapi

# Remove old user management (backend handles this)
rm -rf app/models/user.py
rm -rf app/services/user_service.py
rm -rf app/api/v1/endpoints/users.py

# Remove duplicate camera CRUD (backend handles this)
rm -rf app/services/camera_crud_service.py

# Keep only streaming-related files
```

### 2.2 New Clean Structure

```
fastapi/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── streaming.py          # Clean camera streaming endpoints
│   ├── models/
│   │   └── prisma_client.py          # Prisma connection
│   ├── services/
│   │   └── streaming_service.py      # Camera streaming service
│   └── main_clean.py                 # Clean FastAPI app
├── prisma/
│   └── schema.prisma                 # Copied from backend
├── requirements_clean.txt            # Minimal dependencies
└── .env                             # Database connection
```

## Step 3: Integration Flow

### 3.1 User Authentication Flow

1. **Frontend** → **NestJS Backend**: User logs in, gets JWT token
2. **Frontend** → **NestJS Backend**: Get user's cameras and company info
3. **Frontend** → **FastAPI**: Send camera requests with company ID header
4. **FastAPI**: Verify camera belongs to company, provide streaming

### 3.2 Camera Management Flow

1. **Admin** → **NestJS Backend**: Create/update/delete cameras
2. **NestJS Backend** → **Database**: Store camera configs (RTSP URLs, settings)
3. **FastAPI**: Read camera configs from database for streaming
4. **FastAPI** → **Database**: Write streaming events (recordings, alerts)

### 3.3 Example API Calls

#### NestJS Backend (Camera Management)
```http
POST /api/cameras
Authorization: Bearer JWT_TOKEN
{
  "name": "Front Door Camera",
  "rtspUrl": "rtsp://admin:pass@192.168.1.100:554/stream",
  "location": "Main Entrance",
  "companyId": 1
}
```

#### FastAPI (Camera Streaming)
```http
GET /api/v1/cameras/stream/frame/1
X-Company-Id: 1
```

## Step 4: Implementation Steps

### 4.1 Backend Setup (Already Done)
Your NestJS backend is already perfect with:
- ✅ Complete Prisma schema
- ✅ User authentication
- ✅ Camera CRUD operations
- ✅ Company management

### 4.2 FastAPI Cleanup

1. **Replace current FastAPI with clean version:**
```bash
cd /home/husain/alrazy/fastapi
cp app/main_clean.py app/main.py
cp requirements_clean.txt requirements.txt
```

2. **Install clean dependencies:**
```bash
pip install -r requirements.txt
```

3. **Generate Prisma client:**
```bash
prisma generate
```

4. **Run FastAPI on different port:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 4.3 Frontend Integration

Update your frontend to:
1. Authenticate with NestJS backend (port 3000)
2. Get camera list from NestJS backend
3. Stream video from FastAPI (port 8001) with company ID

## Step 5: WebSocket Streaming Implementation

### 5.1 Real-time Camera Feed

```typescript
// Frontend WebSocket connection
const ws = new WebSocket('ws://localhost:8001/ws/camera-stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'start_stream',
    camera_id: 1,
    company_id: 1
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'frame') {
    // Update video display
    document.getElementById('camera-feed').src = 
      `data:image/jpeg;base64,${data.frame}`;
  }
};
```

### 5.2 Motion Detection Events

```typescript
// Listen for motion detection
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'motion_detected') {
    // Show alert
    showMotionAlert(data.camera_id, data.confidence);
  }
};
```

## Step 6: Benefits of This Architecture

### ✅ **Separation of Concerns**
- **NestJS Backend**: User management, CRUD operations, business logic
- **FastAPI**: Real-time streaming, computer vision, performance-critical tasks

### ✅ **Shared Database**
- Single source of truth for all data
- Consistent camera configurations
- Unified user and company management

### ✅ **Scalability**
- FastAPI can be scaled independently for streaming load
- Backend can be scaled for API load
- Each service has optimal technology stack

### ✅ **Security**
- Authentication handled by backend
- FastAPI only handles streaming with company verification
- No duplicate user management

### ✅ **Development Efficiency**
- Clear boundaries between services
- No code duplication
- Easy to maintain and extend

## Step 7: Testing the Integration

### 7.1 Test Backend

```bash
# Start NestJS backend
cd /home/husain/alrazy/backend
npm run start:dev

# Test camera creation
curl -X POST http://localhost:3000/api/cameras \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Camera", "rtspUrl": "rtsp://test", "companyId": 1}'
```

### 7.2 Test FastAPI Streaming

```bash
# Start FastAPI streaming service
cd /home/husain/alrazy/fastapi
uvicorn app.main:app --port 8001

# Test camera info
curl -X GET http://localhost:8001/api/v1/cameras/stream/info/1 \
  -H "X-Company-Id: 1"
```

## Next Steps

1. **Clean up FastAPI** using the provided files
2. **Test database connection** between services
3. **Implement WebSocket streaming** for real-time video
4. **Add motion detection** with database event logging
5. **Create unified frontend** that uses both services

This architecture gives you the best of both worlds: robust backend management with high-performance streaming!
