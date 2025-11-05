# Professional Streaming Configuration Guide

## 📺 Current Setup

### Video Specifications

| Parameter | Value |
|-----------|-------|
| **Resolution** | 2560 × 1440 (2K) |
| **Frame Rate** | 30 fps |
| **Codec** | H.265 (HEVC) |
| **Bitrate** | 6 Mbps (6144 kbps) |
| **Quality** | High (Professional) |

### Why H.265 (HEVC)?

✅ **50% Better Compression** - H.265 achieves better quality at half the bitrate of H.264
✅ **Future Proof** - Latest codec standard for 2K/4K streaming
✅ **Lower Bandwidth** - 6 Mbps H.265 ≈ 12 Mbps H.264 in quality
✅ **Better for Person Re-ID** - Preserves fine details needed for face/gait recognition

### Frame Rate Selection

| FPS | Use Case | Bandwidth Impact |
|-----|----------|-----------------|
| 25 fps | Standard surveillance (minimum) | Baseline |
| 30 fps | High-quality real-time monitoring | +20% bandwidth |
| 60 fps | Fast-motion detection (sports, etc) | +100% bandwidth |

**Current choice: 30 fps** - Smooth real-time playback with good motion capture for person re-ID

## 🎥 Camera System Integration

### Camera Streaming Layers

**Main Stream (4K or higher)**
- Source: `Channels/101, 201, 301, 401` (room1-4 main)
- Use case: Long-term recording, high-quality archival
- Not used by detection (CPU intensive)

**Sub Stream (Low Quality)**
- Source: `Channels/102, 202, 302, 402` (room1-4 sub)
- Current: 352×288 @ 25fps
- Use case: Real-time detection/tracking
- **Good:** Lower CPU, faster processing

**Recommendation:** Configure sub-stream to H.265 at:
- Resolution: 1920×1080 (1080p) or 2560×1440 (2K)
- Codec: H.265
- Bitrate: 4-8 Mbps
- FPS: 25-30

## 🔧 Configuration Options

### Environment Variables

```bash
# Streaming codec
export STREAMING_CODEC="H.265"  # Options: H.265, H.264

# Resolution (width, height)
export STREAMING_RESOLUTION="2560,1440"  # 2K default

# Frame rate
export STREAMING_FPS="30"  # Range: 15-60

# Bitrate in kbps
export STREAMING_BITRATE_KBPS="6144"  # 6 Mbps (4-8 Mbps typical)

# Quality level
export STREAMING_QUALITY="high"  # Options: high, medium, low

# Enable/disable streaming
export STREAMING_ENABLED="true"
```

### Quality Presets

#### 🥇 High Quality (Current)
```json
{
  "resolution": "2560x1440",
  "fps": 30,
  "bitrate_mbps": 6,
  "codec": "H.265",
  "use_case": "Professional monitoring, person re-ID, forensics"
}
```

#### 🥈 Medium Quality
```json
{
  "resolution": "1920x1080",
  "fps": 25,
  "bitrate_mbps": 4,
  "codec": "H.265",
  "use_case": "Balanced quality/bandwidth for standard surveillance"
}
```

#### 🥉 Low Quality / Mobile
```json
{
  "resolution": "1280x720",
  "fps": 20,
  "bitrate_mbps": 2,
  "codec": "H.264",
  "use_case": "Mobile viewing, bandwidth-constrained networks"
}
```

## 📊 Bandwidth Requirements

### Per-Camera Bitrates

| Resolution | Codec | FPS | Bitrate | Bandwidth (4 cameras) |
|------------|-------|-----|---------|----------------------|
| 2560×1440 | H.265 | 30  | 6 Mbps  | **24 Mbps** ✅ |
| 2560×1440 | H.264 | 30  | 12 Mbps | 48 Mbps |
| 1920×1080 | H.265 | 25  | 4 Mbps  | **16 Mbps** ✅ |
| 1920×1080 | H.264 | 25  | 8 Mbps  | 32 Mbps |
| 1280×720  | H.265 | 20  | 2 Mbps  | **8 Mbps** ✅ |
| 1280×720  | H.264 | 20  | 4 Mbps  | 16 Mbps |

**✅ Recommended:** H.265 @ 2560×1440 (24 Mbps total) - Excellent quality with reasonable bandwidth

## 🚀 Performance Optimization

### Hardware Recommendations

| Task | Min Requirement | Recommended |
|------|-----------------|-------------|
| 4×2K @30fps Detection | 4-core CPU | 8+ cores, GPU |
| Person Re-ID | 8GB RAM | 16GB+ |
| Storage (24h) | 500 GB | 1-2 TB |
| Network | 25 Mbps | 100 Mbps |

