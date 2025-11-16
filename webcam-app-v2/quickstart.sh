#!/bin/bash
# Quick Start Guide for Running the Webcam App

echo "========================================"
echo "🚀 Webcam App - Quick Start"
echo "========================================"
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    exit 1
fi

# Check if CUDA is available
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  NVIDIA GPU not detected - app will run on CPU (slower)"
fi

echo ""
echo "========================================"
echo "📋 Running GPU Diagnostics"
echo "========================================"
echo ""

cd "$(dirname "$0")" || exit

# Run GPU fix script
python3 gpu_fix.py

echo ""
echo "========================================"
echo "🎯 Ready to Start!"
echo "========================================"
echo ""
echo "Choose one option:"
echo ""
echo "Option 1 - Run with auto GPU configuration:"
echo "  bash run_app.sh"
echo ""
echo "Option 2 - Run with manual configuration:"
echo "  export TF_FORCE_GPU_ALLOW_GROWTH=true"
echo "  export TF_XLA_FLAGS='--tf_xla_enable_xla_devices=false'"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Option 3 - Run on CPU only (if GPU issues persist):"
echo "  export CUDA_VISIBLE_DEVICES=-1"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
