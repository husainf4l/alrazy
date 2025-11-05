#!/bin/bash
# Start RTMP Receiver for Phone Camera #5

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
RTMP_URL="${RTMP_URL:-rtmp://0.0.0.0:1935/live/camera5}"
CAMERA_ID="${CAMERA_ID:-camera5}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ROOM_ID="${ROOM_ID:-room_safe}"

echo "🎬 SafeRoom RTMP Receiver for Phone Camera #5"
echo "=============================================="
echo ""
echo "Configuration:"
echo "  RTMP URL:      $RTMP_URL"
echo "  Camera ID:     $CAMERA_ID"
echo "  Backend URL:   $BACKEND_URL"
echo "  Room ID:       $ROOM_ID"
echo ""

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is not installed!"
    echo ""
    echo "Install FFmpeg:"
    echo "  Ubuntu/Debian: sudo apt-get install -y ffmpeg"
    echo "  macOS:         brew install ffmpeg"
    echo ""
    exit 1
fi

echo "✅ FFmpeg found: $(ffmpeg -version | head -n1)"
echo ""

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/upgrade required packages
echo "📦 Checking Python dependencies..."
pip install -q requests

# Start RTMP receiver
echo ""
echo "🚀 Starting RTMP receiver..."
echo ""

python3 rtmp_receiver.py \
    --rtmp-url "$RTMP_URL" \
    --camera-id "$CAMERA_ID" \
    --backend-url "$BACKEND_URL" \
    --room-id "$ROOM_ID"
