#!/bin/bash

# Script to configure firewall for direct WebRTC access
# This allows better performance by bypassing nginx for media streams

echo "Configuring firewall for WebRTC direct access..."

# Allow port 8083 for WebRTC
sudo ufw allow 8083/tcp comment 'WebRTC Server'

# Show status
sudo ufw status | grep 8083

echo "✅ Port 8083 opened for WebRTC"
echo ""
echo "WebRTC server will be accessible at:"
echo "  - Via nginx (HTTPS): https://aqlinks.com/webrtc/"
echo "  - Direct (HTTP): http://aqlinks.com:8083/"
echo ""
echo "For best performance, the frontend will use direct connection when possible."
