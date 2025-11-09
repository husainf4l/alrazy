# Quick Reference: Stream 500 Error Fix

## What Was Wrong

Your backend was sending JSON to the RTSPtoWebRTC service:
```python
# ❌ WRONG - RTSPtoWebRTC couldn't read this
response = await client.post(
    "http://localhost:8083/stream",
    json={"url": camera.rtsp_url}
)
```

But RTSPtoWebRTC's Go handler uses `c.PostForm()` which only reads form-encoded data:
```go
// In http.go line 159
url := c.PostForm("url")  // ← Reads from form body, not JSON
```

**Result:** The `url` variable was empty, RTSPtoWebRTC tried to connect to `:554` with no hostname, and returned HTTP 500.

---

## What Was Fixed

**File:** `RAZZv4-backend/routes/vault_rooms.py` line ~230

**Changed to:** Send form-encoded data
```python
# ✅ CORRECT - RTSPtoWebRTC can read this
response = await client.post(
    "http://localhost:8083/stream",
    data={"url": camera.rtsp_url},  # Form-encoded
    headers={"Accept": "application/json"},
    timeout=20.0
)
```

This sends `application/x-www-form-urlencoded` which Gin's `c.PostForm("url")` reads correctly.

---

## How to Verify the Fix

### Option A: Quick Test (2 minutes)
```bash
cd /Users/husain/Desktop/alrazy/razzv4

# Run the diagnostic script
./test_stream_diagnostics.sh

# If services are running, you'll see which cameras fail and why
```

### Option B: Full Test (5 minutes)
```bash
# 1. Make sure services are running
cd RAZZv4-backend && python main.py &  # Start backend
cd RTSPtoWebRTC && ./rtsp-to-webrtc &  # Start WebRTC service

# 2. In another terminal, tail the WebRTC logs
tail -f RTSPtoWebRTC/logs/rtsp-webrtc-0.log

# 3. In another terminal, trigger a stream request
curl -X GET "http://localhost:8000/vault-rooms/1/cameras/webrtc"

# 4. Watch the logs - you should now see:
#    ✅ "Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/..."
#    (BEFORE FIX: "Stream Try Connect " with empty URL)
```

---

## What the Logs Should Show Now

### ✅ After Fix is Applied and Services Restarted

**Good** (camera is reachable):
```
2025/11/09 02:00:00 Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/102/
2025/11/09 02:00:02 Set ICEServers [stun:stun.l.google.com:19302]
[GIN] 2025/11/09 - 02:00:05 | 200 | ... | POST "/stream"
```

**Bad** (camera unreachable - YOUR CAMERA ISSUE):
```
2025/11/09 02:00:00 Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/102/
2025/11/09 02:00:00 dial tcp 192.168.1.75:554: connect: no route to host
2025/11/09 02:00:05 Stream Codec Not Found
[GIN] 2025/11/09 - 02:00:05 | 500 | ... | POST "/stream"
```

**Bad** (wrong RTSP path):
```
2025/11/09 02:00:00 Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/102/
2025/11/09 02:00:01 Camera send statusRTSP/1.0 404 Not Found
2025/11/09 02:00:05 Stream Codec Not Found
[GIN] 2025/11/09 - 02:00:05 | 500 | ... | POST "/stream"
```

---

## Camera-Specific Issues

Based on your logs, your cameras had these problems:

| Camera | Issue | Fix |
|--------|-------|-----|
| **camera1_main** | RTSP 404 Not Found | Check stream path on camera |
| **camera2_main** | Works fine ✅ | No action needed |
| **camera1 / camera12** | Empty URL (NOW FIXED) | Restart services to test |

---

## Files Modified

1. **`RAZZv4-backend/routes/vault_rooms.py`** - Fixed POST to use form encoding
   - Line ~230: Changed `json=` to `data=`
   - Line ~235: Added timeout increase and error logging
   - Line ~250: Improved error response logging

2. **`STREAM_500_ERROR_DIAGNOSIS.md`** - This diagnosis document
3. **`test_stream_diagnostics.sh`** - Automated test script

---

## Restart Instructions

```bash
# Kill existing processes
pkill -f "rtsp-to-webrtc" || true
pkill -f "python main.py" || true

# Restart RTSPtoWebRTC service
cd /Users/husain/Desktop/alrazy/razzv4/RTSPtoWebRTC
./rtsp-to-webrtc > logs/rtsp-webrtc-0.log 2>&1 &

# Restart backend
cd /Users/husain/Desktop/alrazy/razzv4/RAZZv4-backend
python main.py &

# Verify
sleep 2
curl -s http://localhost:8000/health | head -20
```

---

## Still Getting 500?

1. **Check the actual error** in RTSPtoWebRTC logs:
   ```bash
   tail -20 RTSPtoWebRTC/logs/rtsp-webrtc-0.log
   ```

2. **If you see "connect: no route to host":**
   - Camera is offline or unreachable
   - Test: `ping 192.168.1.75` from the machine running RTSPtoWebRTC

3. **If you see "404 Not Found":**
   - Wrong RTSP stream path
   - Test: Ask your camera vendor for correct path
   - Common paths: `/live`, `/stream`, `/main`, `/Streaming/Channels/1/`

4. **If you see empty "Stream Try Connect":**
   - Form encoding fix didn't apply
   - Restart services

---

## Questions?

Check the detailed diagnosis in: `STREAM_500_ERROR_DIAGNOSIS.md`
