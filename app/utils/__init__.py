"""
Utility functions for the Al Razy Pharmacy Security System.
"""
import base64
import cv2
import numpy as np
import time
import asyncio
from typing import Optional, Tuple, Any, Dict
import logging


def encode_frame_to_base64(frame: np.ndarray, quality: int = 85) -> str:
    """Encode OpenCV frame to base64 string."""
    try:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_param)
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        del buffer  # Clean up memory
        return frame_b64
    except Exception as e:
        logging.error(f"Error encoding frame to base64: {e}")
        return ""


def decode_base64_to_frame(base64_string: str) -> Optional[np.ndarray]:
    """Decode base64 string to OpenCV frame."""
    try:
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logging.error(f"Error decoding base64 to frame: {e}")
        return None


def get_frame_info(frame: np.ndarray) -> Dict[str, Any]:
    """Get information about a frame."""
    if frame is None:
        return {"error": "Frame is None"}
    
    return {
        "shape": frame.shape,
        "dtype": str(frame.dtype),
        "size": frame.size,
        "resolution": f"{frame.shape[1]}x{frame.shape[0]}"
    }


def resize_frame(frame: np.ndarray, width: int = None, height: int = None, 
                scale: float = None) -> np.ndarray:
    """Resize frame with various options."""
    if frame is None:
        return None
    
    if scale:
        width = int(frame.shape[1] * scale)
        height = int(frame.shape[0] * scale)
    elif width and not height:
        aspect_ratio = frame.shape[0] / frame.shape[1]
        height = int(width * aspect_ratio)
    elif height and not width:
        aspect_ratio = frame.shape[1] / frame.shape[0]
        width = int(height * aspect_ratio)
    
    if width and height:
        return cv2.resize(frame, (width, height))
    
    return frame


def annotate_frame(frame: np.ndarray, text: str, position: Tuple[int, int] = (10, 30),
                  color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
    """Add text annotation to frame."""
    if frame is None:
        return None
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    
    # Add background rectangle for better text visibility
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(frame, 
                 (position[0] - 5, position[1] - text_height - 5),
                 (position[0] + text_width + 5, position[1] + 5),
                 (0, 0, 0), -1)
    
    # Add text
    cv2.putText(frame, text, position, font, font_scale, color, thickness)
    
    return frame


def draw_detection_box(frame: np.ndarray, bbox: Tuple[int, int, int, int],
                      label: str = "", confidence: float = None,
                      color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
    """Draw detection bounding box on frame."""
    if frame is None:
        return None
    
    x, y, w, h = bbox
    
    # Draw rectangle
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    
    # Add label with confidence if provided
    if label:
        label_text = f"{label}"
        if confidence is not None:
            label_text += f" ({confidence:.2f})"
        
        # Calculate label size and position
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        (label_w, label_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
        
        # Draw label background
        cv2.rectangle(frame, (x, y - label_h - 10), (x + label_w, y), color, -1)
        
        # Draw label text
        cv2.putText(frame, label_text, (x, y - 5), font, font_scale, (255, 255, 255), thickness)
    
    return frame


def calculate_fps(timestamps: list) -> float:
    """Calculate FPS from timestamp list."""
    if len(timestamps) < 2:
        return 0.0
    
    time_diff = timestamps[-1] - timestamps[0]
    if time_diff == 0:
        return 0.0
    
    return (len(timestamps) - 1) / time_diff


def create_timestamp() -> float:
    """Create current timestamp."""
    return time.time()


def format_timestamp(timestamp: float, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to readable string."""
    return time.strftime(format_string, time.localtime(timestamp))


def safe_async_run(coroutine, timeout: float = 30.0):
    """Safely run async coroutine with timeout."""
    try:
        return asyncio.wait_for(coroutine, timeout=timeout)
    except asyncio.TimeoutError:
        logging.warning(f"Async operation timed out after {timeout} seconds")
        return None
    except Exception as e:
        logging.error(f"Async operation failed: {e}")
        return None


def validate_camera_id(camera_id: int, available_cameras: list) -> bool:
    """Validate if camera ID is in available cameras list."""
    return camera_id in available_cameras


def generate_unique_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix."""
    import uuid
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id


def ensure_directory_exists(directory_path: str) -> bool:
    """Ensure directory exists, create if not."""
    import os
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Failed to create directory {directory_path}: {e}")
        return False


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    import os
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0


def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """Clean up old files in directory."""
    import os
    import glob
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    cleaned_count = 0
    
    try:
        for file_path in glob.glob(os.path.join(directory, "*")):
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    cleaned_count += 1
                    logging.info(f"Cleaned up old file: {file_path}")
    except Exception as e:
        logging.error(f"Error cleaning up files in {directory}: {e}")
    
    return cleaned_count
