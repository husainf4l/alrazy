# Al Razy Pharmacy Security System

A comprehensive FastAPI-based security monitoring system designed specifically for pharmacies, featuring AI-powered threat detection, real-time camera surveillance, and automated alert systems.

## 🏗️ **Project Structure (Best Practices)**

```
alrazy/
├── app/                           # Main application package
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # FastAPI application and lifespan management
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── api.py            # API router aggregation
│   │       └── endpoints/        # Individual endpoint modules
│   │           ├── __init__.py
│   │           ├── cameras.py    # Camera-related endpoints
│   │           ├── security.py   # Security endpoints
│   │           └── dashboards.py # Dashboard endpoints
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management
│   │   └── dependencies.py       # FastAPI dependencies
│   ├── models/                   # Data models and schemas
│   │   ├── __init__.py
│   │   ├── camera.py             # Camera-related models
│   │   └── security.py           # Security-related models
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── camera_service.py     # Camera management
│   │   ├── security_service.py   # Security orchestration
│   │   ├── recording_service.py  # Video recording
│   │   ├── webhook_service.py    # Webhook alerts
│   │   ├── llm_service.py        # LLM analysis
│   │   ├── activity_service.py   # Activity detection
│   │   └── websocket_service.py  # WebSocket management
│   ├── utils/                    # Utility functions
│   │   └── __init__.py           # Common utilities
│   └── static/                   # Static files (HTML, CSS, JS)
│       ├── index.html
│       ├── security-dashboard.html
│       ├── multi-camera.html
│       └── ...
├── tests/                        # Test suite
│   ├── __init__.py
│   └── conftest.py               # Test configuration
├── config.json                   # Application configuration
├── requirements.txt              # Python dependencies
├── run.py                        # Application entry point
└── README.md                     # This file
```

## 🚀 **Quick Start**

### 1. **Setup Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Configure System**
Edit `config.json` to match your environment:
```json
{
  "pharmacy_name": "Your Pharmacy Name",
  "camera_config": {
    "base_ip": "192.168.1.100",
    "username": "admin",
    "password": "your_password",
    "port": "554",
    "cameras": {
      "1": "/Streaming/Channels/101",
      "2": "/Streaming/Channels/201"
    }
  }
}
```

### 4. **Run Application**
```bash
python run.py
```

## 📋 **Available Endpoints**

### **Main Endpoints**
- **Root**: `http://localhost:8000/` - System status and navigation
- **Health**: `http://localhost:8000/health` - Health check
- **API Docs**: `http://localhost:8000/docs` - Interactive API documentation

### **Camera Endpoints**
- `GET /api/v1/cameras/info` - Get all cameras information
- `GET /api/v1/cameras/info/{camera_id}` - Get specific camera info
- `GET /api/v1/cameras/frames` - Get current frames from all cameras
- `GET /api/v1/cameras/frame/{camera_id}` - Get frame from specific camera
- `POST /api/v1/cameras/initialize` - Initialize all cameras
- `POST /api/v1/cameras/initialize/{camera_id}` - Initialize specific camera
- `GET /api/v1/cameras/motion/{camera_id}` - Detect motion in camera
- `GET /api/v1/cameras/list` - List available cameras

### **Security Endpoints**
- `GET /api/v1/security/status` - Get security system status
- `GET /api/v1/security/risk-assessment` - Get current risk assessment
- `GET /api/v1/security/events` - Get recent security events
- `GET /api/v1/security/analytics` - Get security analytics
- `POST /api/v1/security/process-frame/{camera_id}` - Analyze specific frame
- `POST /api/v1/security/test-llm` - Test LLM analysis functionality

### **Dashboard Endpoints**
- `GET /api/v1/dashboard/` - Main dashboard
- `GET /api/v1/dashboard/security` - Security monitoring dashboard
- `GET /api/v1/dashboard/multi-camera` - Multi-camera view
- `GET /api/v1/dashboard/analytics` - Analytics dashboard
- `GET /api/v1/dashboard/streaming` - Real-time streaming dashboard

## 🏗️ **Architecture Benefits**

### **1. Separation of Concerns**
- **API Layer**: Handles HTTP requests/responses and validation
- **Services Layer**: Contains business logic and external integrations
- **Models Layer**: Defines data structures and validation schemas
- **Core Layer**: Configuration and shared dependencies

### **2. Scalability**
- **Modular Design**: Easy to add new features or modify existing ones
- **Service Isolation**: Services can be easily extracted to microservices
- **API Versioning**: Support for multiple API versions

### **3. Maintainability**
- **Clear Structure**: Easy to navigate and understand
- **Type Safety**: Pydantic models ensure data validation
- **Dependency Injection**: Testable and flexible dependencies

### **4. Development Experience**
- **Auto-generated Documentation**: OpenAPI/Swagger docs
- **IDE Support**: Better autocomplete and error detection
- **Testing**: Structured testing with pytest

## 🔧 **Configuration**

The system uses a hierarchical configuration approach:

1. **config.json** - Main configuration file
2. **Environment Variables** - Override config values using `${ENV_VAR}` syntax
3. **Default Values** - Fallback to sensible defaults

### **Configuration Sections**
- `camera_config` - Camera connection settings
- `llm_config` - LLM analysis configuration
- `recording_config` - Video recording settings
- `webhook_config` - Alert webhook configuration
- `activity_detection` - Activity detection parameters

## 🚦 **Development**

### **Adding New Endpoints**
1. Create endpoint function in appropriate file under `app/api/v1/endpoints/`
2. Add models in `app/models/` if needed
3. Add business logic in `app/services/`
4. Update router in `app/api/v1/api.py`

### **Adding New Services**
1. Create service file in `app/services/`
2. Add service factory function
3. Update dependencies in `app/core/dependencies.py`

### **Running Tests**
```bash
pytest tests/
```

## 🔒 **Security Features**

- **Real-time Monitoring**: Continuous camera surveillance
- **AI-Powered Detection**: LLM-enhanced threat analysis
- **Automated Alerts**: Webhook notifications for security events
- **Activity Recognition**: Detection of suspicious behaviors
- **Video Recording**: Automatic recording of security incidents
- **Risk Assessment**: Continuous evaluation of pharmacy security status

## 📊 **Monitoring and Analytics**

- **System Health**: Real-time system status monitoring
- **Performance Metrics**: Camera performance and system statistics
- **Security Analytics**: Incident patterns and risk analysis
- **Activity Trends**: Historical activity and threat level tracking

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Cameras Not Connecting**
   - Check network connectivity to camera IP
   - Verify camera credentials
   - Use `/api/v1/cameras/test/{camera_id}` endpoint

2. **LLM Analysis Not Working**
   - Verify OpenAI API key in config
   - Check internet connectivity
   - Review LLM service logs

3. **Performance Issues**
   - Reduce camera frame quality in configuration
   - Limit concurrent camera connections
   - Monitor system resources

This restructured application follows FastAPI best practices and provides a solid foundation for scaling and maintaining the Al Razy Pharmacy Security System.
