"""
Multi-Camera People Tracking and Counting Service

This service implements cross-camera tracking and global people counting using:
1. YOLO11m with BoT-SORT tracker (with ReID enabled)
2. Re-identification embeddings to match people across cameras
3. Global track coordination to prevent double-counting
4. Zone-based camera overlap management

Best Practices:
- Uses BoT-SORT tracker with ReID for robust cross-camera matching
- Maintains global track registry across all cameras
- Implements similarity matching for person re-identification
- Provides accurate total people count without duplicates
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import numpy as np
from ultralytics import YOLO
import cv2

from config.yolo_config import (
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_DEVICE,
    YOLO_HALF_PRECISION,
    YOLO_IMAGE_SIZE,
)


@dataclass
class PersonTrack:
    """Represents a tracked person across cameras."""
    global_id: int
    camera_tracks: Dict[str, int] = field(default_factory=dict)  # camera_name -> local_track_id
    last_seen: float = field(default_factory=time.time)
    reid_embeddings: List[np.ndarray] = field(default_factory=list)
    bounding_boxes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    active_cameras: Set[str] = field(default_factory=set)


@dataclass
class CameraDetection:
    """Detection data from a single camera."""
    camera_name: str
    track_id: int
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    reid_embedding: Optional[np.ndarray] = None
    timestamp: float = field(default_factory=time.time)


class MultiCameraTrackingService:
    """
    Multi-camera tracking service with ReID for accurate global people counting.
    
    This service:
    1. Tracks people within each camera using YOLO track mode with BoT-SORT + ReID
    2. Matches tracks across cameras using ReID embeddings
    3. Maintains global unique person IDs
    4. Provides total people count without double-counting
    
    Usage:
        service = MultiCameraTrackingService()
        for each camera frame:
            detections = service.process_frame(frame, camera_name)
        total_count = service.get_total_people_count()
    """
    
    def __init__(
        self,
        model_path: str = YOLO_MODEL_PATH,
        confidence_threshold: float = YOLO_CONFIDENCE_THRESHOLD,
        device: str = YOLO_DEVICE,
        half_precision: bool = YOLO_HALF_PRECISION,
        imgsz: int = YOLO_IMAGE_SIZE,
        reid_similarity_threshold: float = 0.75,
        track_timeout: float = 3.0,
    ):
        """
        Initialize multi-camera tracking service.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Detection confidence threshold
            device: Device for inference ('0' for GPU, 'cpu' for CPU)
            half_precision: Enable FP16 half-precision inference
            imgsz: Input image size
            reid_similarity_threshold: Threshold for matching tracks across cameras (0-1)
            track_timeout: Seconds before considering a track lost
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.half_precision = half_precision
        self.imgsz = imgsz
        self.reid_similarity_threshold = reid_similarity_threshold
        self.track_timeout = track_timeout
        
        # Thread-local storage for per-thread YOLO models
        self._thread_local = threading.local()
        
        # Global tracking state (thread-safe)
        self._global_tracks: Dict[int, PersonTrack] = {}
        self._next_global_id = 1
        self._tracks_lock = threading.Lock()
        
        # Camera-specific tracking state
        self._camera_local_to_global: Dict[str, Dict[int, int]] = defaultdict(dict)
        
        # Performance monitoring
        self._fps_counters: Dict[str, List[float]] = defaultdict(list)
        
        # Cached statistics (lock-free read for API endpoints)
        self._cached_stats: Dict = {}
        self._stats_cache_time: float = 0
        self._stats_cache_ttl: float = 0.5  # Cache stats for 500ms to prevent lock contention
        
        # Camera zone overlaps (configure based on camera positions)
        self._camera_overlaps = self._initialize_camera_overlaps()
        
    def _initialize_camera_overlaps(self) -> Dict[str, List[str]]:
        """
        Define which cameras have overlapping fields of view.
        Loads configuration from camera_zones.json.
        
        Returns:
            Dict mapping camera name to list of overlapping camera names
        """
        import json
        import os
        
        # Try to load from config file
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            "camera_zones.json"
        )
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Remove comment keys
                    return {k: v for k, v in config.items() if not k.startswith('_')}
            except Exception as e:
                print(f"Warning: Could not load camera zones config: {e}")
        
        # Default configuration (customize for your setup)
        print("Using default camera overlap configuration")
        return {
            "camera2_back_yard": ["camera3_back_yard_2"],
            "camera3_back_yard_2": ["camera2_back_yard"],
            "camera4_front": ["camera5_front_yard"],
            "camera5_front_yard": ["camera4_front"],
            "camera6_entrance": [],  # No overlaps
        }
    
    def _get_model(self) -> YOLO:
        """Get thread-local YOLO model instance with tracking enabled."""
        if not hasattr(self._thread_local, "model"):
            # Initialize YOLO model with tracking
            model = YOLO(self.model_path)
            self._thread_local.model = model
        
        return self._thread_local.model
    
    def process_frame(
        self,
        frame: np.ndarray,
        camera_name: str,
    ) -> Tuple[np.ndarray, List[CameraDetection], int]:
        """
        Process a single camera frame with tracking and ReID.
        
        Args:
            frame: Input image frame (BGR)
            camera_name: Unique camera identifier
            
        Returns:
            Tuple of (annotated_frame, detections, global_people_count)
        """
        start_time = time.time()
        
        # Get thread-local model
        model = self._get_model()
        
        # Run YOLO tracking with ReID enabled (GPU-optimized)
        # persist=True maintains tracks across frames
        # tracker="botsort.yaml" uses BoT-SORT with ReID
        results = model.track(
            frame,
            persist=True,
            tracker="botsort.yaml",
            conf=self.confidence_threshold,
            classes=[0],  # Person class only
            device=self.device,
            half=self.half_precision,
            imgsz=self.imgsz,
            verbose=False,
            stream=False,  # Disable stream mode for lower latency
            agnostic_nms=True,  # Faster NMS
            max_det=50,  # Limit detections for speed
        )
        
        result = results[0]
        detections = []
        
        # Extract detections with track IDs and ReID embeddings
        if result.boxes is not None and len(result.boxes) > 0:
            # Check if tracking is active
            if hasattr(result.boxes, 'id') and result.boxes.id is not None:
                boxes = result.boxes.xywh.cpu().numpy()
                track_ids = result.boxes.id.int().cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                
                # Get ReID embeddings if available
                reid_embeddings = None
                if hasattr(result, 'features') and result.features is not None:
                    reid_embeddings = result.features.cpu().numpy()
                
                for idx, (box, track_id, conf) in enumerate(zip(boxes, track_ids, confidences)):
                    x, y, w, h = box
                    bbox = (int(x), int(y), int(w), int(h))
                    
                    # Get ReID embedding for this detection
                    reid_emb = reid_embeddings[idx] if reid_embeddings is not None else None
                    
                    detection = CameraDetection(
                        camera_name=camera_name,
                        track_id=int(track_id),
                        bbox=bbox,
                        confidence=float(conf),
                        reid_embedding=reid_emb,
                    )
                    detections.append(detection)
        
        # Update global tracking state
        self._update_global_tracks(camera_name, detections)
        
        # Annotate frame with global IDs
        annotated_frame = self._annotate_frame(frame, camera_name, detections)
        
        # Update FPS counter
        elapsed = time.time() - start_time
        self._fps_counters[camera_name].append(elapsed)
        if len(self._fps_counters[camera_name]) > 30:
            self._fps_counters[camera_name].pop(0)
        
        # Get current global count
        global_count = self.get_total_people_count()
        
        return annotated_frame, detections, global_count
    
    def _update_global_tracks(
        self,
        camera_name: str,
        detections: List[CameraDetection]
    ):
        """
        Update global track registry with new detections.
        Matches tracks across cameras using ReID embeddings.
        """
        with self._tracks_lock:
            current_time = time.time()
            
            # Clean up old tracks
            self._cleanup_old_tracks(current_time)
            
            # Process each detection
            for detection in detections:
                local_track_id = detection.track_id
                
                # Check if we already have a global ID for this local track
                if local_track_id in self._camera_local_to_global[camera_name]:
                    global_id = self._camera_local_to_global[camera_name][local_track_id]
                    
                    # Update existing global track
                    if global_id in self._global_tracks:
                        track = self._global_tracks[global_id]
                        track.last_seen = current_time
                        track.active_cameras.add(camera_name)
                        track.bounding_boxes.append(detection.bbox)
                        if detection.reid_embedding is not None:
                            track.reid_embeddings.append(detection.reid_embedding)
                        # Keep only recent embeddings (last 10)
                        if len(track.reid_embeddings) > 10:
                            track.reid_embeddings = track.reid_embeddings[-10:]
                else:
                    # New local track - try to match with existing global tracks
                    matched_global_id = self._find_matching_global_track(
                        detection,
                        camera_name
                    )
                    
                    if matched_global_id is not None:
                        # Match found - assign to existing global track
                        self._camera_local_to_global[camera_name][local_track_id] = matched_global_id
                        track = self._global_tracks[matched_global_id]
                        track.camera_tracks[camera_name] = local_track_id
                        track.last_seen = current_time
                        track.active_cameras.add(camera_name)
                        if detection.reid_embedding is not None:
                            track.reid_embeddings.append(detection.reid_embedding)
                    else:
                        # No match - create new global track
                        global_id = self._next_global_id
                        self._next_global_id += 1
                        
                        new_track = PersonTrack(
                            global_id=global_id,
                            camera_tracks={camera_name: local_track_id},
                            last_seen=current_time,
                            reid_embeddings=[detection.reid_embedding] if detection.reid_embedding is not None else [],
                            bounding_boxes=[detection.bbox],
                            active_cameras={camera_name},
                        )
                        
                        self._global_tracks[global_id] = new_track
                        self._camera_local_to_global[camera_name][local_track_id] = global_id
    
    def _find_matching_global_track(
        self,
        detection: CameraDetection,
        camera_name: str
    ) -> Optional[int]:
        """
        Find matching global track for a new local track using ReID embeddings.
        Only matches with tracks from overlapping cameras.
        
        Args:
            detection: New detection to match
            camera_name: Source camera name
            
        Returns:
            Global track ID if match found, None otherwise
        """
        if detection.reid_embedding is None:
            return None
        
        # Get overlapping cameras
        overlapping_cameras = self._camera_overlaps.get(camera_name, [])
        if not overlapping_cameras:
            return None
        
        best_match_id = None
        best_similarity = self.reid_similarity_threshold
        
        # Check each global track
        for global_id, track in self._global_tracks.items():
            # Only consider tracks from overlapping cameras
            track_cameras = track.active_cameras.intersection(overlapping_cameras)
            if not track_cameras:
                continue
            
            # Skip if track already has this camera
            if camera_name in track.active_cameras:
                continue
            
            # Skip if track is too old
            if time.time() - track.last_seen > self.track_timeout:
                continue
            
            # Compare ReID embeddings
            if track.reid_embeddings:
                similarity = self._compute_embedding_similarity(
                    detection.reid_embedding,
                    track.reid_embeddings
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_id = global_id
        
        return best_match_id
    
    def _compute_embedding_similarity(
        self,
        embedding1: np.ndarray,
        embeddings2: List[np.ndarray]
    ) -> float:
        """
        Compute cosine similarity between embedding and list of embeddings.
        Returns the maximum similarity.
        """
        if not embeddings2:
            return 0.0
        
        # Normalize embeddings
        emb1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        
        max_similarity = 0.0
        for emb2 in embeddings2:
            emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)
            similarity = np.dot(emb1_norm, emb2_norm)
            max_similarity = max(max_similarity, similarity)
        
        return float(max_similarity)
    
    def _cleanup_old_tracks(self, current_time: float):
        """Remove tracks that haven't been seen recently."""
        to_remove = []
        
        for global_id, track in self._global_tracks.items():
            if current_time - track.last_seen > self.track_timeout:
                to_remove.append(global_id)
        
        for global_id in to_remove:
            # Remove from global tracks
            track = self._global_tracks.pop(global_id)
            
            # Remove from camera mappings
            for camera_name, local_id in track.camera_tracks.items():
                if camera_name in self._camera_local_to_global:
                    self._camera_local_to_global[camera_name].pop(local_id, None)
    
    def _annotate_frame(
        self,
        frame: np.ndarray,
        camera_name: str,
        detections: List[CameraDetection]
    ) -> np.ndarray:
        """
        Annotate frame with global IDs and bounding boxes.
        """
        annotated = frame.copy()
        
        for detection in detections:
            # Get global ID
            local_id = detection.track_id
            global_id = self._camera_local_to_global[camera_name].get(local_id, -1)
            
            # Draw bounding box
            x, y, w, h = detection.bbox
            x1, y1 = int(x - w/2), int(y - h/2)
            x2, y2 = int(x + w/2), int(y + h/2)
            
            # Color based on global ID (consistent across cameras)
            color = self._get_color_for_id(global_id)
            
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label with global ID
            label = f"Person {global_id} ({detection.confidence:.2f})"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        # Draw total count
        total_count = len(self._global_tracks)
        count_text = f"Total People: {total_count}"
        cv2.putText(
            annotated,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )
        
        return annotated
    
    def _get_color_for_id(self, global_id: int) -> Tuple[int, int, int]:
        """Generate consistent color for each global ID."""
        if global_id < 0:
            return (128, 128, 128)  # Gray for unmatched
        
        # Use golden ratio for good color distribution
        golden_ratio = 0.618033988749895
        hue = (global_id * golden_ratio) % 1.0
        
        # Convert HSV to BGR
        import colorsys
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
        bgr = (int(rgb[2] * 255), int(rgb[1] * 255), int(rgb[0] * 255))
        return bgr
    
    def get_total_people_count(self) -> int:
        """
        Get total number of unique people currently tracked across all cameras.
        
        Returns:
            Number of unique people
        """
        with self._tracks_lock:
            current_time = time.time()
            # Count only active tracks (seen recently)
            active_count = sum(
                1 for track in self._global_tracks.values()
                if current_time - track.last_seen < self.track_timeout
            )
            return active_count
    
    def get_people_per_camera(self) -> Dict[str, int]:
        """
        Get people count per camera (may include duplicates if person is in multiple views).
        Uses lock with timeout to prevent blocking.
        
        Returns:
            Dict mapping camera name to people count
        """
        # Try to acquire lock with timeout
        lock_acquired = self._tracks_lock.acquire(timeout=0.05)
        if not lock_acquired:
            # Return empty dict if lock is busy
            return {}
        
        try:
            camera_counts = defaultdict(int)
            current_time = time.time()
            
            for track in self._global_tracks.values():
                if current_time - track.last_seen < self.track_timeout:
                    for camera_name in track.active_cameras:
                        camera_counts[camera_name] += 1
            
            return dict(camera_counts)
        finally:
            self._tracks_lock.release()
    
    def get_total_people_count_fast(self) -> int:
        """
        Get total people count quickly without blocking (cached).
        This is optimized for API endpoints to prevent overload.
        
        Returns:
            Total unique people count
        """
        # Use cached value if available and recent
        current_time = time.time()
        if current_time - self._stats_cache_time < self._stats_cache_ttl:
            if self._cached_stats:
                return self._cached_stats.get("total_unique_people", 0)
        
        # If cache is stale, use get_statistics which handles lock timeout
        stats = self.get_statistics()
        return stats.get("total_unique_people", 0)
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive tracking statistics (cached for performance).
        Uses cached data to prevent lock contention with camera threads.
        
        Returns:
            Dictionary with tracking statistics
        """
        current_time = time.time()
        
        # Return cached stats if still valid (prevents lock contention)
        if current_time - self._stats_cache_time < self._stats_cache_ttl:
            if self._cached_stats:
                return self._cached_stats.copy()
        
        # Try to acquire lock with timeout to prevent blocking
        lock_acquired = self._tracks_lock.acquire(timeout=0.1)
        if not lock_acquired:
            # Return last cached stats if lock is busy
            if self._cached_stats:
                return self._cached_stats.copy()
            # Return empty stats if no cache available
            return {
                "total_unique_people": 0,
                "people_per_camera": {},
                "total_tracks_created": 0,
                "active_tracks": 0,
                "camera_fps": {},
                "reid_enabled": True,
                "tracker": "BoT-SORT with ReID",
            }
        
        try:
            active_tracks = [
                track for track in self._global_tracks.values()
                if current_time - track.last_seen < self.track_timeout
            ]
            
            camera_fps = {}
            for camera_name, times in self._fps_counters.items():
                if times:
                    avg_time = sum(times) / len(times)
                    camera_fps[camera_name] = 1.0 / avg_time if avg_time > 0 else 0.0
            
            stats = {
                "total_unique_people": len(active_tracks),
                "people_per_camera": self.get_people_per_camera(),
                "total_tracks_created": self._next_global_id - 1,
                "active_tracks": len(active_tracks),
                "camera_fps": camera_fps,
                "reid_enabled": True,
                "tracker": "BoT-SORT with ReID",
            }
            
            # Update cache
            self._cached_stats = stats.copy()
            self._stats_cache_time = current_time
            
            return stats
        finally:
            self._tracks_lock.release()
    
    def reset(self):
        """Reset all tracking state."""
        with self._tracks_lock:
            self._global_tracks.clear()
            self._camera_local_to_global.clear()
            self._next_global_id = 1
            self._fps_counters.clear()


# Global service instance
_global_tracking_service: Optional[MultiCameraTrackingService] = None
_service_lock = threading.Lock()


def get_multi_camera_tracking_service() -> MultiCameraTrackingService:
    """
    Get or create the global multi-camera tracking service instance.
    Thread-safe singleton pattern.
    
    Returns:
        MultiCameraTrackingService instance
    """
    global _global_tracking_service
    
    if _global_tracking_service is None:
        with _service_lock:
            if _global_tracking_service is None:
                _global_tracking_service = MultiCameraTrackingService()
    
    return _global_tracking_service
