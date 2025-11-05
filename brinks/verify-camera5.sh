#!/bin/bash
# Camera #5 Setup Verification Script

echo "🔍 SafeRoom Camera #5 Setup Verification"
echo "========================================="
echo ""

# Check 1: Backend IP
echo "✓ Checking backend IP..."
BACKEND_IP=$(hostname -I | awk '{print $1}')
echo "  Backend IP: $BACKEND_IP"
echo "  RTMP URL: rtmp://$BACKEND_IP:1935/live/camera5"
echo ""

# Check 2: FFmpeg installed
echo "✓ Checking FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    echo "  ✅ FFmpeg installed: $FFMPEG_VERSION"
else
    echo "  ❌ FFmpeg NOT installed!"
    echo "  Install: sudo apt-get install ffmpeg"
fi
echo ""

# Check 3: Python dependencies
echo "✓ Checking Python dependencies..."
if python3 -c "import requests" 2>/dev/null; then
    echo "  ✅ requests module installed"
else
    echo "  ⚠️  requests module not installed"
    echo "  Install: pip install requests"
fi
echo ""

# Check 4: Backend running
echo "✓ Checking backend status..."
if curl -s http://localhost:8000/status > /dev/null 2>&1; then
    echo "  ✅ Backend is running"
else
    echo "  ⚠️  Backend may not be running"
    echo "  Start: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
fi
echo ""

# Check 5: Files exist
echo "✓ Checking required files..."
FILES=(
    "rtmp_receiver.py"
    "start-rtmp-receiver.sh"
    ".rtmp-env"
    "CAMERA5_SUMMARY.md"
    "SETUP_PHONE_CAMERA5.md"
    "CAMERA5_INDEX.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file NOT FOUND"
    fi
done
echo ""

# Check 6: Scripts executable
echo "✓ Checking script permissions..."
if [ -x "rtmp_receiver.py" ]; then
    echo "  ✅ rtmp_receiver.py is executable"
else
    echo "  ⚠️  rtmp_receiver.py not executable (chmod +x rtmp_receiver.py)"
fi

if [ -x "start-rtmp-receiver.sh" ]; then
    echo "  ✅ start-rtmp-receiver.sh is executable"
else
    echo "  ⚠️  start-rtmp-receiver.sh not executable (chmod +x start-rtmp-receiver.sh)"
fi
echo ""

# Check 7: Camera configuration
echo "✓ Checking camera_system.py..."
if grep -q "camera5" camera_system.py 2>/dev/null; then
    echo "  ✅ Camera #5 configured in camera_system.py"
else
    echo "  ❌ Camera #5 NOT configured"
fi
echo ""

# Check 8: Port availability
echo "✓ Checking port 1935 (RTMP)..."
if netstat -tlnp 2>/dev/null | grep -q ":1935 "; then
    echo "  ⚠️  Port 1935 already in use"
else
    echo "  ✅ Port 1935 is available"
fi
echo ""

# Summary
echo "========================================="
echo "✅ Verification Complete!"
echo ""
echo "📱 Next Steps:"
echo "1. Start RTMP receiver: ./start-rtmp-receiver.sh"
echo "2. Configure Larix on iPhone (see CAMERA5_SUMMARY.md)"
echo "3. Open dashboard: http://$BACKEND_IP:8000/dashboard"
echo ""
echo "📚 Documentation:"
echo "   - Quick start: CAMERA5_SUMMARY.md"
echo "   - Setup guide: SETUP_PHONE_CAMERA5.md"
echo "   - Index: CAMERA5_INDEX.md"
echo ""
