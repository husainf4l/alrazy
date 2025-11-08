"""
Cross-Camera Tracking Service
Handles person re-identification across multiple cameras in the same room
Prevents double-counting when cameras have overlapping views
"""

import numpy as np
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from datetime import datetime, timedelta
import cv2
from shapely.geometry import Point, Polygon
import asyncio


class GlobalPersonTracker:
    """
    Tracks people globally across multiple cameras in the same room
    Uses appearance features + spatial reasoning to match people
    """
    
    def __init__(self, similarity_threshold: float = 0.6, time_window: int = 3):
        """
        Initialize cross-camera tracker
        
        Args:
            similarity_threshold: Minimum similarity to consider same person (0.0-1.0)
            time_window: Maximum seconds between camera detections to match (seconds)
        """
        self.similarity_threshold = similarity_threshold
        self.time_window = timedelta(seconds=time_window)
        
        # Global person registry per room
        # Format: {room_id: {global_person_id: PersonProfile}}
        self.room_persons = defaultdict(dict)
        
        # Next global person ID per room
        self.next_person_id = defaultdict(lambda: 1)
        
        # Camera-to-global ID mapping
        # Format: {room_id: {camera_id: {local_track_id: global_person_id}}}
        self.camera_mappings = defaultdict(lambda: defaultdict(dict))
        
        # Overlap zones per room
        # Format: {room_id: [{camera_id_1, camera_id_2, polygon}]}
        self.overlap_zones = defaultdict(list)
        
        print("🌐 Global Cross-Camera Tracker initialized")
    
    def configure_overlap_zone(self, room_id: int, camera_id_1: int, 
                               camera_id_2: int, polygon_coords: List[List[int]]):
        """
        Configure an overlap zone between two cameras
        
        Args:
            room_id: Room identifier
            camera_id_1: First camera ID
            camera_id_2: Second camera ID
            polygon_coords: Polygon coordinates [[x1,y1], [x2,y2], ...]
        """
        polygon = Polygon(polygon_coords)
        self.overlap_zones[room_id].append({
            'cameras': {camera_id_1, camera_id_2},
            'polygon': polygon
        })
        print(f"✅ Configured overlap zone for cameras {camera_id_1} & {camera_id_2} in room {room_id}")
    
    def _is_in_overlap_zone(self, room_id: int, camera_id: int, 
                            point: Tuple[int, int]) -> Tuple[bool, Set[int]]:
        """
        Check if a point is in an overlap zone and return overlapping cameras
        
        Args:
            room_id: Room identifier
            camera_id: Camera identifier
            point: Point coordinates (x, y)
            
        Returns:
            Tuple of (is_in_overlap, set_of_overlapping_camera_ids)
        """
        pt = Point(point)
        overlapping_cameras = set()
        
        for zone in self.overlap_zones[room_id]:
            if camera_id in zone['cameras'] and zone['polygon'].contains(pt):
                # This person is in overlap zone
                overlapping_cameras.update(zone['cameras'] - {camera_id})
        
        return len(overlapping_cameras) > 0, overlapping_cameras
    
    def _extract_appearance_features(self, frame: np.ndarray, 
                                     bbox: List[int]) -> np.ndarray:
        """
        Extract appearance features from person crop for ReID
        Uses color histogram as a simple but effective feature
        
        Args:
            frame: Full camera frame
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Feature vector (normalized histogram)
        """
        x1, y1, x2, y2 = bbox
        
        # Crop person region
        person_crop = frame[max(0, y1):y2, max(0, x1):x2]
        
        if person_crop.size == 0:
            return np.zeros(512)  # Return zero vector if crop failed
        
        # Convert to HSV for better color representation
        hsv = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
        
        # Calculate color histogram (simple but effective for ReID)
        h_hist = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256])
        v_hist = cv2.calcHist([hsv], [2], None, [32], [0, 256])
        
        # Concatenate and normalize
        features = np.concatenate([h_hist, s_hist, v_hist]).flatten()
        features = features / (np.linalg.norm(features) + 1e-6)
        
        return features
    
    def _calculate_similarity(self, features1: np.ndarray, 
                             features2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two feature vectors
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if features1 is None or features2 is None:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(features1, features2)
        return float(similarity)
    
    def update_tracks(self, room_id: int, camera_id: int, frame: np.ndarray,
                     tracks: Dict[int, Dict]) -> Dict[int, int]:
        """
        Update global person tracking for a camera in a room
        
        Args:
            room_id: Room identifier
            camera_id: Camera identifier
            frame: Current camera frame
            tracks: Local tracks from ByteTrack/DeepSORT
                   Format: {local_track_id: {bbox, confidence, center, ...}}
        
        Returns:
            Mapping of local_track_id to global_person_id
        """
        current_time = datetime.now()
        global_mapping = {}
        
        for local_track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            center = track_data['center']
            
            # Extract appearance features
            features = self._extract_appearance_features(frame, bbox)
            
            # Check if person is in overlap zone
            in_overlap, overlapping_cameras = self._is_in_overlap_zone(
                room_id, camera_id, center
            )
            
            # Try to match with existing global persons
            best_match_id = None
            best_similarity = 0.0
            
            for global_id, person_profile in self.room_persons[room_id].items():
                # Skip if not recently seen
                if current_time - person_profile['last_seen'] > self.time_window:
                    continue
                
                # Calculate appearance similarity
                similarity = self._calculate_similarity(
                    features, person_profile['features']
                )
                
                # If in overlap zone, check if this person is visible in overlapping cameras
                if in_overlap:
                    # Check if this global person is currently in any overlapping camera
                    for other_cam_id in overlapping_cameras:
                        if other_cam_id in person_profile.get('visible_in_cameras', {}):
                            # Strong indication this is the same person
                            similarity += 0.2  # Boost similarity
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match_id = global_id
            
            # Assign or create global person ID
            if best_match_id is not None:
                # Matched with existing person
                global_person_id = best_match_id
                
                # Update person profile
                self.room_persons[room_id][global_person_id].update({
                    'features': features,  # Update with latest appearance
                    'last_seen': current_time,
                    'last_camera': camera_id,
                    'last_bbox': bbox,
                    'visible_in_cameras': {
                        **self.room_persons[room_id][global_person_id].get('visible_in_cameras', {}),
                        camera_id: current_time
                    }
                })
            else:
                # New person detected
                global_person_id = self.next_person_id[room_id]
                self.next_person_id[room_id] += 1
                
                # Create new person profile
                self.room_persons[room_id][global_person_id] = {
                    'features': features,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'last_camera': camera_id,
                    'last_bbox': bbox,
                    'visible_in_cameras': {camera_id: current_time},
                    'in_overlap_zone': in_overlap,
                    'name': None  # Name can be assigned later
                }
            
            # Store mapping
            global_mapping[local_track_id] = global_person_id
            self.camera_mappings[room_id][camera_id][local_track_id] = global_person_id
        
        # Clean up old persons (not seen in time window)
        self._cleanup_old_persons(room_id, current_time)
        
        return global_mapping
    
    def _cleanup_old_persons(self, room_id: int, current_time: datetime):
        """
        Remove persons not seen recently from tracking
        
        Args:
            room_id: Room identifier
            current_time: Current timestamp
        """
        to_remove = []
        
        for global_id, person_profile in self.room_persons[room_id].items():
            if current_time - person_profile['last_seen'] > self.time_window * 2:
                to_remove.append(global_id)
        
        for global_id in to_remove:
            del self.room_persons[room_id][global_id]
    
    def get_room_person_count(self, room_id: int) -> int:
        """
        Get unique person count in a room (across all cameras)
        
        Args:
            room_id: Room identifier
            
        Returns:
            Number of unique people in the room
        """
        current_time = datetime.now()
        active_count = 0
        
        for person_profile in self.room_persons[room_id].values():
            # Only count if seen recently
            if current_time - person_profile['last_seen'] <= self.time_window:
                active_count += 1
        
        return active_count
    
    def get_room_stats(self, room_id: int) -> Dict:
        """
        Get detailed statistics for a room
        
        Args:
            room_id: Room identifier
            
        Returns:
            Statistics dictionary
        """
        current_time = datetime.now()
        active_persons = []
        
        for global_id, person_profile in self.room_persons[room_id].items():
            if current_time - person_profile['last_seen'] <= self.time_window:
                active_persons.append({
                    'global_id': global_id,
                    'name': person_profile.get('name'),
                    'last_camera': person_profile['last_camera'],
                    'last_seen': person_profile['last_seen'].isoformat(),
                    'visible_in_cameras': list(person_profile['visible_in_cameras'].keys()),
                    'in_overlap_zone': person_profile.get('in_overlap_zone', False)
                })
        
        current_count = len(active_persons)
        
        # Check for people leaving and send SMS alert (synchronous check)
        try:
            from services.sms_alert_service import sms_alert_service
            # Print for debugging
            print(f"🔍 Checking SMS alert for room {room_id}: count={current_count}")
            # Check synchronously to avoid event loop issues
            sms_alert_service.check_and_alert_sync(
                room_id=room_id,
                current_count=current_count,
                room_name=f"Room {room_id}"
            )
        except Exception as e:
            print(f"⚠️ SMS alert check failed: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            'room_id': room_id,
            'unique_person_count': current_count,
            'active_persons': active_persons,
            'timestamp': current_time.isoformat()
        }
    
    def get_camera_to_global_mapping(self, room_id: int, 
                                     camera_id: int) -> Dict[int, int]:
        """
        Get mapping of local track IDs to global person IDs for a camera
        
        Args:
            room_id: Room identifier
            camera_id: Camera identifier
            
        Returns:
            Mapping dict {local_track_id: global_person_id}
        """
        return self.camera_mappings[room_id].get(camera_id, {})
    
    def set_person_name(self, room_id: int, global_id: int, name: str) -> bool:
        """
        Assign a name to a tracked person
        
        Args:
            room_id: Room identifier
            global_id: Global person ID
            name: Name to assign
            
        Returns:
            True if successful, False if person not found
        """
        if global_id in self.room_persons[room_id]:
            self.room_persons[room_id][global_id]['name'] = name
            print(f"✅ Assigned name '{name}' to person {global_id} in room {room_id}")
            return True
        return False
    
    def get_person_info(self, room_id: int, global_id: int) -> Dict:
        """
        Get detailed information about a tracked person
        
        Args:
            room_id: Room identifier
            global_id: Global person ID
            
        Returns:
            Person profile dictionary or None if not found
        """
        if global_id in self.room_persons[room_id]:
            profile = self.room_persons[room_id][global_id]
            return {
                'global_id': global_id,
                'name': profile.get('name'),
                'first_seen': profile.get('first_seen', profile['last_seen']).isoformat(),
                'last_seen': profile['last_seen'].isoformat(),
                'last_camera': profile['last_camera'],
                'visible_in_cameras': list(profile['visible_in_cameras'].keys())
            }
        return None
