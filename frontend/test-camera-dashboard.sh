#!/bin/bash

# Camera Dashboard Test Script
# Tests connectivity, API endpoints, and camera functionality
# Updated for IP: 149.200.251.12

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Camera configuration
CAMERA_IP="149.200.251.12"
CAMERA_USERNAME="admin"
CAMERA_PASSWORD="admin123"
PORTS=(554 555 556 557)
CAMERA_NAMES=("Main Security Camera" "Secondary Camera" "Backup Camera" "Auxiliary Camera")

# API base URL (adjust if needed)
API_BASE="http://localhost:3000/api"

# Log file
LOG_FILE="camera_test_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}🎥 Camera Dashboard Test Suite${NC}"
echo -e "${BLUE}================================${NC}"
echo "Camera IP: $CAMERA_IP"
echo "Test Log: $LOG_FILE"
echo ""

# Function to log messages
log_message() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $message" >> "$LOG_FILE"
}

# Function to print test result
print_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    if [ "$result" = "PASS" ]; then
        echo -e "✅ ${GREEN}$test_name: PASS${NC} $details"
        log_message "PASS" "$test_name: $details"
    elif [ "$result" = "FAIL" ]; then
        echo -e "❌ ${RED}$test_name: FAIL${NC} $details"
        log_message "FAIL" "$test_name: $details"
    elif [ "$result" = "WARN" ]; then
        echo -e "⚠️  ${YELLOW}$test_name: WARNING${NC} $details"
        log_message "WARN" "$test_name: $details"
    else
        echo -e "ℹ️  ${BLUE}$test_name: INFO${NC} $details"
        log_message "INFO" "$test_name: $details"
    fi
}

# Test 1: Basic Network Connectivity
echo -e "${YELLOW}📡 Testing Network Connectivity...${NC}"
echo ""

if ping -c 3 -W 1000 "$CAMERA_IP" >/dev/null 2>&1; then
    print_result "Network Ping" "PASS" "Camera IP $CAMERA_IP is reachable"
else
    print_result "Network Ping" "FAIL" "Camera IP $CAMERA_IP is not reachable"
fi

# Test 2: Port Connectivity
echo ""
echo -e "${YELLOW}🔌 Testing Port Connectivity...${NC}"
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

# Test 3: RTSP URL Testing
echo ""
echo -e "${YELLOW}📺 Testing RTSP URLs...${NC}"
echo ""

for i in "${!PORTS[@]}"; do
    port="${PORTS[$i]}"
    camera_name="${CAMERA_NAMES[$i]}"
    rtsp_url="rtsp://$CAMERA_USERNAME:$CAMERA_PASSWORD@$CAMERA_IP:$port/stream$((i+1))"
    
    # Test RTSP URL with timeout
    if command -v ffprobe >/dev/null 2>&1; then
        if timeout 10 ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$rtsp_url" >/dev/null 2>&1; then
            print_result "RTSP Stream $((i+1))" "PASS" "Stream accessible at $rtsp_url"
        else
            print_result "RTSP Stream $((i+1))" "FAIL" "Stream not accessible at $rtsp_url"
        fi
    else
        print_result "RTSP Stream $((i+1))" "WARN" "ffprobe not available - install ffmpeg to test RTSP streams"
    fi
done

# Test 4: Check if Next.js server is running
echo ""
echo -e "${YELLOW}🌐 Testing Next.js Server...${NC}"
echo ""

if curl -s "http://localhost:3000" >/dev/null 2>&1; then
    print_result "Next.js Server" "PASS" "Server is running on http://localhost:3000"
    SERVER_RUNNING=true
else
    print_result "Next.js Server" "FAIL" "Server is not running on http://localhost:3000"
    SERVER_RUNNING=false
fi

# Test 5: API Endpoints (only if server is running)
if [ "$SERVER_RUNNING" = true ]; then
    echo ""
    echo -e "${YELLOW}🔗 Testing API Endpoints...${NC}"
    echo ""
    
    # Test camera connection API
    for i in "${!PORTS[@]}"; do
        port="${PORTS[$i]}"
        camera_id="cam$((i+1))"
        
        response=$(curl -s -X POST "$API_BASE/test-camera-connection" \
            -H "Content-Type: application/json" \
            -d "{\"ip\":\"$CAMERA_IP\",\"port\":$port,\"username\":\"$CAMERA_USERNAME\",\"password\":\"$CAMERA_PASSWORD\",\"cameraId\":\"$camera_id\"}" \
            -w "%{http_code}")
        
        http_code="${response: -3}"
        response_body="${response%???}"
        
        if [ "$http_code" = "200" ]; then
            # Check if response contains success
            if echo "$response_body" | grep -q '"success":true'; then
                print_result "API Test Connection - Camera $((i+1))" "PASS" "Connection test successful"
            else
                print_result "API Test Connection - Camera $((i+1))" "FAIL" "Connection test failed: $response_body"
            fi
        else
            print_result "API Test Connection - Camera $((i+1))" "FAIL" "HTTP $http_code: $response_body"
        fi
    done
    
    # Test camera websocket endpoint
    echo ""
    for i in "${!PORTS[@]}"; do
        camera_id="cam$((i+1))"
        
        response=$(curl -s "$API_BASE/camera-websocket?cameraId=$camera_id&ip=$CAMERA_IP&port=${PORTS[$i]}" -w "%{http_code}")
        http_code="${response: -3}"
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "426" ]; then
            print_result "API WebSocket - Camera $((i+1))" "PASS" "WebSocket endpoint responding"
        else
            print_result "API WebSocket - Camera $((i+1))" "FAIL" "HTTP $http_code"
        fi
    done
