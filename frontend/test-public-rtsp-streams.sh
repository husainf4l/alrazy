#!/bin/bash

# Script to test public RTSP camera streams and add them to the dashboard
echo "=== Testing Public RTSP Camera Streams ==="
echo "Date: $(date)"
echo

# Define public RTSP streams to test
declare -a streams=(
    "Big Buck Bunny Test|rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"
    "Wowza Demo 175k|rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov"
    "Strba Lake View|rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream"
    "Beenius Demo|rtsp://demo.beenius.com:554/multicast/test/elementary"
)

# Function to test RTSP stream connectivity
test_rtsp_stream() {
    local name="$1"
    local url="$2"
    
    echo "Testing: $name"
    echo "URL: $url"
    
    # Use ffprobe to test the stream (timeout after 10 seconds)
    if timeout 10s ffprobe -v quiet -print_format json -show_streams "$url" > /dev/null 2>&1; then
        echo "✅ SUCCESS: Stream is accessible"
        return 0
    else
        echo "❌ FAILED: Stream is not accessible or timed out"
        return 1
    fi
}

# Function to add cameras to the enhanced component
add_to_component() {
    local component_file="/Users/al-husseinabdullah/alrazy/frontend/src/components/CameraStreamGridEnhanced.tsx"
    
    if [ ! -f "$component_file" ]; then
        echo "❌ Component file not found: $component_file"
        return 1
    fi
    
    echo
    echo "=== Adding Public Test Cameras to Component ==="
    
    # Create backup
    cp "$component_file" "${component_file}.backup"
    
    # Add public test cameras array after imports
    cat > temp_public_cameras.txt << 'EOF'

// Public test cameras for development and testing
const publicTestCameras = [
  {
    id: 'public-1',
    name: 'Big Buck Bunny Test',
    rtspUrl: 'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov',
    username: '',
    password: '',
    location: 'Test Stream',
    status: 'active' as const
  },
  {
    id: 'public-2', 
    name: 'Wowza Demo 175k',
    rtspUrl: 'rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov',
    username: '',
    password: '',
    location: 'Test Stream',
    status: 'active' as const
  },
  {
    id: 'public-3',
    name: 'Strba Lake View',
    rtspUrl: 'rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream',
    username: '',
    password: '',
    location: 'Slovakia',
    status: 'active' as const
  }
];

EOF
    
    echo "✅ Public test cameras configuration created"
    echo "📝 To manually add these cameras to your component:"
    echo "   1. Open $component_file"
    echo "   2. Add the publicTestCameras array after your imports"
    echo "   3. Combine with your existing cameras: const allCameras = [...cameras, ...publicTestCameras];"
    echo "   4. Use allCameras instead of cameras in your component"
}

# Function to create MediaMTX configuration for public streams
create_mediamtx_config() {
    echo
    echo "=== Creating MediaMTX Configuration for Public Streams ==="
    
    cat > public-streams-mediamtx.yml << 'EOF'
# Add these paths to your mediamtx.yml to proxy public streams

paths:
  public-bigbuck-115k:
    source: rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
    
  public-bigbuck-175k:
    source: rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
    
  public-strba-lake:
    source: rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
    
  public-beenius-demo:
    source: rtsp://demo.beenius.com:554/multicast/test/elementary
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s

# Then access via:
# rtsp://localhost:8554/public-bigbuck-115k
# rtsp://localhost:8554/public-bigbuck-175k  
# rtsp://localhost:8554/public-strba-lake
# rtsp://localhost:8554/public-beenius-demo
EOF
    
    echo "✅ MediaMTX configuration created in 'public-streams-mediamtx.yml'"
    echo "📝 Copy the paths section to your mediamtx.yml file"
}

# Function to create test environment file
create_test_env() {
    echo
    echo "=== Creating Test Environment Configuration ==="
    
    cat > .env.test << 'EOF'
# Public RTSP test streams for development
PUBLIC_RTSP_1=rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov
PUBLIC_RTSP_2=rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov
PUBLIC_RTSP_3=rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream
PUBLIC_RTSP_4=rtsp://demo.beenius.com:554/multicast/test/elementary

# MediaMTX proxied public streams (if using MediaMTX proxy)
PROXIED_PUBLIC_1=rtsp://localhost:8554/public-bigbuck-115k
PROXIED_PUBLIC_2=rtsp://localhost:8554/public-bigbuck-175k
PROXIED_PUBLIC_3=rtsp://localhost:8554/public-strba-lake
PROXIED_PUBLIC_4=rtsp://localhost:8554/public-beenius-demo
EOF
    
    echo "✅ Test environment file created: .env.test"
    echo "📝 Copy relevant variables to your .env file"
}

# Main execution
echo "Starting public RTSP stream tests..."
echo

# Test streams
successful_streams=0
total_streams=${#streams[@]}

for stream in "${streams[@]}"; do
    IFS='|' read -r name url <<< "$stream"
    echo "----------------------------------------"
    if test_rtsp_stream "$name" "$url"; then
        ((successful_streams++))
    fi
    echo
done

echo "========================================="
echo "Test Results: $successful_streams/$total_streams streams accessible"
echo

# Generate configuration files
add_to_component
create_mediamtx_config  
create_test_env

echo
echo "=== Next Steps ==="
echo "1. 📹 Review the working streams above"
echo "2. 🔧 Add MediaMTX paths from 'public-streams-mediamtx.yml' to your mediamtx.yml"
echo "3. 🚀 Start/restart MediaMTX server"
echo "4. 💻 Add public cameras to your React component"
echo "5. 🌐 Test in your dashboard at http://localhost:3000/dashboard"
echo
echo "=== Quick Test Commands ==="
echo "# Test with VLC:"
echo "vlc rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"
echo
echo "# Test with ffplay:"
echo "ffplay rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"
echo
echo "# Test MediaMTX proxy (after adding paths):"
echo "vlc rtsp://localhost:8554/public-bigbuck-115k"
echo

echo "=== Testing Complete ==="
