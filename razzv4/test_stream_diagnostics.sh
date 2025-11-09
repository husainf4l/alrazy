#!/bin/bash

# Test script to diagnose stream 500 errors
# Run this from the razzv4 directory

set -e

BACKEND_PORT=${BACKEND_PORT:-8000}
WEBRTC_PORT=${WEBRTC_PORT:-8083}
LOG_FILE="RTSPtoWebRTC/logs/rtsp-webrtc-0.log"

echo "═══════════════════════════════════════════════════════"
echo "Stream 500 Error Diagnostic Test"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check if services are running
echo "1️⃣  Checking if services are running..."
echo ""

if ! nc -z localhost $WEBRTC_PORT 2>/dev/null; then
    echo "❌ RTSPtoWebRTC service NOT running on port $WEBRTC_PORT"
    echo "   Start it with: cd RTSPtoWebRTC && ./rtsp-to-webrtc"
    exit 1
else
    echo "✅ RTSPtoWebRTC service is running on port $WEBRTC_PORT"
fi

if ! nc -z localhost $BACKEND_PORT 2>/dev/null; then
    echo "❌ Backend service NOT running on port $BACKEND_PORT"
    echo "   Start it with: cd RAZZv4-backend && python main.py"
    exit 1
else
    echo "✅ Backend service is running on port $BACKEND_PORT"
fi

echo ""
echo "2️⃣  Testing RTSPtoWebRTC /stream endpoint directly..."
echo ""

# Test with a dummy RTSP URL
TEST_RESPONSE=$(curl -s -X POST http://localhost:$WEBRTC_PORT/stream \
    -d "url=rtsp://test:test@192.168.1.1:554/test" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -n1)
BODY=$(echo "$TEST_RESPONSE" | head -n-1)

echo "HTTP Status: $HTTP_CODE"
echo "Response: $BODY"
echo ""

if [ "$HTTP_CODE" = "500" ]; then
    echo "❌ RTSPtoWebRTC returned 500 (this is expected for unreachable camera)"
    if echo "$BODY" | grep -q "dial tcp"; then
        echo "   Issue: Cannot connect to camera (network/camera offline)"
    elif echo "$BODY" | grep -q "404"; then
        echo "   Issue: RTSP path not found on camera"
    fi
else
    echo "⚠️  Unexpected HTTP code. Check if RTSPtoWebRTC is configured correctly"
fi

echo ""
echo "3️⃣  Checking backend's database for cameras..."
echo ""

# Try to connect to backend and get vault rooms
VAULT_RESPONSE=$(curl -s http://localhost:$BACKEND_PORT/vault-rooms/ 2>/dev/null || echo "{}")

if echo "$VAULT_RESPONSE" | grep -q "vault_rooms"; then
    ROOM_COUNT=$(echo "$VAULT_RESPONSE" | grep -o '"id"' | wc -l)
    echo "✅ Found database connection"
    echo "   Vault rooms: $ROOM_COUNT"
    echo ""
    echo "   $VAULT_RESPONSE" | head -c 500
    echo "..."
else
    echo "❌ Could not fetch vault rooms from backend"
    echo "   Response: $VAULT_RESPONSE"
fi

echo ""
echo ""
echo "4️⃣  Checking RTSPtoWebRTC logs for errors..."
echo ""

if [ -f "$LOG_FILE" ]; then
    echo "Recent errors in log:"
    grep -i "error\|failed\|500" "$LOG_FILE" 2>/dev/null | tail -10 || echo "No errors found"
    echo ""
    echo "Recent stream attempts:"
    grep "Stream Try Connect\|Stream Codec Not Found" "$LOG_FILE" 2>/dev/null | tail -5 || echo "No stream attempts found"
else
    echo "⚠️  Log file not found at $LOG_FILE"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "Summary:"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "If you see 'Failed to initialize stream: 500':"
echo ""
echo "1. Check RTSPtoWebRTC logs for the actual error:"
echo "   tail -f $LOG_FILE"
echo ""
echo "2. Test RTSP URL directly from this machine:"
echo "   ffprobe -v error 'rtsp://user:pass@camera-ip:554/path'"
echo ""
echo "3. Verify camera RTSP URLs in database:"
echo "   sqlite3 RAZZv4-backend/data.db '.schema cameras' '.mode column' 'SELECT * FROM cameras;'"
echo ""
echo "4. Restart both services:"
echo "   pkill -f 'rtsp-to-webrtc' && sleep 2"
echo "   cd RAZZv4-backend && python main.py &"
echo "   cd RTSPtoWebRTC && ./rtsp-to-webrtc &"
