"""
Global Person Tracker - Cross-Camera Re-Identification
Maintains consistent person IDs across multiple cameras using OSNet Re-ID
WITH DATABASE PERSISTENCE - Person data shared across all cameras
WITH FAISS INDEX - Fast similarity search for large galleries
"""

import logging
import threading
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import DetectedPerson
import json

logger = logging.getLogger(__name__)


@dataclass
class GlobalPerson:
    """Represents a person tracked across multiple cameras"""
    global_id: int
    face_embedding: Optional[np.ndarray] = None  # 512-dim Re-ID embedding (OSNet)
    name: Optional[str] = None  # Name from database or manual assignment
    
    # Tracking state
    camera_tracks: Dict[int, int] = field(default_factory=dict)  # {camera_id: local_track_id}
    camera_positions: Dict[int, Tuple[float, float, float, float]] = field(default_factory=dict)  # {camera_id: bbox}
    last_seen: float = field(default_factory=time.time)
    first_seen: float = field(default_factory=time.time)
    
    # Statistics
    total_appearances: int = 0
    cameras_visited: set = field(default_factory=set)
    
    # Quality metrics (quality now based on bbox size)
    best_face_quality: float = 0.0
    best_face_embedding: Optional[np.ndarray] = None
    
    def update_from_camera(self, camera_id: int, local_track_id: int, 
                          face_embedding: Optional[np.ndarray] = None,
                          face_quality: float = 0.0,
                          bbox: Optional[Tuple[int, int, int, int]] = None):
        """Update person state from camera detection"""
        self.camera_tracks[camera_id] = local_track_id
        self.last_seen = time.time()
        self.cameras_visited.add(camera_id)
        self.total_appearances += 1
        
        # Store position from this camera
        if bbox is not None:
            self.camera_positions[camera_id] = bbox
        
        # Update face embedding if quality is better
        if face_embedding is not None and face_quality > self.best_face_quality:
            self.best_face_quality = face_quality
            self.best_face_embedding = face_embedding.copy()
            
            # Update primary embedding if significantly better
            if self.face_embedding is None or face_quality > self.best_face_quality * 0.8:
                self.face_embedding = face_embedding.copy()
    
    def remove_camera_track(self, camera_id: int):
        """Remove tracking from a specific camera"""
        if camera_id in self.camera_tracks:
            del self.camera_tracks[camera_id]
        if camera_id in self.camera_positions:
            del self.camera_positions[camera_id]
    
    def is_active(self, timeout: float = 30.0) -> bool:
        """Check if person is still being tracked"""
        return len(self.camera_tracks) > 0 and (time.time() - self.last_seen) < timeout


