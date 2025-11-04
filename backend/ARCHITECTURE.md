# Security System Backend - Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                          │
│                  Real-time Dashboard                            │
└────────────┬──────────────────────────────────┬─────────────────┘
             │ REST API Calls                   │ WebSocket Events
             │                                  │
     ┌───────▼──────────────────────────────────▼────────┐
     │         NestJS Backend (This Project)             │
     │                                                    │
     │  ┌──────────────────────────────────────────────┐ │
     │  │         HTTP REST API                       │ │
     │  │                                              │ │
     │  │  /auth                                      │ │
     │  │  /api/users       (User Management)         │ │
     │  │  /api/cameras     (Camera Management)       │ │
     │  │  /api/events      (Event Management)        │ │
     │  │  /api/lock        (Door Lock Control)       │ │
     │  └──────────────────────────────────────────────┘ │
     │                                                    │
     │  ┌──────────────────────────────────────────────┐ │
     │  │    WebSocket Gateway (Socket.io)            │ │
     │  │                                              │ │
     │  │  Real-time Event Broadcasting               │ │
     │  │  Camera Stream Subscriptions                │ │
     │  │  Lock Status Updates                        │ │
     │  └──────────────────────────────────────────────┘ │
     │                                                    │
     └────────────┬──────────────────────────────────────┘
                  │
                  ├─ POST /api/events ◄── AI Engine (FastAPI)
                  │  (Person Detection)     Camera → YOLO
                  │
                  └─ GPIO Pin #17 ──► Door Lock Relay
                     (GPIO Control)

┌─────────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                            │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  Users   │  │ Cameras  │  │  Events  │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Module Structure

```
APPLICATION MODULES
├── Auth Module
│   ├── AuthService (login, register, validate)
│   ├── AuthController (endpoints)
│   ├── JwtStrategy (token validation)
│   └── LocalStrategy (password validation)
│
├── User Module
│   ├── UserService (CRUD)
│   ├── UserController (endpoints)
│   └── DTOs
│
├── Camera Module
│   ├── CameraService (CRUD)
│   ├── CameraController (endpoints)
│   └── DTOs
│
├── Event Module
│   ├── EventService (CRUD, analytics)
│   ├── EventController (endpoints)
│   ├── EventsGateway (WebSocket)
│   └── DTOs
│
└── Lock Module
    ├── LockService (GPIO control)
    ├── LockController (endpoints)
    └── GPIO Abstraction

INFRASTRUCTURE MODULES
├── Prisma Module (Database)
│   └── PrismaService
│
└── Config Module
    └── Configuration Service
```

## 🔄 Data Flow - Person Detection Event

```
1. DETECTION
   ┌─────────────────────────────────────┐
   │  AI Engine (FastAPI + YOLO)         │
   │  - Process camera stream            │
   │  - Detect persons                   │
   │  - Generate snapshot                │
   └─────────────────────────────────────┘
                    │
                    │ POST /api/events
                    ▼
2. RECEPTION
   ┌─────────────────────────────────────┐
   │  EventController.create()           │
   │  - Validate event data              │
   │  - Determine event type             │
   │  (PERSON_DETECTED, MULTIPLE_PERSONS)│
   └─────────────────────────────────────┘
                    │
                    ▼
3. STORAGE
   ┌─────────────────────────────────────┐
   │  EventService.create()              │
   │  - Save to database                 │
   │  - Create event record              │
   └─────────────────────────────────────┘
                    │
                    ▼
4. BROADCAST
   ┌─────────────────────────────────────┐
   │  EventsGateway.broadcastEvent()    │
   │  - Emit to all connected clients    │
   │  - Send camera-specific stream      │
   │  - Update lock if threshold met     │
   └─────────────────────────────────────┘
                    │
                    ▼
5. FRONTEND UPDATE
   ┌─────────────────────────────────────┐
   │  WebSocket Client                   │
   │  - Receive event:detected           │
   │  - Update dashboard                 │
   │  - Show alert/snapshot              │
   │  - Allow manual lock control        │
   └─────────────────────────────────────┘
```

## 🔐 Authentication Flow

```
1. USER REGISTRATION
   POST /auth/register
   ├─ Validate input
   ├─ Hash password
   ├─ Create user in DB
   └─ Return JWT token

2. USER LOGIN
   POST /auth/login
   ├─ Find user
   ├─ Validate password
   ├─ Generate JWT
   └─ Return token

3. PROTECTED REQUEST
   GET /api/cameras
   ├─ Extract token from Authorization header
   ├─ Verify JWT signature
   ├─ Validate expiration
   ├─ Attach user to request
   └─ Allow access

4. TOKEN PAYLOAD
   {
     sub: userId,
     username: "admin",
     email: "admin@security.com",
     role: "ADMIN",
     iat: 1234567890,
     exp: 1234654290
   }
```

## 🔌 WebSocket Event Flow

```
CLIENT CONNECTION
┌─────────────────────────────────────┐
│ const socket = io(...)              │
└─────────────────────────────────────┘
         │
         ▼
    [CONNECTED]
         │
         ├─► Server: connection event
         │
         ├─ socket.emit('subscribe:camera', {cameraId: 1})
         │
         ├─ socket.on('event:detected', (event) => {...})
         │
         ├─ socket.emit('request:latest-events', {limit: 10})
         │
         └─ socket.emit('ping')  // Keep-alive

SERVER BROADCAST
┌─────────────────────────────────────┐
│ EventsGateway.broadcastEvent(data)  │
└─────────────────────────────────────┘
         │
         ├─► server.emit('event:detected')
         │   [Broadcast to all clients]
         │
         ├─► server.to(`camera:${id}`).emit('event:detected')
         │   [Send to camera subscribers]
         │
         └─► server.emit('lock:status', {...})
             [Broadcast lock changes]
```

