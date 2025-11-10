"""
Simple People Tracking Service - Official YOLO Pattern
Following official Ultralytics YOLO tracking documentation
"""

import cv2
import numpy as np
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)


class TrackingService:
    """Simple YOLO tracking following official pattern"""
    
    def __init__(self, model_name: str = "yolo11x.pt", conf_threshold: float = 0.6):
        logger.info(f"Initializing YOLO tracking with {model_name}...")
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        
        # Detect device
        self.device = self._detect_device()
        
        # Per-camera YOLO models (official pattern for multi-camera)
        self.trackers = {}  # {camera_id: YOLO model}
        
        # Simple track storage
        self.camera_tracks = defaultdict(lambda: {
            'count': 0,
            'tracks': {},  # {track_id: {bbox, confidence, last_seen}}
        })
        
        # Global person management for cross-camera matching
        self.global_persons = {}  # {global_id: {'name': str, 'cameras': set}}
        self.track_to_global = {}  # {(camera_id, track_id): global_id}
        self.next_global_id = 1
        
        # Name pool for auto-naming
        self.name_pool = [
            "Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Harper",
            "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Navy", "Oakley", "Parker",
            "Quinn", "River", "Sage", "Taylor", "Unity", "Vale", "Winter", "Zen"
        ]
        self.used_names = 0
        
        logger.info(f"✅ Tracking service initialized on {self.device}")
    
    def _detect_device(self) -> str:
        """Detect if GPU is available"""
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
                return 'cuda'
        except:
            pass
        logger.info("Using CPU")
        return 'cpu'
    
    def track_people(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Track people in frame - Official YOLO pattern
        
        Args:
            camera_id: Camera ID
            frame: Video frame
            
        Returns:
            Dictionary with people_count and tracks
        """
        # Get or create tracker for this camera (official multi-camera pattern)
        if camera_id not in self.trackers:
            model = YOLO(self.model_name)
            if self.device == 'cuda':
                model.to('cuda')
            self.trackers[camera_id] = model
            logger.info(f"Created tracker for camera {camera_id}")
        
        tracker = self.trackers[camera_id]
        
        # Run tracking - Official YOLO way
        results = tracker.track(
            frame,
            persist=True,  # Official: maintain tracks between frames
            conf=self.conf_threshold,
            classes=[0],  # Person class only
            verbose=False
        )
        
        # Extract tracking results
        tracks = {}
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and hasattr(result.boxes, 'id') and result.boxes.id is not None:
                # Get track IDs and boxes
                track_ids = result.boxes.id.cpu().numpy().astype(int)
                boxes = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                
                for track_id, box, conf in zip(track_ids, boxes, confs):
                    tracks[int(track_id)] = {
                        'bbox': [int(box[0]), int(box[1]), int(box[2]), int(box[3])],
                        'confidence': float(conf),
                        'last_seen': datetime.now()
                    }
        
        # Update storage
        self.camera_tracks[camera_id]['tracks'] = tracks
        self.camera_tracks[camera_id]['count'] = len(tracks)
        
        return {
            'camera_id': camera_id,
            'people_count': len(tracks),
            'tracks': tracks
        }
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """Draw tracking boxes on frame"""
        annotated = frame.copy()
        tracks = self.camera_tracks[camera_id].get('tracks', {})
        
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            
            # Get global info if available
            track_key = (camera_id, track_id)
            if track_key in self.track_to_global:
                global_id = self.track_to_global[track_key]
                name = self.global_persons[global_id]['name']
                label = name
                color = (0, 255, 255)  # Yellow for named
            else:
                label = f"Track {track_id}"
                color = (0, 255, 0)  # Green
            
            # Draw box and label
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            cv2.putText(annotated, label, (bbox[0], bbox[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return annotated
    
    def get_people_in_room(self, camera_ids: List[int]) -> List[Dict]:
        """
        Get all people across cameras with global IDs
        Simple cross-camera matching
        """
        people = []
        seen_global_ids = set()
        
        for camera_id in camera_ids:
            tracks = self.camera_tracks[camera_id].get('tracks', {})
            
            for track_id, track_data in tracks.items():
                track_key = (camera_id, track_id)
                
                # Assign global ID if needed
                if track_key not in self.track_to_global:
                    # Check if this person exists in another camera (simple matching)
                    matched_global_id = None
                    for other_cam in camera_ids:
                        if other_cam == camera_id:
                            continue
                        for other_track_id in self.camera_tracks[other_cam].get('tracks', {}).keys():
                            other_key = (other_cam, other_track_id)
                            if other_key in self.track_to_global:
                                # Found same person in another camera
                                matched_global_id = self.track_to_global[other_key]
                                logger.info(f"🔗 Matched Camera {camera_id} Track {track_id} with existing global ID {matched_global_id}")
                                break
                        if matched_global_id:
                            break
                    
                    if matched_global_id:
                        global_id = matched_global_id
                    else:
                        # Create new global person
                        global_id = self.next_global_id
                        self.next_global_id += 1
                        name = self.name_pool[self.used_names % len(self.name_pool)]
                        self.used_names += 1
                        self.global_persons[global_id] = {'name': name, 'cameras': set()}
                        logger.info(f"✨ New person: {name} (ID: {global_id})")
                    
                    self.track_to_global[track_key] = global_id
                    self.global_persons[global_id]['cameras'].add(camera_id)
                
                # Get global info
                global_id = self.track_to_global[track_key]
                name = self.global_persons[global_id]['name']
                
                # Add to result (deduplicate by global ID)
                if global_id not in seen_global_ids:
                    people.append({
                        'global_id': global_id,
                        'name': name,
                        'camera_id': camera_id,
                        'track_id': track_id,
                        'bbox': track_data['bbox']
                    })
                    seen_global_ids.add(global_id)
        
        return people
    
    def get_unique_people_count_across_cameras(self, camera_ids: List[int]) -> int:
        """Get unique people count across cameras"""
        return len(self.get_people_in_room(camera_ids))
    
    def set_person_name(self, global_id: int, name: str) -> bool:
        """Rename a person"""
        if global_id in self.global_persons:
            self.global_persons[global_id]['name'] = name
            logger.info(f"Renamed person {global_id} to '{name}'")
            return True
        return False
    
    def get_all_person_names(self) -> Dict[int, str]:
        """Get all person names"""
        return {gid: data['name'] for gid, data in self.global_persons.items()}
    
    def reset(self, camera_id: int = None):
        """Reset tracker"""
        if camera_id:
            self.trackers.pop(camera_id, None)
            self.camera_tracks.pop(camera_id, None)
            logger.info(f"Reset tracker for camera {camera_id}")
        else:
            self.trackers = {}
            self.camera_tracks = defaultdict(lambda: {'count': 0, 'tracks': {}})
            self.global_persons = {}
            self.track_to_global = {}
            self.next_global_id = 1
            logger.info("Reset all trackers")
