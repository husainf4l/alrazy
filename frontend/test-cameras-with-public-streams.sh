#!/bin/bash

# Enhanced Camera Test Script with Public RTSP Streams
# Tests both your cameras (149.200.251.12) and public test cameras

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Camera configurations
CAMERA_IP="149.200.251.12"
CAMERA_USERNAME="admin"
CAMERA_PASSWORD="admin123"
PORTS=(554 555 556 557)
CAMERA_NAMES=("Main Security Camera" "Secondary Camera" "Backup Camera" "Auxiliary Camera")

# Public test RTSP streams for comparison
declare -A PUBLIC_CAMERAS=(
    ["Big Buck Bunny"]="rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
    ["Sample Stream 1"]="rtsp://rtsp.stream/pattern"
    ["Test Camera"]="rtsp://demo:demo@ipvmdemo.dyndns.org:5541/onvif-media/media.amp?profile=profile_1_h264"
    ["MJPEG Test"]="http://webcam.st-malo.com/axis-cgi/mjpg/video.cgi"
)

# API base URL
API_BASE="http://localhost:3000/api"

# Log file
LOG_FILE="enhanced_camera_test_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}🎥 Enhanced Camera Test Suite with Public Streams${NC}"
echo -e "${BLUE}====================================================${NC}"
echo ""
echo "Primary Camera IP: $CAMERA_IP"
echo "Public Test Streams: ${#PUBLIC_CAMERAS[@]} streams"
echo "Log file: $LOG_FILE"
echo ""

# Initialize counters
total_tests=0
passed_tests=0

function log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1: $2" >> "$LOG_FILE"
}