class GlobalPersonTracker:
    """
    Manages global person identities across multiple cameras
    WITH DATABASE PERSISTENCE - All cameras share person data
    WITH FAISS INDEX - Fast similarity search for large person galleries
    
    Features:
    - OSNet Re-ID for full-body matching across cameras
    - FAISS for fast nearest-neighbor search
    - Spatial matching for overlapping views
    - Database persistence for cross-camera sharing
    - Physical dimensions tracking
    - Automatic sync to database
    """
    
    def __init__(self, 
                 face_similarity_threshold: float = 0.5,
                 person_timeout: float = 30.0,
                 cleanup_interval: float = 60.0,
                 db_sync_interval: float = 5.0):
        """
        Initialize global person tracker
        
        Args:
            face_similarity_threshold: Minimum cosine similarity for Re-ID match (0-1)
            person_timeout: Seconds before removing inactive person
            cleanup_interval: Seconds between cleanup runs
            db_sync_interval: Seconds between database syncs
        """
        self.face_similarity_threshold = face_similarity_threshold
        self.person_timeout = person_timeout
        self.cleanup_interval = cleanup_interval
        self.db_sync_interval = db_sync_interval
        
        # Global person registry (in-memory cache)
        self.persons: Dict[int, GlobalPerson] = {}  # {global_id: GlobalPerson}
        self.next_global_id = 1
        
        # Camera-to-global mapping
        self.camera_track_to_global: Dict[Tuple[int, int], int] = {}  # {(camera_id, local_track_id): global_id}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # FAISS index for fast similarity search
        from services.faiss_index_service import get_faiss_service
        self.faiss_service = get_faiss_service()
        
        # Load existing persons from database
        self._load_from_database()
        
        # Background threads
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        self.sync_thread = threading.Thread(target=self._database_sync_loop, daemon=True)
        self.sync_thread.start()
        
        logger.info(f"✅ Global person tracker initialized with database persistence")
        logger.info(f"   Face threshold: {face_similarity_threshold}, Timeout: {person_timeout}s")
        logger.info(f"   Loaded {len(self.persons)} persons from database")
    
    def match_or_create_person(self,
                               camera_id: int,
                               local_track_id: int,
                               face_embedding: Optional[np.ndarray] = None,
                               face_quality: float = 0.0,
                               bbox: Optional[Tuple[int, int, int, int]] = None) -> int:
        """
        Match person to existing global ID or create new one
        Uses both face recognition AND spatial matching for overlapping camera views
        
        Args:
            camera_id: Source camera ID
            local_track_id: Local tracking ID from this camera
            face_embedding: 512-dim face embedding (if available)
            face_quality: Face detection quality score
            bbox: Person bounding box (for spatial reasoning)
        
        Returns:
            global_id: Unique person ID across all cameras
        """
        with self.lock:
            # Check if this camera track is already mapped
            key = (camera_id, local_track_id)
            if key in self.camera_track_to_global:
                global_id = self.camera_track_to_global[key]
                
                # Update existing person
                if global_id in self.persons:
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox)
                    return global_id
            
            # PRIORITY 1: Try face matching (most reliable)
            if face_embedding is not None:
                face_match = self._find_best_face_match(face_embedding, camera_id)
                
                if face_match:
                    global_id = face_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Face match: Global ID {global_id} on camera {camera_id} (track {local_track_id})")
                    return global_id
            
            # PRIORITY 2: Try spatial matching (for same-view cameras or when face not visible)
            if bbox is not None:
                spatial_match = self._find_best_spatial_match(bbox, camera_id)
                
                if spatial_match:
                    global_id = spatial_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Spatial match: Global ID {global_id} on camera {camera_id} (track {local_track_id})")
                    return global_id
            
            # No match found - create new person
            global_id = self._create_new_person(camera_id, local_track_id, face_embedding, face_quality, bbox)
            logger.info(f"🆕 New person: Global ID {global_id} on camera {camera_id} (track {local_track_id})")
            return global_id
    
    def _find_best_face_match(self, query_embedding: np.ndarray, camera_id: int) -> Optional[int]:
        """
        Find best matching person by face similarity
        Checks both in-memory cache AND database for cross-camera sharing
        
        Args:
            query_embedding: Face embedding to match
            camera_id: Source camera (for spatial filtering)
        
        Returns:
            global_id of best match, or None
        """
        best_match_id = None
        best_similarity = self.face_similarity_threshold
        
        # First check in-memory persons
        for global_id, person in self.persons.items():
            # Only match active persons
            if not person.is_active(self.person_timeout):
                continue
            
            # Skip if person has no face embedding
            if person.face_embedding is None:
                continue
            
            # Calculate cosine similarity
            similarity = float(np.dot(query_embedding, person.face_embedding))
            
            # Boost similarity if person was recently seen on nearby camera
            # (temporal-spatial consistency)
            if camera_id in person.cameras_visited:
                time_since_seen = time.time() - person.last_seen
                if time_since_seen < 5.0:  # Recently seen on this camera
                    similarity *= 1.1  # 10% boost
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = global_id
        
        # If no match in memory, check database (for cross-camera sharing)
        if best_match_id is None:
            try:
                db = SessionLocal()
                try:
                    # Query database for persons with face embeddings
                    # Use vector similarity search (pgvector)
                    from sqlalchemy import text
                    
                    result = db.execute(text("""
                        SELECT global_id, face_embedding, 
                               1 - (face_embedding <=> :embedding::vector) as similarity
                        FROM detected_persons
                        WHERE face_embedding IS NOT NULL
                          AND is_active = true
                        ORDER BY face_embedding <=> :embedding::vector
                        LIMIT 5
                    """), {'embedding': query_embedding.tolist()})
                    
                    for row in result:
                        global_id, embedding_list, similarity = row
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match_id = global_id
                            
                            # Load this person into memory for future use
                            dp = db.query(DetectedPerson).filter(
                                DetectedPerson.global_id == global_id
                            ).first()
                            
                            if dp and global_id not in self.persons:
                                person = GlobalPerson(
                                    global_id=dp.global_id,
                                    face_embedding=np.array(dp.face_embedding),
                                    name=dp.assigned_name,
                                    best_face_quality=dp.face_quality or 0.0
                                )
                                person.first_seen = dp.first_seen.timestamp()
                                person.last_seen = dp.last_seen.timestamp()
                                person.cameras_visited = set(dp.cameras_visited or [])
                                self.persons[global_id] = person
                                logger.info(f"📥 Loaded person {global_id} from database for matching")
                            
                            break
                    
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Database face matching error: {e}")
        
        if best_match_id:
            logger.debug(f"Face match: Global ID {best_match_id} (similarity={best_similarity:.3f})")
        
        return best_match_id
    
    def _find_best_spatial_match(self, bbox: Tuple[int, int, int, int], camera_id: int) -> Optional[int]:
        """
        Find best matching person by spatial position (for overlapping camera views)
        
        When two cameras view the same space, the same person appears in similar positions.
        We use IoU (Intersection over Union) to match bounding boxes.
        
        Args:
            bbox: Person bounding box [x1, y1, x2, y2]
            camera_id: Source camera ID
        
        Returns:
            global_id of best match, or None
        """
        best_match_id = None
        best_iou = 0.3  # Minimum IoU threshold for spatial match
        
        current_time = time.time()
        
        for global_id, person in self.persons.items():
            # Only match active persons
            if not person.is_active(self.person_timeout):
                continue
            
            # Don't match with same camera (already handled by ByteTrack)
            if camera_id in person.camera_tracks:
                continue
            
            # Check if person is currently visible on ANY other camera
            if not person.camera_positions:
                continue
            
            # Only match if recently seen (within 2 seconds - simultaneous view)
            time_since_seen = current_time - person.last_seen
            if time_since_seen > 2.0:
                continue
            
            # Compare with all camera positions this person is currently in
            for other_camera_id, other_bbox in person.camera_positions.items():
                if other_camera_id == camera_id:
                    continue
                
                # Calculate IoU (Intersection over Union)
                iou = self._calculate_iou(bbox, other_bbox)
                
                if iou > best_iou:
                    best_iou = iou
                    best_match_id = global_id
        
        if best_match_id:
            logger.debug(f"Spatial match: Global ID {best_match_id} (IoU={best_iou:.3f})")
        
        return best_match_id
    
    @staticmethod
    def _calculate_iou(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """
        Calculate Intersection over Union between two bounding boxes
        
        Args:
            bbox1, bbox2: Bounding boxes as [x1, y1, x2, y2]
        
        Returns:
            IoU score (0-1, where 1 = perfect overlap)
        """
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
    
    def _create_new_person(self,
                          camera_id: int,
                          local_track_id: int,
                          face_embedding: Optional[np.ndarray],
                          face_quality: float,
                          bbox: Optional[Tuple[int, int, int, int]] = None) -> int:
        """Create a new global person entry"""
        global_id = self.next_global_id
        self.next_global_id += 1
        
        person = GlobalPerson(
            global_id=global_id,
            face_embedding=face_embedding.copy() if face_embedding is not None else None,
            best_face_quality=face_quality,
            best_face_embedding=face_embedding.copy() if face_embedding is not None else None
        )
        
        person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox)
        
        self.persons[global_id] = person
        self.camera_track_to_global[(camera_id, local_track_id)] = global_id
        
        return global_id
    
    def update_person_name(self, global_id: int, name: str):
        """Update person's name"""
        with self.lock:
            if global_id in self.persons:
                self.persons[global_id].name = name
                logger.info(f"Updated name for Global ID {global_id}: {name}")
    
    def get_person(self, global_id: int) -> Optional[GlobalPerson]:
        """Get person by global ID"""
        with self.lock:
            return self.persons.get(global_id)
    
    def get_global_id_for_camera_track(self, camera_id: int, local_track_id: int) -> Optional[int]:
        """Get global ID for a camera's local track"""
        with self.lock:
            return self.camera_track_to_global.get((camera_id, local_track_id))
    
    def remove_camera_track(self, camera_id: int, local_track_id: int):
        """Remove a camera track (when person leaves camera view)"""
        with self.lock:
            key = (camera_id, local_track_id)
            if key in self.camera_track_to_global:
                global_id = self.camera_track_to_global[key]
                
                # Remove from person's camera tracks
                if global_id in self.persons:
                    self.persons[global_id].remove_camera_track(camera_id)
                
                # Remove mapping
                del self.camera_track_to_global[key]
    
    def get_all_active_persons(self) -> List[GlobalPerson]:
        """Get all currently active persons"""
        with self.lock:
            return [p for p in self.persons.values() if p.is_active(self.person_timeout)]
    
    def get_statistics(self) -> Dict:
        """Get tracker statistics"""
        with self.lock:
            active_persons = [p for p in self.persons.values() if p.is_active(self.person_timeout)]
            
            return {
                'total_persons_seen': len(self.persons),
                'active_persons': len(active_persons),
                'persons_with_faces': sum(1 for p in self.persons.values() if p.face_embedding is not None),
                'multi_camera_persons': sum(1 for p in active_persons if len(p.cameras_visited) > 1),
                'total_mappings': len(self.camera_track_to_global)
            }
    
    def _cleanup_loop(self):
        """Background thread to cleanup inactive persons"""
        while self.running:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_inactive_persons()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_inactive_persons(self):
        """Remove persons that haven't been seen recently"""
        with self.lock:
            current_time = time.time()
            inactive_ids = []
            
            for global_id, person in self.persons.items():
                if not person.is_active(self.person_timeout):
                    inactive_ids.append(global_id)
            
            if inactive_ids:
                logger.info(f"🧹 Cleaning up {len(inactive_ids)} inactive persons")
                
                for global_id in inactive_ids:
                    # Remove camera mappings
                    keys_to_remove = [
                        key for key, gid in self.camera_track_to_global.items()
                        if gid == global_id
                    ]
                    for key in keys_to_remove:
                        del self.camera_track_to_global[key]
                    
                    # Remove person
                    del self.persons[global_id]
    
    def shutdown(self):
        """Shutdown the tracker"""
        logger.info("Shutting down global person tracker")
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
        if hasattr(self, 'sync_thread') and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2.0)
        # Final sync to database
        self._sync_to_database()
    
    def _load_from_database(self):
        """Load active persons from database on startup"""
        try:
            db = SessionLocal()
            try:
                # Load active persons from last 1 hour
                active_persons = db.query(DetectedPerson).filter(
                    DetectedPerson.is_active == True
                ).all()
                
                for dp in active_persons:
                    # Convert database model to in-memory GlobalPerson
                    person = GlobalPerson(
                        global_id=dp.global_id,
                        face_embedding=np.array(dp.face_embedding) if dp.face_embedding else None,
                        name=dp.assigned_name,
                        best_face_quality=dp.face_quality or 0.0,
                        best_face_embedding=np.array(dp.face_embedding) if dp.face_embedding else None
                    )
                    
                    person.first_seen = dp.first_seen.timestamp()
                    person.last_seen = dp.last_seen.timestamp()
                    person.total_appearances = dp.total_appearances
                    person.cameras_visited = set(dp.cameras_visited or [])
                    
                    self.persons[dp.global_id] = person
                    
                    # Update next_global_id
                    if dp.global_id >= self.next_global_id:
                        self.next_global_id = dp.global_id + 1
                
                logger.info(f"📥 Loaded {len(active_persons)} active persons from database")
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to load persons from database: {e}")
    
    def _database_sync_loop(self):
        """Background thread to sync persons to database"""
        while self.running:
            try:
                time.sleep(self.db_sync_interval)
                self._sync_to_database()
            except Exception as e:
                logger.error(f"Error in database sync loop: {e}")
    
    def _sync_to_database(self):
        """Sync in-memory persons to database"""
        with self.lock:
            try:
                db = SessionLocal()
                try:
                    for global_id, person in self.persons.items():
                        # Check if person exists in database
                        dp = db.query(DetectedPerson).filter(
                            DetectedPerson.global_id == global_id
                        ).first()
                        
                        # Calculate average dimensions from positions
                        avg_height = 0.0
                        avg_width = 0.0
                        if person.camera_positions:
                            heights = []
                            widths = []
                            for bbox in person.camera_positions.values():
                                x1, y1, x2, y2 = bbox
                                heights.append(y2 - y1)
                                widths.append(x2 - x1)
                            avg_height = sum(heights) / len(heights) if heights else 0.0
                            avg_width = sum(widths) / len(widths) if widths else 0.0
                        
                        # Prepare current positions for JSON
                        current_positions = {}
                        for cam_id, bbox in person.camera_positions.items():
                            current_positions[str(cam_id)] = {
                                'bbox': list(bbox),
                                'timestamp': datetime.now().isoformat()
                            }
                        
                        if dp:
                            # Update existing record
                            dp.assigned_name = person.name
                            dp.last_seen = datetime.fromtimestamp(person.last_seen)
                            dp.total_appearances = person.total_appearances
                            dp.cameras_visited = list(person.cameras_visited)
                            dp.is_active = person.is_active(self.person_timeout)
                            dp.current_positions = current_positions
                            dp.avg_height_pixels = avg_height
                            dp.avg_width_pixels = avg_width
                            
                            # Update face embedding if better quality
                            if person.face_embedding is not None and person.best_face_quality > (dp.face_quality or 0):
                                dp.face_embedding = person.face_embedding.tolist()
                                dp.face_quality = person.best_face_quality
                        else:
                            # Create new record
                            dp = DetectedPerson(
                                global_id=global_id,
                                assigned_name=person.name,
                                face_embedding=person.face_embedding.tolist() if person.face_embedding is not None else None,
                                face_quality=person.best_face_quality,
                                avg_height_pixels=avg_height,
                                avg_width_pixels=avg_width,
                                first_seen=datetime.fromtimestamp(person.first_seen),
                                last_seen=datetime.fromtimestamp(person.last_seen),
                                total_appearances=person.total_appearances,
                                cameras_visited=list(person.cameras_visited),
                                is_active=person.is_active(self.person_timeout),
                                current_positions=current_positions
                            )
                            db.add(dp)
                    
                    db.commit()
                    logger.debug(f"💾 Synced {len(self.persons)} persons to database")
                    
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Failed to sync persons to database: {e}")


# Global singleton instance
_global_tracker_instance = None


def get_global_person_tracker() -> GlobalPersonTracker:
    """Get singleton global person tracker"""
    global _global_tracker_instance
    if _global_tracker_instance is None:
        _global_tracker_instance = GlobalPersonTracker()
    return _global_tracker_instance
