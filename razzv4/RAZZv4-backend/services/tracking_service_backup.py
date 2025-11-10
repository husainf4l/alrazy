"""
People Detection and Tracking Service using YOLO11 + BoT-SORT
Best practice implementation using YOLO's built-in tracking with ReID
"""

import cv2
import numpy as np
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)


class TrackingService:
    """YOLO11 with native BoT-SORT tracker (includes ReID for cross-camera matching)"""
    
    def __init__(self, model_name: str = "yolo11n.pt", conf_threshold: float = 0.5):
        logger.info("Initializing YOLO tracking service with BoT-SORT...")
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.device = self._detect_device()
        
        # Per-camera YOLO models (each maintains its own tracking state)
        self.yolo_trackers = {}
        
        # Track storage
        self.camera_tracks = defaultdict(lambda: {
            'count': 0, 
            'tracks': {},  # {track_id: {bbox, confidence, last_seen, global_id, name}}
            'last_update': None,
            'last_frame': None
        })
        
        # Cross-camera global person database
        self.global_persons = {}  # {global_id: {'name': str, 'track_mappings': [(cam, track_id)]}}
        self.camera_track_to_global = {}  # {(camera_id, track_id): global_id}
        self.next_global_id = 1
        
        # Name pool
        self.name_pool = [
            "Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Harper",
            "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Navy", "Oakley", "Parker",
            "Quinn", "River", "Sage", "Taylor", "Unity", "Vale", "Winter", "Zen"
        ]
        self.used_name_index = 0
        
        logger.info("✅ YOLO tracking service initialized with BoT-SORT")
    
    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
                return 'cuda'
        except: pass
        logger.info("Using CPU for tracking")
        return 'cpu'
    
    def _get_yolo_tracker(self, camera_id: int) -> YOLO:
        """Get or create YOLO tracker for camera with BoT-SORT + ReID enabled"""
        if camera_id not in self.yolo_trackers:
            model = YOLO(self.model_name)
            if self.device == 'cuda':
                model.to('cuda')
            self.yolo_trackers[camera_id] = model
            logger.info(f"Created YOLO tracker for camera {camera_id} with BoT-SORT + ReID")
        return self.yolo_trackers[camera_id]
    
    def track_people(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Track people using YOLO's built-in BoT-SORT tracker with ReID
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            
        Returns:
            Dictionary with tracking information
        """
        model = self._get_yolo_tracker(camera_id)
        
        # Use YOLO's native tracking with BoT-SORT + ReID
        # persist=True maintains tracking across frames
        # tracker="botsort_custom.yaml" uses our optimized BoT-SORT config
        results = model.track(
            frame,
            classes=[0],  # Person class only
            conf=self.conf_threshold,
            iou=0.5,  # Lower IOU = more forgiving track matching (reduces duplicate IDs)
            persist=True,  # Maintain tracks across frames
            tracker="botsort_custom.yaml",  # Custom BoT-SORT config with stricter thresholds
            verbose=False,
            device=self.device,
            half=True if self.device == 'cuda' else False
        )
        
        # Extract tracks
        tracks = {}
        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            
            # Check if tracking IDs are available
            if hasattr(boxes, 'id') and boxes.id is not None:
                track_ids = boxes.id.cpu().numpy().astype(int)
                
                for i, track_id in enumerate(track_ids):
                    bbox = boxes.xyxy[i].cpu().numpy()
                    confidence = float(boxes.conf[i])
                    
                    tracks[int(track_id)] = {
                        'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                        'confidence': confidence,
                        'last_seen': datetime.now()
                    }
        
        # Store for cross-camera access
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
                color = (0, 255, 255)  # Yellow for named
            elif global_id:
                label = f"ID {global_id}"
                color = (0, 255, 255)
            else:
                label = f"Track {track_id}"
                color = (0, 255, 0)  # Green for unnamed
            
            # Draw box
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label with background
            (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (bbox[0], bbox[1] - label_height - 10), 
                         (bbox[0] + label_width, bbox[1]), color, -1)
            cv2.putText(annotated, label, (bbox[0], bbox[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Draw count
        cv2.putText(annotated, f"People: {len(tracks)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return annotated
    
    def get_people_in_room(self, camera_ids: List[int]) -> List[Dict]:
        """
        Get all people currently visible across cameras with their global IDs
        Assigns global IDs and names to tracks with cross-camera matching
        """
        # Clean up stale tracks first
        self.cleanup_stale_tracks(max_age_seconds=10.0)
        
        logger.info(f"🔍 get_people_in_room called for cameras: {camera_ids}")
        people = []
        seen_global_ids = set()
        
        # Collect all active tracks from all cameras
        active_tracks = []
        for camera_id in camera_ids:
            if camera_id not in self.camera_tracks:
                logger.info(f"  📷 Camera {camera_id}: NOT in camera_tracks")
                continue
            
            tracks = self.camera_tracks[camera_id].get('tracks', {})
            logger.info(f"  📷 Camera {camera_id}: {len(tracks)} tracks found")
            
            for track_id, track_data in tracks.items():
                active_tracks.append({
                    'camera_id': camera_id,
                    'track_id': track_id,
                    'track_data': track_data,
                    'track_key': (camera_id, track_id)
                })
        
        # Process each track and assign/match global IDs
        for track_info in active_tracks:
            camera_id = track_info['camera_id']
            track_id = track_info['track_id']
            track_data = track_info['track_data']
            track_key = track_info['track_key']
            
            # Check if this track already has a global ID
            if track_key in self.camera_track_to_global:
                global_id = self.camera_track_to_global[track_key]
                name = self.global_persons[global_id]['name']
            else:
                # Try to match with existing global persons from OTHER cameras
                matched_global_id = None
                
                # Look for recently seen persons in other cameras that might be the same person
                for existing_global_id, person_data in self.global_persons.items():
                    for existing_track_key in person_data['track_mappings']:
                        existing_camera_id, existing_track_id = existing_track_key
                        
                        # Skip if same camera (each camera has unique tracks)
                        if existing_camera_id == camera_id:
                            continue
                        
                        # Check if this track is currently active in another camera
                        if existing_camera_id in self.camera_tracks:
                            other_tracks = self.camera_tracks[existing_camera_id].get('tracks', {})
                            if existing_track_id in other_tracks:
                                # This person is visible in another camera right now
                                # Assume same room = same person appearing in multiple cameras
                                matched_global_id = existing_global_id
                                logger.info(f"🔗 Matched Camera {camera_id} Track {track_id} with existing person {person_data['name']} (ID: {existing_global_id})")
                                break
                    
                    if matched_global_id:
                        break
                
                if matched_global_id:
                    # Use existing global ID
                    global_id = matched_global_id
                    name = self.global_persons[global_id]['name']
                    # Add this track to the person's mappings
                    if track_key not in self.global_persons[global_id]['track_mappings']:
                        self.global_persons[global_id]['track_mappings'].append(track_key)
                    self.camera_track_to_global[track_key] = global_id
                else:
                    # Create new global ID and name
                    global_id = self.next_global_id
                    self.next_global_id += 1
                    
                    if self.used_name_index < len(self.name_pool):
                        name = self.name_pool[self.used_name_index]
                        self.used_name_index += 1
                    else:
                        name = f"Person {global_id}"
                    
                    # Store mapping
                    self.camera_track_to_global[track_key] = global_id
                    self.global_persons[global_id] = {
                        'name': name,
                        'track_mappings': [track_key]
                    }
                    
                    logger.info(f"✨ Assigned: {name} (ID: {global_id}) to Camera {camera_id} Track {track_id}")
            
            # Update track data
            track_data['global_id'] = global_id
            track_data['name'] = name
            
            # Add to list (deduplicate by global_id)
            if global_id not in seen_global_ids:
                people.append({
                    'global_id': global_id,
                    'name': name,
                    'camera_id': camera_id,
                    'track_id': track_id,
                    'bbox': track_data['bbox']
                })
                seen_global_ids.add(global_id)
        
        logger.info(f"✅ Returning {len(people)} unique people")
        return people
    
    def cleanup_stale_tracks(self, max_age_seconds: float = 10.0):
        """Remove tracks that haven't been updated recently"""
        from datetime import datetime, timedelta
        current_time = datetime.now()
        removed_count = 0
        
        for camera_id, camera_data in list(self.camera_tracks.items()):
            tracks = camera_data.get('tracks', {})
            stale_track_ids = []
            
            for track_id, track_data in tracks.items():
                last_seen = track_data.get('last_seen')
                if not last_seen:
                    continue
                    
                age = (current_time - last_seen).total_seconds()
                
                if age > max_age_seconds:
                    stale_track_ids.append(track_id)
            
            # Remove stale tracks
            for track_id in stale_track_ids:
                del tracks[track_id]
                removed_count += 1
            
            # Update count
            camera_data['count'] = len(tracks)
        
        if removed_count > 0:
            logger.info(f"🧹 Cleaned up {removed_count} stale tracks")
        
        return removed_count
    
    def get_unique_people_count_across_cameras(self, camera_ids: List[int]) -> int:
        """Get count of unique people across cameras"""
        return len(self.get_people_in_room(camera_ids))
    
    def set_person_name(self, global_id: int, name: str) -> bool:
        """Rename a person by their global ID"""
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
    
    def reset(self, camera_id: int = None):
        """Reset tracker state"""
        if camera_id:
            self.yolo_trackers.pop(camera_id, None)
            self.camera_tracks.pop(camera_id, None)
            logger.info(f"Reset tracker for camera {camera_id}")
        else:
            self.yolo_trackers = {}
            self.camera_tracks = defaultdict(lambda: {
                'count': 0, 'tracks': {}, 'last_update': None, 'last_frame': None
            })
            logger.info("Reset all trackers")
