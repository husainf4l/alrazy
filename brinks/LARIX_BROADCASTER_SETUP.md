# 📱 Larix Broadcaster iOS Setup Guide

## Overview

Use **Larix Broadcaster** (iOS app) to stream camera feeds from your iPhone to your SafeRoom Detection System via SRT, RTMP, or RTSP protocols.

---

## 📲 Prerequisites

1. **Larix Broadcaster** app installed on iOS
2. **Your Backend IP**: `192.168.1.137`
3. **Your Backend Port**: `8000`
4. **Same Network**: iPhone on same WiFi as backend
5. **Token**: (Optional for WebRTC, but recommended for security)

---

## 🚀 Protocol Comparison

| Protocol | Latency | Quality | Use Case | Setup Complexity |
|----------|---------|---------|----------|------------------|
| **RTMP** | Low (2-5s) | High | Traditional streaming | Easy |
| **RTSP** | Medium (5-10s) | High | IP camera feeds | Medium |
| **SRT** | Very Low (<1s) | Excellent | Professional | Hard |
| **WebRTC** | Ultra-Low (50-100ms) | Excellent | Mobile viewing | Easy |

**Recommendation**: Use **RTMP** for easiest setup, or **WebRTC** if using the web viewer.

---

## 1️⃣ RTMP Setup (Easiest)

### Step 1: Get Your Backend RTMP URL

```
rtmp://192.168.1.137:1935/live/stream_key
```

**Stream Key Options:**
- `room1` - Stream to Room 1
- `room2` - Stream to Room 2
- `room3` - Stream to Room 3
- `room4` - Stream to Room 4
- `camera_feed_1` - Generic feed 1

### Step 2: Configure Larix Broadcaster

1. **Open Larix Broadcaster** on your iPhone
2. **Tap Settings** (⚙️)
3. **Add Connection**:
   - **Type**: RTMP
   - **URL**: `rtmp://192.168.1.137:1935/live`
   - **Stream Name**: `room1`
   - **Video Bitrate**: 2000-4000 kbps (adjust for network)
   - **Video Resolution**: 1280×720 or 1920×1080
   - **FPS**: 25-30

### Step 3: Test Connection

1. **Tap "Start Broadcast"** (red button)
2. Your stream should appear on SafeRoom system
3. **Check**: `http://192.168.1.137:8000/dashboard` should show your feed

### RTMP Screenshot Settings

```
Connection Name: SafeRoom RTMP
URL: rtmp://192.168.1.137:1935/live
Stream Name: room1
Audio Bitrate: 96 kbps
Video Bitrate: 2500 kbps
Resolution: 1280x720
FPS: 25
Video Profile: Baseline
Reconnect: Enabled
```

---

## 2️⃣ RTSP Setup (Professional)

### Step 1: Get Your Backend RTSP URL

```
rtsp://192.168.1.137:8554/live/stream_key
```

### Step 2: Configure Larix Broadcaster for RTSP Push

1. **Open Larix Broadcaster**
2. **Tap Settings** (⚙️)
3. **Add Connection**:
   - **Type**: RTSP (or RTSP Push)
   - **URL**: `rtsp://192.168.1.137:8554/live`
   - **Stream Name**: `room1`
   - **Video Bitrate**: 3000-5000 kbps
   - **Resolution**: 1920×1080
   - **FPS**: 30

### Step 3: RTSP Stream Configuration

```
Connection Name: SafeRoom RTSP
URL: rtsp://192.168.1.137:8554/live
Stream Name: room1
Protocol: RTSP/RTP over TCP (more reliable)
Video Bitrate: 4000 kbps
Audio Bitrate: 128 kbps
Resolution: 1920x1080
FPS: 30
Video Profile: Main
Reconnect Timeout: 10 seconds
```

---

## 3️⃣ SRT Setup (Low Latency)

### Step 1: Get Your Backend SRT URL

```
srt://192.168.1.137:10001?mode=listener&streamid=room1
```

Or for caller mode (recommended):
```
srt://192.168.1.137:10001?mode=caller&streamid=room1
```

### Step 2: Configure Larix Broadcaster for SRT

1. **Open Larix Broadcaster**
2. **Tap Settings** (⚙️)
3. **Add Connection**:
   - **Type**: SRT
   - **URL**: `srt://192.168.1.137:10001`
   - **Mode**: Caller or Listener
   - **Stream ID**: `room1`
   - **Latency**: 50-100ms (for ultra-low latency)
   - **Video Bitrate**: 2000-3000 kbps