### CPU/GPU Encoding Considerations

**Software Encoding (CPU)**
- codec: libx265 (H.265)
- preset: medium, slow, slower (quality vs speed tradeoff)
- **Current system uses:** Software encoding

**Hardware Encoding (GPU - if available)**
- NVIDIA: nvenc_hevc
- AMD: hevc_amf
- Intel: hevc_qsv
- **10-20× faster than software encoding**

### Detection Optimization

Current system uses:
- **Model:** YOLOv8n (lightweight, CPU-friendly)
- **Input:** Sub-stream only (352×288)
- **Person Re-ID:** Global shared gallery (efficient cross-camera matching)
- **Image Enhancement:** CLAHE + unsharp masking (preserve details for re-ID)

## 📋 API Endpoints

### Get Current Configuration

```bash
curl http://localhost:8000/config | jq '.streaming'
```

Response:
```json
{
  "enabled": true,
  "codec": "H.265",
  "resolution": [2560, 1440],
  "resolution_2k": "2560x1440",
  "fps": 30,
  "bitrate_kbps": 6144,
  "bitrate_mbps": 6.0,
  "quality": "high"
}
```

## 🛠️ Deployment Steps

### 1. Update Camera Sub-Stream Settings

On your Hikvision camera (192.168.1.186):
- Login to web UI: `http://192.168.1.186:80`
- Navigate to **Channel Management** → **Video**
- Select **Sub Stream (Channel 102, 202, 302, 402)**
- Set:
  - **Codec:** H.265
  - **Resolution:** 2560×1440 (or 1920×1080)
  - **Frame Rate:** 30 fps
  - **Bitrate Type:** CBR (Constant Bit Rate)
  - **Bitrate:** 6000 kbps (6 Mbps)

### 2. Configure Backend

```bash
# Set environment variables
export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="2560,1440"
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="6144"

# Start backend
cd /home/husain/alrazy/brinks
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

### 3. Verify Configuration

```bash
# Check config endpoint
curl http://localhost:8000/config | jq '.streaming'

# Monitor backend logs
tail -f backend.log
```

## 📈 Quality Verification

### Image Quality Metrics

```bash
# Test frame ingestion with image quality
curl -X POST http://localhost:8000/ingest \
  -F "file=@test_frame.jpg" \
  -F "camera_id=room1" \
  -F "room_id=room_safe"
```

### Monitor Performance

```bash
# Check processing time (look for frame processing duration)
tail -100 backend.log | grep -E "ms|FPS|detection"

# Monitor bandwidth usage
watch -n 1 'ifstat | tail -3'
```

## 🔍 Troubleshooting

### Issue: High CPU Usage

**Solutions:**
1. Reduce resolution (2560×1440 → 1920×1080)
2. Lower FPS (30 → 25)
3. Use H.264 codec (slightly easier to encode)
4. Enable GPU encoding if available
5. Reduce detection frequency (process every Nth frame)

### Issue: Quality Reduced After Enhancement

**Check:**
1. CLAHE is enabled: `enable_clahe: true`
2. Sharpening active: `enable_sharpening: true`
3. JPEG quality high: `jpeg_quality: 98`
4. Denoising disabled: `enable_denoise: false` (preserves detail)

### Issue: Low Frame Rate

**Solutions:**
1. Check network bandwidth: `iftop`, `nethogs`
2. Verify camera bitrate settings
3. Check backend logs for bottlenecks
4. Ensure all cameras use sub-stream
5. Reduce output resolution temporarily

### Issue: Camera Latency

**Solutions:**
1. Reduce buffer size in OpenCV: `CAP_PROP_BUFFERSIZE=1` ✅ (already set)
2. Use UDP for RTSP: Add `?transport=udp` to stream URL
3. Lower sub-stream resolution
4. Reduce detection interval

## 📚 References

- **H.265 Codec:** HEVC (High Efficiency Video Coding) - ITU-T H.265
- **FFmpeg H.265:** `libx265` encoder options and presets
- **OpenCV Streaming:** VideoCapture with RTSP support
- **Bitrate Calculator:** bitrate = resolution × fps × quality_factor

## 🎯 Summary

Your system is now configured for **professional-grade 2K streaming** with:
- ✅ H.265 codec (50% better compression)
- ✅ 2560×1440 resolution (2K quality)
- ✅ 30 fps (smooth real-time)
- ✅ 6 Mbps bitrate (balanced quality/bandwidth)
- ✅ High-quality image enhancement (CLAHE + sharpening)
- ✅ Global cross-camera person re-ID (unified person tracking)

This configuration is optimal for security monitoring with advanced person re-identification capabilities.
