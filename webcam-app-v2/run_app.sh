#!/bin/bash
# Webcam App GPU-Optimized Startup Script
# This script sets all necessary environment variables for GPU optimization
# and then starts the FastAPI application

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

export TF_CPP_MIN_LOG_LEVEL=2
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_THREAD_MODE=gpu_private
export TF_GPU_THREAD_PER_CORE=2
export TF_AUTOGRAPH_VERBOSITY=0
export TF_XLA_FLAGS='--tf_xla_enable_xla_devices=false'
export TF_ENABLE_GPU_GARBAGE_COLLECTION=true

if [ -d "/usr/local/cuda" ]; then
    export XLA_FLAGS='--xla_gpu_cuda_data_dir=/usr/local/cuda'
    export CUDA_HOME=/usr/local/cuda
    echo "✅ CUDA found at /usr/local/cuda"
else
    echo "⚠️  CUDA not found at /usr/local/cuda"
fi

echo ""
echo "🚀 Starting Webcam App with GPU optimization..."
echo "📊 Environment Variables Set:"
echo "   - TF_FORCE_GPU_ALLOW_GROWTH=true"
echo "   - TF_XLA_FLAGS=--tf_xla_enable_xla_devices=false"
echo ""

# Run the application
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
