# Security System Backend (NestJS)

Person Detection & Door Lock Control System - NestJS API Server

## 📋 Overview

This is a RESTful API backend built with NestJS that:
- Manages user authentication and authorization
- Receives person detection events from AI engine (FastAPI)
- Broadcasts real-time events via WebSocket to connected clients
- Controls door lock via GPIO relay
- Stores camera configurations and detection events in PostgreSQL

## 🏗️ Architecture

```
Camera Stream
    ↓
FastAPI (AI Engine) - YOLO Person Detection
    ↓
NestJS Backend (This Project)
    ├── REST API (/api/events, /api/lock, /api/cameras, /api/users)
    ├── WebSocket Gateway (Real-time event broadcasting)
    └── Database (PostgreSQL)
         ↓
Next.js Frontend (Real-time dashboard)
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 12+
- npm or yarn

### Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Setup database**
   ```bash
   # Run migrations
   npx prisma migrate dev

   # (Optional) Seed initial data
   npm run db:seed
   ```

4. **Start development server**
   ```bash
   npm run start:dev
   ```

   The server will run on `http://localhost:3000`
   API Documentation: `http://localhost:3000/docs`

## 📁 Project Structure

```
src/
├── auth/                 # Authentication & Authorization
│   ├── auth.controller.ts
│   ├── auth.service.ts
│   ├── auth.module.ts
│   ├── dto/
│   ├── guards/          # JWT Guard, Local Guard
│   └── strategies/      # JWT Strategy, Local Strategy
│
├── camera/              # Camera Management
│   ├── camera.controller.ts
│   ├── camera.service.ts
│   ├── camera.module.ts
│   └── dto/
│
├── event/               # Event Detection & Processing
│   ├── event.controller.ts
│   ├── event.service.ts
│   ├── events.gateway.ts    # WebSocket Gateway
│   ├── event.module.ts
│   └── dto/
│
├── lock/                # Door Lock Control (GPIO)
│   ├── lock.controller.ts
│   ├── lock.service.ts
│   └── lock.module.ts
│
├── user/                # User Management
│   ├── user.controller.ts
│   ├── user.service.ts
│   ├── user.module.ts
│   └── dto/
│
├── prisma/              # Database Service
│   └── prisma.service.ts
│
├── config/              # Configuration
│   └── configuration.ts
│
├── app.module.ts        # Main Application Module
└── main.ts             # Application Entry Point

prisma/
├── schema.prisma       # Database Schema
├── migrations/         # Database Migrations
└── seed.ts            # Seed Script
```

## 🔌 API Endpoints

### Authentication
```
POST   /auth/register         - Register new user
POST   /auth/login            - Login user
GET    /auth/profile          - Get current user profile
```

### Users
```
GET    /api/users             - Get all users
POST   /api/users             - Create user (admin)
GET    /api/users/:id         - Get user by ID
PUT    /api/users/:id         - Update user
DELETE /api/users/:id         - Delete user
GET    /api/users/stats       - Get user statistics
```

### Cameras
```
GET    /api/cameras           - Get all cameras
POST   /api/cameras           - Create camera
GET    /api/cameras/:id       - Get camera details
PUT    /api/cameras/:id       - Update camera
DELETE /api/cameras/:id       - Delete camera
GET    /api/cameras/stats     - Get camera statistics
```

### Events
```
POST   /api/events            - Create event (from AI engine)
GET    /api/events            - Get all events (paginated)
GET    /api/events/:id        - Get event details
GET    /api/events/camera/:cameraId - Get events for specific camera
GET    /api/events/unresolved - Get unresolved events
PATCH  /api/events/:id/resolve - Mark event as resolved
GET    /api/events/stats      - Get event statistics
```

### Lock Control
```
POST   /api/lock/open         - Open door (activate relay)
POST   /api/lock/close        - Close door (deactivate relay)
POST   /api/lock/toggle       - Toggle lock state
GET    /api/lock/status       - Get current lock status
```

## 🔌 WebSocket Events

### Client → Server
```javascript
// Subscribe to specific camera events
socket.emit('subscribe:camera', { cameraId: 1 });

// Unsubscribe from camera
socket.emit('unsubscribe:camera', { cameraId: 1 });

// Request latest events
socket.emit('request:latest-events', { limit: 10 });

// Request unresolved events
socket.emit('request:unresolved-events');

// Keep-alive ping
socket.emit('ping');
```

### Server → Client
```javascript
// Connection confirmation
socket.on('connection', (data) => {
  console.log('Connected:', data);
});

// Event detection (broadcast to all)
socket.on('event:detected', (event) => {
  console.log('New event:', event);
});

// Lock status update
socket.on('lock:status', (data) => {
  console.log('Lock status:', data.status);
});

// Pong response
socket.on('pong', (data) => {
  console.log('Pong at:', data.timestamp);
});
```

