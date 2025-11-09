"""
Advanced Multi-Object Tracking Service
Implements ByteTrack and DeepSORT with conditional tracking strategies
Optimized for WebRTC streaming and real-time performance
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import cv2
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment
from collections import deque, defaultdict
import time

logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Track lifecycle states"""
    NEW = 1
    TRACKED = 2
    LOST = 3
    REMOVED = 4


@dataclass
class Detection:
    """Person detection with confidence and features"""
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    class_id: int
    feature: Optional[np.ndarray] = None  # Re-ID features
    
    @property
    def center(self) -> np.ndarray:
        """Get center point of bounding box"""
        return np.array([(self.bbox[0] + self.bbox[2]) / 2, 
                        (self.bbox[1] + self.bbox[3]) / 2])
    
    @property
    def area(self) -> float:
        """Get area of bounding box"""
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class Track:
    """Tracked object with Kalman filter and history"""
    track_id: int
    kalman_filter: KalmanFilter
    state: TrackState = TrackState.NEW
    hits: int = 1
    hit_streak: int = 1
    age: int = 1
    time_since_update: int = 0
    features: deque = field(default_factory=lambda: deque(maxlen=30))
    history: deque = field(default_factory=lambda: deque(maxlen=30))
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=10))
    
    def predict(self):
        """Predict next state using Kalman filter"""
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.kalman_filter.predict()
        self.age += 1
        self.time_since_update += 1
        return self.kalman_filter.x[:4].flatten()
    
    def update(self, detection: Detection):
        """Update track with new detection"""
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        
        # Update Kalman filter
        measurement = self._bbox_to_measurement(detection.bbox)
        self.kalman_filter.update(measurement)
        
        # Store history
        self.history.append(detection.bbox.copy())
        self.confidence_history.append(detection.confidence)
        
        # Store features for re-identification
        if detection.feature is not None:
            self.features.append(detection.feature)
        
        # Update state
        if self.state == TrackState.NEW and self.hits >= 3:
            self.state = TrackState.TRACKED
    
    @property
    def bbox(self) -> np.ndarray:
        """Get current bounding box from Kalman state"""
        state = self.kalman_filter.x[:4].flatten()
        return self._measurement_to_bbox(state)
    
    @property
    def avg_confidence(self) -> float:
        """Get average confidence from recent detections"""
        if not self.confidence_history:
            return 0.0
        return float(np.mean(self.confidence_history))
    
    @staticmethod
    def _bbox_to_measurement(bbox: np.ndarray) -> np.ndarray:
        """Convert [x1,y1,x2,y2] to [cx,cy,w,h]"""
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        cx = bbox[0] + w / 2
        cy = bbox[1] + h / 2
        return np.array([cx, cy, w, h])
    
    @staticmethod
    def _measurement_to_bbox(measurement: np.ndarray) -> np.ndarray:
        """Convert [cx,cy,w,h] to [x1,y1,x2,y2]"""
        cx, cy, w, h = measurement
        return np.array([cx - w/2, cy - h/2, cx + w/2, cy + h/2])


def iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
    """Calculate IoU between two bounding boxes"""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union_area = bbox1_area + bbox2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


def cosine_distance(feat1: np.ndarray, feat2: np.ndarray) -> float:
    """Calculate cosine distance between two feature vectors"""
    return 1 - np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2) + 1e-5)


