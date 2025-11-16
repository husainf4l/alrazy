# GPU Memory and CUDA Compilation Fixes

## Problem Summary

Your application is experiencing the following issues:

1. **libdevice Not Found**: CUDA XLA compiler can't find `libdevice.10.bc` causing JIT compilation failures
2. **GPU Memory Exhaustion**: Running out of 4.56GB GPU memory on GTX 1660 Ti
3. **BatchNormalization Errors**: JIT compilation failures in embedding extraction layer

## Root Causes

### 1. XLA JIT Compilation Issue
- TensorFlow tries to use XLA JIT compilation for GPU operations
- CUDA libdevice path is not properly configured
- This causes `libdevice not found` error

### 2. GPU Memory Pressure
- Default TensorFlow allocates entire GPU memory upfront
- BatchNormalization layer requires significant temporary memory
- Multiple models (face recognition, YOLO) compete for GPU memory

### 3. CUDA Configuration
- Missing XLA_FLAGS environment variable pointing to CUDA directory
- Missing CUDA_HOME configuration

## Solutions Implemented

### 1. Environment Variable Configuration (CRITICAL)

Added to `main.py` and `face_recognition.py`:

```python
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'              # Reduce verbose logging
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'      # Grow GPU memory as needed
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'      # Optimize threading
os.environ['TF_GPU_THREAD_PER_CORE'] = '2'            # Reduce thread contention
os.environ['TF_AUTOGRAPH_VERBOSITY'] = '0'            # Disable autograph logging
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'  # Disable XLA JIT
os.environ['XLA_FLAGS'] = '--xla_gpu_cuda_data_dir=/usr/local/cuda'  # Fix libdevice
os.environ['CUDA_HOME'] = '/usr/local/cuda'
```

### 2. Why These Fixes Work

- **TF_FORCE_GPU_ALLOW_GROWTH=true**: Instead of allocating all GPU memory upfront, allows TensorFlow to allocate memory dynamically. This prevents OOM errors and reduces initial memory pressure.

- **TF_XLA_FLAGS=--tf_xla_enable_xla_devices=false**: Disables XLA JIT compilation which was causing the libdevice errors. TensorFlow will use eager execution instead (slightly slower but more stable with limited GPU memory).

- **XLA_FLAGS=--xla_gpu_cuda_data_dir=/usr/local/cuda**: Explicitly tells XLA where to find CUDA libraries, fixing the "libdevice not found" error if XLA is used.

## How to Run

### Option 1: Use the Startup Script (RECOMMENDED)

```bash
cd /home/husain/alrazy/webcam-app-v2
python3 gpu_fix.py          # Run diagnostics and setup
bash run_app.sh              # Run the app with proper GPU config
```

### Option 2: Manual Environment Setup

```bash
cd /home/husain/alrazy/webcam-app-v2

export TF_CPP_MIN_LOG_LEVEL=2
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_THREAD_MODE=gpu_private
export TF_GPU_THREAD_PER_CORE=2
export TF_AUTOGRAPH_VERBOSITY=0
export TF_XLA_FLAGS='--tf_xla_enable_xla_devices=false'
export XLA_FLAGS='--xla_gpu_cuda_data_dir=/usr/local/cuda'
export CUDA_HOME=/usr/local/cuda

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Use run_app.sh

```bash
bash /home/husain/alrazy/webcam-app-v2/run_app.sh
```

## Verification

Run the GPU fix script to verify everything is working:

```bash
python3 gpu_fix.py
```

This will:
- ✅ Set all GPU environment variables
- ✅ Detect available GPUs
- ✅ Test TensorFlow operations
- ✅ Test DeepFace configuration
- ✅ Create optimized startup script

## Performance Expectations

### With These Fixes
- ✅ No more "libdevice not found" errors
- ✅ No more JIT compilation failures
- ✅ Gradual GPU memory allocation prevents OOM
- ✅ Embedding extraction should work correctly
- ✅ App starts successfully on GTX 1660 Ti

### Still Expected Warnings (Normal)
- "Garbage collection" messages are normal when near memory threshold
- TensorFlow warnings about device placement are informational
- CUDA warnings are typically harmless

## If Issues Persist

### Symptom: Still running out of GPU memory
**Solution:**
1. Lower batch sizes in processing:
   ```python
   # In face_recognition.py, reduce images processed per batch
   BATCH_SIZE = 1  # Process one image at a time
   ```

2. Use CPU for specific operations:
   ```python
   os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Use only GPU 0
   # Or completely CPU:
   os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Use CPU only
   ```

### Symptom: Still seeing "JIT compilation failed"
**Solution:**
- The fix `TF_XLA_FLAGS=--tf_xla_enable_xla_devices=false` disables XLA
- If you still see errors, they're from eager execution (should be recoverable)
- Check that CUDA_HOME is set correctly: `echo $CUDA_HOME`

### Symptom: GPU not detected
**Check:**
```bash
nvidia-smi  # Check if GPU driver is working
nvcc --version  # Check CUDA compiler version
```

## Technical Details

### Why Disable XLA JIT?
- XLA is an optimization that compiles TensorFlow operations to machine code
- On systems with limited GPU memory or incomplete CUDA setup, it causes issues
- Eager execution (the alternative) is slower but more stable
- For your GTX 1660 Ti with face recognition workload, eager execution is acceptable

### GPU Memory Growth Benefits
- Traditional: Allocates all 4560MB immediately → can't do anything else
- With TF_FORCE_GPU_ALLOW_GROWTH: Allocates as needed → keeps memory free for OS
- Enables multiple processes and better system stability

### Thread Configuration
- gpu_private: Each GPU thread has its own resource pool (better isolation)
- 2 threads per core: Balances parallelism with memory efficiency
- Reduces thread contention on GTX 1660 Ti

## References

- [TensorFlow GPU Configuration](https://www.tensorflow.org/guide/gpu)
- [XLA JIT Compiler](https://www.tensorflow.org/xla)
- [DeepFace Documentation](https://github.com/serengp/deepface)
- [CUDA Environment Variables](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)

## Files Modified

1. `/home/husain/alrazy/webcam-app-v2/main.py` - Added GPU config at top
2. `/home/husain/alrazy/webcam-app-v2/app/services/face_recognition.py` - Added GPU config before imports
3. `/home/husain/alrazy/webcam-app-v2/gpu_fix.py` - New diagnostic/setup script (CREATED)
4. `/home/husain/alrazy/webcam-app-v2/run_app.sh` - New startup script (CREATED)