## 🗄️ Database Schema Relationships

```
┌─────────────┐
│   User      │
├─────────────┤
│ id (PK)     │
│ username    │
│ email       │
│ password    │
│ firstName   │
│ lastName    │
│ role        │
│ isActive    │
│ createdAt   │
│ updatedAt   │
└─────────────┘

┌─────────────┐          ┌─────────────┐
│   Camera    │◄─────────│   Event     │
├─────────────┤    1:N   ├─────────────┤
│ id (PK)     │          │ id (PK)     │
│ name        │          │ cameraId(FK)│
│ location    │          │ eventType   │
│ streamUrl   │          │ personCount │
│ webrtcUrl   │          │ confidence  │
│ description │          │ snapshotPath│
│ isActive    │          │ isResolved  │
│ createdAt   │          │ createdAt   │
│ updatedAt   │          │ resolvedAt  │
└─────────────┘          └─────────────┘
```

## 🔒 Security Layers

```
1. INPUT VALIDATION
   └─ class-validator decorators on DTOs
      ├─ Type checking
      ├─ Length validation
      ├─ Format validation (email, url)
      └─ Custom validators

2. AUTHENTICATION
   └─ JWT + Passport
      ├─ Token-based auth
      ├─ Signature verification
      ├─ Expiration checking
      └─ Role-based access

3. AUTHORIZATION
   └─ Guards on endpoints
      ├─ @UseGuards(JwtAuthGuard)
      ├─ Role checking
      └─ Resource ownership

4. DATA PROTECTION
   └─ Password hashing
      ├─ bcryptjs (10 salt rounds)
      └─ Never send passwords in responses

5. COMMUNICATION
   └─ CORS configuration
      ├─ Whitelist specific origins
      ├─ HTTPS in production
      └─ WebSocket security
```

## 📊 API Response Format

```json
// Successful Response
{
  "id": 1,
  "username": "admin",
  "email": "admin@security.com",
  "firstName": "Admin",
  "lastName": "User",
  "role": "ADMIN",
  "isActive": true,
  "createdAt": "2025-01-01T12:00:00Z"
}

// Event Response
{
  "id": 1,
  "cameraId": 1,
  "eventType": "PERSON_DETECTED",
  "personCount": 2,
  "confidence": 0.95,
  "snapshotPath": "/snapshots/event_001.jpg",
  "description": "2 persons detected",
  "isResolved": false,
  "createdAt": "2025-01-01T12:30:00Z",
  "camera": {
    "id": 1,
    "name": "Main Entrance"
  }
}

// Error Response
{
  "statusCode": 400,
  "message": "Validation failed",
  "error": "Bad Request"
}
```

## 🚀 Deployment Architecture

```
PRODUCTION SETUP
┌─────────────────────────────────────┐
│      Load Balancer (Optional)       │
│      HTTPS / SSL Certificate        │
└────────────┬────────────────────────┘
             │
     ┌───────▼────────────┐
     │  NestJS Backend    │
     │  (Docker Image)    │
     │  Port: 3000        │
     └───────┬────────────┘
             │
     ┌───────▼─────────────────────┐
     │  PostgreSQL Database        │
     │  (Managed Service/Self-Host)│
     └─────────────────────────────┘
```

## 📈 Scalability Considerations

```
HORIZONTAL SCALING
├─ Stateless API servers
├─ WebSocket with Redis adapter (for multiple servers)
├─ Database connection pooling
└─ Load balancing

PERFORMANCE OPTIMIZATION
├─ Database indexing on frequently queried fields
├─ Event pagination
├─ Caching (future: Redis)
├─ Compression
└─ Connection pooling

MONITORING
├─ Application logs
├─ Error tracking
├─ Performance metrics
├─ WebSocket connection stats
└─ Database health checks
```

## 🔧 Development Workflow

```
CODE → BUILD → TEST → DEPLOY

1. CODE
   └─ Make changes in src/

2. BUILD
   └─ npm run build
      ├─ TypeScript compilation
      ├─ Validation
      └─ Output to dist/

3. TEST (Optional)
   └─ npm test

4. RUN
   └─ npm run start:dev  (development)
      npm run start:prod (production)
```

## 📚 File Organization

```
backend/
├── src/
│   ├── auth/              ◄── Authentication
│   ├── camera/            ◄── Camera Management
│   ├── event/             ◄── Event Processing + WebSocket
│   ├── lock/              ◄── GPIO/Lock Control
│   ├── user/              ◄── User Management
│   ├── prisma/            ◄── Database Service
│   ├── config/            ◄── Configuration
│   ├── app.module.ts      ◄── Main Module
│   └── main.ts            ◄── Entry Point
│
├── prisma/
│   ├── schema.prisma      ◄── Database Schema
│   ├── migrations/        ◄── Schema Versions
│   └── seed.ts            ◄── Initial Data
│
├── dist/                  ◄── Compiled Output
├── node_modules/
├── .env.example
├── QUICKSTART.md          ◄── Quick Start Guide
├── README_API.md          ◄── API Documentation
├── RESTRUCTURING_SUMMARY.md
└── package.json
```

## ✅ Health Check Points

```
On Startup:
1. Database connection ✓
2. JWT secret configured ✓
3. Environment variables loaded ✓
4. Prisma schema synced ✓
5. All modules initialized ✓
6. WebSocket ready ✓
7. API listening ✓

During Operation:
1. Database queries executing ✓
2. WebSocket clients connected ✓
3. JWT tokens valid ✓
4. Events being processed ✓
5. GPIO accessible ✓
```

This architecture is designed for:
- ✅ Real-time responsiveness
- ✅ Scalability
- ✅ Security
- ✅ Maintainability
- ✅ Easy integration with AI and frontend