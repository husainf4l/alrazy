#!/bin/bash

# Script to setup and run MediaMTX with test streams for camera dashboard testing

echo "=== MediaMTX Setup and Test Stream Generator ==="
echo "Date: $(date)"
echo

# Variables
MEDIAMTX_VERSION="v1.9.2"
MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/${MEDIAMTX_VERSION}/mediamtx_${MEDIAMTX_VERSION}_darwin_amd64.tar.gz"
MEDIAMTX_DIR="./mediamtx"
CONFIG_FILE="./mediamtx.yml"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check dependencies
check_dependencies() {
    echo "🔍 Checking dependencies..."
    
    local missing_deps=()
    
    if ! command_exists ffmpeg; then
        missing_deps+=("ffmpeg")
    fi
    
    if ! command_exists curl; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "❌ Missing dependencies: ${missing_deps[*]}"
        echo "📦 Install missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "   brew install $dep"
        done
        return 1
    fi
    
    echo "✅ All dependencies available"
    return 0
}

# Function to download MediaMTX
download_mediamtx() {
    echo "📥 Downloading MediaMTX ${MEDIAMTX_VERSION}..."
    
    if [ -d "$MEDIAMTX_DIR" ]; then
        echo "📁 MediaMTX directory already exists, removing..."
        rm -rf "$MEDIAMTX_DIR"
    fi
    
    mkdir -p "$MEDIAMTX_DIR"
    cd "$MEDIAMTX_DIR" || exit 1
    
    if curl -L "$MEDIAMTX_URL" | tar -xz; then
        echo "✅ MediaMTX downloaded and extracted successfully"
        chmod +x mediamtx
        cd ..
        return 0
    else
        echo "❌ Failed to download MediaMTX"
        cd ..
        return 1
    fi
}

# Function to start MediaMTX
start_mediamtx() {
    echo "🚀 Starting MediaMTX with test streams..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ Configuration file not found: $CONFIG_FILE"
        return 1
    fi
    
    if [ ! -f "${MEDIAMTX_DIR}/mediamtx" ]; then
        echo "❌ MediaMTX binary not found"
        return 1
    fi
    
    echo "📺 Starting MediaMTX server..."
    echo "   - RTSP port: 8554"
    echo "   - HLS port: 8888"  
    echo "   - WebRTC port: 8889"
    echo "   - API port: 9997"
    echo
    
    cd "$MEDIAMTX_DIR" || exit 1
    ./mediamtx "../$CONFIG_FILE"
}

# Function to test MediaMTX streams
test_streams() {
    echo "🧪 Testing MediaMTX streams..."
    
    # Wait for MediaMTX to start
    sleep 5
    
    local streams=(
        "test-pattern-1"
        "test-pattern-2" 
        "test-pattern-3"
        "test-pattern-4"
        "test-motion"
    )
    
    echo "🔍 Checking stream availability..."
    for stream in "${streams[@]}"; do
        echo -n "   Testing $stream: "
        if timeout 5s ffprobe -v quiet "rtsp://localhost:8554/$stream" >/dev/null 2>&1; then
            echo "✅ Available"
        else
            echo "❌ Not available"
        fi
    done
}

# Function to show usage information
show_usage() {
    echo
    echo "=== MediaMTX Test Streams Usage ==="
    echo
    echo "🌐 Web Interfaces:"
    echo "   - Dashboard: http://localhost:3000/dashboard"
    echo "   - HLS Player: http://localhost:8888/test-pattern-1"
    echo "   - WebRTC Player: http://localhost:8889/test-pattern-1"
    echo "   - API: http://localhost:9997/v3/paths/list"
    echo
    echo "📺 RTSP Streams:"
    echo "   - Test Pattern 1: rtsp://localhost:8554/test-pattern-1"
    echo "   - Test Pattern 2: rtsp://localhost:8554/test-pattern-2"
    echo "   - Test Pattern 3: rtsp://localhost:8554/test-pattern-3"
    echo "   - Test Pattern 4: rtsp://localhost:8554/test-pattern-4"
    echo "   - Motion Test: rtsp://localhost:8554/test-motion"
    echo "   - Local Camera: rtsp://localhost:8554/local-camera"
    echo
    echo "🧪 Test Commands:"
    echo "   # Play with VLC:"
    echo "   vlc rtsp://localhost:8554/test-pattern-1"
    echo
    echo "   # Play with ffplay:"
    echo "   ffplay rtsp://localhost:8554/test-pattern-1"
    echo
    echo "   # Test API:"
    echo "   curl http://localhost:9997/v3/paths/list"
    echo
    echo "🎛️  Control:"
    echo "   - Press Ctrl+C to stop MediaMTX"
    echo "   - Logs will show stream connections and activity"
    echo
}

# Function to cleanup
cleanup() {
    echo
    echo "🧹 Cleaning up..."
    if [ -n "$MEDIAMTX_PID" ]; then
        kill "$MEDIAMTX_PID" 2>/dev/null
    fi
    pkill -f mediamtx 2>/dev/null
    echo "✅ Cleanup complete"
}

# Trap to handle script interruption
trap cleanup EXIT INT TERM

# Main execution
echo "🚀 Starting MediaMTX setup..."

# Check dependencies
if ! check_dependencies; then
    exit 1
fi

# Download MediaMTX if not exists
if [ ! -f "${MEDIAMTX_DIR}/mediamtx" ]; then
    if ! download_mediamtx; then
        exit 1
    fi
else
    echo "✅ MediaMTX binary already exists"
fi

# Show usage information
show_usage

# Start MediaMTX
echo "🎬 Starting MediaMTX in 3 seconds..."
echo "   Press Ctrl+C to stop at any time"
sleep 3

start_mediamtx
