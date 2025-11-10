"""
People Detection and Tracking Service using YOLO11 + ByteTrack + DeepSORT
Following clean architecture principles with centralized configuration
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import supervision as sv
from deep_sort_realtime.deepsort_tracker import DeepSort
from logging_config import get_logger
from config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class TrackingService:
    """ByteTrack (30 FPS) + DeepSORT ReID fallback with global cross-camera tracking"""
    
    def __init__(self, conf_threshold: float = None, bytetrack_threshold: float = None):
        logger.info("Initializing tracking service with clean architecture...")
        
        # Use centralized config or fallback to defaults
        self.conf_threshold = conf_threshold or settings.YOLO_CONFIDENCE
        self.bytetrack_threshold = bytetrack_threshold or settings.BYTETRACK_THRESHOLD
        self.device = self._detect_device()
        
        # Tracking state
        self.byte_trackers = {}
        self.deepsort_trackers = {}
        self.camera_tracks = defaultdict(lambda: {
            'count': 0, 'tracks': {}, 'history': deque(maxlen=100),
            'last_update': None, 'bytetrack_confident': 0,
            'deepsort_assisted': 0, 'last_frame': None
        })
        
        # Global ReID for cross-camera tracking (using config values)
        self.global_person_id = 0
        self.global_id_map = {}  # {f"{camera_id}_{local_track_id}": global_id}
        self.global_features = {}  # {global_id: feature_vector}
        self.global_last_seen = {}  # {global_id: timestamp}
        self.global_id_timeout = settings.GLOBAL_ID_TIMEOUT
        
        logger.info(f"✅ Tracking service initialized (conf={self.conf_threshold}, timeout={self.global_id_timeout}s)")
    
    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
                return 'cuda'
        except: pass
        logger.info("Using CPU for tracking")
        return 'cpu'
    
    def _get_bytetrack_tracker(self, camera_id: int) -> sv.ByteTrack:
        if camera_id not in self.byte_trackers:
            self.byte_trackers[camera_id] = sv.ByteTrack(
                track_activation_threshold=0.5,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=30
            )
            logger.info(f"Created ByteTrack tracker for camera {camera_id}")
        return self.byte_trackers[camera_id]
    
    def _get_deepsort_tracker(self, camera_id: int) -> DeepSort:
        if camera_id not in self.deepsort_trackers:
            embedder_gpu = (self.device == 'cuda')
            self.deepsort_trackers[camera_id] = DeepSort(
                max_age=30, n_init=3, nms_max_overlap=0.7,
                max_cosine_distance=0.3, nn_budget=100,
                embedder="mobilenet", embedder_gpu=embedder_gpu,
                embedder_wts=None, polygon=False, today=None
            )
            if embedder_gpu:
                logger.info(f"🎮 DeepSORT using GPU for camera {camera_id}")
            logger.info(f"Created DeepSORT tracker for camera {camera_id}")
        return self.deepsort_trackers[camera_id]
    
    def track_people(self, camera_id: int, frame: np.ndarray, detections_sv, run_deepsort: bool = True) -> Dict:
        """
        Track people using ByteTrack (30 FPS) with optional DeepSORT fallback (2 FPS)
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            detections_sv: Pre-computed YOLO detections (supervision format)
            run_deepsort: Whether to run DeepSORT for uncertain tracks (2 FPS)
            
        Returns:
            Dictionary with tracking information
        """
        if detections_sv is None or len(detections_sv) == 0:
            # No detections, return empty result
            self.camera_tracks[camera_id]['tracks'] = {}
            self.camera_tracks[camera_id]['count'] = 0
            return {
                'camera_id': camera_id,
                'people_count': 0,
                'detections': [],
                'tracks': {},
                'timestamp': datetime.now().isoformat()
            }
        
        logger.debug(f"🔍 Camera {camera_id}: Processing {len(detections_sv)} detections")
        
        # Step 1: Apply ByteTrack tracking (runs at 30 FPS)
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked_detections = byte_tracker.update_with_detections(detections_sv)
        
        logger.debug(f"📍 Camera {camera_id}: ByteTrack returned {len(tracked_detections.tracker_id)} tracked objects")
        
        uncertain_detections = []
        confident_tracks = {}
        
        for i, track_id in enumerate(tracked_detections.tracker_id):
            confidence = tracked_detections.confidence[i]
            bbox = tracked_detections.xyxy[i]
            
            # Extract crop for appearance feature (for all tracks, not just uncertain ones)
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            crop = frame[y1:y2, x1:x2]
            
            # Get DeepSORT embedder to extract feature
            if crop.size > 0:
                try:
                    deepsort_tracker = self._get_deepsort_tracker(camera_id)
                    # Extract appearance feature using DeepSORT's embedder
                    feature = deepsort_tracker.embedder.predict([crop])[0] if hasattr(deepsort_tracker, 'embedder') else None
                except Exception as e:
                    logger.warning(f"Failed to extract feature: {e}")
                    feature = None
            else:
                feature = None
            
            if confidence >= self.bytetrack_threshold:
                confident_tracks[int(track_id)] = {
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                    'source': 'bytetrack',
                    'feature': feature,  # Now ByteTrack also has features!
                    'last_seen': datetime.now()
                }
                self.camera_tracks[camera_id]['bytetrack_confident'] += 1
            else:
                uncertain_detections.append({
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'bytetrack_id': int(track_id),
                    'feature': feature
                })
        
        # Step 2: Apply DeepSORT for uncertain tracks (only at 2 FPS)
        if run_deepsort and len(uncertain_detections) > 0:
            deepsort_tracker = self._get_deepsort_tracker(camera_id)
            deepsort_input = []
            for det in uncertain_detections:
                bbox = det['bbox']
                deepsort_bbox = [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]]
                deepsort_input.append((deepsort_bbox, det['confidence'], 'person'))
            
            deepsort_tracks = deepsort_tracker.update_tracks(deepsort_input, frame=frame)
            
            for track in deepsort_tracks:
                if track.is_confirmed():
                    bbox = track.to_ltrb()
                    try:
                        deepsort_key = -int(track.track_id)
                    except:
                        deepsort_key = f"ds_{track.track_id}"
                    
                    # Extract appearance feature from DeepSORT track
                    feature = None
                    if hasattr(track, 'get_feature') and callable(track.get_feature):
                        feature = track.get_feature()
                    elif hasattr(track, 'features') and len(track.features) > 0:
                        feature = track.features[-1]  # Get latest feature
                    
                    confident_tracks[deepsort_key] = {
                        'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                        'confidence': track.get_det_conf() if hasattr(track, 'get_det_conf') else 0.5,
                        'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                        'source': 'deepsort',
                        'feature': feature,  # Store appearance feature
                        'last_seen': datetime.now()
                    }
                    self.camera_tracks[camera_id]['deepsort_assisted'] += 1
        
        self.camera_tracks[camera_id]['tracks'] = confident_tracks
        self.camera_tracks[camera_id]['count'] = len(confident_tracks)
        self.camera_tracks[camera_id]['last_update'] = datetime.now()
        self.camera_tracks[camera_id]['last_frame'] = frame  # Store frame for visualization
        
        # Assign global IDs to tracks
        self._assign_global_ids(camera_id, confident_tracks)
        
        self.camera_tracks[camera_id]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'count': len(confident_tracks)
        })
        
        return {
            'camera_id': camera_id,
            'people_count': len(confident_tracks),
            'detections': [],  # Detections are passed in, not computed here
            'tracks': confident_tracks,
            'timestamp': datetime.now().isoformat(),
            'bytetrack_confident': self.camera_tracks[camera_id]['bytetrack_confident'],
            'deepsort_assisted': self.camera_tracks[camera_id]['deepsort_assisted']
        }
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """
        Draw bounding boxes and IDs on frame - BRINKSv2 style
        Args: frame first, then camera_id (matches brinksv2)
        """
        annotated = frame.copy()
        tracks = self.camera_tracks[camera_id].get('tracks', {})
        people_count = self.camera_tracks[camera_id].get('count', 0)
        
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            source = track_data.get('source', 'unknown')
            color = (0, 255, 0) if source == 'bytetrack' else (255, 165, 0)
            
            # Draw bounding box
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Use global ID if available, otherwise use local ID
            local_track_key = f"{camera_id}_{track_id}"
            global_id = self.global_id_map.get(local_track_key)
            
            if global_id is not None:
                label = f"ID:{global_id}"
            else:
                try:
                    abs_track_id = abs(int(track_id)) if not isinstance(track_id, str) else track_id.replace("ds_", "")
                except:
                    abs_track_id = "?"
                label = f"ID:{abs_track_id}"
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            (label_width, label_height), _ = cv2.getTextSize(label, font, 0.6, 2)
            label_y = max(bbox[1] - 8, label_height + 13)
            
            # Draw label background
            cv2.rectangle(annotated, (bbox[0], label_y - label_height - 5),
                         (bbox[0] + label_width + 10, label_y + 3), color, -1)
            cv2.putText(annotated, label, (bbox[0] + 5, label_y - 1),
                       font, 0.6, (0, 0, 0), 2)
        
        # Draw count overlay
        cv2.rectangle(annotated, (5, 5), (200, 35), (0, 0, 0), -1)
        cv2.putText(annotated, f"Tracks: {people_count}", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return annotated
    
    def get_statistics(self, camera_id: int) -> Dict:
        if camera_id not in self.camera_tracks:
            return {"total_frames": 0, "active_tracks": 0, "tracks_created": 0, "avg_processing_time": 0.0}
        camera_data = self.camera_tracks[camera_id]
        return {
            "total_frames": len(camera_data['history']),
            "active_tracks": camera_data['count'],
            "tracks_created": camera_data['bytetrack_confident'] + camera_data['deepsort_assisted'],
            "bytetrack_confident": camera_data['bytetrack_confident'],
            "deepsort_assisted": camera_data['deepsort_assisted'],
            "avg_processing_time": 0.03
        }
    
    def get_people_in_room(self, camera_ids: List[int]) -> List[Dict]:
        """
        Get all people currently tracked in the given cameras
        Returns people with global IDs for cross-camera consistency
        Shows ALL detections from ALL cameras (not deduplicated)
        Same person will have same global ID across cameras
        """
        people_list = []
        
        # Collect all tracks with their global IDs from ALL cameras
        for camera_id in camera_ids:
            if camera_id not in self.camera_tracks:
                continue
            
            camera_data = self.camera_tracks[camera_id]
            tracks = camera_data.get('tracks', {})
            
            for track_id, track_info in tracks.items():
                # Get global ID for this track
                local_track_key = f"{camera_id}_{track_id}"
                global_id = self.global_id_map.get(local_track_key, track_id)  # Fallback to local if no global ID
                
                people_list.append({
                    "track_id": str(global_id),  # Use global ID - same person = same ID across cameras
                    "local_track_id": local_track_key,  # Keep local for debugging
                    "camera_id": camera_id,
                    "confidence": track_info.get('confidence', 0.0),
                    "source": track_info.get('source', 'unknown'),
                    "bbox": track_info.get('bbox', [0, 0, 0, 0]),  # [x1, y1, x2, y2]
                    "feature": track_info.get('feature'),  # Appearance embedding for ReID
                    "last_seen": track_info.get('last_seen', datetime.now()).isoformat() if hasattr(track_info.get('last_seen'), 'isoformat') else str(track_info.get('last_seen'))
                })
        
        # Don't deduplicate here - return all detections with global IDs
        # Same person will have same global_id in multiple cameras
        return people_list
    
    def _deduplicate_people(self, people_list: List[Dict], similarity_threshold: float = None, distance_threshold: float = None) -> List[Dict]:
        """
        Remove duplicate people detected by multiple cameras using ReID appearance similarity
        Uses cosine similarity on DeepSORT feature embeddings for robust cross-camera matching
        Falls back to spatial distance for ByteTrack detections without features
        """
        # Use config defaults if not provided
        similarity_threshold = similarity_threshold or settings.DEDUP_SIMILARITY_THRESHOLD
        distance_threshold = distance_threshold or settings.DEDUP_DISTANCE_THRESHOLD
        
        if len(people_list) <= 1:
            return people_list
        
        # Sort by confidence (keep highest confidence detections)
        people_list.sort(key=lambda x: x['confidence'], reverse=True)
        
        deduplicated = []
        used_indices = set()
        match_count = 0
        
        for i, person1 in enumerate(people_list):
            if i in used_indices:
                continue
            
            # Add first occurrence
            deduplicated.append(person1)
            used_indices.add(i)
            
            # Check for duplicates using appearance features or spatial distance
            feature1 = person1.get('feature')
            bbox1 = person1['bbox']
            center1_x = (bbox1[0] + bbox1[2]) / 2
            center1_y = (bbox1[1] + bbox1[3]) / 2
            
            for j in range(i + 1, len(people_list)):
                if j in used_indices:
                    continue
                
                person2 = people_list[j]
                # Skip if same camera (can't be duplicate)
                if person1['camera_id'] == person2['camera_id']:
                    continue
                
                is_duplicate = False
                match_reason = ""
                
                # Try appearance-based matching first (if both have features)
                feature2 = person2.get('feature')
                if feature1 is not None and feature2 is not None:
                    similarity = self._cosine_similarity(feature1, feature2)
                    if similarity > similarity_threshold:
                        is_duplicate = True
                        match_reason = f"ReID sim={similarity:.3f}>{similarity_threshold}"
                
                # Always also check spatial distance as fallback/confirmation
                if not is_duplicate:
                    bbox2 = person2['bbox']
                    center2_x = (bbox2[0] + bbox2[2]) / 2
                    center2_y = (bbox2[1] + bbox2[3]) / 2
                    
                    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
                    if distance < distance_threshold:
                        is_duplicate = True
                        match_reason = f"Distance={distance:.1f}px<{distance_threshold}px"
                
                if is_duplicate:
                    used_indices.add(j)
                    match_count += 1
        
        # Only log summary if there were duplicates
        if match_count > 0:
            logger.info(f"Deduplicated: {len(people_list)} → {len(deduplicated)} people ({match_count} duplicates removed)")
        return deduplicated
    
    def _assign_global_ids(self, camera_id: int, tracks: Dict):
        """
        Assign global IDs to tracks based on cross-camera ReID matching
        Same person gets same global ID across all cameras
        
        Best practices for multi-camera tracking:
        1. Use appearance features (ReID) as primary matching
        2. Lower similarity threshold (0.5) to catch more matches
        3. Consider temporal constraints (people don't teleport)
        4. Update global features with running average
        """
        current_time = datetime.now()
        
        # Clean up expired global IDs (30 seconds timeout)
        expired_ids = []
        for global_id, last_seen in self.global_last_seen.items():
            if (current_time - last_seen).total_seconds() > self.global_id_timeout:
                expired_ids.append(global_id)
        
        for global_id in expired_ids:
            self.global_features.pop(global_id, None)
            self.global_last_seen.pop(global_id, None)
            # Remove from map
            keys_to_remove = [k for k, v in self.global_id_map.items() if v == global_id]
            for k in keys_to_remove:
                self.global_id_map.pop(k, None)
        
        # Process each track
        for track_id, track_data in tracks.items():
            local_track_key = f"{camera_id}_{track_id}"
            feature = track_data.get('feature')
            
            # If already has global ID, update last seen
            if local_track_key in self.global_id_map:
                global_id = self.global_id_map[local_track_key]
                self.global_last_seen[global_id] = current_time
                
                # Update feature with running average if available (use config smoothing)
                if feature is not None and global_id in self.global_features:
                    old_feature = self.global_features[global_id]
                    smoothing = settings.GLOBAL_ID_FEATURE_SMOOTHING
                    self.global_features[global_id] = smoothing * old_feature + (1 - smoothing) * feature
                elif feature is not None:
                    self.global_features[global_id] = feature
                
                continue
            
            # Try to match with existing global IDs from OTHER cameras
            best_match_id = None
            best_similarity = 0.0
            
            if feature is not None and len(self.global_features) > 0:
                for global_id, global_feature in self.global_features.items():
                    # Skip if this global ID is from the same camera (already matched locally)
                    existing_keys = [k for k, v in self.global_id_map.items() if v == global_id]
                    same_camera = any(k.startswith(f"{camera_id}_") for k in existing_keys)
                    
                    if same_camera:
                        continue  # Don't match with IDs from same camera
                    
                    similarity = self._cosine_similarity(feature, global_feature)
                    
                    if similarity > best_similarity and similarity > settings.GLOBAL_ID_SIMILARITY_THRESHOLD:
                        best_similarity = similarity
                        best_match_id = global_id
            
            if best_match_id is not None:
                # Match found - assign existing global ID
                self.global_id_map[local_track_key] = best_match_id
                self.global_last_seen[best_match_id] = current_time
                
                # Update feature with running average (configurable smoothing)
                if feature is not None and best_match_id in self.global_features:
                    old_feature = self.global_features[best_match_id]
                    smoothing = settings.GLOBAL_ID_FEATURE_SMOOTHING
                    self.global_features[best_match_id] = smoothing * old_feature + (1 - smoothing) * feature
                elif feature is not None:
                    self.global_features[best_match_id] = feature
                
                logger.info(f"✅ Matched Cam{camera_id} Track{track_id} → Global ID {best_match_id} (sim={best_similarity:.3f})")
            else:
                # No match - create new global ID
                self.global_person_id += 1
                new_global_id = self.global_person_id
                self.global_id_map[local_track_key] = new_global_id
                self.global_last_seen[new_global_id] = current_time
                if feature is not None:
                    self.global_features[new_global_id] = feature
                logger.info(f"🆕 New Global ID {new_global_id} for Cam{camera_id} Track{track_id}")
    
    def _cosine_similarity(self, feature1, feature2) -> float:
        """Calculate cosine similarity between two feature vectors"""
        try:
            if isinstance(feature1, list):
                feature1 = np.array(feature1)
            if isinstance(feature2, list):
                feature2 = np.array(feature2)
            
            # Flatten if needed
            feature1 = feature1.flatten()
            feature2 = feature2.flatten()
            
            # Calculate cosine similarity
            dot_product = np.dot(feature1, feature2)
            norm1 = np.linalg.norm(feature1)
            norm2 = np.linalg.norm(feature2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.warning(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        if len(bbox1) != 4 or len(bbox2) != 4:
            return 0.0
        
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Calculate intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        
        # Calculate union
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area
        
        if union_area == 0:
            return 0.0
        
        return inter_area / union_area
    
    def reset(self, camera_id: int = None):
        if camera_id:
            for d in [self.byte_trackers, self.deepsort_trackers, self.camera_tracks]:
                d.pop(camera_id, None)
            logger.info(f"Reset tracker for camera {camera_id}")
        else:
            self.byte_trackers = {}
            self.deepsort_trackers = {}
            self.camera_tracks = defaultdict(lambda: {
                'count': 0, 'tracks': {}, 'history': deque(maxlen=100),
                'last_update': None, 'bytetrack_confident': 0,
                'deepsort_assisted': 0, 'last_frame': None
            })
            logger.info("Reset all trackers")
