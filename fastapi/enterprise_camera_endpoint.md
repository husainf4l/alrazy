# Enterprise Camera Management Endpoint

## Endpoint Information

**URL:** `POST /api/v1/cameras/add-enterprise`

**Description:** Add a camera with advanced enterprise features including multi-user access, admin assignment, and automatic connection testing.

**Authentication:** Bearer Token Required

---

## Request Body Schema

```json
{
  "name": "string (required)",
  "rtsp_url": "string (required)",
  "location": "string (optional)",
  "description": "string (optional)",
  "camera_type": "rtsp|http|usb|ip (optional, default: rtsp)",
  "username": "string (optional)",
  "password": "string (optional)",
  "ip_address": "string (optional)",
  "port": "integer (optional, default: 554)",
  "is_active": "boolean (optional, default: true)",
  "user_ids": ["array of integers (optional)"],
  "admin_user_id": "integer (optional)"
}
```

---

## Postman Example

### 1. Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### 2. Request Body (JSON)
```json
{
  "name": "Main Entrance Camera",
  "rtsp_url": "rtsp://admin:password123@192.168.1.100:554/stream",
  "location": "Main Entrance - Ground Floor",
  "description": "Primary security camera monitoring the main entrance",
  "camera_type": "rtsp",
  "username": "admin",
  "password": "password123",
  "ip_address": "192.168.1.100",
  "port": 554,
  "is_active": true,
  "user_ids": [2, 3, 5, 8],
  "admin_user_id": 3
}
```

### 3. Example Response (Success)
```json
{
  "success": true,
  "message": "Enterprise camera added successfully",
  "camera": {
    "id": 12,
    "name": "Main Entrance Camera",
    "rtsp_url": "rtsp://admin:password123@192.168.1.100:554/stream",
    "location": "Main Entrance - Ground Floor",
    "is_active": true,
    "admin_user_id": 3,
    "user_id": 1,
    "company_id": 1,
    "created_at": "2025-07-01T10:30:45"
  },
  "access_info": {
    "primary_owner": 1,
    "admin_user": 3,
    "additional_users": [2, 3, 5, 8],
    "company_id": 1
  },
  "test_result": {
    "connection_successful": true,
    "resolution": "1920x1080",
    "frame_shape": [1080, 1920, 3]
  }
}
```

### 4. Example Response (Connection Failed)
```json
{
  "success": false,
  "step": "connection_test",
  "message": "Camera connection failed - camera not added",
  "test_result": {
    "rtsp_url": "rtsp://admin:password123@192.168.1.100:554/stream",
    "error": "Could not connect to camera with any backend",
    "error_details": "Connection failed with all available backends"
  },
  "recommendations": [
    "Check if the RTSP URL is correct",
    "Verify camera IP address and port",
    "Check username/password credentials",
    "Ensure camera is online and accessible",
    "Test the URL in VLC or another media player first"
  ]
}
```

---

## Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the camera |
| `rtsp_url` | string | Yes | Complete RTSP URL (rtsp://user:pass@ip:port/path) |
| `location` | string | No | Physical location description |
| `description` | string | No | Additional details about the camera |
| `camera_type` | enum | No | Camera type (default: "rtsp") |
| `username` | string | No | Camera username (if separate from URL) |
| `password` | string | No | Camera password (if separate from URL) |
| `ip_address` | string | No | Camera IP address |
| `port` | integer | No | Camera port (default: 554) |
| `is_active` | boolean | No | Enable/disable camera (default: true) |
| `user_ids` | array | No | List of user IDs to grant camera access |
| `admin_user_id` | integer | No | User ID who will be the camera admin |

---

## Authentication

Get your Bearer token from the login endpoint:

**Login URL:** `POST /api/v1/auth/login`

```json
{
  "username": "husain",
  "password": "tt55oo77"
}
```

Use the `access_token` from the response as Bearer token.

---

## cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/cameras/add-enterprise" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Entrance Camera",
    "rtsp_url": "rtsp://admin:password123@192.168.1.100:554/stream",
    "location": "Main Entrance - Ground Floor",
    "description": "Primary security camera monitoring the main entrance",
    "user_ids": [2, 3, 5, 8],
    "admin_user_id": 3
  }'
```

---

## Features

✅ **Automatic Connection Testing** - Tests camera before saving  
✅ **Multi-User Access** - Grant access to multiple users  
✅ **Admin Assignment** - Assign a specific admin for the camera  
✅ **Company Integration** - Automatically assigned to user's company  
✅ **Detailed Error Messages** - Clear troubleshooting information  
✅ **RTSP URL Validation** - Validates connection and captures test frame  

---

## Testing in Postman

1. **Import Collection:** Create a new collection in Postman
2. **Set Variables:** 
   - `base_url`: `http://localhost:8000`
   - `auth_token`: Your JWT token
3. **Authentication:** Use `{{auth_token}}` in Authorization header
4. **Test Connection First:** Use `/cameras/test-only` endpoint to validate RTSP URL
5. **Add Camera:** Use `/cameras/add-enterprise` with validated URL

---

## Next Level Features

This endpoint provides the foundation for enterprise camera management:

- **Multi-tenant support** with company isolation
- **Role-based access control** with admin/viewer permissions
- **Automatic camera testing** before database insertion
- **User access management** with granular permissions
- **Audit trail** with creation timestamps and user tracking

Perfect for SaaS-level camera management systems! 🚀
