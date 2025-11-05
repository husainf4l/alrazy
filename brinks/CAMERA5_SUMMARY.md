# 📱 Phone Camera #5 - Setup Summary

## Your Setup at a Glance

```
iPhone/iPad (Larix Broadcaster)
    ↓ RTMP stream rtmp://192.168.1.137:1935/live/camera5
    ↓
RTMP Receiver (./start-rtmp-receiver.sh)
    ↓ JPEG frames to /ingest
    ↓
SafeRoom Backend (Detection + Tracking + Re-ID)
    ↓
Dashboard + WebRTC Viewer
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start RTMP Receiver
```bash
cd /home/husain/alrazy/brinks
./start-rtmp-receiver.sh
```
**Keep this running!**

### Step 2: Configure Larix on iPhone
1. Open Larix Broadcaster
2. Add RTMP connection:
   - **URL:** `rtmp://192.168.1.137:1935/live/camera5`
   - **Stream Key:** `camera5`
3. Set video: 1280×720, 25fps, 3000kbps
4. Tap START

### Step 3: View in Dashboard
```
http://192.168.1.137:8000/dashboard
```

**Done!** Camera #5 (your phone) is now live! 📱

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `PHONE_CAMERA5_SETUP.md` | Detailed setup guide |
| `CAMERA5_QUICK_SETUP.md` | Quick reference card |
| `SETUP_PHONE_CAMERA5.md` | Complete workflow |
| `rtmp_receiver.py` | RTMP receiver script |
| `start-rtmp-receiver.sh` | Start script |
| `.rtmp-env` | Environment variables |

---

## 🔗 Your Connection Details

**Backend IP:** `192.168.1.137`
**RTMP URL:** `rtmp://192.168.1.137:1935/live/camera5`
**Camera ID:** `camera5`

---

## ✅ Verification

### Check RTMP receiver is running
```bash
ps aux | grep rtmp_receiver
```

### Check backend logs
```bash
tail -f backend.log | grep camera5
```

### Check camera5 is detected
```bash
curl http://localhost:8000/cameras | jq .camera5
```

---

## 📊 What's Included

✅ **Person Detection** - Detects people via YOLO
✅ **Person Tracking** - Tracks with ByteTrack
✅ **Person Re-ID** - Same person recognized across all 5 cameras
✅ **Occupancy** - Counted in statistics
✅ **Dashboard** - Shows in camera grid
✅ **WebRTC** - Low-latency streaming
✅ **APIs** - Full REST API access
✅ **Alerts** - Same violation detection as other cameras

---

## 🛑 Stop Streaming

1. **Phone:** Tap STOP in Larix
2. **Receiver:** `Ctrl + C` in receiver terminal
3. **Done!**

---

## 🔄 Terminal Sessions Needed

Keep these running simultaneously:

**Terminal 1: Backend** (already running)
```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2: RTMP Receiver** (new)
```bash
./start-rtmp-receiver.sh
```

**Terminal 3: Monitoring** (optional)
```bash
tail -f backend.log
```

---

## 🎯 Next Steps

1. **Verify:** Open dashboard and see camera5 live
2. **Test:** Walk in front of phone camera
3. **Monitor:** Check person tracking works
4. **Integrate:** Set up alerts if needed

---

## 📞 Support

**Issue: Connection Failed**
- Check WiFi: `ping 192.168.1.137`
- Check URL: Must be `rtmp://` not `http://`
- Check firewall: Port 1935 must be open

**Issue: No Frames**
- Restart Larix on phone
- Restart RTMP receiver
- Check logs: `tail -f rtmp_receiver.log`

**Issue: High Latency**
- RTMP has 1-2 sec latency (normal)
- Use WebRTC viewer for low latency: `http://192.168.1.137:8000/webrtc.html?camera_id=camera5`

---

**Your phone is now camera #5! 🎉**

For detailed instructions, see: `SETUP_PHONE_CAMERA5.md`