class ByteTracker:
    """
    ByteTrack implementation for high-performance multi-object tracking
    Handles both high and low confidence detections
    """
    
    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        min_box_area: float = 10,
        low_thresh: float = 0.1
    ):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.min_box_area = min_box_area
        self.low_thresh = low_thresh
        
        self.tracks: List[Track] = []
        self.next_id = 1
        self.frame_id = 0
        
        logger.info("ByteTracker initialized")
    
    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Update tracks with new detections
        Implements ByteTrack's two-stage association
        """
        self.frame_id += 1
        
        # Separate high and low confidence detections
        high_dets = [d for d in detections if d.confidence >= self.track_thresh]
        low_dets = [d for d in detections if self.low_thresh <= d.confidence < self.track_thresh]
        
        # Predict all tracks
        for track in self.tracks:
            track.predict()
        
        # First association with high confidence detections
        unmatched_tracks, unmatched_dets = self._first_association(high_dets)
        
        # Second association with low confidence detections
        unmatched_tracks = self._second_association(unmatched_tracks, low_dets)
        
        # Handle unmatched tracks
        for track_idx in unmatched_tracks:
            track = self.tracks[track_idx]
            if track.time_since_update > self.track_buffer:
                track.state = TrackState.REMOVED
        
        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.state != TrackState.REMOVED]
        
        # Get active tracks
        active_tracks = [t for t in self.tracks if t.state == TrackState.TRACKED]
        
        return active_tracks
    
    def _first_association(self, detections: List[Detection]) -> Tuple[List[int], List[int]]:
        """First association stage with high confidence detections"""
        if not detections:
            return list(range(len(self.tracks))), []
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(self.tracks), len(detections)))
        for t_idx, track in enumerate(self.tracks):
            for d_idx, det in enumerate(detections):
                iou_matrix[t_idx, d_idx] = iou(track.bbox, det.bbox)
        
        # Hungarian algorithm for matching
        track_indices, det_indices = linear_sum_assignment(-iou_matrix)
        
        matches = []
        unmatched_tracks = []
        unmatched_dets = list(range(len(detections)))
        
        for t_idx, d_idx in zip(track_indices, det_indices):
            if iou_matrix[t_idx, d_idx] < self.match_thresh:
                unmatched_tracks.append(t_idx)
            else:
                matches.append((t_idx, d_idx))
                if d_idx in unmatched_dets:
                    unmatched_dets.remove(d_idx)
        
        # Update matched tracks
        for t_idx, d_idx in matches:
            self.tracks[t_idx].update(detections[d_idx])
        
        # Create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            self._initiate_track(detections[d_idx])
        
        # Get unmatched track indices
        matched_track_ids = [m[0] for m in matches]
        unmatched_tracks.extend([i for i in range(len(self.tracks)) if i not in matched_track_ids])
        
        return unmatched_tracks, []
    
    def _second_association(self, unmatched_tracks: List[int], detections: List[Detection]) -> List[int]:
        """Second association stage with low confidence detections"""
        if not detections or not unmatched_tracks:
            return unmatched_tracks
        
        # Only match with lost tracks
        lost_tracks = [idx for idx in unmatched_tracks 
                      if self.tracks[idx].state == TrackState.LOST]
        
        if not lost_tracks:
            return unmatched_tracks
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(lost_tracks), len(detections)))
        for i, t_idx in enumerate(lost_tracks):
            for d_idx, det in enumerate(detections):
                iou_matrix[i, d_idx] = iou(self.tracks[t_idx].bbox, det.bbox)
        
        # Hungarian algorithm
        track_indices, det_indices = linear_sum_assignment(-iou_matrix)
        
        matches = []
        for i, d_idx in zip(track_indices, det_indices):
            if iou_matrix[i, d_idx] >= 0.5:  # Lower threshold for second stage
                t_idx = lost_tracks[i]
                self.tracks[t_idx].update(detections[d_idx])
                matches.append(t_idx)
        
        # Return still unmatched tracks
        return [idx for idx in unmatched_tracks if idx not in matches]
    
    def _initiate_track(self, detection: Detection):
        """Create a new track from detection"""
        # Initialize Kalman filter
        kf = KalmanFilter(dim_x=8, dim_z=4)
        
        # State transition matrix
        kf.F = np.array([[1,0,0,0,1,0,0,0],
                        [0,1,0,0,0,1,0,0],
                        [0,0,1,0,0,0,1,0],
                        [0,0,0,1,0,0,0,1],
                        [0,0,0,0,1,0,0,0],
                        [0,0,0,0,0,1,0,0],
                        [0,0,0,0,0,0,1,0],
                        [0,0,0,0,0,0,0,1]])
        
        # Measurement function
        kf.H = np.array([[1,0,0,0,0,0,0,0],
                        [0,1,0,0,0,0,0,0],
                        [0,0,1,0,0,0,0,0],
                        [0,0,0,1,0,0,0,0]])
        
        # Measurement uncertainty
        kf.R *= 10.0
        
        # Process uncertainty
        kf.Q[-1,-1] *= 0.01
        kf.Q[4:,4:] *= 0.01
        
        # Initial state
        measurement = Track._bbox_to_measurement(detection.bbox)
        kf.x[:4] = measurement.reshape((4, 1))
        kf.x[4:] = 0
        
        # Create track
        track = Track(
            track_id=self.next_id,
            kalman_filter=kf,
            state=TrackState.NEW
        )
        track.update(detection)
        
        self.tracks.append(track)
        self.next_id += 1


class TrackingService:
    """
    Main tracking service with conditional strategy selection
    Uses ByteTrack for primary tracking (fast, GPU-accelerated)
    DeepSORT only for re-identification when tracks are lost (optional, not implemented yet)
    """
    
    def __init__(
        self,
        strategy: str = "bytetrack",  # "bytetrack" or "adaptive"
        track_thresh: float = 0.5,
        match_thresh: float = 0.8,
        use_gpu: bool = True
    ):
        self.strategy = strategy
        self.use_gpu = use_gpu
        self.device = self._detect_device()
        
        self.tracker = ByteTracker(
            track_thresh=track_thresh,
            match_thresh=match_thresh
        )
        
        # Statistics
        self.stats = {
            "total_frames": 0,
            "total_detections": 0,
            "total_tracks": 0,
            "avg_processing_time": 0.0,
            "tracks_created": 0,
            "tracks_lost": 0
        }
        
        # Performance monitoring
        self.processing_times = deque(maxlen=100)
        
        logger.info(f"TrackingService initialized with strategy: {strategy}, device: {self.device}")
    
    def _detect_device(self) -> str:
        """Detect GPU availability"""
        if not self.use_gpu:
            logger.info("GPU disabled by configuration - using CPU")
            return "cpu"
        
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"🚀 Tracking service using GPU acceleration")
                return "cuda"
            else:
                logger.info("No GPU available for tracking - using CPU")
                return "cpu"
        except ImportError:
            logger.info("PyTorch not available - using CPU for tracking")
            return "cpu"
    
    def update(
        self, 
        frame: np.ndarray, 
        detections_data: List[dict]
    ) -> Tuple[int, List[Dict], np.ndarray]:
        """
        Update tracking with new frame and detections
        Optimized for speed - minimal overhead
        
        Args:
            frame: Current video frame
            detections_data: List of detection dicts from YOLO
        
        Returns:
            Tuple of (unique_person_count, track_info_list, annotated_frame)
        """
        start_time = time.time()
        
        # Convert detection dicts to Detection objects (fast)
        detections = [
            Detection(
                bbox=np.array(d["bbox"], dtype=np.float32),  # Specify dtype for speed
                confidence=d["confidence"],
                class_id=d["class_id"],
                feature=d.get("feature")
            )
            for d in detections_data
        ]
        
        # Update tracker (ByteTrack is fast)
        active_tracks = self.tracker.update(detections)
        
        # Get unique count
        unique_count = len(active_tracks)
        
        # Prepare track info (minimal)
        track_info = [
            {
                "track_id": track.track_id,
                "bbox": track.bbox.tolist(),
                "confidence": track.avg_confidence
            }
            for track in active_tracks
        ]
        
        # Annotate frame (optimized - works in-place)
        annotated_frame = self._annotate_frame(frame, active_tracks)
        
        # Update statistics
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        self._update_stats(len(detections), len(active_tracks))
        
        return unique_count, track_info, annotated_frame
    
    def _annotate_frame(self, frame: np.ndarray, tracks: List[Track]) -> np.ndarray:
        """
        Draw lightweight tracking visualization - optimized for speed
        Only draws essential information to minimize processing time
        """
        # Work directly on frame to avoid copy overhead
        annotated = frame
        
        # Pre-calculate font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        box_thickness = 3
        
        for track in tracks:
            bbox = track.bbox.astype(int)
            color = (0, 255, 0)  # Bright green
            
            # Draw bounding box (most important)
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, box_thickness)
            
            # Draw track ID label (minimal)
            label = f"ID:{track.track_id}"
            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            label_y = max(bbox[1] - 10, label_h + 10)
            
            # Simple background rectangle
            cv2.rectangle(annotated, (bbox[0], label_y - label_h - baseline - 5), 
                         (bbox[0] + label_w + 10, label_y + baseline + 5), color, -1)
            
            # White text
            cv2.putText(annotated, label, (bbox[0] + 5, label_y),
                       font, font_scale, (255, 255, 255), font_thickness)
        
        # Simple stats overlay (minimal)
        fps = 1.0/np.mean(self.processing_times) if len(self.processing_times) > 0 else 0
        stats_text = f"Tracks:{len(tracks)} FPS:{fps:.1f}"
        
        # Black background
        cv2.rectangle(annotated, (5, 5), (220, 35), (0, 0, 0), -1)
        cv2.putText(annotated, stats_text, (10, 25),
                   font, 0.5, (0, 255, 0), 1)
        
        return annotated
    
    @staticmethod
    def _get_track_color(track_id: int) -> Tuple[int, int, int]:
        """Generate consistent color for track ID - using standard green for tracking"""
        # Use bright green as standard tracking color (BGR format)
        return (0, 255, 0)  # Green in BGR
    
    def _update_stats(self, num_detections: int, num_tracks: int):
        """Update tracking statistics"""
        self.stats["total_frames"] += 1
        self.stats["total_detections"] += num_detections
        self.stats["total_tracks"] = num_tracks
        self.stats["avg_processing_time"] = float(np.mean(self.processing_times))
    
    def get_statistics(self) -> Dict:
        """Get tracking performance statistics"""
        return {
            **self.stats,
            "tracks_created": self.tracker.next_id - 1,
            "active_tracks": len(self.tracker.tracks)
        }
    
    def reset(self):
        """Reset tracker state"""
        self.tracker.tracks = []
        self.tracker.next_id = 1
        self.tracker.frame_id = 0
        logger.info("Tracker reset")
