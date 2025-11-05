# Streaming Configuration - Quick Reference

## ⚡ Quick Start

### Current Configuration (Loaded)
```bash
# Verify current settings
curl http://localhost:8000/config | jq '.streaming'
```

**Output:**
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

## 🔄 Change Streaming Configuration

### Restart with Different Settings

#### 🥇 High Quality (2K) - Current Default
```bash
cd /home/husain/alrazy/brinks

# Environment variables for high quality
export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="2560,1440"
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="6144"
export STREAMING_QUALITY="high"

# Restart backend
pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

#### 🥈 Medium Quality (1080p)
```bash
cd /home/husain/alrazy/brinks

export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="1920,1080"
export STREAMING_FPS="25"
export STREAMING_BITRATE_KBPS="4096"
export STREAMING_QUALITY="medium"

pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

#### 🥉 Low Quality / Mobile
```bash
cd /home/husain/alrazy/brinks

export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="1280,720"
export STREAMING_FPS="20"
export STREAMING_BITRATE_KBPS="2048"
export STREAMING_QUALITY="low"

pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

#### 💾 H.264 (If H.265 Not Supported)
```bash
cd /home/husain/alrazy/brinks

export STREAMING_CODEC="H.264"
export STREAMING_RESOLUTION="2560,1440"
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="12288"  # Double bitrate for H.264
export STREAMING_QUALITY="high"

pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

## 📊 Predefined Configurations

### Mobile Streaming (Cellular Networks)
```bash
# Low bandwidth, acceptable quality
export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="1024,576"
export STREAMING_FPS="15"
export STREAMING_BITRATE_KBPS="1024"
export STREAMING_QUALITY="low"
```

### LAN/Local Network (Max Quality)
```bash
# Gigabit network available
export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="3840,2160"  # 4K
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="10240"    # 10 Mbps
export STREAMING_QUALITY="high"
```

### Person Re-ID Optimized (Current)
```bash
# Balanced for re-identification accuracy
export STREAMING_CODEC="H.265"
export STREAMING_RESOLUTION="2560,1440"  # 2K - enough detail for faces/gait
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="6144"     # 6 Mbps
export STREAMING_QUALITY="high"
```

## 🎯 Bandwidth Planning

### 4-Camera System Bandwidth

| Configuration | Per-Camera | Total (4x) | Network Link |
|---------------|-----------|-----------|--------------|
| 2560×1440@30 H.265 | 6 Mbps | **24 Mbps** | ≥100 Mbps LAN |
| 1920×1080@25 H.265 | 4 Mbps | **16 Mbps** | ≥100 Mbps LAN |
| 1280×720@20 H.265 | 2 Mbps | **8 Mbps** | ≥10 Mbps WAN |
| 1024×576@15 H.265 | 1 Mbps | **4 Mbps** | ≥5 Mbps WAN |

## 🔍 Monitor & Verify

### Check Backend Status
```bash
# Is backend running?
ps aux | grep "uvicorn backend.main"

# Recent logs (last 30 lines)
tail -30 /home/husain/alrazy/brinks/backend.log

# Real-time log monitoring
tail -f /home/husain/alrazy/brinks/backend.log | grep -E "initialized|streaming|config|ERROR"
```

### Verify Configuration Loaded
```bash
# Full configuration
curl -s http://localhost:8000/config | jq '.' | head -50

# Just streaming section
curl -s http://localhost:8000/config | jq '.streaming'

# Just image quality section
curl -s http://localhost:8000/config | jq '.camera_quality'
```

### Test Frame Ingestion
```bash
# With pretty-print
curl -s http://localhost:8000/config | jq '.streaming' | tee /tmp/streaming_config.json
```

## 🛠️ Common Tasks

### Reload Backend with Current Config
```bash
cd /home/husain/alrazy/brinks
pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
sleep 3
curl -s http://localhost:8000/config | jq '.streaming'
```

### Switch to H.264 Quickly
```bash
export STREAMING_CODEC="H.264"
export STREAMING_BITRATE_KBPS="12288"  # Double for H.264
pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

### Reduce Quality Temporarily
```bash
export STREAMING_RESOLUTION="1920,1080"
export STREAMING_FPS="20"
export STREAMING_BITRATE_KBPS="3000"
pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

### Enable High Performance Mode
```bash
export STREAMING_RESOLUTION="2560,1440"
export STREAMING_FPS="30"
export STREAMING_BITRATE_KBPS="8192"   # 8 Mbps
pkill -f "uvicorn backend.main"
sleep 2
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

## 📝 Default Environment Values

If not set, these defaults are used:

```python
STREAMING_ENABLED = "true"
STREAMING_CODEC = "H.265"
STREAMING_RESOLUTION = "2560,1440"
STREAMING_FPS = "30"
STREAMING_BITRATE_KBPS = "6144"        # 6 Mbps
STREAMING_QUALITY = "high"
```

## 🎬 Integration with Image Quality

The streaming configuration works alongside image quality settings:

```bash
# Both can be enabled simultaneously
Image Quality Settings:
- JPEG_QUALITY=98              # Maximum JPEG compression quality
- ENABLE_CLAHE=true            # Contrast enhancement
- ENABLE_SHARPENING=true       # Detail enhancement
- ENABLE_AUTO_CONTRAST=true    # Dynamic range

Streaming Configuration:
- STREAMING_CODEC="H.265"      # Video codec
- STREAMING_RESOLUTION="2560,1440"    # Frame resolution
- STREAMING_BITRATE_KBPS="6144"       # Network bitrate
```

Result: **High-quality 2K streaming with enhanced image preprocessing**

## 🚀 Performance Tips

1. **For CPU**: Reduce FPS or resolution if CPU > 80%
2. **For Network**: Monitor bandwidth with `iftop` or `nethogs`
3. **For Quality**: Ensure `enable_clahe=true` and `enable_sharpening=true`
4. **For Real-time**: Keep FPS ≥ 25 for smooth playback
5. **For Person Re-ID**: Keep resolution ≥ 1080p for accurate matching

## 📞 Support

Check these files for more information:
- `STREAMING_CONFIG.md` - Detailed configuration guide
- `backend/main.py` - Search for `STREAMING_CONFIG` and `IMAGE_QUALITY_CONFIG`
- `camera_system.py` - Camera RTSP stream management
- `backend.log` - Real-time system logs
