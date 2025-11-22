"""
YOLO Configuration Settings
"""

# YOLO Model Configuration
YOLO_MODEL_PATH = "yolo11m.pt"  # Model weights file (will auto-download if not present)
YOLO_CONFIDENCE_THRESHOLD = 0.45  # Lower threshold for better detection (0.0 - 1.0)
YOLO_IOU_THRESHOLD = 0.45  # IoU threshold for Non-Maximum Suppression
YOLO_MAX_DETECTIONS = 50  # Reduced for faster processing
YOLO_IMAGE_SIZE = 640  # Optimal size for speed/accuracy balance

# Device Configuration (Optimized for GPU)
YOLO_DEVICE = "0"  # "0" for GPU (CUDA)
YOLO_HALF_PRECISION = True  # FP16 for 2x faster GPU inference

# Detection Classes
YOLO_DETECT_CLASSES = [0]  # [0] = person only, [] = all classes

# Performance Settings
YOLO_STREAM_MODE = True  # Use streaming mode for memory efficiency
YOLO_VERBOSE = False  # Disable verbose logging

# Detection Settings
YOLO_ENABLE_DETECTION = True  # Enable/disable YOLO detection globally
YOLO_ANNOTATE_FRAMES = True  # Draw bounding boxes on frames
YOLO_SAVE_DETECTIONS = False  # Save detection results to database

# Camera-specific settings (optional overrides)
CAMERA_YOLO_SETTINGS = {
    # "camera2_back_yard": {
    #     "conf_threshold": 0.6,
    #     "enable": True,
    # },
    # "camera5": {
    #     "conf_threshold": 0.4,
    #     "enable": False,  # Disable YOLO for this camera
    # },
}
