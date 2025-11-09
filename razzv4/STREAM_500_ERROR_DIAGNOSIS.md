# Stream 500 Error Diagnosis & Fix

## Root Causes Found in RTSPtoWebRTC Logs

### Issue 1: Empty RTSP URL Being Sent (FIXED)
**Symptom:** `Stream Try Connect ` (empty URL) followed by `dial tcp :554: connect: connection refused`
**Root Cause:** Backend was sending JSON `{"url": "..."}` but the Go handler uses `c.PostForm("url")` which only reads form-encoded fields
**Line in logs (01:52:45):**
```
2025/11/09 01:52:40 Stream Try Connect 
2025/11/09 01:52:40 dial tcp :554: connect: connection refused
2025/11/09 01:52:45 Stream Codec Not Found
[GIN] 2025/11/09 - 01:52:45 | 500 |   5.10375675s |             ::1 | POST     "/stream"
```

**Fix Applied:** Changed backend to send form-encoded data instead of JSON:
```python
# Before (WRONG):
response = await client.post(
    "http://localhost:8083/stream",
    json={"url": camera.rtsp_url}
)

# After (CORRECT):
response = await client.post(
    "http://localhost:8083/stream",
    data={"url": camera.rtsp_url},  # form-encoded
    headers={"Accept": "application/json"},
    timeout=20.0
)
```

**Why this works:** 
- httpx with `data=` sends `application/x-www-form-urlencoded` 
- Gin's `c.PostForm("url")` reads from form body
- Previously, `c.PostForm("url")` was reading an empty string from JSON body

---

### Issue 2: Network Unreachability (NOT FIXED - This is Your Camera)
**Symptom:** `dial tcp 192.168.1.75:554: connect: no route to host`
**Root Cause:** The RTSPtoWebRTC service cannot reach camera IP `192.168.1.75`
**Line in logs (01:57:16):**
```
2025/11/09 01:57:11 Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/102/
2025/11/09 01:57:11 dial tcp 192.168.1.75:554: connect: no route to host
2025/11/09 01:57:16 Stream Codec Not Found
[GIN] 2025/11/09 - 01:57:16 | 500 |  5.126568417s |             ::1 | POST     "/stream"
```

**What to do:**
- Check if cameras are on the same network
- Test connectivity from the RTSPtoWebRTC service machine: `ping 192.168.1.75`
- Verify RTSP credentials in database: `admin:tt55oo77`
- Check if camera is powered on and responding

---

### Issue 3: RTSP Path Not Found (Camera Configuration Issue)
**Symptom:** `Camera send statusRTSP/1.0 404 Not Found`
**Root Cause:** Camera exists but RTSP stream path is wrong
**Line in logs (23:38:41):**
```
2025/11/08 23:38:40 Stream Try Connect camera1_main
2025/11/08 23:38:41 Camera send statusRTSP/1.0 404 Not Found
```

**What to do:**
- Test RTSP URL directly from terminal where RTSPtoWebRTC runs:
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries format=duration -of default=noprint_wrappers=1:nokey=1:divider=" " "rtsp://admin:tt55oo77@192.168.1.75:554/Streaming/Channels/102/"
  ```
- Adjust the RTSP path in your camera configuration
- Different camera vendors use different paths (e.g., `/live`, `/stream`, `/main`, etc.)

---

## Testing the Fix

### Step 1: Restart the RTSPtoWebRTC Service
```bash
# Kill any existing process
pkill -f "rtsp-to-webrtc" || true

# Navigate to the service directory
cd /Users/husain/Desktop/alrazy/razzv4/RTSPtoWebRTC

# Run the service (or use your existing startup method)
./rtsp-to-webrtc
```

### Step 2: Test Backend Fix (Form-Encoded POST)
```bash
# Test the backend endpoint directly
# This should now send form data correctly to RTSPtoWebRTC
curl -v -X POST http://localhost:8000/vault-rooms/1/cameras/webrtc 2>&1 | head -50
```

Expected behavior:
- If cameras have valid RTSP URLs and network connectivity → should get 200 with WebRTC SDP
- If cameras unreachable → should get 500 with "no route to host" in logs
- If RTSP path wrong → should get 500 with "404 Not Found" in logs

### Step 3: Verify with RTSPtoWebRTC Logs
```bash
# Monitor the log file in real-time
tail -f /Users/husain/Desktop/alrazy/razzv4/RTSPtoWebRTC/logs/rtsp-webrtc-0.log
```

Look for:
- ✅ `Stream Try Connect rtsp://admin:tt55oo77@192.168.1.75:554/...` (correct URL)
- ✅ `[GIN] ... | 200 | ... | POST "/stream"` (successful response)
- ❌ `Stream Try Connect ` (empty URL - would mean form encoding still broken)
- ❌ `connect: no route to host` (network issue)
- ❌ `404 Not Found` (wrong RTSP path)

---

## Summary of Changes

**File Modified:** `/Users/husain/Desktop/alrazy/razzv4/RAZZv4-backend/routes/vault_rooms.py`

**Function:** `get_camera_webrtc_streams()` (around line 230)

**Changes:**
1. POST data format: `json={"url": ...}` → `data={"url": ...}` ✅ FIXED
2. Timeout increased: `10.0` → `20.0` seconds (accounts for slow camera startup)
3. Better error logging: Now logs `status=500, body={error_json}` to see actual error

---

## Next Steps

Once you restart the services, try these steps:

1. **For camera1 / camera12 specifically:**
   - Check if those camera IDs exist in your database
   - Verify their RTSP URLs in the database
   - Confirm those cameras are online and accessible

2. **Test with a working camera (camera2_main):**
   - If camera2 works → your setup is fine, just need to fix camera1/12
   - If camera2 also fails → likely network or database issue

3. **If still getting 500:**
   - Check RTSPtoWebRTC logs (provided above) for the exact error
   - Share that error message and I can help further
