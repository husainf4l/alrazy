"""
Face Matching & Recognition Service
Compares new face embeddings against database to identify same persons
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from scipy.spatial.distance import cosine
import logging
from app.models.database import SessionLocal, FacePerson

logger = logging.getLogger(__name__)


class FaceMatchingService:
    """
    Matches newly detected faces against database
    Uses cosine similarity for embedding comparison
    """
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize face matching service
        
        similarity_threshold: Cosine similarity threshold (0-1)
                             Higher = stricter matching
                             0.6 = good balance (60% similar = match)
        """
        self.threshold = similarity_threshold
        self.db_session = SessionLocal
        logger.info(f"✅ FaceMatchingService initialized (threshold: {similarity_threshold})")
    
    def get_database_faces(self) -> List[FacePerson]:
        """
        Retrieve all faces from database
        Returns list of FacePerson records with embeddings
        """
        try:
            db = self.db_session()
            faces = db.query(FacePerson).all()
            db.close()
            return faces
        except Exception as e:
            logger.error(f"❌ Error retrieving faces from database: {str(e)}")
            return []
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        Returns value between 0 (different) and 1 (identical)
        
        Formula: similarity = 1 - cosine_distance
        """
        try:
            if not embedding1 or not embedding2:
                return 0.0
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)
            
            # Normalize embeddings (ArcFace outputs are already normalized)
            vec1 = vec1 / (np.linalg.norm(vec1) + 1e-8)
            vec2 = vec2 / (np.linalg.norm(vec2) + 1e-8)
            
            # Calculate cosine distance and convert to similarity
            distance = cosine(vec1, vec2)
            similarity = 1 - distance  # Convert distance to similarity
            
            return float(similarity)
        
        except Exception as e:
            logger.error(f"❌ Error calculating similarity: {str(e)}")
            return 0.0
    
    def find_matching_faces(self, new_embedding: List[float]) -> List[Dict]:
        """
        Find all matching faces in database for a new embedding
        Returns sorted list of matches with similarity scores
        
        Returns:
            [
                {
                    "face_id": "e7acd7a8",
                    "name": "Person_1_Face_e7acd7a8",
                    "similarity": 0.87,
                    "match_type": "high_confidence" | "medium_confidence" | "no_match",
                    "image_path": "app/static/faces/e7acd7a8.jpg",
                    "detection_count": 5,
                    "last_seen": "2025-11-11T12:54:12"
                },
                ...
            ]
        """
        try:
            db_faces = self.get_database_faces()
            
            if not db_faces:
                logger.info("ℹ️ No faces in database for comparison")
                return []
            
            matches = []
            
            # Compare with each database face
            for db_face in db_faces:
                if not db_face.embedding:
                    continue
                
                similarity = self.calculate_similarity(new_embedding, db_face.embedding)
                
                # Determine match type
                if similarity >= self.threshold:
                    match_type = "high_confidence" if similarity >= 0.75 else "medium_confidence"
                    
                    matches.append({
                        "face_id": db_face.id,
                        "name": db_face.name,
                        "similarity": round(similarity, 4),
                        "match_type": match_type,
                        "image_path": db_face.image_path,
                        "detection_count": db_face.detection_count,
                        "last_seen": db_face.last_seen.isoformat() if db_face.last_seen else None
                    })
            
            # Sort by similarity descending (best matches first)
            matches.sort(key=lambda x: x["similarity"], reverse=True)
            
            if matches:
                logger.info(f"✅ Found {len(matches)} matching face(s) in database")
            else:
                logger.info("ℹ️ No matching faces found in database")
            
            return matches
        
        except Exception as e:
            logger.error(f"❌ Error finding matching faces: {str(e)}")
            return []
    
    def get_best_match(self, new_embedding: List[float]) -> Optional[Dict]:
        """
        Get the single best matching face from database
        Returns None if no good match found
        """
        matches = self.find_matching_faces(new_embedding)
        
        if matches and matches[0]["similarity"] >= self.threshold:
            best_match = matches[0]
            logger.info(f"🎯 Best match: {best_match['name']} (similarity: {best_match['similarity']})")
            return best_match
        
        logger.info("ℹ️ No confident match found (below threshold)")
        return None
    
    def update_person_on_match(self, db_face_id: str, new_embedding: List[float], new_image_path: str) -> bool:
        """
        When a new face matches an existing person, update their record with new data
        - Add new embedding to backup_embeddings
        - Update image_paths list
        - Increment detection_count
        - Update last_seen timestamp
        
        Returns True if successful
        """
        try:
            db = self.db_session()
            face_record = db.query(FacePerson).filter(FacePerson.id == db_face_id).first()
            
            if not face_record:
                logger.error(f"❌ Face record not found: {db_face_id}")
                db.close()
                return False
            
            # Update backup embeddings
            if not face_record.backup_embeddings:
                face_record.backup_embeddings = []
            face_record.backup_embeddings.append(new_embedding)
            
            # Update image paths
            if not face_record.image_paths:
                face_record.image_paths = []
            face_record.image_paths.append(new_image_path)
            
            # Update counts and timestamps
            face_record.detection_count = (face_record.detection_count or 0) + 1
            face_record.embedding_count = len(face_record.backup_embeddings) + 1
            face_record.last_seen = __import__('datetime').datetime.now()
            face_record.updated_at = __import__('datetime').datetime.now()
            
            db.commit()
            db.close()
            
            logger.info(f"✅ Updated person record: {db_face_id} (detection_count: {face_record.detection_count})")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error updating person record: {str(e)}")
            return False
    
    def get_similarity_report(self, new_embedding: List[float], top_n: int = 5) -> Dict:
        """
        Get comprehensive similarity report for all faces in database
        Useful for debugging and tuning threshold
        
        Returns report with all similarities even below threshold
        """
        try:
            db_faces = self.get_database_faces()
            
            similarities = []
            for db_face in db_faces:
                if db_face.embedding:
                    similarity = self.calculate_similarity(new_embedding, db_face.embedding)
                    similarities.append({
                        "face_id": db_face.id,
                        "name": db_face.name,
                        "similarity": round(similarity, 4),
                        "meets_threshold": similarity >= self.threshold
                    })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            return {
                "total_database_faces": len(db_faces),
                "top_matches": similarities[:top_n],
                "threshold": self.threshold,
                "matches_above_threshold": len([s for s in similarities if s["meets_threshold"]])
            }
        
        except Exception as e:
            logger.error(f"❌ Error generating similarity report: {str(e)}")
            return {
                "error": str(e),
                "total_database_faces": 0,
                "top_matches": [],
                "threshold": self.threshold,
                "matches_above_threshold": 0
            }