## 📊 Database Schema

### Users
- `id` (INT) - Primary Key
- `username` (VARCHAR) - Unique username
- `email` (VARCHAR) - Unique email
- `password` (VARCHAR) - Hashed password
- `firstName` (VARCHAR) - First name
- `lastName` (VARCHAR) - Last name
- `role` (ENUM) - ADMIN or USER
- `isActive` (BOOLEAN) - Account active status
- `createdAt` (TIMESTAMP)
- `updatedAt` (TIMESTAMP)

### Cameras
- `id` (INT) - Primary Key
- `name` (VARCHAR) - Camera name
- `location` (VARCHAR) - Physical location
- `streamUrl` (VARCHAR) - Stream URL (RTSP/HTTP)
- `webrtcUrl` (VARCHAR) - WebRTC URL
- `description` (TEXT)
- `isActive` (BOOLEAN)
- `createdAt` (TIMESTAMP)
- `updatedAt` (TIMESTAMP)

### Events
- `id` (INT) - Primary Key
- `cameraId` (INT) - Foreign Key to Camera
- `eventType` (ENUM) - PERSON_DETECTED, MULTIPLE_PERSONS, etc.
- `personCount` (INT) - Number of persons detected
- `confidence` (FLOAT) - Detection confidence (0.0-1.0)
- `snapshotPath` (VARCHAR) - Path to saved image
- `description` (TEXT)
- `isResolved` (BOOLEAN)
- `createdAt` (TIMESTAMP)
- `resolvedAt` (TIMESTAMP)

## 🛡️ Security Features

- **JWT Authentication** - Secure token-based authentication
- **Password Hashing** - bcryptjs for password encryption
- **Input Validation** - class-validator for DTO validation
- **CORS Protection** - Configurable CORS origins
- **Environment Variables** - Sensitive data in .env files

## 🔧 Configuration

### Environment Variables

```bash
# Application
NODE_ENV=development|production
PORT=3000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/db_name

# JWT
JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRATION=24h

# CORS
CORS_ORIGIN=http://localhost:3000,http://localhost:3001

# WebSocket
WEBSOCKET_PORT=3001

# GPIO (Door Lock)
GPIO_RELAY_PIN=17
GPIO_SIMULATED=true|false

# AI Service
AI_SERVICE_URL=http://localhost:5000
PERSON_DETECTION_THRESHOLD=0.5
```

## 🗄️ Database Commands

```bash
# Create new migration
npm run db:migrate

# Generate Prisma client
npm run db:generate

# Reset database (dev only)
npm run db:reset

# Seed database
npm run db:seed
```

## 🚀 Production Deployment

1. **Build**
   ```bash
   npm run build
   ```

2. **Start**
   ```bash
   npm run start:prod
   ```

3. **Environment Setup**
   ```bash
   # Set all required environment variables
   NODE_ENV=production
   JWT_SECRET=<strong-random-string>
   DATABASE_URL=<production-database-url>
   CORS_ORIGIN=https://yourdomain.com
   ```

## 📝 API Usage Examples

### Register User
```bash
curl -X POST http://localhost:3000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "password123",
    "firstName": "Admin",
    "lastName": "User"
  }'
```

### Login
```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password123"
  }'
```

### Create Camera
```bash
curl -X POST http://localhost:3000/api/cameras \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Front Door",
    "location": "Main Entrance",
    "streamUrl": "rtsp://camera-ip:554/stream",
    "webrtcUrl": "webrtc://camera-ip/webrtc",
    "description": "Main entrance camera"
  }'
```

### Create Event (from AI Engine)
```bash
curl -X POST http://localhost:3000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "cameraId": 1,
    "personCount": 2,
    "confidence": 0.95,
    "snapshotPath": "/snapshots/event_123.jpg",
    "description": "2 persons detected at main entrance"
  }'
```

### Open Door
```bash
curl -X POST http://localhost:3000/api/lock/open \
  -H "Authorization: Bearer <access_token>"
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Database Connection Error
```bash
# Verify DATABASE_URL is correct
# Check PostgreSQL is running
psql -U postgres -h localhost
```

### JWT Errors
- Make sure JWT_SECRET is set
- Check token expiration time
- Verify Bearer token format in headers

## 📚 Additional Resources

- [NestJS Documentation](https://docs.nestjs.com)
- [Prisma Documentation](https://www.prisma.io/docs/)
- [Socket.io Documentation](https://socket.io/docs/)
- [JWT Introduction](https://jwt.io/introduction)

## 📄 License

This project is licensed under the MIT License.