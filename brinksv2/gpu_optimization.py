"""
GPU Optimization utilities for CUDA acceleration
"""
import os
import torch


def enable_gpu_optimization():
    """Enable GPU optimizations for better performance"""
    if torch.cuda.is_available():
        # Enable TF32 for better performance on Ampere+ GPUs (RTX 3000/4000 series)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        
        # Enable cuDNN benchmarking for optimal convolution algorithms
        torch.backends.cudnn.benchmark = True
        
        # Set memory allocation strategy for better GPU memory utilization
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
        
        print("✅ GPU optimizations enabled")
        print(f"   - TF32: Enabled")
        print(f"   - cuDNN Benchmark: Enabled")
        print(f"   - Memory Strategy: Expandable segments")
    else:
        print("⚠️  No CUDA GPU detected, running on CPU")


def print_gpu_status():
    """Print current GPU status and availability"""
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        print(f"\n🎮 GPU Status:")
        print(f"   - CUDA Available: Yes")
        print(f"   - GPU Count: {device_count}")
        
        for i in range(device_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"   - GPU {i}: {gpu_name} ({gpu_memory:.2f} GB)")
        
        # Print current GPU memory usage
        if device_count > 0:
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            reserved = torch.cuda.memory_reserved(0) / (1024**3)
            print(f"   - Memory Allocated: {allocated:.2f} GB")
            print(f"   - Memory Reserved: {reserved:.2f} GB")
    else:
        print(f"\n🎮 GPU Status:")
        print(f"   - CUDA Available: No")
        print(f"   - Running on: CPU")


def get_optimal_device():
    """Get the optimal device for computation"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    else:
        return torch.device('cpu')


def clear_gpu_cache():
    """Clear GPU cache to free up memory"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print("🧹 GPU cache cleared")