function print_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    
    total_tests=$((total_tests + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "✅ ${GREEN}$test_name: PASS${NC} $details"
        log_message "PASS" "$test_name: $details"
        passed_tests=$((passed_tests + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "❌ ${RED}$test_name: FAIL${NC} $details"
        log_message "FAIL" "$test_name: $details"
    else
        echo -e "⚠️  ${YELLOW}$test_name: WARN${NC} $details"
        log_message "WARN" "$test_name: $details"
    fi
}

# Test 1: Network Connectivity
echo -e "${YELLOW}📡 Testing Network Connectivity...${NC}"
echo ""

if ping -c 3 -W 1000 "$CAMERA_IP" >/dev/null 2>&1; then
    print_result "Primary Camera Network" "PASS" "Camera IP $CAMERA_IP is reachable"
else
    print_result "Primary Camera Network" "FAIL" "Camera IP $CAMERA_IP is not reachable"
fi

# Test 2: Port Connectivity for Primary Cameras
echo ""
echo -e "${YELLOW}🔌 Testing Primary Camera Ports...${NC}"
echo ""

for i in "${!PORTS[@]}"; do
    port="${PORTS[$i]}"
    camera_name="${CAMERA_NAMES[$i]}"
    
    if timeout 5 bash -c "</dev/tcp/$CAMERA_IP/$port" 2>/dev/null; then
        print_result "Port $port ($camera_name)" "PASS" "Port is open and accessible"
    else
        print_result "Port $port ($camera_name)" "FAIL" "Port is closed or inaccessible"
    fi
done

# Test 3: Public RTSP Streams
echo ""
echo -e "${PURPLE}🌍 Testing Public RTSP Streams...${NC}"
echo ""

if command -v ffprobe >/dev/null 2>&1; then
    for camera_name in "${!PUBLIC_CAMERAS[@]}"; do
        rtsp_url="${PUBLIC_CAMERAS[$camera_name]}"
        echo "Testing: $camera_name"
        
        if timeout 10 ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$rtsp_url" >/dev/null 2>&1; then
            print_result "Public Stream: $camera_name" "PASS" "Stream accessible"
        else
            print_result "Public Stream: $camera_name" "FAIL" "Stream not accessible"
        fi
    done
else
    print_result "Public RTSP Test" "WARN" "ffprobe not available - install ffmpeg to test public streams"
fi

# Test 4: Primary Camera RTSP URLs
echo ""
echo -e "${YELLOW}📺 Testing Primary Camera RTSP URLs...${NC}"
echo ""

if command -v ffprobe >/dev/null 2>&1; then
    for i in "${!PORTS[@]}"; do
        port="${PORTS[$i]}"
        camera_name="${CAMERA_NAMES[$i]}"
        rtsp_url="rtsp://$CAMERA_USERNAME:$CAMERA_PASSWORD@$CAMERA_IP:$port/stream$((i+1))"
        
        if timeout 10 ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$rtsp_url" >/dev/null 2>&1; then
            print_result "RTSP $camera_name" "PASS" "Stream accessible"
        else
            print_result "RTSP $camera_name" "FAIL" "Stream not accessible"
        fi
    done
else
    echo -e "${YELLOW}⚠️  ffprobe not available. Install ffmpeg to test RTSP streams:${NC}"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    echo ""
fi

# Test 5: Next.js Server
echo ""
echo -e "${YELLOW}🌐 Testing Next.js Server...${NC}"
echo ""

if curl -s "http://localhost:3000" >/dev/null 2>&1; then
    print_result "Next.js Server" "PASS" "Server is running on http://localhost:3000"
    server_running=true
else
    print_result "Next.js Server" "FAIL" "Server is not running on http://localhost:3000"
    server_running=false
fi

# Test 6: API Endpoints (if server is running)
if [ "$server_running" = true ]; then
    echo ""
    echo -e "${YELLOW}🔗 Testing API Endpoints...${NC}"
    echo ""
    
    # Test camera connection API
    for i in "${!PORTS[@]}"; do
        port="${PORTS[$i]}"
        camera_name="${CAMERA_NAMES[$i]}"
        camera_id="cam$((i+1))"
        
        response=$(curl -s -X POST "http://localhost:3000/api/test-camera-connection" \
            -H "Content-Type: application/json" \
            -d "{\"ip\":\"$CAMERA_IP\",\"port\":$port,\"username\":\"$CAMERA_USERNAME\",\"password\":\"$CAMERA_PASSWORD\",\"cameraId\":\"$camera_id\"}")
        
        if echo "$response" | grep -q '"success":true'; then
            print_result "API $camera_name" "PASS" "Connection test successful"
        else
            print_result "API $camera_name" "FAIL" "Connection test failed"
        fi
    done
    
    # Test WebSocket endpoint
    ws_response=$(curl -s "http://localhost:3000/api/camera-websocket?cameraId=cam1&ip=$CAMERA_IP&port=554")
    if echo "$ws_response" | grep -q '"status":"available"'; then
        print_result "WebSocket API" "PASS" "Endpoint responding correctly"
    else
        print_result "WebSocket API" "FAIL" "Endpoint not responding correctly"
    fi
fi

# Test 7: Component Files
echo ""
echo -e "${YELLOW}📁 Testing Component Files...${NC}"
echo ""

if [ -f "src/components/CameraStreamGridEnhanced.tsx" ] && [ -s "src/components/CameraStreamGridEnhanced.tsx" ]; then
    print_result "Enhanced Component" "PASS" "File exists and has content"
else
    print_result "Enhanced Component" "FAIL" "File missing or empty"
fi

if grep -q "CameraStreamGridEnhanced" "src/app/dashboard/page.tsx" 2>/dev/null; then
    print_result "Dashboard Integration" "PASS" "Uses enhanced component"
else
    print_result "Dashboard Integration" "FAIL" "Not using enhanced component"
fi

# Summary
echo ""
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"
echo -e "✅ Passed: ${GREEN}$passed_tests${NC}"
echo -e "❌ Failed: ${RED}$((total_tests - passed_tests))${NC}"
echo -e "📊 Total: ${BLUE}$total_tests${NC}"
echo ""

if [ "$passed_tests" -eq "$total_tests" ]; then
    echo -e "${GREEN}🎉 All tests passed! Camera dashboard should be working perfectly.${NC}"
    exit_code=0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Check the issues above.${NC}"
    exit_code=1
fi

# Add public test camera to your dashboard
echo ""
echo -e "${PURPLE}🔧 Adding Public Test Camera to Dashboard...${NC}"
echo ""

if [ "$server_running" = true ]; then
    echo "You can add these public test cameras to your component:"
    echo ""
    for camera_name in "${!PUBLIC_CAMERAS[@]}"; do
        rtsp_url="${PUBLIC_CAMERAS[$camera_name]}"
        echo "// $camera_name"
        echo "{"
        echo "  id: 'public_$(echo "$camera_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')',"
        echo "  name: '$camera_name',"
        echo "  ip: 'public',"
        echo "  port: 554,"
        echo "  rtspUrl: '$rtsp_url',"
        echo "  username: '',"
        echo "  password: '',"
        echo "  status: 'offline'"
        echo "},"
        echo ""
    done
fi

# Manual testing instructions
echo ""
echo -e "${BLUE}🧪 Manual Testing Instructions:${NC}"
echo -e "${BLUE}================================${NC}"
echo "1. Start the development server:"
echo "   npm run dev"
echo ""
echo "2. Open browser to: http://localhost:3000/dashboard"
echo ""
echo "3. Test camera functionality:"
echo "   - Click 'Start' button on each camera"
echo "   - Check connection status indicators"
echo "   - Test fullscreen mode (expand button)"
echo "   - Verify error handling (if cameras fail)"
echo ""
echo "4. Test with public streams:"
echo "   - Add public test cameras to your component"
echo "   - Verify streaming works with known good streams"
echo "   - Compare performance between your cameras and test streams"
echo ""

# VLC Testing Commands
echo -e "${PURPLE}🎬 VLC Test Commands:${NC}"
echo -e "${PURPLE}=====================${NC}"
echo "Test your cameras with VLC:"
for i in "${!PORTS[@]}"; do
    port="${PORTS[$i]}"
    camera_name="${CAMERA_NAMES[$i]}"
    echo "# $camera_name"
    echo "vlc --intf dummy --extraintf http --http-password vlc rtsp://$CAMERA_USERNAME:$CAMERA_PASSWORD@$CAMERA_IP:$port/stream$((i+1))"
done

echo ""
echo "Test public streams with VLC:"
for camera_name in "${!PUBLIC_CAMERAS[@]}"; do
    rtsp_url="${PUBLIC_CAMERAS[$camera_name]}"
    echo "# $camera_name"
    echo "vlc '$rtsp_url'"
done

echo ""
echo "Test log saved to: $LOG_FILE"
echo ""

exit $exit_code
