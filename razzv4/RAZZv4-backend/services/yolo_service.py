"""
YOLO11 Service for person detection and counting
Uses Ultralytics YOLO11 model for real-time person detection
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
from ultralytics import YOLO
import cv2
from pathlib import Path
import supervision as sv

logger = logging.getLogger(__name__)


class YOLOService:
    """
    Service class for YOLO11 person detection
    Handles model loading, inference, and person counting
    """
    
    def __init__(self, model_name: str = "yolo11n.pt", confidence_threshold: float = 0.5):
        """
        Initialize YOLO service
        
        Args:
            model_name: YOLO model to use (yolo11n.pt, yolo11s.pt, yolo11m.pt, yolo11l.pt, yolo11x.pt)
                       n=nano (fastest), s=small, m=medium, l=large, x=extra large (most accurate)
            confidence_threshold: Minimum confidence score for detections (0.0-1.0)
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None
        self.person_class_id = 0  # In COCO dataset, person class is 0
        self.device = None
        
        logger.info(f"Initializing YOLO service with model: {model_name}")
        self._detect_device()
        self._load_model()
    
    def _detect_device(self):
        """Detect and configure GPU if available"""
        try:
            import torch
            if torch.cuda.is_available():
                self.device = 'cuda'
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"🚀 GPU detected: {gpu_name} ({gpu_memory:.1f}GB VRAM)")
                logger.info(f"🎮 YOLO will use CUDA acceleration")
            else:
                self.device = 'cpu'
                logger.warning("⚠️  No GPU detected - using CPU (slower)")
        except ImportError:
            self.device = 'cpu'
            logger.warning("⚠️  PyTorch not found - using CPU")
    
    def _load_model(self):
        """Load YOLO11 model and move to GPU if available"""
        try:
            # This will automatically download the model if not present
            self.model = YOLO(self.model_name)
            
            # Move model to GPU if available
            if self.device == 'cuda':
                self.model.to('cuda')
                logger.info(f"✅ YOLO model loaded on GPU: {self.model_name}")
            else:
                logger.info(f"✅ YOLO model loaded on CPU: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect_people(self, frame: np.ndarray) -> Tuple[int, List[dict], sv.Detections]:
        """
        Detect people in a frame using YOLO with GPU acceleration
        Returns both legacy dict format and supervision Detections for ByteTrack
        
        Args:
            frame: Input image/frame as numpy array (BGR format from OpenCV)
        
        Returns:
            Tuple of (person_count, detections_list, detections_sv)
        """
        if self.model is None:
            raise RuntimeError("YOLO model not loaded")
        
        try:
            # Run inference with GPU and FP16 optimization (same as brinksv2)
            results = self.model.predict(
                frame,
                classes=[0],  # Person class only (faster)
                conf=self.confidence_threshold,
                iou=0.7,  # IoU threshold for NMS
                verbose=False,
                device=self.device,
                half=True if self.device == 'cuda' else False  # FP16 for faster GPU inference
            )
            
            # Convert to supervision Detections format for ByteTrack
            detections_sv = sv.Detections.from_ultralytics(results[0])
            
            detections = []
            person_count = 0
            
            # Also create legacy format for compatibility
            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                    
                    detections.append({
                        "bbox": bbox.tolist(),
                        "confidence": confidence,
                        "class_name": "person",
                        "class_id": 0
                    })
                    person_count += 1
            
            logger.debug(f"Detected {person_count} people in frame")
            return person_count, detections, detections_sv
            
        except Exception as e:
            logger.error(f"Error during YOLO inference: {e}")
            return 0, []
    
    def annotate_frame(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Input image/frame
            detections: List of detections from detect_people()
        
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            bbox = detection["bbox"]
            confidence = detection["confidence"]
            
            # Convert bbox to integers
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"Person {confidence:.2f}"
            (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_frame, (x1, y1 - label_height - 10), (x1 + label_width, y1), (0, 255, 0), -1)
            cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Add total count at top
        count_text = f"People Count: {len(detections)}"
        cv2.putText(annotated_frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return annotated_frame
    
    def process_frame(self, frame: np.ndarray, annotate: bool = False) -> Tuple[int, Optional[np.ndarray]]:
        """
        Process a single frame: detect people and optionally annotate
        
        Args:
            frame: Input frame
            annotate: Whether to return annotated frame
        
        Returns:
            Tuple of (person_count, annotated_frame or None)
        """
        person_count, detections = self.detect_people(frame)
        
        annotated_frame = None
        if annotate:
            annotated_frame = self.annotate_frame(frame, detections)
        
        return person_count, annotated_frame
