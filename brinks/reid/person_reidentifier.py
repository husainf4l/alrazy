"""
Person Re-Identification Module
Persistent person labeling with embedding-based recognition and re-ID tracking
"""

import json
import time
import hashlib
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class PersonEmbedding:
    """Represents a person's embedding"""
    person_id: str
    label: str
    embedding: np.ndarray
    confidence: float
    timestamp: float
    camera_id: str
    bbox: List[int]  # [x1, y1, x2, y2]


@dataclass
class Person:
    """Represents a known person in the system"""
    person_id: str
    label: str
    first_seen: float
    last_seen: float
    embeddings: List[Dict]  # Serializable version
    visit_count: int
    cameras: List[str]  # Which cameras detected them
    confidence_scores: List[float]


class PersonEmbeddingExtractor:
    """
    Extract appearance embeddings from person patches
    Uses multiple methods: HOG, color histograms, deep features
    """
    
    def __init__(self, model_type: str = "lightweight"):
        """
        Initialize embedding extractor
        
        Args:
            model_type: 'lightweight' (HOG+color) or 'heavy' (if using external models)
        """
        self.model_type = model_type
        self.feature_dim = 512
    
    def extract_features(self, patch: np.ndarray) -> np.ndarray:
        """
        Extract appearance features from person patch
        
        Args:
            patch: BGR image patch
        
        Returns:
            512-dim feature vector
        """
        features = []
        
        # 1. Color histogram features
        color_features = self._extract_color_features(patch)
        features.append(color_features)
        
        # 2. Spatial features (HOG-like)
        spatial_features = self._extract_spatial_features(patch)
        features.append(spatial_features)
        
        # 3. Texture features
        texture_features = self._extract_texture_features(patch)
        features.append(texture_features)
        
        # Concatenate and normalize
        all_features = np.concatenate(features)
        
        # Pad or trim to 512 dimensions
        if len(all_features) < self.feature_dim:
            all_features = np.pad(all_features, (0, self.feature_dim - len(all_features)))
        else:
            all_features = all_features[:self.feature_dim]
        
        # L2 normalize
        norm = np.linalg.norm(all_features)
        if norm > 0:
            all_features = all_features / norm
        
        return all_features.astype(np.float32)
    
    @staticmethod
    def _extract_color_features(patch: np.ndarray) -> np.ndarray:
        """Extract color histogram features"""
        if patch.size == 0:
            return np.zeros(48, dtype=np.float32)
        
        # Resize for consistent feature size
        patch_resized = cv2.resize(patch, (64, 128))
        
        # Color histograms per channel (16 bins each)
        hist_b = cv2.calcHist([patch_resized[:, :, 0]], [0], None, [16], [0, 256]).flatten()
        hist_g = cv2.calcHist([patch_resized[:, :, 1]], [0], None, [16], [0, 256]).flatten()
        hist_r = cv2.calcHist([patch_resized[:, :, 2]], [0], None, [16], [0, 256]).flatten()
        
        # Normalize
        features = np.concatenate([hist_b, hist_g, hist_r]).astype(np.float32)
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
        
        return features
    
    @staticmethod
    def _extract_spatial_features(patch: np.ndarray) -> np.ndarray:
        """Extract spatial/shape features"""
        if patch.size == 0:
            return np.zeros(128, dtype=np.float32)
        
        patch_resized = cv2.resize(patch, (64, 128))
        gray = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2GRAY)
        
        # Edges using Canny
        edges = cv2.Canny(gray, 50, 150)
        
        # Divide into 8x8 grid and compute edge density
        h, w = edges.shape
        cell_h, cell_w = h // 8, w // 8
        features = []
        
        for i in range(8):
            for j in range(8):
                cell = edges[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                density = np.sum(cell) / (cell_h * cell_w + 1e-6)
                features.append(density)
        
        return np.array(features, dtype=np.float32)
    
    @staticmethod
    def _extract_texture_features(patch: np.ndarray) -> np.ndarray:
        """Extract texture features"""
        if patch.size == 0:
            return np.zeros(128, dtype=np.float32)
        
        patch_resized = cv2.resize(patch, (64, 128))
        gray = cv2.cvtColor(patch_resized, cv2.COLOR_BGR2GRAY)
        
        # Local Binary Pattern (LBP) approximation using Gaussian
        features = []
        
        # Apply Gaussian blur and compute gradients
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx**2 + gy**2)
        
        # Compute orientation histogram
        angle = np.arctan2(gy, gx)
        angle_bins = np.histogram(angle.flatten(), bins=9, range=(-np.pi, np.pi))[0]
        
        # Magnitude histogram
        mag_bins = np.histogram(magnitude.flatten(), bins=9, range=(0, 256))[0]
        
        features = np.concatenate([angle_bins, mag_bins]).astype(np.float32)
        
        # Pad to 128
        if len(features) < 128:
            features = np.pad(features, (0, 128 - len(features)))
        
        return features[:128]


