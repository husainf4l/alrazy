#!/bin/bash

# Quick Camera Test Script
# Simple connectivity test for cameras at 149.200.251.12

CAMERA_IP="149.200.251.12"
PORTS=(554 555 556 557)

echo "🎥 Quick Camera Connectivity Test"
echo "=================================="
echo "Camera IP: $CAMERA_IP"
echo ""

# Test ping
echo "📡 Testing network connectivity..."
if ping -c 3 -W 1000 "$CAMERA_IP" >/dev/null 2>&1; then
    echo "✅ Camera IP is reachable"
else
    echo "❌ Camera IP is NOT reachable"
    exit 1
fi

echo ""
echo "🔌 Testing camera ports..."

# Test each port
for i in "${!PORTS[@]}"; do
    port="${PORTS[$i]}"
    echo -n "Camera $((i+1)) (port $port): "
    
    if timeout 5 bash -c "</dev/tcp/$CAMERA_IP/$port" 2>/dev/null; then
        echo "✅ OPEN"
    else
        echo "❌ CLOSED"
    fi
done

echo ""
echo "🌐 Testing Next.js server..."
if curl -s "http://localhost:3000" >/dev/null 2>&1; then
    echo "✅ Next.js server is running"
    
    echo ""
    echo "🔗 Testing camera API..."
    response=$(curl -s -X POST "http://localhost:3000/api/test-camera-connection" \
        -H "Content-Type: application/json" \
        -d '{"ip":"'$CAMERA_IP'","port":554,"username":"admin","password":"admin123","cameraId":"cam1"}')
    
    if echo "$response" | grep -q '"success":true'; then
        echo "✅ Camera API test successful"
    else
        echo "❌ Camera API test failed"
        echo "Response: $response"
    fi
else
    echo "❌ Next.js server is NOT running"
    echo "💡 Start with: npm run dev"
fi

echo ""
echo "📋 Manual test steps:"
echo "1. npm run dev"
echo "2. Open: http://localhost:3000/dashboard"
echo "3. Click 'Start' on each camera"
echo ""