### Step 3: SRT Stream Configuration

```
Connection Name: SafeRoom SRT
URL: srt://192.168.1.137:10001
Mode: Caller (iOS connects to backend)
Stream ID: room1
Latency: 100ms (low) or 50ms (ultra-low)
Video Bitrate: 2500 kbps
Audio Bitrate: 96 kbps
Resolution: 1280x720
FPS: 25
Reconnect: Enabled
```

### SRT Advantages:
- ✅ Ultra-low latency (<1 second)
- ✅ Excellent recovery from packet loss
- ✅ Works over unstable connections
- ✅ Professional broaX_TzcbYkV2qhwGnGx-rkvpBI5cr-oGQNantDAojQEVAdcasting standard

---

## 🔗 Backend Endpoints

Your SafeRoom backend automatically accepts streams on these endpoints:

### RTMP
```
rtmp://192.168.1.137:1935/live/<stream_key>
```
- Port: **1935** (standard RTMP)
- Path: `/live/`
- Key: `room1`, `room2`, `room3`, `room4`

### RTSP
```
rtsp://192.168.1.137:8554/live/<stream_key>
```
- Port: **8554** (standard RTSP)
- Path: `/live/`
- Key: `room1`, `room2`, `room3`, `room4`

### SRT
```
srt://192.168.1.137:10001
```
- Port: **10001** (configurable)
- Stream ID: `room1`, `room2`, `room3`, `room4`

---

## 📊 Recommended Settings by Network

### 🏠 Home WiFi (Stable)
```
Protocol: RTMP
Bitrate: 4000 kbps
Resolution: 1920×1080
FPS: 30
Codec: H.264
```

### 📱 Mobile Hotspot (Unstable)
```
Protocol: SRT (with FEC)
Bitrate: 1500-2000 kbps
Resolution: 1280×720
FPS: 25
Latency: 100ms
```

### 🏢 Corporate Network (Professional)
```
Protocol: RTSP/SRT
Bitrate: 5000+ kbps
Resolution: 1920×1080
FPS: 30
Codec: H.265 (if supported)
```

---

## 🎬 Step-by-Step: First Stream (RTMP - Easiest)

### On Your iPhone:

1. **Open Larix Broadcaster**
   
2. **Tap "+"** (add new connection)
   
3. **Fill in details:**
   ```
   Name: SafeRoom
   URL: rtmp://192.168.1.137:1935/live
   Stream Name: room1
   ```
   
4. **Tap "Video Settings":**
   - Bitrate: 2500 kbps
   - Resolution: 1280×720
   - FPS: 25
   
5. **Tap "Start"** (red record button)
   
6. **Watch dashboard**: Open browser on laptop:
   ```
   http://192.168.1.137:8000/dashboard
   ```
   
7. **Verify**: Your iPhone camera feed should appear in Room 1!

---

## 🔐 Security with Tokens (Optional)

For secure streaming, add your WebRTC token to the URL:

### RTMP with Token
```
rtmp://192.168.1.137:1935/live/room1?token=X_TzcbYkV2qhwGnGx-rkvpBI5cr-oGQNantDAojQEVA
```

### RTSP with Token
```
rtsp://192.168.1.137:8554/live/room1?token=X_TzcbYkV2qhwGnGx-rkvpBI5cr-oGQNantDAojQEVA
```

### SRT with Token
```
srt://192.168.1.137:10001?mode=caller&streamid=room1&token=X_TzcbYkV2qhwGnGx-rkvpBI5cr-oGQNantDAojQEVA
```

---

## 📋 Configuration Presets

### Copy & Paste Configurations

#### **RTMP (Recommended for Beginners)**
```
Protocol: RTMP
Server: 192.168.1.137:1935
Application: live
Stream: room1
Video Codec: H.264
Bitrate: 2500 kbps
Resolution: 1280×720
FPS: 25
Audio: 96 kbps AAC
```

#### **RTSP (Professional)**
```
Protocol: RTSP
Server: rtsp://192.168.1.137:8554/live/room1
Transport: TCP
Video Codec: H.264
Bitrate: 4000 kbps
Resolution: 1920×1080
FPS: 30
Audio: 128 kbps AAC
```

#### **SRT (Ultra Low Latency)**
```
Protocol: SRT
Server: 192.168.1.137
Port: 10001
Mode: Caller
Stream ID: room1
Latency: 100ms
Bitrate: 2500 kbps
Resolution: 1280×720
FPS: 25
```

