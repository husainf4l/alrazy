# App package

# CRITICAL: Configure TensorFlow GPU FIRST - before any ML library imports
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'
os.environ['TF_GPU_THREAD_PER_CORE'] = '2'
os.environ['TF_AUTOGRAPH_VERBOSITY'] = '0'
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'
os.environ['TF_ENABLE_GPU_GARBAGE_COLLECTION'] = 'true'
os.environ['TF_DISABLE_MKL'] = 'false'

# Use CPU for embedding extraction to avoid libdevice errors
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Fix CUDA libdevice issue (for reference)
cuda_path = '/usr/local/cuda'
if os.path.exists(cuda_path):
    os.environ['XLA_FLAGS'] = f'--xla_gpu_cuda_data_dir={cuda_path}'
    os.environ['CUDA_HOME'] = cuda_path
