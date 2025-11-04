# 🚀 Quick Start Guide - Security System Backend

## Prerequisites
- Node.js 18+
- PostgreSQL 12+
- npm or yarn

## Installation & Setup (5 minutes)

### 1️⃣ Install Dependencies
```bash
cd backend
npm install
```

### 2️⃣ Configure Database
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your PostgreSQL URL
# DATABASE_URL=postgresql://user:password@localhost:5432/security_system
```

### 3️⃣ Setup Database
```bash
# Generate Prisma client
npm run db:generate

# Run migrations
npm run db:migrate

# Seed initial data (admin user, sample cameras)
npm run db:seed
```

### 4️⃣ Start Development Server
```bash
npm run start:dev
```

✅ Server running at: `http://localhost:3000`
📚 API Docs at: `http://localhost:3000/docs`

## 🔑 Default Credentials

**Admin Account:**
- Email: `admin@security.com`
- Username: `admin`
- Password: `password123`

**Regular User:**
- Email: `user@security.com`
- Username: `user`
- Password: `password123`

## 📝 Quick API Examples

### 1. Register New User
```bash
curl -X POST http://localhost:3000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "firstName": "John",
    "lastName": "Doe"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password123"
  }'

# Response includes: access_token
```

### 3. Create Camera
```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:3000/api/cameras \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Front Door",
    "location": "Main Entrance",
    "streamUrl": "rtsp://camera-ip:554/stream",
    "webrtcUrl": "webrtc://camera-ip/stream",
    "description": "Main entrance camera"
  }'
```

### 4. Report Person Detection Event
```bash
curl -X POST http://localhost:3000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "cameraId": 1,
    "personCount": 2,
    "confidence": 0.95,
    "snapshotPath": "/snapshots/event_001.jpg",
    "description": "2 persons detected at main entrance"
  }'
```

### 5. Open Door (Lock Control)
```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:3000/api/lock/open \
  -H "Authorization: Bearer $TOKEN"

# Response: { status: "SUCCESS", message: "Door opened successfully", pin: 17 }
```

### 6. Get Events
```bash
TOKEN="your_access_token_here"

curl http://localhost:3000/api/events \
  -H "Authorization: Bearer $TOKEN"
```

## 🔌 WebSocket Connection (Real-time Events)

### JavaScript/Node.js
```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:3000');

// Connect
socket.on('connection', (data) => {
  console.log('Connected:', data);
});

// Subscribe to camera events
socket.emit('subscribe:camera', { cameraId: 1 });

// Listen for events
socket.on('event:detected', (event) => {
  console.log('New event:', event);
});

// Listen for lock status changes
socket.on('lock:status', (data) => {
  console.log('Lock status:', data.status);
});

// Keep connection alive
setInterval(() => {
  socket.emit('ping');
}, 30000);
```

### Python
```python
from socketio import Client

sio = Client()

@sio.event
def connect():
    print('Connected to server')
    sio.emit('subscribe:camera', {'cameraId': 1})

@sio.on('event:detected')
def on_event(data):
    print('New event:', data)

sio.connect('http://localhost:3000')
sio.wait()
```

## 📊 Available Endpoints

### Authentication
- `POST /auth/register` - Register
- `POST /auth/login` - Login
- `GET /auth/profile` - Get profile

### Users (requires auth)
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `GET /api/users/:id` - Get user
- `PUT /api/users/:id` - Update user
- `DELETE /api/users/:id` - Delete user
- `GET /api/users/stats` - Statistics

### Cameras (requires auth)
- `GET /api/cameras` - List cameras
- `POST /api/cameras` - Create camera
- `GET /api/cameras/:id` - Get camera
- `PUT /api/cameras/:id` - Update camera
- `DELETE /api/cameras/:id` - Delete camera
- `GET /api/cameras/stats` - Statistics

### Events
- `POST /api/events` - Create event (no auth needed)
- `GET /api/events` - List events (requires auth)
- `GET /api/events/:id` - Get event (requires auth)
- `GET /api/events/camera/:cameraId` - Get camera events (requires auth)
- `GET /api/events/unresolved` - Get unresolved (requires auth)
- `PATCH /api/events/:id/resolve` - Resolve event (requires auth)
- `GET /api/events/stats` - Statistics (requires auth)

### Lock Control (requires auth)
- `POST /api/lock/open` - Open door
- `POST /api/lock/close` - Close door
- `POST /api/lock/toggle` - Toggle
- `GET /api/lock/status` - Get status

## 🔧 Configuration

Edit `.env` file:

```bash
# Server
NODE_ENV=development
PORT=3000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/security_system

# JWT
JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRATION=24h

# CORS
CORS_ORIGIN=http://localhost:3000,http://localhost:3001

# GPIO (Door Lock)
GPIO_RELAY_PIN=17
GPIO_SIMULATED=true  # Set to false for real GPIO

# AI Service
AI_SERVICE_URL=http://localhost:5000
PERSON_DETECTION_THRESHOLD=0.5
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Database Connection Error
```bash
# Verify PostgreSQL is running
psql -U postgres -h localhost

# Check DATABASE_URL format
echo $DATABASE_URL
```

### Build Errors
```bash
# Clean and rebuild
rm -rf node_modules dist
npm install
npm run build
```

### WebSocket Connection Failed
- Ensure server is running
- Check firewall settings
- Verify CORS_ORIGIN in .env

## 📚 Full Documentation

See these files for more details:
- `README_API.md` - Complete API reference
- `RESTRUCTURING_SUMMARY.md` - Architecture overview
- `src/*/dto/` - API request/response schemas

## 🎯 Common Tasks

### Create Initial Data
```bash
npm run db:seed
```

### Reset Database
```bash
# ⚠️ This will delete all data (development only)
npm run db:reset
```

### Generate Prisma Types
```bash
npm run db:generate
```

### Format Code
```bash
npm run format
```

### Lint Code
```bash
npm run lint
```

## 🔐 Security Notes

✅ Passwords are hashed with bcryptjs
✅ JWT tokens expire after 24 hours
✅ CORS configured for specific origins
✅ All non-public endpoints require authentication
✅ GPIO operations can be simulated for development

## 📞 Support

For issues or questions:
1. Check API docs at `http://localhost:3000/docs`
2. Review log output in console
3. Check `.env` configuration
4. Verify database connectivity

## 🎉 You're Ready!

Your security system backend is now running and ready to:
- Receive person detection events from AI engine
- Broadcast real-time notifications via WebSocket
- Control door locks via GPIO relay
- Manage cameras and events through REST API

Happy coding! 🚀