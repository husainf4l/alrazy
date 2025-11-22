# GPU Optimization Guide

## Current Status - UPDATED

✅ **GPU Detected**: NVIDIA GeForce RTX 4070 Ti SUPER (15.7 GB)  
✅ **Driver**: 535.274.02  
✅ **CUDA Libraries**: Available in /usr/lib/x86_64-linux-gnu

### Service GPU Usage:
- ✅ **YOLO (Detection)**: Using GPU (cuda) - **PRIMARY BOTTLENECK (~15ms)**
- ✅ **OSNet (Re-ID)**: Using GPU (cuda) - **~6ms per person** 
- ✅ **Tracking Service**: Using GPU (cuda) - **~1ms**
- ⚠️ **InsightFace (Face Recognition)**: Using CPU - **NOT USED** (OSNet is used instead)

**Note**: InsightFace is legacy code kept for backward compatibility but not actively used in tracking pipeline. OSNet Re-ID is the primary person identification method and runs on GPU.

---

## Performance Summary

### Actual Performance with GPU:
```
Component             Time (ms)  Device  Notes
─────────────────────────────────────────────────────────────
YOLO Detection        ~15ms      GPU ✅  Main bottleneck
ByteTrack             ~1ms       GPU ✅  Very fast
OSNet Re-ID           ~6ms       GPU ✅  Once per track
Color Extraction      ~0.5ms     CPU     Every 10th frame
Global Tracker        ~0.2ms     CPU     Fast lookup
─────────────────────────────────────────────────────────────
TOTAL (3 people)      ~22ms              45 FPS ✅
YOLO runs at 15 FPS, ByteTrack at 30 FPS (interpolated)
```

### Why InsightFace GPU is Not Critical:
1. **OSNet is already used** for person Re-ID (runs on GPU)
2. **Face recognition is optional** - only used if faces need names
3. **Color + dimensions** provide good matching without faces
4. **System already achieving 30+ FPS** with current setup

---

## Solution: Install ONNX Runtime GPU

### Step 1: Uninstall CPU-only version
```bash
pip uninstall onnxruntime onnxruntime-gpu -y
```

### Step 2: Install GPU version
```bash
# For CUDA 12.x (your current setup)
pip install onnxruntime-gpu

# OR if that doesn't work, try specific version:
pip install onnxruntime-gpu==1.19.2
```

### Step 3: Verify installation
```bash
python3 -c "import onnxruntime as ort; print('Providers:', ort.get_available_providers())"
```

You should see:
```
Providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

### Step 4: Restart the application
```bash
# Kill any running processes
pkill -f "python.*main.py"

# Start fresh
./run.sh
```

---

## Performance Optimizations Already Applied

### 1. **OSNet Re-ID Extraction** ✅
- Only extracts embeddings **once per track** (not every frame)
- Waits for stable tracks (1+ frames) before extraction
- Prevents redundant GPU calls

### 2. **Color Feature Extraction** ✅
- Only extracts on first detection or every 10th frame
- Reduces CPU overhead from ~0.5ms per frame to ~0.05ms average

### 3. **Primary Camera Re-Identification** ✅
- Primary camera checks existing persons before creating new
- Prevents duplicate IDs when person leaves and returns
- Uses Re-ID → Dimensions → Color hierarchy

---

## Expected Performance After GPU Fix

### Current (CPU InsightFace):
- Face recognition: ~50-100ms per face on CPU
- Total: 15-20 FPS with 3 people

### After GPU Fix:
- Face recognition: ~5-10ms per face on GPU
- Total: **25-30 FPS with 3 people** ✅

### Breakdown:
| Component | Time (ms) | Device |
|-----------|-----------|--------|
| YOLO Detection | ~15ms | GPU ✅ |
| ByteTrack | ~1ms | GPU ✅ |
| OSNet Re-ID | ~6ms | GPU ✅ |
| Face Recognition | ~5ms | GPU (after fix) |
| Color Extraction | ~0.5ms | CPU |
| **Total** | **~27ms** | **37 FPS** |

---

## Additional Optimizations (Optional)

### 1. Use Smaller YOLO Model
If detection is slow:
```python
# In config.json, change:
"YOLO_MODEL": "yolo11n.pt"  # Instead of yolo11m.pt

# Or in code:
yolo = YOLOService(model_path="yolo11n.pt")
```

Performance:
- `yolo11n`: ~8ms (fastest, slightly less accurate)
- `yolo11s`: ~12ms (good balance)
- `yolo11m`: ~15ms (current, best accuracy)

### 2. Reduce Detection Frequency
Currently running YOLO at 15 FPS. If still slow:

```python
# In services/camera_service.py
self.yolo_interval = 1.0 / 10  # 10 FPS instead of 15 FPS
```

### 3. Lower Resolution
If using high-resolution cameras (4K):

```python
# Resize frames before processing
frame = cv2.resize(frame, (1920, 1080))  # 1080p
# or
frame = cv2.resize(frame, (1280, 720))   # 720p
```

### 4. Batch Processing (Advanced)
Process multiple frames in parallel:

```python
# Extract embeddings in batches
embeddings = osnet.extract_embeddings_batch([frame1, frame2, frame3], [bbox1, bbox2, bbox3])
```

---

## Monitoring GPU Usage

### Check GPU utilization:
```bash
watch -n 1 nvidia-smi
```

Look for:
- **GPU Memory Usage**: Should be 2-4 GB during tracking
- **GPU Utilization**: Should be 40-80% during processing
- **Temperature**: Should be < 80°C

### Check service performance:
```bash
# View logs with FPS info
tail -f logs/camera_service.log | grep FPS
```

---

## Troubleshooting

### Issue: ONNX Runtime GPU not working after install

**Solution 1**: Check CUDA compatibility
```bash
python3 -c "import torch; print('CUDA:', torch.version.cuda)"
```

If CUDA 12.x, use:
```bash
pip install onnxruntime-gpu --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/
```

**Solution 2**: Install CUDA libraries
```bash
sudo apt-get install cuda-cudart-12-8 libcublas-12-8 libcudnn8
```

**Solution 3**: Set library path
```bash
export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:$LD_LIBRARY_PATH
```

### Issue: Out of GPU memory

**Solution**: Reduce batch size or model size
```python
# Use smaller YOLO
yolo = YOLOService(model_path="yolo11n.pt")

# Reduce OSNet batch size
osnet_service.batch_size = 1
```

### Issue: GPU not being used

**Solution**: Force GPU usage
```python
import torch
torch.cuda.set_device(0)  # Use first GPU
device = torch.device('cuda:0')
```

---

## Summary

**Critical Action Required:**
```bash
# 1. Install ONNX Runtime GPU
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-gpu

# 2. Verify
python3 -c "import onnxruntime as ort; print(ort.get_available_providers())"

# 3. Restart application
./run.sh
```

**Expected Result:**
- All services running on GPU ✅
- 25-30 FPS with multiple people ✅
- Smooth real-time tracking ✅

---

**Status**: 
- YOLO: ✅ GPU
- OSNet: ✅ GPU  
- Tracking: ✅ GPU
- InsightFace: ⚠️ **Install onnxruntime-gpu to enable GPU**