---

## 🧪 Testing Your Setup

### Test 1: Check Backend is Listening
```bash
# From your laptop, test RTMP port
telnet 192.168.1.137 1935
```

### Test 2: Check Stream Reception
```bash
# Monitor incoming streams on backend
curl http://192.168.1.137:8000/streams/status
```

### Test 3: View on Dashboard
```
Open: http://192.168.1.137:8000/dashboard
Watch for your iPhone feed in Room 1
```

---

## 🔧 Troubleshooting

### iPhone Can't Connect to Backend

**Problem**: "Failed to connect" error in Larix
```
Solution:h
1. Verify iPhone is on same WiFi network
2. Check: ping 192.168.1.137 from iPhone (use WiFi Analyzer app)
3. Verify firewall allows port 1935 (RTMP)
```

### Stream Keeps Disconnecting

**Problem**: Connection drops every few seconds
```
Solution:
1. Lower bitrate: 2000 kbps instead of 4000
2. Reduce resolution: 1280×720 instead of 1920×1080
3. Enable "Auto Reconnect" in Larix
4. Use SRT instead of RTMP (better recovery)
```

### Poor Video Quality

**Problem**: Pixelated or blocky video
```
Solution:
1. Increase bitrate: 3500-4500 kbps
2. Check WiFi signal strength
3. Reduce FPS to 25 (uses less bandwidth)
4. Get closer to WiFi router
```

### High Latency

**Problem**: Video lags (5+ second delay)
```
Solution:
1. Use SRT instead of RTMP (latency: <1 second)
2. Lower bitrate (faster encoding)
3. Reduce resolution (easier to process)
4. Use "Baseline" video profile in Larix
```

---

## 📊 Monitor Stream Status

### Command Line Monitoring

```bash
# Watch stream connections in real-time
watch -n 1 'curl -s http://192.168.1.137:8000/streams/status | jq'

# Get CPU/memory usage during streaming
top -p $(pgrep -f "uvicorn backend.main")

# Check backend logs for stream errors
tail -f /home/husain/alrazy/brinks/backend.log | grep -i stream
```

---

## 💾 Save Your Configurations

### Export from Larix

1. Open Larix
2. Tap ⚙️ Settings
3. Tap "Connections"
4. Find your SafeRoom configs
5. Long-press → Export (saves to files)

### Backup Configuration

```bash
# Backup your Larix config (if accessible)
# Typically stored in iOS Documents folder via Files app
```

---

## 🎯 Quick Start Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Download Larix Broadcaster | 2 min |
| 2 | Add RTMP connection | 3 min |
| 3 | Configure video settings | 2 min |
| 4 | Start broadcast | 1 min |
| 5 | Verify on dashboard | 1 min |
| **Total** | **Complete setup** | **9 minutes** |

---

## 🎥 After Streaming

Once your iPhone streams are working:

1. **Switch between cameras**: Use Larix to stream different rooms
2. **View on web**: Open dashboard to monitor all feeds
3. **View on phone**: Use WebRTC viewer for low-latency viewing
4. **Record**: SafeRoom backend auto-records all streams
5. **Analyze**: Person re-ID and detection runs on all feeds

---

## 📚 Additional Resources

### Larix Broadcaster Documentation
- Official: https://softorino.com/larix/
- Support: In-app help menu

### RTMP Specification
- Adobe RTMP Protocol Specs

### SRT Community
- SRT Alliance: https://www.srtalliance.org/

### Your Backend API
```
Swagger Docs: http://192.168.1.137:8000/docs
Stream Status: http://192.168.1.137:8000/streams/status
Dashboard: http://192.168.1.137:8000/dashboard
```

---

## ✅ Checklist Before Streaming

- [ ] Larix Broadcaster installed on iPhone
- [ ] iPhone connected to same WiFi as backend
- [ ] Backend IP: 192.168.1.137 (verified)
- [ ] Port 1935 (RTMP) accessible
- [ ] Larix connection configured with correct URL
- [ ] Video bitrate: 2000-4000 kbps
- [ ] Resolution: 1280×720 or higher
- [ ] FPS: 25-30
- [ ] Test broadcast: Started successfully
- [ ] Stream visible on dashboard: ✅ Confirmed

---

**Ready to stream! 📱🎥** 

Start with RTMP, and switch to SRT if you need ultra-low latency!
