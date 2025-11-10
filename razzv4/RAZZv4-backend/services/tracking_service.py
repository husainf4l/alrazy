"""
People Detection and Tracking Service using YOLO11 + ByteTrack
Following clean architecture principles with centralized configuration
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import supervision as sv
from logging_config import get_logger
from config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class TrackingService:
    """ByteTrack (30 FPS) with spatial-based global cross-camera tracking"""
    
    def __init__(self, conf_threshold: float = None, bytetrack_threshold: float = None):
        logger.info("Initializing tracking service with clean architecture...")
        
        # Use centralized config or fallback to defaults
        self.conf_threshold = conf_threshold or settings.YOLO_CONFIDENCE
        self.bytetrack_threshold = bytetrack_threshold or settings.BYTETRACK_THRESHOLD
        self.device = self._detect_device()
        
        # Tracking state
        self.byte_trackers = {}
        self.camera_tracks = defaultdict(lambda: {
            'count': 0, 'tracks': {}, 'history': deque(maxlen=100),
            'last_update': None, 'last_frame': None, 'frame_count': 0
        })
        
        # Global tracking for cross-camera (spatial-based)
        self.global_person_id = 0
        self.global_id_map = {}  # {f"{camera_id}_{local_track_id}": global_id}
        self.global_positions = {}  # {global_id: (x, y, width, height)}
        self.global_last_seen = {}  # {global_id: timestamp}
        self.person_names = {}  # {global_id: name}
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
    
    def track_people(self, camera_id: int, frame: np.ndarray, detections_sv) -> Dict:
        """
        Track people using ByteTrack (30 FPS) with spatial-based global ID matching
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            detections_sv: Pre-computed YOLO detections (supervision format)
            
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
        
        # Increment frame count for this camera
        self.camera_tracks[camera_id]['frame_count'] += 1
        
        # Apply ByteTrack tracking (runs at 30 FPS)
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked_detections = byte_tracker.update_with_detections(detections_sv)
        
        logger.debug(f"📍 Camera {camera_id}: ByteTrack returned {len(tracked_detections.tracker_id)} tracked objects")
        
        confident_tracks = {}
        
        for i, track_id in enumerate(tracked_detections.tracker_id):
            confidence = tracked_detections.confidence[i]
            bbox = tracked_detections.xyxy[i]
            
            confident_tracks[int(track_id)] = {
                'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                'confidence': float(confidence),
                'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                'source': 'bytetrack',
                'last_seen': datetime.now()
            }
        
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
            'timestamp': datetime.now().isoformat()
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
                # Check if this person has a name
                person_name = self.get_person_name(global_id)
                if person_name:
                    label = f"{person_name} (ID:{global_id})"
                else:
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
                
                # Get person name if set
                person_name = self.get_person_name(global_id) if isinstance(global_id, int) else None
                
                people_list.append({
                    "track_id": str(global_id),  # Use global ID - same person = same ID across cameras
                    "local_track_id": local_track_key,  # Keep local for debugging
                    "camera_id": camera_id,
                    "confidence": track_info.get('confidence', 0.0),
                    "source": track_info.get('source', 'unknown'),
                    "bbox": track_info.get('bbox', [0, 0, 0, 0]),  # [x1, y1, x2, y2]
                    "name": person_name,  # Include person name if set
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
        Assign global IDs to tracks using spatial matching across cameras
        Since cameras view the same space, we use position and size to match people
        """
        current_time = datetime.now()
        
        # Clean up expired global IDs
        expired_ids = []
        for global_id, last_seen in self.global_last_seen.items():
            if (current_time - last_seen).total_seconds() > self.global_id_timeout:
                expired_ids.append(global_id)
        
        for global_id in expired_ids:
            self.global_positions.pop(global_id, None)
            self.global_last_seen.pop(global_id, None)
            keys_to_remove = [k for k, v in self.global_id_map.items() if v == global_id]
            for k in keys_to_remove:
                self.global_id_map.pop(k, None)
        
        # Process each track
        for track_id, track_data in tracks.items():
            local_track_key = f"{camera_id}_{track_id}"
            bbox = track_data.get('bbox')
            
            # If already has global ID, just update
            if local_track_key in self.global_id_map:
                global_id = self.global_id_map[local_track_key]
                self.global_last_seen[global_id] = current_time
                self.global_positions[global_id] = bbox
                continue
            
            # Try to match with existing global IDs from OTHER cameras using spatial overlap
            best_match_id = None
            best_iou = 0.0
            
            if len(self.global_positions) > 0:
                for global_id, global_bbox in self.global_positions.items():
                    # Skip if this global ID is from the same camera
                    existing_keys = [k for k, v in self.global_id_map.items() if v == global_id]
                    same_camera = any(k.startswith(f"{camera_id}_") for k in existing_keys)
                    
                    if same_camera:
                        continue
                    
                    # Calculate IoU (Intersection over Union)
                    iou = self._calculate_iou(bbox, global_bbox)
                    
                    # Use IoU threshold of 0.3 for spatial matching
                    if iou > best_iou and iou > 0.3:
                        best_iou = iou
                        best_match_id = global_id
            
            if best_match_id is not None:
                # Match found - assign existing global ID
                self.global_id_map[local_track_key] = best_match_id
                self.global_last_seen[best_match_id] = current_time
                self.global_positions[best_match_id] = bbox
                logger.info(f"✅ Matched Cam{camera_id} Track{track_id} → Global ID {best_match_id} (IoU={best_iou:.3f})")
            else:
                # No match - create new global ID
                self.global_person_id += 1
                new_global_id = self.global_person_id
                self.global_id_map[local_track_key] = new_global_id
                self.global_last_seen[new_global_id] = current_time
                self.global_positions[new_global_id] = bbox
                logger.info(f"🆕 New Global ID {new_global_id} for Cam{camera_id} Track{track_id}")
    
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
    
    def set_person_name(self, global_id: int, name: str) -> bool:
        """Set a name for a person by their global ID"""
        try:
            self.person_names[global_id] = name
            logger.info(f"Set name for person {global_id}: '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to set name for person {global_id}: {e}")
            return False
    
    def get_person_name(self, global_id: int) -> Optional[str]:
        """Get the name of a person by their global ID"""
        return self.person_names.get(global_id)