class PersonReIdentifier:
    """
    Re-identify persons across time and cameras
    Maintains person gallery and matches new detections
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.6,
        embedding_extractor: Optional[PersonEmbeddingExtractor] = None
    ):
        """
        Initialize re-identifier
        
        Args:
            similarity_threshold: Minimum similarity to match persons (0-1)
            embedding_extractor: Custom extractor, or None to create default
        """
        self.similarity_threshold = similarity_threshold
        self.extractor = embedding_extractor or PersonEmbeddingExtractor()
        
        # Gallery: person_id -> list of embeddings
        self.gallery: Dict[str, List[PersonEmbedding]] = {}
        
        # Person info: person_id -> Person
        self.persons: Dict[str, Person] = {}
        
        # Counter for generating person IDs
        self.person_counter = 0
        self.next_label_id = 0
        
        logger.info("PersonReIdentifier initialized")
    
    def get_next_label(self) -> str:
        """Generate next person label (Visitor-A, Visitor-B, etc.)"""
        label = f"Visitor-{chr(65 + (self.next_label_id % 26))}"
        if self.next_label_id >= 26:
            label += f"-{self.next_label_id // 26}"
        self.next_label_id += 1
        return label
    
    def extract_person_embedding(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        """
        Extract embedding from person bounding box
        
        Args:
            frame: BGR image
            bbox: [x1, y1, x2, y2]
        
        Returns:
            512-dim embedding or None
        """
        try:
            x1, y1, x2, y2 = bbox
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            patch = frame[y1:y2, x1:x2]
            
            if patch.size == 0:
                return None
            
            embedding = self.extractor.extract_features(patch)
            return embedding
        
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute similarity between two embeddings (cosine)
        
        Args:
            embedding1: First 512-dim vector
            embedding2: Second 512-dim vector
        
        Returns:
            Similarity score (0-1)
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Ensure 1D
        e1 = embedding1.flatten()
        e2 = embedding2.flatten()
        
        # Cosine similarity
        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(e1, e2) / (norm1 * norm2)
        return float(np.clip(similarity, 0, 1))
    
    def match_person(
        self,
        embedding: np.ndarray,
        camera_id: str,
        bbox: List[int],
        min_matches: int = 1
    ) -> Tuple[Optional[str], float]:
        """
        Match embedding against gallery
        
        Args:
            embedding: Person embedding
            camera_id: Which camera detected
            bbox: Bounding box [x1, y1, x2, y2]
            min_matches: Require this many high-confidence matches
        
        Returns:
            Tuple of (person_id, confidence) or (None, 0.0)
        """
        if not self.gallery:
            return None, 0.0
        
        best_person_id = None
        best_similarity = 0.0
        match_count = 0
        
        # Compare with all gallery embeddings
        for person_id, embeddings_list in self.gallery.items():
            similarities = []
            
            for person_emb in embeddings_list:
                sim = self.compute_similarity(embedding, person_emb.embedding)
                similarities.append(sim)
            
            if similarities:
                max_sim = max(similarities)
                avg_sim = np.mean(similarities)
                
                # Track if meets threshold
                if max_sim >= self.similarity_threshold:
                    match_count += 1
                    
                    # Use weighted average (prefer recent matches)
                    time_weight = min(1.0, 1.0 - (time.time() - person_emb.timestamp) / 86400)
                    weighted_sim = max_sim * 0.7 + avg_sim * 0.3
                    
                    if weighted_sim > best_similarity:
                        best_similarity = weighted_sim
                        best_person_id = person_id
        
        # Return match if enough matches
        if match_count >= min_matches and best_person_id:
            return best_person_id, best_similarity
        
        return None, 0.0
    
    def register_person(
        self,
        embedding: np.ndarray,
        frame: np.ndarray,
        bbox: List[int],
        camera_id: str,
        label: Optional[str] = None
    ) -> str:
        """
        Register new person in gallery
        
        Args:
            embedding: Person embedding
            frame: Original frame
            bbox: Bounding box
            camera_id: Source camera
            label: Optional custom label
        
        Returns:
            person_id
        """
        person_id = f"person_{int(time.time() * 1000)}_{self.person_counter}"
        self.person_counter += 1
        
        if label is None:
            label = self.get_next_label()
        
        # Create embedding record
        person_emb = PersonEmbedding(
            person_id=person_id,
            label=label,
            embedding=embedding,
            confidence=0.95,
            timestamp=time.time(),
            camera_id=camera_id,
            bbox=bbox
        )
        
        # Add to gallery
        self.gallery[person_id] = [person_emb]
        
        # Create person record
        self.persons[person_id] = Person(
            person_id=person_id,
            label=label,
            first_seen=time.time(),
            last_seen=time.time(),
            embeddings=[self._serialize_embedding(person_emb)],
            visit_count=1,
            cameras=[camera_id],
            confidence_scores=[0.95]
        )
        
        logger.info(f"Registered new person: {label} ({person_id})")
        return person_id
    
    def update_person(
        self,
        person_id: str,
        embedding: np.ndarray,
        frame: np.ndarray,
        bbox: List[int],
        camera_id: str,
        confidence: float = 0.95
    ) -> bool:
        """
        Update person with new detection
        
        Args:
            person_id: Person to update
            embedding: New embedding
            frame: Frame
            bbox: New bounding box
            camera_id: Source camera
            confidence: Detection confidence
        
        Returns:
            True if successful
        """
        if person_id not in self.gallery:
            return False
        
        try:
            # Add embedding to gallery (keep last 10)
            person_emb = PersonEmbedding(
                person_id=person_id,
                label=self.persons[person_id].label,
                embedding=embedding,
                confidence=confidence,
                timestamp=time.time(),
                camera_id=camera_id,
                bbox=bbox
            )
            
            self.gallery[person_id].append(person_emb)
            self.gallery[person_id] = self.gallery[person_id][-10:]
            
            # Update person record
            person = self.persons[person_id]
            person.last_seen = time.time()
            person.embeddings.append(self._serialize_embedding(person_emb))
            person.embeddings = person.embeddings[-10:]
            person.confidence_scores.append(confidence)
            person.confidence_scores = person.confidence_scores[-10:]
            
            if camera_id not in person.cameras:
                person.cameras.append(camera_id)
            
            # Increment visit count if gap > 5 minutes
            time_since_last = time.time() - person.first_seen
            if time_since_last > 300:  # 5 minutes
                person.visit_count += 1
            
            logger.debug(f"Updated person {person.label}: confidence={confidence:.2f}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update person: {e}")
            return False
    
    @staticmethod
    def _serialize_embedding(person_emb: PersonEmbedding) -> Dict:
        """Convert embedding to JSON-serializable format"""
        return {
            "timestamp": person_emb.timestamp,
            "camera_id": person_emb.camera_id,
            "confidence": person_emb.confidence,
            "bbox": person_emb.bbox
        }
    
    def get_person_info(self, person_id: str) -> Optional[Dict]:
        """Get person information"""
        if person_id not in self.persons:
            return None
        
        person = self.persons[person_id]
        return {
            "person_id": person.person_id,
            "label": person.label,
            "first_seen": person.first_seen,
            "last_seen": person.last_seen,
            "visit_count": person.visit_count,
            "cameras": person.cameras,
            "avg_confidence": float(np.mean(person.confidence_scores)) if person.confidence_scores else 0.0,
            "num_embeddings": len(person.embeddings)
        }
    
    def list_persons(self) -> List[Dict]:
        """List all known persons"""
        return [self.get_person_info(pid) for pid in self.persons.keys()]
    
    def merge_persons(self, person_id1: str, person_id2: str) -> bool:
        """Merge two persons (keep ID1 label, combine embeddings)"""
        if person_id1 not in self.persons or person_id2 not in self.persons:
            return False
        
        try:
            # Merge embeddings
            self.gallery[person_id1].extend(self.gallery[person_id2])
            self.gallery[person_id1] = self.gallery[person_id1][-20:]  # Keep last 20
            
            # Update person info
            p1 = self.persons[person_id1]
            p2 = self.persons[person_id2]
            
            p1.first_seen = min(p1.first_seen, p2.first_seen)
            p1.last_seen = max(p1.last_seen, p2.last_seen)
            p1.visit_count += p2.visit_count
            p1.embeddings.extend(p2.embeddings)
            p1.embeddings = p1.embeddings[-20:]
            p1.confidence_scores.extend(p2.confidence_scores)
            p1.confidence_scores = p1.confidence_scores[-20:]
            
            for cam in p2.cameras:
                if cam not in p1.cameras:
                    p1.cameras.append(cam)
            
            # Remove person 2
            del self.gallery[person_id2]
            del self.persons[person_id2]
            
            logger.info(f"Merged {person_id2} into {person_id1}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to merge persons: {e}")
            return False
    
    def reset(self):
        """Reset all persons"""
        self.gallery.clear()
        self.persons.clear()
        self.person_counter = 0
        self.next_label_id = 0
        logger.info("Re-ID gallery reset")
    
    def get_stats(self) -> Dict:
        """Get re-ID statistics"""
        if not self.persons:
            return {
                "total_persons": 0,
                "total_embeddings": 0,
                "avg_visits": 0,
                "cameras": []
            }
        
        embeddings_count = sum(len(embs) for embs in self.gallery.values())
        visits = [p.visit_count for p in self.persons.values()]
        cameras = set()
        for p in self.persons.values():
            cameras.update(p.cameras)
        
        return {
            "total_persons": len(self.persons),
            "total_embeddings": embeddings_count,
            "avg_visits": float(np.mean(visits)) if visits else 0,
            "cameras": list(cameras)
        }
