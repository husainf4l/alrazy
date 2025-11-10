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
        
        # Cross-camera tracking - GLOBAL PERSON DATABASE
        # Key insight: Global IDs persist forever, embeddings stored per global_id
        self.global_persons = {}  # {global_id: {'embedding': np.ndarray, 'name': str, 'track_mappings': [(cam, track_id)]}}
        self.camera_track_to_global = {}  # {(camera_id, track_id): global_id} - quick lookup
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
        if global_id in self.global_persons:
            self.global_persons[global_id]['name'] = name
            
            # Update all active tracks with this global_id
            for camera_data in self.camera_tracks.values():
                for track_data in camera_data.get('tracks', {}).values():
                    if track_data.get('global_id') == global_id:
                        track_data['name'] = name
            
            logger.info(f"✏️ Renamed person {global_id} to '{name}'")
            return True
        return False
    
    
    def get_all_person_names(self) -> Dict[int, str]:
        """Get all person names"""
        return {gid: data['name'] for gid, data in self.global_persons.items()}
    
    def generate_embeddings_for_camera(self, camera_id: int):
        """
        Generate ReID embeddings for tracks and assign global IDs
        Called periodically (every 2 seconds) for cross-camera matching
        
        Core logic:
        1. Generate embedding for each track
        2. Compare against ALL existing global persons
        3. If match found (similarity > threshold): assign existing global_id
        4. If no match: create NEW global person with new ID
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
        
        # Process each track with embedding
        for i, ds_track in enumerate(ds_tracks):
            if not ds_track.is_confirmed() or i >= len(track_ids):
                continue
            
            if not hasattr(ds_track, 'get_feature'):
                continue
            
            embedding = ds_track.get_feature()
            if embedding is None:
                continue
            
            track_id = track_ids[i]
            track_key = (camera_id, track_id)
            
            # Check if this track already has a global ID (temporary or permanent)
            if track_key in self.camera_track_to_global:
                existing_global_id = self.camera_track_to_global[track_key]
                
                # If it has a temporary ID (no embedding), we need to check if this is actually an existing person
                if existing_global_id in self.global_persons and self.global_persons[existing_global_id].get('embedding') is None:
                    # This was a temporary ID - now validate with embedding
                    best_match_id = None
                    best_similarity = 0.0
                    
                    # Compare against ALL persons with embeddings (excluding self)
                    for global_id, person_data in self.global_persons.items():
                        if global_id == existing_global_id:
                            continue
                        if person_data.get('embedding') is None:
                            continue
                        sim = self._cosine_similarity(embedding, person_data['embedding'])
                        if sim > best_similarity and sim > self.similarity_threshold:
                            best_similarity = sim
                            best_match_id = global_id
                    
                    if best_match_id is not None:
                        # Found a match! Merge temporary ID into existing person
                        logger.info(f"🔄 Merging temporary ID {existing_global_id} into existing person {best_match_id} [sim={best_similarity:.3f}]")
                        
                        # Update mapping
                        self.camera_track_to_global[track_key] = best_match_id
                        
                        # Update track data
                        name = self.global_persons[best_match_id]['name']
                        tracks[track_id]['global_id'] = best_match_id
                        tracks[track_id]['name'] = name
                        
                        # Add track mapping
                        if track_key not in self.global_persons[best_match_id]['track_mappings']:
                            self.global_persons[best_match_id]['track_mappings'].append(track_key)
                        
                        # Remove temporary person entry
                        del self.global_persons[existing_global_id]
                    else:
                        # No match - temporary ID becomes permanent, just add embedding
                        self.global_persons[existing_global_id]['embedding'] = embedding
                        logger.info(f"✅ Temporary ID {existing_global_id} confirmed as new person with embedding")
                else:
                    # Already has embedding - just update it
                    if existing_global_id in self.global_persons:
                        self.global_persons[existing_global_id]['embedding'] = embedding
                continue
            
            # NEW TRACK - find if this person already exists globally
            best_match_id = None
            best_similarity = 0.0
            
            for global_id, person_data in self.global_persons.items():
                if 'embedding' not in person_data:
                    continue
                sim = self._cosine_similarity(embedding, person_data['embedding'])
                if sim > best_similarity and sim > self.similarity_threshold:
                    best_similarity = sim
                    best_match_id = global_id
            
            if best_match_id is not None:
                # EXISTING PERSON - assign existing global_id
                global_id = best_match_id
                self.camera_track_to_global[track_key] = global_id
                
                # Add track mapping
                if track_key not in self.global_persons[global_id]['track_mappings']:
                    self.global_persons[global_id]['track_mappings'].append(track_key)
                
                # Update track data
                name = self.global_persons[global_id]['name']
                tracks[track_id]['global_id'] = global_id
                tracks[track_id]['name'] = name
                
                logger.info(f"👤 Camera {camera_id} Track {track_id} → Existing person {global_id} ({name}) [sim={best_similarity:.3f}]")
            
            else:
                # NEW PERSON - create new global ID
                global_id = self.next_global_id
                self.next_global_id += 1
                
                # Assign name from pool
                if self.used_name_index < len(self.name_pool):
                    name = self.name_pool[self.used_name_index]
                    self.used_name_index += 1
                else:
                    name = f"Person {global_id}"
                
                # Create global person record
                self.global_persons[global_id] = {
                    'embedding': embedding,
                    'name': name,
                    'track_mappings': [track_key]
                }
                
                # Map track to global ID
                self.camera_track_to_global[track_key] = global_id
                
                # Update track data
                tracks[track_id]['global_id'] = global_id
                tracks[track_id]['name'] = name
                
                logger.info(f"✨ NEW person detected: {name} (ID: {global_id}) on Camera {camera_id} Track {track_id}")
    
    def get_unique_people_count_across_cameras(self, camera_ids: List[int]) -> int:
        """
        Get count of unique people across cameras
        Uses get_people_in_room which assigns temporary IDs if needed
        """
        return len(self.get_people_in_room(camera_ids))
    
    def get_people_in_room(self, camera_ids: List[int]) -> List[Dict]:
        """
        Get all people currently visible across cameras with their global IDs
        Returns list of {global_id, name, camera_id, track_id, bbox}
        
        Shows ALL tracked people immediately, even before embeddings are generated.
        Tracks without embeddings yet get temporary IDs until ReID assigns permanent ones.
        """
        logger.info(f"🔍 get_people_in_room called for cameras: {camera_ids}")
        people = []
        seen_global_ids = set()
        
        for camera_id in camera_ids:
            if camera_id not in self.camera_tracks:
                logger.info(f"  📷 Camera {camera_id}: NOT in camera_tracks")
                continue
            
            tracks = self.camera_tracks[camera_id].get('tracks', {})
            logger.info(f"  📷 Camera {camera_id}: {len(tracks)} tracks found")
            
            for track_id, track_data in tracks.items():
                global_id = track_data.get('global_id')
                logger.info(f"    🔸 Track {track_id}: global_id={global_id}, bbox={track_data.get('bbox')}")
                
                # If no global_id yet, assign a temporary one
                if not global_id:
                    track_key = (camera_id, track_id)
                    
                    # Check if we already assigned a temporary ID to this track
                    if track_key in self.camera_track_to_global:
                        global_id = self.camera_track_to_global[track_key]
                    else:
                        # Create temporary global ID (will be validated/updated when embedding is generated)
                        global_id = self.next_global_id
                        self.next_global_id += 1
                        
                        # Assign temporary name
                        if self.used_name_index < len(self.name_pool):
                            name = self.name_pool[self.used_name_index]
                            self.used_name_index += 1
                        else:
                            name = f"Person {global_id}"
                        
                        # Store temporarily (will be updated by embedding generation)
                        self.camera_track_to_global[track_key] = global_id
                        self.global_persons[global_id] = {
                            'embedding': None,  # No embedding yet
                            'name': name,
                            'track_mappings': [track_key]
                        }
                        
                        # Update track
                        track_data['global_id'] = global_id
                        track_data['name'] = name
                        
                        logger.info(f"⏱️ Temporary ID assigned: {name} (ID: {global_id}) on Camera {camera_id} Track {track_id} [awaiting embedding]")
                
                # Add to list (deduplicate by global_id)
                if global_id and global_id not in seen_global_ids:
                    people.append({
                        'global_id': global_id,
                        'name': track_data.get('name', f'Person {global_id}'),
                        'camera_id': camera_id,
                        'track_id': track_id,
                        'bbox': track_data['bbox']
                    })
                    seen_global_ids.add(global_id)
        
        logger.info(f"✅ Returning {len(people)} people from get_people_in_room")
        return people
    
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
