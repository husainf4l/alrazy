#!/bin/bash

# Simple camera dashboard test without external dependencies
echo "=== Simple Camera Dashboard Test ==="
echo "Date: $(date)"
echo

# Function to test your dashboard
test_dashboard() {
    echo "🧪 Testing Camera Dashboard..."
    echo
    
    # Check if Next.js is running
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "✅ Next.js server is running"
        echo "🌐 Dashboard URL: http://localhost:3000/dashboard"
    else
        echo "❌ Next.js server is not running"
        echo "🚀 Start with: npm run dev"
        return 1
    fi
    
    # Test your camera directly
    echo
    echo "📹 Testing direct camera connection..."
    echo "🔍 Camera IP: 149.200.251.12"
    
    if ping -c 1 149.200.251.12 >/dev/null 2>&1; then
        echo "✅ Camera IP is reachable"
        
        # Test RTSP port
        if nc -z 149.200.251.12 554 2>/dev/null; then
            echo "✅ RTSP port 554 is open"
        else
            echo "⚠️  RTSP port 554 might not be accessible"
        fi
    else
        echo "❌ Camera IP is not reachable"
        echo "   Check network connection and camera IP"
    fi
}

# Function to test API endpoints
test_api_endpoints() {
    echo
    echo "🔌 Testing API endpoints..."
    
    local base_url="http://localhost:3000"
    local endpoints=(
        "/api/camera-snapshot"
        "/api/camera-stream" 
        "/api/rtsp-stream"
        "/api/test-camera-connection"
    )
    
    for endpoint in "${endpoints[@]}"; do
        echo -n "   Testing $endpoint: "
        if curl -s "${base_url}${endpoint}" >/dev/null 2>&1; then
            echo "✅ Available"
        else
            echo "❌ Not responding"
        fi
    done
}

# Function to show camera stream URLs for testing
show_test_urls() {
    echo
    echo "🎯 Camera Stream URLs for Testing:"
    echo
    echo "📺 Direct camera access:"
    echo "   rtsp://149.200.251.12:554/stream"
    echo "   rtsp://admin:admin123@149.200.251.12:554/stream"
    echo
    echo "🌐 Web interfaces:"
    echo "   Dashboard: http://localhost:3000/dashboard"
    echo "   Camera snapshot: http://localhost:3000/api/camera-snapshot"
    echo "   Stream test: http://localhost:3000/api/test-camera-connection"
    echo
    echo "🧪 Test commands (if tools available):"
    echo "   # VLC (if installed):"
    echo "   vlc rtsp://admin:admin123@149.200.251.12:554/stream"
    echo
    echo "   # curl test:"
    echo "   curl http://localhost:3000/api/test-camera-connection"
    echo
}

# Function to show MediaMTX setup info
show_mediamtx_info() {
    echo
    echo "🔧 Advanced Testing with MediaMTX:"
    echo
    echo "📦 To enable MediaMTX test streams:"
    echo "   1. Install FFmpeg: brew install ffmpeg"
    echo "   2. Run setup script: ./setup-mediamtx-test-streams.sh"
    echo "   3. This will provide 5 additional test streams"
    echo
    echo "🎬 MediaMTX test streams (when running):"
    echo "   - rtsp://localhost:8554/test-pattern-1"
    echo "   - rtsp://localhost:8554/test-pattern-2"
    echo "   - rtsp://localhost:8554/test-pattern-3"
    echo "   - rtsp://localhost:8554/test-pattern-4"
    echo "   - rtsp://localhost:8554/test-motion"
    echo
}

# Function to check dashboard component
check_dashboard_component() {
    echo
    echo "🔍 Checking dashboard component..."
    
    local component_file="src/components/CameraStreamGridEnhanced.tsx"
    
    if [ -f "$component_file" ]; then
        echo "✅ Enhanced camera component exists"
        
        # Check if test cameras are included
        if grep -q "testCameras" "$component_file"; then
            echo "✅ Test cameras are configured in component"
        else
            echo "⚠️  Test cameras not found in component"
        fi
        
        # Check if component is exported
        if grep -q "export.*CameraStreamGridEnhanced" "$component_file"; then
            echo "✅ Component is properly exported"
        else
            echo "❌ Component export issue"
        fi
    else
        echo "❌ Camera component not found: $component_file"
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    echo "🚀 Next Steps:"
    echo
    echo "1. 🖥️  Start Next.js development server:"
    echo "   npm run dev"
    echo
    echo "2. 🌐 Open dashboard in browser:"
    echo "   http://localhost:3000/dashboard"
    echo
    echo "3. 📹 Test camera connections in the dashboard"
    echo
    echo "4. 🔧 Optional: Setup MediaMTX for additional test streams:"
    echo "   ./setup-mediamtx-test-streams.sh"
    echo
    echo "5. 🐛 Check browser console for any errors"
    echo
    echo "6. 📊 Monitor camera status indicators in the dashboard"
    echo
}

# Main execution
echo "Starting simple camera dashboard test..."
echo

# Run tests
test_dashboard
test_api_endpoints
check_dashboard_component

# Show information
show_test_urls
show_mediamtx_info
show_next_steps

echo "=== Test Complete ==="
echo "🎉 Your camera dashboard is ready for testing!"
echo
