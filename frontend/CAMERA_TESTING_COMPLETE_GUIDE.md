# Complete Camera Dashboard Testing Guide

This guide provides multiple test streams for your camera dashboard, including local MediaMTX generated streams and configuration for testing both local and remote cameras.

## 🎯 Quick Start

### Option 1: MediaMTX Test Streams (Recommended)

1. **Setup MediaMTX with test streams:**

   ```bash
   ./setup-mediamtx-test-streams.sh
   ```

2. **Start your Next.js dashboard:**

   ```bash
   npm run dev
   ```

3. **Visit your dashboard:**
   ```
   http://localhost:3000/dashboard
   ```

### Option 2: Manual MediaMTX Setup

1. **Download MediaMTX manually:**

   ```bash
   # Download for macOS
   curl -L "https://github.com/bluenviron/mediamtx/releases/download/v1.9.2/mediamtx_v1.9.2_darwin_amd64.tar.gz" | tar -xz
   cd mediamtx_v1.9.2_darwin_amd64
   ```

2. **Use the provided configuration:**
   ```bash
   ./mediamtx ../mediamtx.yml
   ```

## 📺 Available Test Streams

### MediaMTX Generated Streams

| Stream         | URL                                    | Description                  |
| -------------- | -------------------------------------- | ---------------------------- |
| Test Pattern 1 | `rtsp://localhost:8554/test-pattern-1` | Color bars with counter      |
| Test Pattern 2 | `rtsp://localhost:8554/test-pattern-2` | Moving Mandelbrot pattern    |
| Test Pattern 3 | `rtsp://localhost:8554/test-pattern-3` | Blue gradient with timestamp |
| Test Pattern 4 | `rtsp://localhost:8554/test-pattern-4` | HD noise pattern             |
| Motion Test    | `rtsp://localhost:8554/test-motion`    | Motion detection test        |
| Local Camera   | `rtsp://localhost:8554/local-camera`   | Your physical camera         |

### Web Players

| Interface     | URL                                    | Purpose                      |
| ------------- | -------------------------------------- | ---------------------------- |
| HLS Player    | `http://localhost:8888/test-pattern-1` | Browser-compatible streaming |
| WebRTC Player | `http://localhost:8889/test-pattern-1` | Low-latency streaming        |
| Dashboard     | `http://localhost:3000/dashboard`      | Your React dashboard         |
| API           | `http://localhost:9997/v3/paths/list`  | MediaMTX API                 |

## 🧪 Testing Commands

### Test Individual Streams

```bash
# Test with VLC
vlc rtsp://localhost:8554/test-pattern-1

# Test with ffplay
ffplay rtsp://localhost:8554/test-pattern-1

# Test with ffprobe (check stream info)
ffprobe rtsp://localhost:8554/test-pattern-1

# Test API
curl http://localhost:9997/v3/paths/list
```

### Test Your Physical Camera

```bash
# Test direct connection to your camera
ffplay rtsp://149.200.251.12:554/stream

# Test through MediaMTX proxy
ffplay rtsp://localhost:8554/local-camera
```

## 🔧 Configuration Files

### MediaMTX Configuration (`mediamtx.yml`)

- ✅ Created and configured
- Includes 5 test streams + your camera
- Enables API, HLS, WebRTC, and RTSP

### React Component Updates

- ✅ `CameraStreamGridEnhanced.tsx` updated
- Includes both real and test cameras
- Ready for testing multiple streams

## 📊 Dashboard Features to Test

### Camera Grid View

- Multiple camera layout
- Individual stream controls
- Error handling and retry logic
- Full-screen mode for individual cameras

### Stream Management

- Play/pause controls
- Connection status indicators
- Automatic reconnection
- Error reporting

### Performance Testing

- Multiple simultaneous streams
- Different resolutions and bitrates
- Network connectivity issues
- Browser compatibility

## 🐛 Troubleshooting

### Common Issues

1. **MediaMTX not starting:**

   ```bash
   # Check if ports are available
   lsof -i :8554
   lsof -i :8888
   lsof -i :8889

   # Kill any existing MediaMTX processes
   pkill mediamtx
   ```

2. **FFmpeg not found:**

   ```bash
   # Install FFmpeg on macOS
   brew install ffmpeg
   ```

3. **Streams not visible in dashboard:**

   - Check MediaMTX logs for errors
   - Verify test streams are running: `curl http://localhost:9997/v3/paths/list`
   - Check browser console for errors

4. **Camera connection issues:**

   ```bash
   # Test direct camera connection
   ping 149.200.251.12

   # Test RTSP port
   telnet 149.200.251.12 554
   ```

### Debug Commands

```bash
# Check MediaMTX status
curl http://localhost:9997/v3/paths/list

# Check specific stream
curl http://localhost:9997/v3/paths/get/test-pattern-1

# Monitor MediaMTX logs
tail -f mediamtx.log

# Test network connectivity
ping 149.200.251.12
telnet 149.200.251.12 554
```

## 🚀 Production Considerations

### Security

- Change default credentials in `mediamtx.yml`
- Use HTTPS for web interfaces
- Implement proper authentication
- Restrict API access

### Performance

- Adjust stream bitrates based on network
- Use appropriate codecs for your use case
- Monitor CPU usage with multiple streams
- Consider using GPU acceleration

### Monitoring

- Set up stream health checks
- Monitor MediaMTX logs
- Implement alerting for stream failures
- Track bandwidth usage

## 📝 Next Steps

1. **Test all streams** using the provided commands
2. **Customize stream settings** in `mediamtx.yml`
3. **Add more cameras** to the React component
4. **Implement recording** if needed
5. **Deploy to production** with proper security

## 🆘 Support

If you encounter issues:

1. Check the MediaMTX logs
2. Verify all dependencies are installed
3. Test streams individually with VLC or ffplay
4. Check network connectivity to your cameras
5. Review browser console for JavaScript errors

## 📚 References

- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [RTSP Protocol Specification](https://tools.ietf.org/html/rfc2326)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [WebRTC Documentation](https://webrtc.org/getting-started/)
