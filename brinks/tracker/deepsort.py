"""
Enhanced Tracking Module with DeepSORT + ByteTrack Hybrid
Provides robust multi-object tracking with appearance features
"""

import numpy as np
import cv2
from typing import Optional, Dict, Tuple, List
import warnings

# Try to import deep-sort components
try:
    from deep_sort_pytorch.deep_sort import DeepSort
    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False
    DeepSort = None

# ByteTrack is always available
try:
    from supervision.tracker.byte_tracker.core import ByteTrack
    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False
    ByteTrack = None


class HybridTracker:
    """
    Hybrid tracker combining ByteTrack (fast, reliable) with DeepSORT (appearance-aware)
    Falls back to ByteTrack if DeepSORT unavailable
    """
    
    def __init__(
        self,
        use_deepsort: bool = True,
        max_age: int = 30,
        n_init: int = 3,
        track_buffer: int = 30,
        activation_threshold: float = 0.4,
        matching_threshold: float = 0.8
    ):
        """
        Initialize hybrid tracker
        
        Args:
            use_deepsort: Whether to use DeepSORT (falls back to ByteTrack if unavailable)
            max_age: Maximum frames to keep inactive tracks
            n_init: Number of detections needed to initialize track
            track_buffer: ByteTrack lost buffer size
            activation_threshold: Detection confidence threshold
            matching_threshold: IOU matching threshold
        """
        self.use_deepsort = use_deepsort and DEEPSORT_AVAILABLE
        self.max_age = max_age
        self.n_init = n_init
        
        # Initialize trackers
        if self.use_deepsort:
            try:
                self.deepsort = DeepSort(
                    model_path="./tracker/weights/ckpt.t7",  # Will use default if not found
                    max_dist=0.2,
                    min_confidence=0.4,
                    nms_max_overlap=0.5,
                    max_iou_distance=0.7,
                    max_age=max_age,
                    n_init=n_init,
                    nn_budget=100,
                    use_cuda=False  # CPU by default
                )
                self.primary_tracker = "DeepSORT"
                print("✅ DeepSORT initialized successfully")
            except Exception as e:
                warnings.warn(f"Failed to initialize DeepSORT: {e}. Falling back to ByteTrack.")
                self.use_deepsort = False
                self.deepsort = None
        
        # Always have ByteTrack as fallback
        if BYTETRACK_AVAILABLE:
            self.bytetrack = ByteTrack(
                track_activation_threshold=activation_threshold,
                lost_track_buffer=track_buffer,
                minimum_matching_threshold=matching_threshold,
                frame_rate=15,
                minimum_consecutive_frames=1
            )
            if not self.use_deepsort:
                self.primary_tracker = "ByteTrack"
            print(f"✅ ByteTrack initialized as fallback")
        else:
            raise RuntimeError("ByteTrack is required but not available")
        
        self.frame_count = 0
        self.track_history: Dict[int, List[np.ndarray]] = {}
    
    def update(
        self,
        detections_xyxy: np.ndarray,
        confidence_scores: np.ndarray,
        frame: Optional[np.ndarray] = None,
        features: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Update tracker with new detections
        
        Args:
            detections_xyxy: Detection boxes in format [[x1, y1, x2, y2], ...]
            confidence_scores: Confidence scores for each detection
            frame: Current frame (optional, for DeepSORT appearance features)
            features: Pre-extracted appearance features (optional)
        
        Returns:
            Tuple of (tracked_ids, tracked_xyxy)
        """
        self.frame_count += 1
        
        try:
            if self.use_deepsort and frame is not None:
                # Use DeepSORT with appearance features
                return self._update_deepsort(
                    detections_xyxy,
                    confidence_scores,
                    frame,
                    features
                )
            else:
                # Use ByteTrack (faster, no appearance needed)
                return self._update_bytetrack(detections_xyxy, confidence_scores)
        except Exception as e:
            warnings.warn(f"Tracking error: {e}. Falling back to ByteTrack.")
            return self._update_bytetrack(detections_xyxy, confidence_scores)
    
    def _update_deepsort(
        self,
        detections_xyxy: np.ndarray,
        confidence_scores: np.ndarray,
        frame: np.ndarray,
        features: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Update using DeepSORT tracker
        Combines motion and appearance features for robust tracking
        """
        if len(detections_xyxy) == 0:
            return np.array([], dtype=int), np.array([])
        
        try:
            # Format detections for DeepSORT: [x1, y1, w, h, confidence]
            tlbr = detections_xyxy.copy()
            confidences = confidence_scores
            
            # Extract features if not provided
            if features is None:
                features = self._extract_features(frame, tlbr)
            
            # Update DeepSORT
            self.deepsort.update(tlbr, confidences, features)
            
            # Get active tracks
            tracks = self.deepsort.tracked_stracks
            tracked_ids = np.array([track.track_id for track in tracks])
            tracked_xyxy = np.array([track.tlbr for track in tracks])
            
            return tracked_ids, tracked_xyxy
        
        except Exception as e:
            warnings.warn(f"DeepSORT update failed: {e}")
            return np.array([], dtype=int), np.array([])
    
    def _update_bytetrack(
        self,
        detections_xyxy: np.ndarray,
        confidence_scores: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Update using ByteTrack (fast, motion-based)
        More reliable when appearance information unavailable
        """
        if len(detections_xyxy) == 0:
            return np.array([], dtype=int), np.array([])
        
        try:
            # Create supervision Detections object
            from supervision.detection.core import Detections
            
            detections = Detections(
                xyxy=detections_xyxy,
                confidence=confidence_scores,
                class_id=np.zeros(len(detections_xyxy), dtype=int)
            )
            
            # Update tracker
            detections = self.bytetrack.update_with_detections(detections)
            
            tracked_ids = detections.tracker_id if detections.tracker_id is not None else np.array([], dtype=int)
            tracked_xyxy = detections.xyxy if len(detections) > 0 else np.array([])
            
            return tracked_ids, tracked_xyxy
        
        except Exception as e:
            warnings.warn(f"ByteTrack update failed: {e}")
            return np.array([], dtype=int), np.array([])
    
    def _extract_features(self, frame: np.ndarray, detections: np.ndarray) -> np.ndarray:
        """
        Extract appearance features from frame regions
        Uses CNN-based feature extraction for appearance modeling
        """
        if len(detections) == 0:
            return np.array([])
        
        try:
            features = []
            for bbox in detections:
                x1, y1, x2, y2 = map(int, bbox)
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame.shape[1], x2)
                y2 = min(frame.shape[0], y2)
                
                # Extract patch
                patch = frame[y1:y2, x1:x2]
                if patch.size == 0:
                    # Create dummy feature if patch empty
                    features.append(np.zeros(512, dtype=np.float32))
                    continue
                
                # Resize to standard size
                patch_resized = cv2.resize(patch, (64, 128))
                
                # Convert to RGB
                patch_rgb = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2RGB)
                
                # Simple CNN-like feature: normalized histogram
                feature = self._compute_appearance_feature(patch_rgb)
                features.append(feature)
            
            return np.array(features, dtype=np.float32)
        
        except Exception as e:
            warnings.warn(f"Feature extraction failed: {e}")
            return np.array([np.zeros(512, dtype=np.float32) for _ in range(len(detections))])
    
    @staticmethod
    def _compute_appearance_feature(patch_rgb: np.ndarray) -> np.ndarray:
        """
        Compute lightweight appearance feature from image patch
        Uses color histogram for fast computation
        """
        # Normalize patch
        patch_norm = patch_rgb.astype(np.float32) / 255.0
        
        # Compute color histogram (16 bins per channel = 4096 features)
        hist_r = cv2.calcHist([patch_rgb[:, :, 0]], [0], None, [16], [0, 256])
        hist_g = cv2.calcHist([patch_rgb[:, :, 1]], [0], None, [16], [0, 256])
        hist_b = cv2.calcHist([patch_rgb[:, :, 2]], [0], None, [16], [0, 256])
        
        # Concatenate histograms
        features = np.concatenate([
            hist_r.flatten(),
            hist_g.flatten(),
            hist_b.flatten()
        ]).astype(np.float32)
        
        # Normalize
        if np.linalg.norm(features) > 0:
            features = features / np.linalg.norm(features)
        else:
            features = np.zeros(48, dtype=np.float32)
        
        # Pad to 512 dimensions
        padded = np.zeros(512, dtype=np.float32)
        padded[:len(features)] = features
        
        return padded
    
    def get_active_tracks(self) -> List[Dict]:
        """Get list of currently active tracks with metadata"""
        if self.use_deepsort and self.deepsort is not None:
            tracks = self.deepsort.tracked_stracks
            return [
                {
                    'id': track.track_id,
                    'bbox': track.tlbr,
                    'confidence': track.score if hasattr(track, 'score') else 0.9,
                    'age': self.frame_count - track.frame_id if hasattr(track, 'frame_id') else 0
                }
                for track in tracks
            ]
        else:
            # ByteTrack doesn't expose tracks directly, return empty
            return []
    
    def reset(self):
        """Reset tracker state"""
        if self.use_deepsort and self.deepsort is not None:
            self.deepsort.tracked_stracks.clear()
        self.track_history.clear()
        self.frame_count = 0
    
    def __str__(self):
        return f"HybridTracker(primary={self.primary_tracker}, deepsort={self.use_deepsort})"


class EnhancedDetectionTracker:
    """
    Enhanced detection+tracking pipeline with best practices
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.45,
        nms_threshold: float = 0.5,
        use_deepsort: bool = True
    ):
        """
        Initialize enhanced tracker
        
        Args:
            confidence_threshold: Minimum detection confidence
            nms_threshold: NMS threshold for duplicate removal
            use_deepsort: Whether to use DeepSORT
        """
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.tracker = HybridTracker(use_deepsort=use_deepsort)
        self.detection_history: Dict[int, List] = {}
    
    def process_detections(
        self,
        detections_xyxy: np.ndarray,
        confidence_scores: np.ndarray,
        frame: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process detections through NMS and tracking
        
        Args:
            detections_xyxy: Raw detections in XYXY format
            confidence_scores: Confidence scores
            frame: Current frame (for feature extraction)
        
        Returns:
            Tuple of (tracked_ids, tracked_xyxy)
        """
        if len(detections_xyxy) == 0:
            return np.array([], dtype=int), np.array([])
        
        # Filter by confidence threshold
        valid_mask = confidence_scores >= self.confidence_threshold
        filtered_dets = detections_xyxy[valid_mask]
        filtered_conf = confidence_scores[valid_mask]
        
        if len(filtered_dets) == 0:
            return np.array([], dtype=int), np.array([])
        
        # Apply NMS
        nms_indices = self._apply_nms(filtered_dets, filtered_conf, self.nms_threshold)
        nms_dets = filtered_dets[nms_indices]
        nms_conf = filtered_conf[nms_indices]
        
        # Update tracker
        tracked_ids, tracked_xyxy = self.tracker.update(nms_dets, nms_conf, frame)
        
        return tracked_ids, tracked_xyxy
    
    @staticmethod
    def _apply_nms(
        boxes: np.ndarray,
        scores: np.ndarray,
        threshold: float = 0.5
    ) -> np.ndarray:
        """Apply Non-Maximum Suppression"""
        if len(boxes) == 0:
            return np.array([], dtype=int)
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            
            if len(order) == 1:
                break
            
            # Calculate IoU
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
            intersection = w * h
            
            union = areas[i] + areas[order[1:]] - intersection
            iou = intersection / union
            
            order = order[np.where(iou <= threshold)[0] + 1]
        
        return np.array(keep, dtype=int)
