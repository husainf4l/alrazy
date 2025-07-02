# Camera Testing Guide

## Overview

This guide provides comprehensive testing procedures for the camera dashboard system using the updated IP address `149.200.251.12`.

## Quick Start Testing

### 1. Basic Connectivity Test

```bash
# Quick network and port test
npm run test:cameras:quick
# or
./quick-camera-test.sh
```

### 2. Comprehensive Test Suite

```bash
# Full test suite with detailed reporting
npm run test:cameras:full
# or
./test-camera-dashboard.sh
```

### 3. Node.js API Test

```bash
# Test all APIs and components
npm run test:cameras
# or
node test-cameras.js
```

## Testing Scripts Overview

### 1. `quick-camera-test.sh`

**Purpose**: Fast connectivity check  
**Tests**:

- Network ping to camera IP
- Port connectivity (554, 555, 556, 557)
- Next.js server status
- Basic API endpoint test

**Usage**:

```bash
./quick-camera-test.sh
```

### 2. `test-camera-dashboard.sh`

**Purpose**: Comprehensive system testing  
**Tests**:

- Network connectivity
- Port accessibility
- RTSP stream validation (requires ffmpeg)
- All API endpoints
- Component file integrity
- TypeScript compilation
- Dependencies check

**Usage**:

```bash
./test-camera-dashboard.sh
```

**Output**: Creates detailed log file with timestamp

### 3. `test-cameras.js`

**Purpose**: Node.js based testing suite  
**Tests**:

- Network connectivity
- Port testing
- API endpoint validation
- File existence and integrity
- Component imports

**Usage**:

```bash
node test-cameras.js
```

## Camera Configuration

### Current Setup

- **IP Address**: 149.200.251.12
- **Credentials**: admin/admin123
- **Cameras**:
  - Camera 1: Port 554 - Main Security Camera
  - Camera 2: Port 555 - Secondary Camera
  - Camera 3: Port 556 - Backup Camera
  - Camera 4: Port 557 - Auxiliary Camera

### RTSP URLs

```
Camera 1: rtsp://admin:admin123@149.200.251.12:554/stream1
Camera 2: rtsp://admin:admin123@149.200.251.12:555/stream2
Camera 3: rtsp://admin:admin123@149.200.251.12:556/stream3
Camera 4: rtsp://admin:admin123@149.200.251.12:557/stream4
```

## Manual Testing Procedures

### 1. Start Development Server

```bash
npm run dev
```

### 2. Access Dashboard

1. Open browser to: `http://localhost:3000/dashboard`
2. Login if required
3. Navigate to "Live Camera Feeds" section

### 3. Test Camera Functions

#### Basic Stream Testing

1. Click "Start" button on each camera
2. Verify connection status indicators:
   - 🟢 Green: Connected and streaming
   - 🔴 Red: Error or disconnected
   - ⚫ Gray: Offline/not connected

#### Advanced Features Testing

1. **Fullscreen Mode**: Click expand icon (⛶) to test fullscreen
2. **Error Recovery**: Test retry functionality if connections fail
3. **System Status**: Monitor live statistics at bottom of dashboard
4. **Responsive Design**: Test on different screen sizes

### 4. API Testing with curl

#### Test Camera Connection

```bash
curl -X POST http://localhost:3000/api/test-camera-connection \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "149.200.251.12",
    "port": 554,
    "username": "admin",
    "password": "admin123",
    "cameraId": "cam1"
  }'
```

#### Test WebSocket Endpoint

```bash
curl "http://localhost:3000/api/camera-websocket?cameraId=cam1&ip=149.200.251.12&port=554"
```

## Troubleshooting

### Common Issues

#### 1. Camera Not Reachable

**Symptoms**: Network ping fails  
**Solutions**:

- Verify camera IP address
- Check network connectivity
- Ensure camera is powered on
- Verify firewall settings

#### 2. Port Connection Failed

**Symptoms**: Ports appear closed  
**Solutions**:

- Check camera port configuration
- Verify RTSP service is running
- Test with different port numbers
- Check camera firewall settings

#### 3. API Errors

**Symptoms**: API tests fail  
**Solutions**:

- Ensure Next.js server is running (`npm run dev`)
- Check API endpoint implementations
- Verify request/response formats
- Check server logs for errors

#### 4. Component Not Loading

**Symptoms**: Dashboard shows errors  
**Solutions**:

- Verify enhanced component file exists
- Check TypeScript compilation (`npm run build`)
- Ensure proper imports in dashboard
- Check browser console for errors

### Advanced Debugging

#### 1. Test RTSP Stream Directly

```bash
# Install ffmpeg if not available
brew install ffmpeg  # macOS
# or
sudo apt install ffmpeg  # Ubuntu

# Test stream playback
ffplay -fflags nobuffer -rtsp_transport tcp rtsp://admin:admin123@149.200.251.12:554/stream1
```

#### 2. Monitor Network Traffic

```bash
# Monitor camera network activity
sudo tcpdump -i any host 149.200.251.12
```

#### 3. Check Server Logs

```bash
# Watch Next.js server logs
npm run dev
# Check browser developer console
# Check network tab in browser dev tools
```

## Expected Test Results

### Successful Test Output

```
🎥 Camera Dashboard Test Suite
================================
✅ Network Ping: PASS Camera IP 149.200.251.12 is reachable
✅ Port 554 (Main Security Camera): PASS Port is open
✅ Port 555 (Secondary Camera): PASS Port is open
✅ Port 556 (Backup Camera): PASS Port is open
✅ Port 557 (Auxiliary Camera): PASS Port is open
✅ Next.js Server: PASS Server is running
✅ API Test - Camera 1: PASS Connection test successful
✅ Enhanced Component: PASS File exists and has content
✅ Dashboard Integration: PASS Imports enhanced component
```

### When Tests Fail

- Check the specific error messages
- Review the generated log files
- Follow troubleshooting steps above
- Verify camera hardware and network setup

## Performance Testing

### Load Testing

```bash
# Test multiple simultaneous connections
for i in {1..4}; do
  curl -X POST http://localhost:3000/api/test-camera-connection \
    -H "Content-Type: application/json" \
    -d "{\"ip\":\"149.200.251.12\",\"port\":$((553+i)),\"cameraId\":\"cam$i\"}" &
done
wait
```

### Memory Usage

```bash
# Monitor Node.js memory usage
node --inspect test-cameras.js
# Open chrome://inspect in browser
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/camera-tests.yml
name: Camera Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: "18"
      - run: npm install
      - run: npm run test:cameras
```

---

## Support

For issues or questions:

1. Check the generated log files
2. Review browser developer console
3. Verify camera network configuration
4. Test with alternative RTSP clients
5. Check component TypeScript compilation
