#!/bin/bash

# Script to update nginx configuration for WebRTC proxy
# Run with: sudo bash update-nginx.sh

echo "Updating nginx configuration for aqlinks.com..."

# Backup existing configuration
cp /etc/nginx/sites-enabled/aqlinks.com /etc/nginx/sites-enabled/aqlinks.com.backup.$(date +%Y%m%d_%H%M%S)

# Copy new configuration
cp /home/husain/alrazy/brinksv2/nginx-aqlinks.conf /etc/nginx/sites-enabled/aqlinks.com

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "Configuration is valid. Reloading nginx..."
    systemctl reload nginx
    echo "✅ Nginx configuration updated successfully!"
    echo ""
    echo "WebRTC will now be accessible at: https://aqlinks.com/webrtc/"
    echo ""
    echo "Make sure the RTSPtoWebRTC server is running:"
    echo "  pm2 list | grep rtsp-webrtc-server"
else
    echo "❌ Configuration test failed. Restoring backup..."
    cp /etc/nginx/sites-enabled/aqlinks.com.backup.$(date +%Y%m%d_%H%M%S) /etc/nginx/sites-enabled/aqlinks.com
    exit 1
fi
