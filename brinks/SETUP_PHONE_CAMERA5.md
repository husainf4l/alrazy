# 🚀 Complete Setup: Phone as Camera #5

## Overview

Your SafeRoom system now has **5 cameras**:
- **Room 1-4**: Fixed Hikvision cameras (RTSP)
- **Camera 5**: Your iPhone/iPad (RTMP via Larix Broadcaster)

---

## Architecture

```
iPhone (Larix Broadcaster)
        ↓ (RTMP stream)
   RTMP Receiver (FFmpeg)
        ↓ (JPEG frames)
   SafeRoom Backend (/ingest)
        ↓
   YOLO Detection + ByteTrack + Re-ID
        ↓
   Dashboard + WebRTC Streaming
```

---

## Prerequisites

✅ **Backend System:**
- SafeRoom backend running
- FFmpeg installed
- Python 3.8+

✅ **Your Phone:**
- iPhone/iPad with Larix Broadcaster installed
- Connected to same WiFi as backend
- Camera permission enabled

---

## 🔧 Part 1: Start RTMP Receiver

The RTMP receiver listens for streams from your phone and forwards frames to the backend.

### Option A: Using Bash Script (Recommended)

```bash
cd /home/husain/alrazy/brinks

# Make script executable
chmod +x start-rtmp-receiver.sh

# Start RTMP receiver
./start-rtmp-receiver.sh
```

**Expected output:**
```
🎬 SafeRoom RTMP Receiver for Phone Camera #5
✅ FFmpeg found: ffmpeg version 4.x.x
📦 Checking Python dependencies...
🚀 Starting RTMP receiver...
📍 Listening on: rtmp://0.0.0.0:1935/live/camera5
🔄 Forwarding to: http://localhost:8000/ingest?camera_id=camera5
✅ RTMP receiver started successfully
```

### Option B: Manual Start (Python)

```bash
cd /home/husain/alrazy/brinks

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install requests

# Start RTMP receiver
python3 rtmp_receiver.py \
    --rtmp-url "rtmp://0.0.0.0:1935/live/camera5" \
    --camera-id "camera5" \
    --backend-url "http://localhost:8000"
```

**Keep this running in a terminal!**

---

## 📱 Part 2: Configure Larix Broadcaster on iPhone

### Step 1: Open Larix and Add Connection

1. Open **Larix Broadcaster** app
2. Tap **+ button** (add connection)
3. Select **RTMP** as connection type
4. Fill in details:

| Field | Value |
|-------|-------|
| **Name** | `SafeRoom Camera 5` |
| **URL** | `rtmp://192.168.1.137:1935/live/camera5` |
| **Stream Key** | `camera5` |

**⚠️ Important:** Replace `192.168.1.137` with **your actual backend IP**

To find your IP:
```bash
hostname -I | awk '{print $1}'
```

### Step 2: Video Settings

1. Tap **Settings ⚙️**
2. Set video to:
   - **Resolution:** 1280×720 (or 1920×1080 for HD)
   - **Frame Rate:** 25 fps
   - **Bitrate:** 3000 kbps (adaptive)
   - **Video Codec:** H.264

### Step 3: Start Streaming

1. Select "SafeRoom Camera 5" connection
2. Tap **red START button**
3. Wait for **"STREAMING"** indicator (green)
4. Point camera at area to monitor

---

## ✅ Part 3: Verify Connection

### Check RTMP Receiver Logs

In the terminal running RTMP receiver, you should see:
```
✅ Sent 30 frames | Camera: camera5 | Backend: 200
✅ Sent 60 frames | Camera: camera5 | Backend: 200
```

### Check Backend Logs

```bash
tail -f /home/husain/alrazy/brinks/backend.log | grep camera5
```

Expected:
```
INFO: 127.0.0.1:xxxxx - "POST /ingest?camera_id=camera5&room_id=room_safe HTTP/1.1" 200 OK
```

### Check Dashboard

Open in browser:
```
http://192.168.1.137:8000/dashboard
```

You should see **Camera 5** in the grid with live feed!

---

## 🎬 Part 4: View Phone Camera

### Option A: Dashboard (Simple)
```
http://192.168.1.137:8000/dashboard
```
Shows all 5 cameras in grid view.

### Option B: WebRTC Viewer (Low Latency)
```
http://192.168.1.137:8000/webrtc.html?camera_id=camera5
```
Low-latency WebRTC streaming (50-100ms).

### Option C: API Direct
```bash
# List all cameras
curl http://localhost:8000/cameras

# Get camera5 info
curl "http://localhost:8000/cameras/camera5"

# Stream detection results (Server-Sent Events)
curl "http://localhost:8000/stream?camera_id=camera5"
```

