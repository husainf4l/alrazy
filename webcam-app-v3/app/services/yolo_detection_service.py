"""
YOLO Detection Service for Real-Time People Detection
Optimized for multi-camera processing with YOLOv11m
"""

import threading
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from app.core.logger import logger


class YOLODetectionService:
    """
    Thread-safe YOLO detection service optimized for real-time multi-camera inference.
    
    Best Practices Implemented:
    - Thread-safe model instances per thread
    - Memory-efficient frame processing
    - Configurable confidence thresholds
    - FPS tracking and performance monitoring
    - Person class filtering (class_id=0 in COCO)
    """
    
    def __init__(
        self,
        model_path: str = "yolo11m.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "0",  # "0" for GPU, "cpu" for CPU
        half_precision: bool = True,  # FP16 for faster inference on GPU
        max_det: int = 100,
        imgsz: int = 640,
    ):
        """
        Initialize YOLO detection service.
        
        Args:
            model_path: Path to YOLO model weights
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            device: Device for inference ("0" for GPU, "cpu" for CPU)
            half_precision: Use FP16 for faster GPU inference
            max_det: Maximum detections per image
            imgsz: Input image size (640, 1280, etc.)
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.half_precision = half_precision and device != "cpu"
        self.max_det = max_det
        self.imgsz = imgsz
        
        # Thread-local storage for model instances
        self._thread_local = threading.local()
        
        # Detection results cache (thread-safe)
        self._detections_lock = threading.Lock()
        self._detections: Dict[str, Dict] = {}
        
        # Performance metrics
        self._fps_counters: Dict[str, deque] = {}
        self._fps_lock = threading.Lock()
        
        # COCO class names (person is class 0)
        self.person_class_id = 0
        
        logger.info(
            f"Initialized YOLO Detection Service: {model_path}, "
            f"device={device}, conf={conf_threshold}, half={half_precision}"
        )
    
    def _get_model(self) -> YOLO:
        """
        Get thread-local YOLO model instance.
        Creates a new model for each thread to ensure thread safety.
        
        Returns:
            YOLO model instance
        """
        if not hasattr(self._thread_local, "model"):
            logger.info(f"Loading YOLO model in thread {threading.current_thread().name}")
            self._thread_local.model = YOLO(self.model_path)
            
            # Warm up the model with a dummy inference
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            self._thread_local.model.predict(
                dummy_img,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                half=self.half_precision,
                max_det=self.max_det,
                imgsz=self.imgsz,
                verbose=False,
            )
            logger.info(f"YOLO model warmed up in thread {threading.current_thread().name}")
        
        return self._thread_local.model
    
    def detect_people(
        self,
        frame: np.ndarray,
        camera_name: str,
        stream: bool = True,
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Detect people in a frame using YOLO.
        
        Args:
            frame: Input frame (BGR format)
            camera_name: Camera identifier for tracking
            stream: Use streaming mode for memory efficiency
        
        Returns:
            Tuple of (annotated_frame, detections_list)
            detections_list contains dicts with: bbox, confidence, class_name
        """
        if frame is None or frame.size == 0:
            return frame, []
        
        start_time = time.time()
        
        try:
            # Get thread-local model
            model = self._get_model()
            
            # Run inference
            results = model.predict(
                frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                half=self.half_precision,
                max_det=self.max_det,
                imgsz=self.imgsz,
                classes=[self.person_class_id],  # Only detect people
                verbose=False,
                stream=stream,
            )
            
            # Process results
            detections = []
            annotated_frame = frame.copy()
            
            for result in results:
                boxes = result.boxes
                
                if boxes is not None and len(boxes) > 0:
                    # Extract detection information
                    for box in boxes:
                        # Get box coordinates (xyxy format)
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        
                        detection = {
                            "bbox": [int(x1), int(y1), int(x2), int(y2)],
                            "confidence": confidence,
                            "class_id": class_id,
                            "class_name": "person",
                        }
                        detections.append(detection)
                        
                        # Draw bounding box
                        cv2.rectangle(
                            annotated_frame,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            (0, 255, 0),  # Green box
                            2,
                        )
                        
                        # Draw label
                        label = f"Person {confidence:.2f}"
                        label_size, _ = cv2.getTextSize(
                            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                        )
                        cv2.rectangle(
                            annotated_frame,
                            (int(x1), int(y1) - label_size[1] - 10),
                            (int(x1) + label_size[0], int(y1)),
                            (0, 255, 0),
                            -1,
                        )
                        cv2.putText(
                            annotated_frame,
                            label,
                            (int(x1), int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 0),
                            2,
                        )
            
            # Calculate inference time
            inference_time = (time.time() - start_time) * 1000  # ms
            
            # Update detections cache
            with self._detections_lock:
                self._detections[camera_name] = {
                    "count": len(detections),
                    "detections": detections,
                    "inference_time": inference_time,
                    "timestamp": time.time(),
                }
            
            # Update FPS counter
            self._update_fps(camera_name)
            
            # Draw detection info on frame
            info_text = f"People: {len(detections)} | {inference_time:.1f}ms"
            cv2.putText(
                annotated_frame,
                info_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            
            return annotated_frame, detections
        
        except Exception as e:
            logger.error(f"Error detecting people in {camera_name}: {e}")
            return frame, []
    
    def _update_fps(self, camera_name: str):
        """Update FPS counter for a camera."""
        with self._fps_lock:
            if camera_name not in self._fps_counters:
                self._fps_counters[camera_name] = deque(maxlen=30)
            
            self._fps_counters[camera_name].append(time.time())
    
    def get_fps(self, camera_name: str) -> float:
        """
        Get current FPS for a camera.
        
        Args:
            camera_name: Camera identifier
        
        Returns:
            FPS value
        """
        with self._fps_lock:
            if camera_name not in self._fps_counters:
                return 0.0
            
            counter = self._fps_counters[camera_name]
            if len(counter) < 2:
                return 0.0
            
            time_diff = counter[-1] - counter[0]
            if time_diff > 0:
                return len(counter) / time_diff
            return 0.0
    
    def get_detections(self, camera_name: Optional[str] = None) -> Dict:
        """
        Get current detections for one or all cameras.
        
        Args:
            camera_name: Specific camera or None for all cameras
        
        Returns:
            Dictionary of detection results
        """
        with self._detections_lock:
            if camera_name:
                return self._detections.get(camera_name, {})
            return self._detections.copy()
    
    def get_stats(self) -> Dict:
        """
        Get performance statistics for all cameras.
        
        Returns:
            Dictionary with stats per camera
        """
        stats = {}
        with self._detections_lock:
            for camera_name, data in self._detections.items():
                stats[camera_name] = {
                    "people_count": data.get("count", 0),
                    "inference_time_ms": data.get("inference_time", 0),
                    "detection_fps": self.get_fps(camera_name),
                    "last_update": data.get("timestamp", 0),
                }
        return stats


# Global YOLO service instance (lazy initialization)
_yolo_service: Optional[YOLODetectionService] = None
_yolo_service_lock = threading.Lock()


def get_yolo_service(
    model_path: str = "yolo11m.pt",
    conf_threshold: float = 0.5,
    device: str = "0",
) -> YOLODetectionService:
    """
    Get or create the global YOLO detection service instance.
    
    Args:
        model_path: Path to YOLO model weights
        conf_threshold: Confidence threshold for detections
        device: Device for inference ("0" for GPU, "cpu" for CPU)
    
    Returns:
        YOLODetectionService instance
    """
    global _yolo_service
    
    if _yolo_service is None:
        with _yolo_service_lock:
            if _yolo_service is None:
                _yolo_service = YOLODetectionService(
                    model_path=model_path,
                    conf_threshold=conf_threshold,
                    device=device,
                )
    
    return _yolo_service
