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
    
    # Physical dimensions (averaged across all sightings)
    avg_height: float = 0.0
    avg_width: float = 0.0
    dimension_samples: List[Tuple[float, float]] = field(default_factory=list)  # [(height, width), ...]
    
    # Appearance features (color-based)
    clothing_color_hist: Optional[np.ndarray] = None  # HSV color histogram of clothing (torso area)
    skin_tone_avg: Optional[np.ndarray] = None  # Average skin tone (face/arms area) in HSV
    color_samples: int = 0  # Number of samples used for color averaging
    
    # Quality metrics (quality now based on bbox size)
    best_face_quality: float = 0.0
    best_face_embedding: Optional[np.ndarray] = None
    
    def update_from_camera(self, camera_id: int, local_track_id: int, 
                          face_embedding: Optional[np.ndarray] = None,
                          face_quality: float = 0.0,
                          bbox: Optional[Tuple[int, int, int, int]] = None,
                          frame: Optional[np.ndarray] = None):
        """Update person state from camera detection"""
        self.camera_tracks[camera_id] = local_track_id
        self.last_seen = time.time()
        self.cameras_visited.add(camera_id)
        self.total_appearances += 1
        
        # Store position from this camera
        if bbox is not None:
            self.camera_positions[camera_id] = bbox
            
            # Update dimensions (rolling average with max 100 samples)
            x1, y1, x2, y2 = bbox
            height = y2 - y1
            width = x2 - x1
            
            self.dimension_samples.append((height, width))
            if len(self.dimension_samples) > 100:
                self.dimension_samples.pop(0)
            
            # Recalculate average dimensions
            if self.dimension_samples:
                self.avg_height = sum(h for h, w in self.dimension_samples) / len(self.dimension_samples)
                self.avg_width = sum(w for h, w in self.dimension_samples) / len(self.dimension_samples)
            
            # Update color features (clothing & skin tone) if frame is provided
            # Only extract color on first detection or periodically (every 10th sample)
            if frame is not None and (self.color_samples == 0 or self.color_samples % 10 == 0):
                self._update_color_features(frame, bbox)
        
        # Update face embedding if quality is better
        if face_embedding is not None and face_quality > self.best_face_quality:
            self.best_face_quality = face_quality
            self.best_face_embedding = face_embedding.copy()
            
            # Update primary embedding if significantly better
            if self.face_embedding is None or face_quality > self.best_face_quality * 0.8:
                self.face_embedding = face_embedding.copy()
    
    def _update_color_features(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]):
        """
        Extract and update clothing color and skin tone features
        Uses HSV color space for robustness to lighting changes
        """
        try:
            import cv2
            
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            
            # Ensure bbox is within frame
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                return
            
            person_crop = frame[y1:y2, x1:x2]
            crop_h, crop_w = person_crop.shape[:2]
            
            if crop_h < 20 or crop_w < 10:  # Too small
                return
            
            # Convert to HSV for better color representation
            hsv_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
            
            # Extract TORSO region (middle 40-70% height, full width) for clothing color
            torso_y1 = int(crop_h * 0.4)
            torso_y2 = int(crop_h * 0.7)
            torso_region = hsv_crop[torso_y1:torso_y2, :]
            
            # Compute color histogram for clothing (16 bins per channel)
            hist_h = cv2.calcHist([torso_region], [0], None, [16], [0, 180])
            hist_s = cv2.calcHist([torso_region], [1], None, [16], [0, 256])
            hist_v = cv2.calcHist([torso_region], [2], None, [16], [0, 256])
            
            # Normalize histograms
            hist_h = cv2.normalize(hist_h, hist_h).flatten()
            hist_s = cv2.normalize(hist_s, hist_s).flatten()
            hist_v = cv2.normalize(hist_v, hist_v).flatten()
            
            # Concatenate into single feature vector (48 dimensions)
            color_hist = np.concatenate([hist_h, hist_s, hist_v])
            
            # Update clothing color with exponential moving average
            if self.clothing_color_hist is None:
                self.clothing_color_hist = color_hist
            else:
                alpha = 0.3  # Weight for new sample
                self.clothing_color_hist = (1 - alpha) * self.clothing_color_hist + alpha * color_hist
            
            # Extract HEAD/NECK region (top 25% height) for skin tone
            skin_y2 = int(crop_h * 0.25)
            skin_region = hsv_crop[:skin_y2, :]
            
            # Average HSV values for skin tone (simple approach)
            skin_mean = np.mean(skin_region, axis=(0, 1))
            
            # Update skin tone with exponential moving average
            if self.skin_tone_avg is None:
                self.skin_tone_avg = skin_mean
            else:
                alpha = 0.3
                self.skin_tone_avg = (1 - alpha) * self.skin_tone_avg + alpha * skin_mean
            
            self.color_samples += 1
            
        except Exception as e:
            logger.debug(f"Error extracting color features: {e}")
    
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
    WITH PRIMARY CAMERA SYSTEM - Camera 10 is the main ID source
    
    Features:
    - OSNet Re-ID for full-body matching across cameras
    - FAISS for fast nearest-neighbor search
    - Spatial matching for overlapping views
    - Database persistence for cross-camera sharing
    - Physical dimensions tracking
    - Automatic sync to database
    - Primary camera (Camera 10) assigns IDs and extracts features
    - Support cameras match against primary camera persons
    """
    
    PRIMARY_CAMERA_ID = 10  # Main camera that assigns IDs
    
    def __init__(self, 
                 face_similarity_threshold: float = 0.5,
                 person_timeout: float = 30.0,
                 cleanup_interval: float = 60.0,
                 db_sync_interval: float = 5.0,
                 primary_camera_id: int = 10):
        """
        Initialize global person tracker
        
        Args:
            face_similarity_threshold: Minimum cosine similarity for Re-ID match (0-1)
            person_timeout: Seconds before removing inactive person
            cleanup_interval: Seconds between cleanup runs
            db_sync_interval: Seconds between database syncs
            primary_camera_id: ID of the primary camera (default: 10)
        """
        self.face_similarity_threshold = face_similarity_threshold
        self.person_timeout = person_timeout
        self.cleanup_interval = cleanup_interval
        self.db_sync_interval = db_sync_interval
        self.PRIMARY_CAMERA_ID = primary_camera_id
        
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
        logger.info(f"   Primary camera: {self.PRIMARY_CAMERA_ID} (assigns IDs)")
        logger.info(f"   Support cameras: All others (match against primary)")
        logger.info(f"   Face threshold: {face_similarity_threshold}, Timeout: {person_timeout}s")
        logger.info(f"   Loaded {len(self.persons)} persons from database")
    
    def match_or_create_person(self,
                               camera_id: int,
                               local_track_id: int,
                               face_embedding: Optional[np.ndarray] = None,
                               face_quality: float = 0.0,
                               bbox: Optional[Tuple[int, int, int, int]] = None,
                               frame: Optional[np.ndarray] = None) -> int:
        """
        Match person to existing global ID or create new one
        
        PRIMARY CAMERA (Camera 10): Assigns IDs and extracts features
        SUPPORT CAMERAS (Others): Match against primary camera persons
        
        Primary Camera Logic:
        1. Check if track already mapped
        2. Always create new person (primary camera is source of truth)
        
        Support Camera Logic:
        1. Check if track already mapped
        2. Try matching against PRIMARY CAMERA persons:
           - Spatial matching (overlapping views)
           - Dimension matching (physical size)
           - Color matching (clothing + skin)
           - Re-ID matching (OSNet embeddings)
        3. Only create new if no primary camera person matches
        
        Args:
            camera_id: Source camera ID
            local_track_id: Local tracking ID from this camera
            face_embedding: 512-dim Re-ID embedding (if available)
            face_quality: Embedding quality score
            bbox: Person bounding box (for spatial + dimension matching)
            frame: Full camera frame (for color feature extraction)
        
        Returns:
            global_id: Unique person ID across all cameras
        """
        with self.lock:
            # Check if this camera track is already mapped
            key = (camera_id, local_track_id)
            if key in self.camera_track_to_global:
                global_id = self.camera_track_to_global[key]
                
                # Update existing person (may now have embedding)
                if global_id in self.persons:
                    person = self.persons[global_id]
                    
                    # If we now have an embedding, update it and add to FAISS
                    if face_embedding is not None and person.face_embedding is None:
                        person.face_embedding = face_embedding.copy()
                        person.best_face_quality = face_quality
                        person.best_face_embedding = face_embedding.copy()
                        
                        # Add to FAISS for future fast matching
                        from services.faiss_index_service import get_faiss_service
                        faiss = get_faiss_service()
                        if faiss.is_available():
                            faiss.add_embedding(global_id, face_embedding)
                            logger.debug(f"📊 Added embedding to FAISS for Global ID {global_id}")
                    
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                    return global_id
            
            # ========================================================================
            # PRIMARY CAMERA: Check existing persons first, then create if needed
            # ========================================================================
            if camera_id == self.PRIMARY_CAMERA_ID:
                # Try to match against existing persons from primary camera
                # (person might have left and returned with new local track ID)
                primary_persons = {
                    gid: person for gid, person in self.persons.items()
                    if self.PRIMARY_CAMERA_ID in person.cameras_visited
                }
                
                if primary_persons:
                    # Try matching by Re-ID (most reliable)
                    if face_embedding is not None:
                        face_match = self._find_best_face_match_from_primary(face_embedding, camera_id, primary_persons)
                        if face_match:
                            global_id = face_match
                            person = self.persons[global_id]
                            person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                            self.camera_track_to_global[key] = global_id
                            logger.info(f"🔄 PRIMARY Camera {camera_id}: Re-identified returning person → Global ID {global_id} (track {local_track_id})")
                            return global_id
                    
                    # Try matching by dimensions
                    if bbox is not None:
                        dimension_match = self._find_best_dimension_match_from_primary(bbox, camera_id, primary_persons)
                        if dimension_match:
                            global_id = dimension_match
                            person = self.persons[global_id]
                            person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                            self.camera_track_to_global[key] = global_id
                            logger.info(f"🔄 PRIMARY Camera {camera_id}: Re-identified returning person by dimensions → Global ID {global_id} (track {local_track_id})")
                            return global_id
                    
                    # Try matching by color
                    if frame is not None and bbox is not None:
                        color_match = self._find_best_color_match_from_primary(frame, bbox, camera_id, primary_persons)
                        if color_match:
                            global_id = color_match
                            person = self.persons[global_id]
                            person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                            self.camera_track_to_global[key] = global_id
                            logger.info(f"🔄 PRIMARY Camera {camera_id}: Re-identified returning person by color → Global ID {global_id} (track {local_track_id})")
                            return global_id
                
                # No match found - create new person
                global_id = self._create_new_person(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                logger.info(f"🎯 PRIMARY Camera {camera_id}: New person Global ID {global_id} (track {local_track_id})")
                return global_id
            
            # ========================================================================
            # SUPPORT CAMERAS: Match against PRIMARY CAMERA persons
            # ========================================================================
            logger.debug(f"📡 Support Camera {camera_id}: Searching for match against primary camera persons...")
            
            # Only match against persons that were seen on the PRIMARY CAMERA
            primary_persons = {
                gid: person for gid, person in self.persons.items()
                if self.PRIMARY_CAMERA_ID in person.cameras_visited
            }
            
            logger.debug(f"📊 Support Camera {camera_id}: Found {len(primary_persons)} persons from primary camera (out of {len(self.persons)} total)")
            
            if not primary_persons:
                logger.warning(f"⚠️  Support Camera {camera_id}: No persons from primary camera yet!")
                # Don't create new person on support camera - wait for primary
                return None
            
            # PRIORITY 1: Try SPATIAL matching (overlapping views with primary camera)
            if bbox is not None:
                spatial_match = self._find_best_spatial_match_from_primary(bbox, camera_id, primary_persons)
                
                if spatial_match:
                    global_id = spatial_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Support Camera {camera_id}: Spatial match → Global ID {global_id} (track {local_track_id})")
                    return global_id
            
            # PRIORITY 2: Try DIMENSION matching (physical size from primary camera)
            if bbox is not None:
                dimension_match = self._find_best_dimension_match_from_primary(bbox, camera_id, primary_persons)
                
                if dimension_match:
                    global_id = dimension_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Support Camera {camera_id}: Dimension match → Global ID {global_id} (track {local_track_id})")
                    return global_id
            
            # PRIORITY 3: Try COLOR matching (clothing + skin from primary camera)
            if bbox is not None and frame is not None:
                color_match = self._find_best_color_match_from_primary(frame, bbox, camera_id, primary_persons)
                
                if color_match:
                    global_id = color_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Support Camera {camera_id}: Color match → Global ID {global_id} (track {local_track_id})")
                    return global_id
            
            # PRIORITY 4: Try Re-ID matching (OSNet embeddings from primary camera)
            if face_embedding is not None:
                face_match = self._find_best_face_match_from_primary(face_embedding, camera_id, primary_persons)
                
                if face_match:
                    global_id = face_match
                    person = self.persons[global_id]
                    person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
                    self.camera_track_to_global[key] = global_id
                    
                    logger.info(f"✅ Support Camera {camera_id}: Re-ID match → Global ID {global_id} (track {local_track_id})")
                    return global_id
            
            # No match found on support camera - DON'T create new person
            # Only primary camera creates persons
            logger.warning(f"⚠️  Support Camera {camera_id}: No match found for track {local_track_id} (waiting for primary camera)")
            return None
            logger.info(f"🆕 New person: Global ID {global_id} on camera {camera_id} (track {local_track_id})")
            return global_id
    
    def _find_best_face_match(self, query_embedding: np.ndarray, camera_id: int) -> Optional[int]:
        """
        Find best matching person by Re-ID embedding similarity
        Uses FAISS for fast search, falls back to database if needed
        
        Args:
            query_embedding: Re-ID embedding to match
            camera_id: Source camera (for spatial filtering)
        
        Returns:
            global_id of best match, or None
        """
        best_match_id = None
        best_similarity = self.face_similarity_threshold
        
        # Build embeddings dict for FAISS fallback
        embeddings_dict = {}
        for global_id, person in self.persons.items():
            if not person.is_active(self.person_timeout):
                continue
            if person.face_embedding is not None:
                embeddings_dict[global_id] = person.face_embedding
        
        # Use FAISS search with fallback to brute-force
        matches = self.faiss_service.search_with_fallback(
            query_embedding=query_embedding,
            embeddings_dict=embeddings_dict,
            k=5,
            threshold=self.face_similarity_threshold
        )
        
        if matches:
            for global_id, similarity in matches:
                person = self.persons.get(global_id)
                if person is None:
                    continue
                
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
                    # Query database for persons with Re-ID embeddings
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
        
        This is the PRIMARY matching method for first 3 frames (before Re-ID embedding available)
        
        Args:
            bbox: Person bounding box [x1, y1, x2, y2]
            camera_id: Source camera ID
        
        Returns:
            global_id of best match, or None
        """
        best_match_id = None
        best_iou = 0.25  # Reduced threshold for more lenient matching (was 0.3)
        
        current_time = time.time()
        
        for global_id, person in self.persons.items():
            # Only match active persons
            if not person.is_active(self.person_timeout):
                continue
            
            # Check if person is currently visible on ANY other camera
            if not person.camera_positions:
                continue
            
            # BEST PRACTICE: Skip if person is already tracked on THIS camera
            # (ByteTrack should handle same-camera tracking)
            if camera_id in person.camera_positions:
                continue
            
            # Extended time window for spatial matching (3 seconds instead of 2)
            # Allows for slight delays in camera processing
            time_since_seen = current_time - person.last_seen
            if time_since_seen > 3.0:
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
    
    def _find_best_dimension_match(self, bbox: Tuple[int, int, int, int], camera_id: int) -> Optional[int]:
        """
        Find best matching person by physical dimensions (height/width similarity)
        
        When person appears after being out of view, physical dimensions help re-identify them.
        Useful when embeddings haven't been extracted yet or spatial overlap isn't available.
        
        Args:
            bbox: Person bounding box [x1, y1, x2, y2]
            camera_id: Source camera ID
        
        Returns:
            global_id of best match, or None
        """
        x1, y1, x2, y2 = bbox
        query_height = y2 - y1
        query_width = x2 - x1
        
        best_match_id = None
        best_similarity = 0.80  # 80% similarity threshold (tolerant to camera angle differences)
        
        for global_id, person in self.persons.items():
            # Skip persons without dimension history
            if person.avg_height == 0 or person.avg_width == 0:
                continue
            
            # BEST PRACTICE: Only skip if person is CURRENTLY ACTIVE on this camera
            # Don't block historical matches - person may have left and returned
            if camera_id in person.camera_positions:
                continue
            
            # Calculate dimension similarity (1 - normalized difference)
            height_diff = abs(query_height - person.avg_height) / max(query_height, person.avg_height)
            width_diff = abs(query_width - person.avg_width) / max(query_width, person.avg_width)
            
            # Combined similarity (average of height and width similarity)
            height_similarity = 1.0 - height_diff
            width_similarity = 1.0 - width_diff
            combined_similarity = (height_similarity + width_similarity) / 2.0
            
            if combined_similarity > best_similarity:
                best_similarity = combined_similarity
                best_match_id = global_id
        
        if best_match_id:
            person = self.persons[best_match_id]
            logger.debug(f"Dimension match: Global ID {best_match_id} (similarity={best_similarity:.2f}, "
                        f"query={query_height:.0f}x{query_width:.0f}px, "
                        f"stored={person.avg_height:.0f}x{person.avg_width:.0f}px)")
        
        return best_match_id
    
    def _find_best_color_match(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], camera_id: int) -> Optional[int]:
        """
        Find best matching person by appearance (clothing color + skin tone)
        
        Extracts color features from the query detection and compares against
        stored color histograms. Useful when Re-ID embeddings aren't available yet.
        
        Args:
            frame: Full camera frame
            bbox: Person bounding box [x1, y1, x2, y2]
            camera_id: Source camera ID
        
        Returns:
            global_id of best match, or None
        """
        try:
            import cv2
            
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            
            # Ensure bbox is within frame
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            person_crop = frame[y1:y2, x1:x2]
            crop_h, crop_w = person_crop.shape[:2]
            
            if crop_h < 20 or crop_w < 10:
                return None
            
            # Convert to HSV
            hsv_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
            
            # Extract torso for clothing color
            torso_y1 = int(crop_h * 0.4)
            torso_y2 = int(crop_h * 0.7)
            torso_region = hsv_crop[torso_y1:torso_y2, :]
            
            # Compute color histogram
            hist_h = cv2.calcHist([torso_region], [0], None, [16], [0, 180])
            hist_s = cv2.calcHist([torso_region], [1], None, [16], [0, 256])
            hist_v = cv2.calcHist([torso_region], [2], None, [16], [0, 256])
            
            hist_h = cv2.normalize(hist_h, hist_h).flatten()
            hist_s = cv2.normalize(hist_s, hist_s).flatten()
            hist_v = cv2.normalize(hist_v, hist_v).flatten()
            
            query_color_hist = np.concatenate([hist_h, hist_s, hist_v])
            
            # Extract head/neck for skin tone
            skin_y2 = int(crop_h * 0.25)
            skin_region = hsv_crop[:skin_y2, :]
            query_skin_tone = np.mean(skin_region, axis=(0, 1))
            
            # Find best match
            best_match_id = None
            best_similarity = 0.70  # 70% threshold for color matching
            
            for global_id, person in self.persons.items():
                # Skip persons without color features
                if person.clothing_color_hist is None or person.skin_tone_avg is None:
                    continue
                
                # Skip if currently active on this camera
                if camera_id in person.camera_positions:
                    continue
                
                # Only match active persons
                if not person.is_active(self.person_timeout):
                    continue
                
                # Compare clothing color (histogram correlation)
                color_similarity = cv2.compareHist(
                    query_color_hist.reshape(-1, 1).astype(np.float32),
                    person.clothing_color_hist.reshape(-1, 1).astype(np.float32),
                    cv2.HISTCMP_CORREL  # Returns 1 for perfect match, -1 for opposite
                )
                color_similarity = (color_similarity + 1) / 2  # Normalize to [0, 1]
                
                # Compare skin tone (Euclidean distance in HSV)
                skin_diff = np.linalg.norm(query_skin_tone - person.skin_tone_avg)
                skin_similarity = 1.0 / (1.0 + skin_diff / 50.0)  # Normalize with decay
                
                # Combined similarity (60% clothing, 40% skin tone)
                combined_similarity = 0.6 * color_similarity + 0.4 * skin_similarity
                
                if combined_similarity > best_similarity:
                    best_similarity = combined_similarity
                    best_match_id = global_id
            
            if best_match_id:
                logger.debug(f"Color match: Global ID {best_match_id} (similarity={best_similarity:.2f})")
            
            return best_match_id
            
        except Exception as e:
            logger.debug(f"Error in color matching: {e}")
            return None
    
    # ========================================================================
    # PRIMARY CAMERA MATCHING METHODS (for support cameras)
    # ========================================================================
    
    def _find_best_spatial_match_from_primary(self, bbox: Tuple[int, int, int, int], 
                                              camera_id: int,
                                              primary_persons: Dict[int, GlobalPerson]) -> Optional[int]:
        """
        Find spatial match from primary camera persons only
        Support cameras match against persons currently visible on primary camera
        """
        best_match_id = None
        best_iou = 0.25
        current_time = time.time()
        
        for global_id, person in primary_persons.items():
            if not person.is_active(self.person_timeout):
                continue
            
            if camera_id in person.camera_positions:
                continue
            
            if not person.camera_positions:
                continue
            
            time_since_seen = current_time - person.last_seen
            if time_since_seen > 3.0:
                continue
            
            for other_camera_id, other_bbox in person.camera_positions.items():
                if other_camera_id == camera_id:
                    continue
                
                iou = self._calculate_iou(bbox, other_bbox)
                
                if iou > best_iou:
                    best_iou = iou
                    best_match_id = global_id
        
        if best_match_id:
            logger.debug(f"Primary spatial match: Global ID {best_match_id} (IoU={best_iou:.3f})")
        
        return best_match_id
    
    def _find_best_dimension_match_from_primary(self, bbox: Tuple[int, int, int, int],
                                                camera_id: int,
                                                primary_persons: Dict[int, GlobalPerson]) -> Optional[int]:
        """
        Find dimension match from primary camera persons only
        """
        x1, y1, x2, y2 = bbox
        query_height = y2 - y1
        query_width = x2 - x1
        
        best_match_id = None
        best_similarity = 0.80
        
        for global_id, person in primary_persons.items():
            if person.avg_height == 0 or person.avg_width == 0:
                continue
            
            if camera_id in person.camera_positions:
                continue
            
            height_diff = abs(query_height - person.avg_height) / max(query_height, person.avg_height)
            width_diff = abs(query_width - person.avg_width) / max(query_width, person.avg_width)
            
            height_similarity = 1.0 - height_diff
            width_similarity = 1.0 - width_diff
            combined_similarity = (height_similarity + width_similarity) / 2.0
            
            if combined_similarity > best_similarity:
                best_similarity = combined_similarity
                best_match_id = global_id
        
        if best_match_id:
            person = primary_persons[best_match_id]
            logger.debug(f"Primary dimension match: Global ID {best_match_id} (similarity={best_similarity:.2f})")
        
        return best_match_id
    
    def _find_best_color_match_from_primary(self, frame: np.ndarray, bbox: Tuple[int, int, int, int],
                                           camera_id: int,
                                           primary_persons: Dict[int, GlobalPerson]) -> Optional[int]:
        """
        Find color match from primary camera persons only
        """
        try:
            import cv2
            
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            person_crop = frame[y1:y2, x1:x2]
            crop_h, crop_w = person_crop.shape[:2]
            
            if crop_h < 20 or crop_w < 10:
                return None
            
            hsv_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
            
            torso_y1 = int(crop_h * 0.4)
            torso_y2 = int(crop_h * 0.7)
            torso_region = hsv_crop[torso_y1:torso_y2, :]
            
            hist_h = cv2.calcHist([torso_region], [0], None, [16], [0, 180])
            hist_s = cv2.calcHist([torso_region], [1], None, [16], [0, 256])
            hist_v = cv2.calcHist([torso_region], [2], None, [16], [0, 256])
            
            hist_h = cv2.normalize(hist_h, hist_h).flatten()
            hist_s = cv2.normalize(hist_s, hist_s).flatten()
            hist_v = cv2.normalize(hist_v, hist_v).flatten()
            
            query_color_hist = np.concatenate([hist_h, hist_s, hist_v])
            
            skin_y2 = int(crop_h * 0.25)
            skin_region = hsv_crop[:skin_y2, :]
            query_skin_tone = np.mean(skin_region, axis=(0, 1))
            
            best_match_id = None
            best_similarity = 0.70
            
            for global_id, person in primary_persons.items():
                if person.clothing_color_hist is None or person.skin_tone_avg is None:
                    continue
                
                if camera_id in person.camera_positions:
                    continue
                
                if not person.is_active(self.person_timeout):
                    continue
                
                color_similarity = cv2.compareHist(
                    query_color_hist.reshape(-1, 1).astype(np.float32),
                    person.clothing_color_hist.reshape(-1, 1).astype(np.float32),
                    cv2.HISTCMP_CORREL
                )
                color_similarity = (color_similarity + 1) / 2
                
                skin_diff = np.linalg.norm(query_skin_tone - person.skin_tone_avg)
                skin_similarity = 1.0 / (1.0 + skin_diff / 50.0)
                
                combined_similarity = 0.6 * color_similarity + 0.4 * skin_similarity
                
                if combined_similarity > best_similarity:
                    best_similarity = combined_similarity
                    best_match_id = global_id
            
            if best_match_id:
                logger.debug(f"Primary color match: Global ID {best_match_id} (similarity={best_similarity:.2f})")
            
            return best_match_id
            
        except Exception as e:
            logger.debug(f"Error in primary color matching: {e}")
            return None
    
    def _find_best_face_match_from_primary(self, query_embedding: np.ndarray,
                                          camera_id: int,
                                          primary_persons: Dict[int, GlobalPerson]) -> Optional[int]:
        """
        Find Re-ID match from primary camera persons only
        """
        best_match_id = None
        best_similarity = self.face_similarity_threshold
        
        embeddings_dict = {}
        for global_id, person in primary_persons.items():
            if not person.is_active(self.person_timeout):
                continue
            if person.face_embedding is not None:
                embeddings_dict[global_id] = person.face_embedding
        
        matches = self.faiss_service.search_with_fallback(
            query_embedding=query_embedding,
            embeddings_dict=embeddings_dict,
            k=5,
            threshold=self.face_similarity_threshold
        )
        
        if matches:
            for global_id, similarity in matches:
                person = primary_persons.get(global_id)
                if person is None:
                    continue
                
                if camera_id in person.cameras_visited:
                    time_since_seen = time.time() - person.last_seen
                    if time_since_seen < 5.0:
                        similarity *= 1.1
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_id = global_id
        
        if best_match_id:
            logger.debug(f"Primary Re-ID match: Global ID {best_match_id} (similarity={best_similarity:.3f})")
        
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
                          bbox: Optional[Tuple[int, int, int, int]] = None,
                          frame: Optional[np.ndarray] = None) -> int:
        """Create a new global person entry"""
        global_id = self.next_global_id
        self.next_global_id += 1
        
        person = GlobalPerson(
            global_id=global_id,
            face_embedding=face_embedding.copy() if face_embedding is not None else None,
            best_face_quality=face_quality,
            best_face_embedding=face_embedding.copy() if face_embedding is not None else None
        )
        
        person.update_from_camera(camera_id, local_track_id, face_embedding, face_quality, bbox, frame)
        
        self.persons[global_id] = person
        self.camera_track_to_global[(camera_id, local_track_id)] = global_id
        
        # Add embedding to FAISS index for fast future searches
        if face_embedding is not None and self.faiss_service.is_available():
            self.faiss_service.add_embedding(global_id, face_embedding)
        
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
                    face_emb = None
                    if dp.face_embedding is not None:
                        try:
                            face_emb = np.array(dp.face_embedding)
                        except:
                            pass
                    
                    person = GlobalPerson(
                        global_id=dp.global_id,
                        face_embedding=face_emb,
                        name=dp.assigned_name,
                        best_face_quality=dp.face_quality or 0.0,
                        best_face_embedding=face_emb
                    )
                    
                    person.first_seen = dp.first_seen.timestamp()
                    person.last_seen = dp.last_seen.timestamp()
                    person.total_appearances = dp.total_appearances
                    person.cameras_visited = set(dp.cameras_visited or [])
                    
                    # Restore physical dimensions from database
                    if dp.avg_height_pixels and dp.avg_width_pixels:
                        person.avg_height = dp.avg_height_pixels
                        person.avg_width = dp.avg_width_pixels
                        # Initialize with one sample so system knows dimensions are available
                        person.dimension_samples = [(dp.avg_height_pixels, dp.avg_width_pixels)]
                    
                    self.persons[dp.global_id] = person
                    
                    # Add embedding to FAISS index
                    if face_emb is not None and self.faiss_service.is_available():
                        self.faiss_service.add_embedding(dp.global_id, face_emb)
                    
                    # Update next_global_id
                    if dp.global_id >= self.next_global_id:
                        self.next_global_id = dp.global_id + 1
                
                logger.info(f"📥 Loaded {len(active_persons)} active persons from database")
                if self.faiss_service.is_available():
                    stats = self.faiss_service.get_stats()
                    logger.info(f"🔍 FAISS index initialized with {stats['total_embeddings']} embeddings")
                
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
