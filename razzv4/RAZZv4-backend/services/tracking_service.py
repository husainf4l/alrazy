"""
People Detection and Tracking Service using YOLO11 + ByteTrack
Professional implementation with optional DeepSORT ReID for cross-camera matching
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import supervision as sv
from deep_sort_realtime.deepsort_tracker import DeepSort
import logging

logger = logging.getLogger(__name__)


class TrackingService:
    """ByteTrack for tracking + optional DeepSORT ReID for cross-camera deduplication"""
    
    def __init__(self, conf_threshold: float = 0.5):
        logger.info("Initializing tracking service...")
        self.device = self._detect_device()
        self.conf_threshold = conf_threshold
        self.byte_trackers = {}
        self.deepsort_tracker = None  # Created on-demand for ReID
        self.camera_tracks = defaultdict(lambda: {
            'count': 0, 
            'tracks': {},  # {track_id: {bbox, confidence, last_seen, global_id, name}}
            'last_update': None,
            'last_frame': None
        })
        
        # Cross-camera tracking
        self.global_person_ids = {}  # {(camera_id, track_id): global_id}
        self.global_person_names = {}  # {global_id: name}
        self.global_embeddings = {}  # {global_id: embedding}
        self.next_global_id = 1
        self.similarity_threshold = 0.75
        
        # Name pool
        self.name_pool = [
            "Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Harper",
            "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Navy", "Oakley", "Parker",
            "Quinn", "River", "Sage", "Taylor", "Unity", "Vale", "Winter", "Zen"
        ]
        self.used_name_index = 0
        
        logger.info("✅ Tracking service initialized")
    
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
        """Get or create ByteTrack tracker for camera"""
        if camera_id not in self.byte_trackers:
            self.byte_trackers[camera_id] = sv.ByteTrack(
                track_activation_threshold=0.5,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=30
            )
        return self.byte_trackers[camera_id]
    
    def _get_deepsort_tracker(self) -> DeepSort:
        """Get or create shared DeepSORT tracker for ReID"""
        if self.deepsort_tracker is None:
            embedder_gpu = (self.device == 'cuda')
            self.deepsort_tracker = DeepSort(
                max_age=30, n_init=3, nms_max_overlap=0.7,
                max_cosine_distance=0.3, nn_budget=100,
                embedder="mobilenet", embedder_gpu=embedder_gpu,
                embedder_wts=None, polygon=False, today=None
            )
            logger.info(f"Created DeepSORT for ReID (GPU: {embedder_gpu})")
        return self.deepsort_tracker
    
    def track_people(self, camera_id: int, frame: np.ndarray, yolo_service) -> Dict:
        """
        Detect and track people using ByteTrack
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            yolo_service: YOLO service instance
            
        Returns:
            Dictionary with tracking information
        """
        # Detect people with YOLO
        person_count, detections_list, detections_sv = yolo_service.detect_people(frame)
        
        if len(detections_sv) == 0:
            self.camera_tracks[camera_id]['tracks'] = {}
            self.camera_tracks[camera_id]['count'] = 0
            return {'camera_id': camera_id, 'people_count': 0, 'tracks': {}}
        
        # Track with ByteTrack
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked = byte_tracker.update_with_detections(detections_sv)
        
        # Build tracks dictionary
        tracks = {}
        for i, track_id in enumerate(tracked.tracker_id):
            bbox = tracked.xyxy[i]
            confidence = tracked.confidence[i]
            
            tracks[int(track_id)] = {
                'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                'confidence': float(confidence),
                'last_seen': datetime.now()
            }
        
        # Store for cross-camera deduplication
        self.camera_tracks[camera_id]['tracks'] = tracks
        self.camera_tracks[camera_id]['count'] = len(tracks)
        self.camera_tracks[camera_id]['last_update'] = datetime.now()
        self.camera_tracks[camera_id]['last_frame'] = frame
        
        return {
            'camera_id': camera_id,
            'people_count': len(tracks),
            'tracks': tracks
        }
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """Draw bounding boxes with IDs/names on frame"""
        annotated = frame.copy()
        tracks = self.camera_tracks[camera_id].get('tracks', {})
        
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            global_id = track_data.get('global_id')
            person_name = track_data.get('name')
            
            # Determine label
            if person_name:
                label = person_name
                color = (0, 255, 255)  # Yellow
            elif global_id:
                label = f"ID {global_id}"
                color = (0, 255, 255)
            else:
                label = f"Track {track_id}"
                color = (0, 255, 0)  # Green
            
            # Draw box
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label
            cv2.putText(annotated, label, (bbox[0], bbox[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw count
        cv2.putText(annotated, f"People: {len(tracks)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return annotated
    
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def set_person_name(self, global_id: int, name: str) -> bool:
        """Assign a name to a person by global ID"""
        if global_id in self.global_person_names:
            self.global_person_names[global_id] = name
            
            # Update all tracks with this global_id
            for camera_data in self.camera_tracks.values():
                for track_data in camera_data.get('tracks', {}).values():
                    if track_data.get('global_id') == global_id:
                        track_data['name'] = name
            
            return True
        return False
    
    
    def get_all_person_names(self) -> Dict[int, str]:
        """Get all person names"""
        return self.global_person_names.copy()
    
    def generate_embeddings_for_camera(self, camera_id: int):
        """
        Generate ReID embeddings for all current tracks in a camera
        Called periodically (e.g., every 2 seconds) for cross-camera matching
        """
        if camera_id not in self.camera_tracks:
            return
        
        camera_data = self.camera_tracks[camera_id]
        tracks = camera_data.get('tracks', {})
        frame = camera_data.get('last_frame')
        
        if frame is None or len(tracks) == 0:
            return
        
        # Use DeepSORT to generate embeddings
        deepsort = self._get_deepsort_tracker()
        deepsort_input = []
        track_ids = []
        
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            # Convert xyxy to xywh
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            deepsort_input.append(([bbox[0], bbox[1], w, h], track_data['confidence'], 'person'))
            track_ids.append(track_id)
        
        # Generate embeddings
        ds_tracks = deepsort.update_tracks(deepsort_input, frame=frame)
        
        # Store embeddings
        embeddings_stored = 0
        for i, ds_track in enumerate(ds_tracks):
            if ds_track.is_confirmed() and i < len(track_ids):
                if hasattr(ds_track, 'get_feature'):
                    embedding = ds_track.get_feature()
                    if embedding is not None:
                        track_id = track_ids[i]
                        # Store in global embeddings with (camera_id, track_id) key
                        key = (camera_id, track_id)
                        self.global_embeddings[key] = embedding
                        embeddings_stored += 1
        
        if embeddings_stored > 0:
            logger.info(f"Generated {embeddings_stored} embeddings for camera {camera_id}")
    
    def get_unique_people_count_across_cameras(self, camera_ids: List[int]) -> int:
        """
        Deduplicate people across cameras using embeddings
        Simple max count fallback if no embeddings
        """
        # Collect all tracks with embeddings
        all_tracks = []
        
        for camera_id in camera_ids:
            if camera_id not in self.camera_tracks:
                continue
            
            tracks = self.camera_tracks[camera_id].get('tracks', {})
            for track_id, track_data in tracks.items():
                key = (camera_id, track_id)
                if key in self.global_embeddings:
                    all_tracks.append({
                        'camera_id': camera_id,
                        'track_id': track_id,
                        'embedding': self.global_embeddings[key],
                        'bbox': track_data['bbox']
                    })
        
        # No embeddings - fallback to max count
        if len(all_tracks) == 0:
            counts = [self.camera_tracks[cid].get('count', 0) for cid in camera_ids if cid in self.camera_tracks]
            return max(counts) if counts else 0
        
        # Cluster by similarity
        unique_people = []
        
        for track in all_tracks:
            is_duplicate = False
            matched_id = None
            
            for unique in unique_people:
                sim = self._cosine_similarity(track['embedding'], unique['embedding'])
                if sim > self.similarity_threshold:
                    is_duplicate = True
                    matched_id = unique['global_id']
                    break
            
            if not is_duplicate:
                # New person
                global_id = self.next_global_id
                self.next_global_id += 1
                
                if self.used_name_index < len(self.name_pool):
                    name = self.name_pool[self.used_name_index]
                    self.used_name_index += 1
                else:
                    name = f"Person {global_id}"
                
                self.global_person_names[global_id] = name
                track['global_id'] = global_id
                track['name'] = name
                unique_people.append(track)
            else:
                global_id = matched_id
                name = self.global_person_names.get(global_id, f"Person {global_id}")
            
            # Update track with global ID
            self.camera_tracks[track['camera_id']]['tracks'][track['track_id']]['global_id'] = global_id
            self.camera_tracks[track['camera_id']]['tracks'][track['track_id']]['name'] = name
        
        return len(unique_people)
    
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