fi

# Test 6: Component Files Check
echo ""
echo -e "${YELLOW}📁 Testing Component Files...${NC}"
echo ""

# Check if enhanced component exists
if [ -f "src/components/CameraStreamGridEnhanced.tsx" ]; then
    file_size=$(stat -f%z "src/components/CameraStreamGridEnhanced.tsx" 2>/dev/null || stat -c%s "src/components/CameraStreamGridEnhanced.tsx" 2>/dev/null)
    if [ "$file_size" -gt 1000 ]; then
        print_result "Enhanced Component File" "PASS" "File exists and has content ($file_size bytes)"
    else
        print_result "Enhanced Component File" "FAIL" "File exists but appears empty or too small ($file_size bytes)"
    fi
else
    print_result "Enhanced Component File" "FAIL" "CameraStreamGridEnhanced.tsx not found"
fi

# Check dashboard page
if [ -f "src/app/dashboard/page.tsx" ]; then
    if grep -q "CameraStreamGridEnhanced" "src/app/dashboard/page.tsx"; then
        print_result "Dashboard Integration" "PASS" "Dashboard imports enhanced component"
    else
        print_result "Dashboard Integration" "FAIL" "Dashboard does not import enhanced component"
    fi
else
    print_result "Dashboard Integration" "FAIL" "Dashboard page not found"
fi

# Test 7: Dependencies Check
echo ""
echo -e "${YELLOW}📦 Testing Dependencies...${NC}"
echo ""

if [ -f "package.json" ]; then
    # Check for required dependencies
    required_deps=("lucide-react" "ws" "next")
    for dep in "${required_deps[@]}"; do
        if grep -q "\"$dep\":" package.json; then
            print_result "Dependency: $dep" "PASS" "Found in package.json"
        else
            print_result "Dependency: $dep" "FAIL" "Missing from package.json"
        fi
    done
else
    print_result "Package.json" "FAIL" "package.json not found"
fi

# Test 8: TypeScript Compilation
echo ""
echo -e "${YELLOW}🔧 Testing TypeScript Compilation...${NC}"
echo ""

if command -v npm >/dev/null 2>&1; then
    if npm run build >/dev/null 2>&1; then
        print_result "TypeScript Build" "PASS" "Project builds successfully"
    else
        print_result "TypeScript Build" "FAIL" "Build failed - check for TypeScript errors"
    fi
else
    print_result "TypeScript Build" "WARN" "npm not available"
fi

# Summary
echo ""
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"

pass_count=$(grep -c "PASS" "$LOG_FILE" || echo "0")
fail_count=$(grep -c "FAIL" "$LOG_FILE" || echo "0")
warn_count=$(grep -c "WARN" "$LOG_FILE" || echo "0")

echo -e "✅ Passed: ${GREEN}$pass_count${NC}"
echo -e "❌ Failed: ${RED}$fail_count${NC}"
echo -e "⚠️  Warnings: ${YELLOW}$warn_count${NC}"
echo ""

if [ "$fail_count" -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed! Camera dashboard should be working.${NC}"
    exit_code=0
else
    echo -e "${RED}❌ Some tests failed. Check the issues above.${NC}"
    exit_code=1
fi

# Manual test instructions
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
echo "4. Monitor system status at bottom of dashboard"
echo ""

# Camera testing script
echo -e "${BLUE}📋 Quick Camera Test Commands:${NC}"
echo -e "${BLUE}===============================${NC}"
echo ""
echo "# Test specific camera RTSP stream:"
for i in "${!PORTS[@]}"; do
    echo "# Camera $((i+1)) - ${CAMERA_NAMES[$i]}"
    echo "ffplay -fflags nobuffer -rtsp_transport tcp rtsp://$CAMERA_USERNAME:$CAMERA_PASSWORD@$CAMERA_IP:${PORTS[$i]}/stream$((i+1))"
    echo ""
done

echo "# Test camera with curl:"
echo "curl -X POST http://localhost:3000/api/test-camera-connection \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"ip\":\"$CAMERA_IP\",\"port\":554,\"username\":\"$CAMERA_USERNAME\",\"password\":\"$CAMERA_PASSWORD\",\"cameraId\":\"cam1\"}'"
echo ""

echo "Test log saved to: $LOG_FILE"
echo ""

exit $exit_code
