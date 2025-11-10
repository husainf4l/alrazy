## WebRTC Performance Optimization Summary

### Changes Made:
1. ✅ Updated WebRTC STUN servers in config.json (added multiple STUN servers)
2. ✅ Optimized nginx proxy settings:
   - Disabled buffering (`proxy_buffering off`)
   - Disabled cache (`proxy_cache off`)
   - Increased timeouts to 60s
   - Set `client_max_body_size 10M`
3. ✅ Restarted WebRTC server
4. ✅ Restarted main application

### To Apply Nginx Changes:
```bash
cd /home/husain/alrazy/brinksv2
sudo bash update-nginx.sh
```

### Performance Tips:

**The delay you're experiencing is likely due to:**
1. **Network latency** - WebRTC goes through nginx proxy
2. **RTSP camera delay** - Original RTSP streams have inherent delay
3. **Processing overhead** - YOLO detection adds ~30-50ms per frame

**To reduce delay further:**

1. **Direct WebRTC Access** (Best performance):
   - Open port 8083 in firewall
   - Use direct connection bypassing nginx
   - Requires SSL certificate on port 8083 or accepting mixed content

2. **Optimize Camera Settings**:
   - Reduce RTSP stream resolution if too high
   - Use H.264 codec (more efficient than H.265)
   - Reduce keyframe interval

3. **Reduce Processing**:
   - Lower detection FPS (currently 30 FPS)
   - Reduce confidence threshold to process faster

4. **Better Network**:
   - Ensure good bandwidth between server and cameras
   - Use wired connections instead of WiFi when possible

### Current Setup:
- WebRTC accessible at: `https://aqlinks.com/webrtc/`
- Proxied through nginx with optimized settings
- Multiple STUN servers for better connectivity

The nginx optimization should help. Apply it with the update script!