---

## 🔄 Complete Workflow

```bash
# Terminal 1: Start backend (if not already running)
cd /home/husain/alrazy/brinks
source .venv/bin/activate
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Terminal 2: Start RTMP receiver
cd /home/husain/alrazy/brinks
./start-rtmp-receiver.sh

# Terminal 3: Monitor logs
cd /home/husain/alrazy/brinks
tail -f backend.log | grep -E "(camera5|POST /ingest)"

# On your iPhone:
# 1. Open Larix Broadcaster
# 2. Select "SafeRoom Camera 5"
# 3. Tap START
# 4. Wait for green STREAMING indicator

# In browser:
# http://192.168.1.137:8000/dashboard
```

---

## 🛑 Stop Everything

### Stop Phone Stream
1. Open Larix Broadcaster
2. Tap **STOP button**
3. Wait for disconnect

### Stop RTMP Receiver
In terminal running receiver:
```bash
Ctrl + C
```

### Stop Backend (if needed)
```bash
pkill -f "uvicorn backend.main"
```

---

## 🐛 Troubleshooting

### **"Connection Failed" in Larix**

**Check 1: Firewall**
```bash
# Check if port 1935 is listening
netstat -tlnp | grep 1935
```

**Check 2: Verify URL**
- Should be exactly: `rtmp://192.168.1.137:1935/live/camera5`
- NOT `http://` - must be `rtmp://`

**Check 3: Network**
From your iPhone, ping backend:
```bash
ping 192.168.1.137
```

### **No Frames in Backend**

Check RTMP receiver logs:
```
⚠️  No more frames from RTMP stream
```

Solution:
- Restart Larix on phone
- Restart RTMP receiver
- Check WiFi connection strength

### **"Backend returned 404"**

Backend not responding to `/ingest` endpoint.

Solution:
```bash
# Verify backend is running
curl http://localhost:8000/status

# Check backend logs
tail -20 backend.log
```

### **Low Frame Rate or Buffering**

Reduce bitrate in Larix:
- Set to **2500 kbps** instead of 3000
- Reduce resolution to **1280×720**
- Lower frame rate to **20 fps**

### **Phone Gets Hot / Battery Drains Fast**

Camera streaming uses a lot of power:
- Lower resolution to **1280×720**
- Lower bitrate to **2000 kbps**
- Reduce frame rate to **15 fps**
- Close other apps
- Keep WiFi signal strong

---

## 📊 Expected Performance

| Metric | Expected |
|--------|----------|
| **Latency** | 1-2 seconds (RTMP) |
| **Resolution** | Up to 1920×1080 |
| **Frame Rate** | 15-30 fps |
| **CPU (Backend)** | +10-15% per stream |
| **Bandwidth (Phone)** | 2-4 Mbps upload |
| **Detection** | Same as other cameras |

---

## 🎯 What Works with Camera #5

✅ **Person Detection** - YOLO detects people
✅ **Tracking** - ByteTrack tracks across frames
✅ **Person Re-ID** - Recognizes same person across all 5 cameras
✅ **Occupancy** - Counted in room statistics
✅ **Violations** - Respects max occupancy rules
✅ **Dashboard** - Shows in camera grid
✅ **WebRTC** - Low-latency WebRTC streaming
✅ **APIs** - Full REST API support

---

## 🔒 Security Notes

⚠️ **RTMP port 1935 is OPEN**
- Only use on trusted networks
- Add firewall rules if needed:
  ```bash
  sudo ufw allow from 192.168.1.0/24 to any port 1935
  ```

🔐 **Phone location is visible**
- Dashboard shows camera location
- WebRTC viewer shows real-time feed
- Ensure proper consent for monitoring

📱 **Phone identity**
- Device can be identified by RTMP stream key
- Different key (`camera5`) for different phone

---

## 🚀 Next Steps

1. ✅ Start RTMP receiver: `./start-rtmp-receiver.sh`
2. ✅ Configure Larix on phone
3. ✅ Start streaming from phone
4. ✅ Open dashboard: `http://192.168.1.137:8000/dashboard`
5. ✅ Verify camera 5 appears with live feed
6. ✅ Set up alerts (optional)

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Get backend IP | `hostname -I \| awk '{print $1}'` |
| Start RTMP receiver | `./start-rtmp-receiver.sh` |
| Check RTMP logs | `tail -f rtmp_receiver.log` |
| Verify backend | `curl http://localhost:8000/status` |
| List cameras | `curl http://localhost:8000/cameras` |
| Stop RTMP receiver | `Ctrl + C` in receiver terminal |

---

**Your phone is now camera #5! 📱🎥✨**
