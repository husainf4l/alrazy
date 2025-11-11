"""
Multi-Angle Face Capture Service
Captures face from 4 angles: front, left, right, back
Stores multiple embeddings for better recognition from any angle
"""

import cv2
import numpy as np
import os
import uuid
from datetime import datetime
from deepface import DeepFace
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, FacePerson
import logging

logger = logging.getLogger(__name__)


class MultiAngleCaptureService:
    """
    Service for capturing faces from multiple angles
    Improves recognition accuracy from different viewpoints
    """
    
    def __init__(self):
        self.model_name = "ArcFace"
        self.detector_backend = "retinaface"
        self.faces_dir = "app/static/faces"
        self.required_angles = ["front", "left", "right", "back"]
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories"""
        if not os.path.exists(self.faces_dir):
            os.makedirs(self.faces_dir)
    
    def _get_db(self) -> Session:
        """Get database session"""
        return SessionLocal()
    
    def extract_face_embedding(self, image: np.ndarray, angle: str = "front") -> Optional[Dict]:
        """
        Extract face embedding from image for a specific angle
        
        Args:
            image: Input image
            angle: Angle identifier (front, left, right, back)
        
        Returns:
            Dict with embedding and metadata or None if failed
        """
        try:
            # Extract faces with alignment
            faces = DeepFace.extract_faces(
                img_path=image,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
                expand_percentage=35  # Capture full head
            )
            
            if not faces or len(faces) == 0:
                logger.warning(f"No face detected for {angle} angle")
                return None
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected for {angle} angle, using first one")
            
            face_data = faces[0]
            
            # Generate embedding
            result = DeepFace.represent(
                img_path=image,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True,
                normalization="ArcFace"
            )
            
            if result and len(result) > 0:
                embedding = result[0]["embedding"]
                
                return {
                    "angle": angle,
                    "embedding": embedding,
                    "facial_area": face_data.get("facial_area", {}),
                    "confidence": face_data.get("confidence", 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting embedding for {angle}: {e}")
            return None
    
    def capture_multi_angle_face(self, images: Dict[str, np.ndarray], person_name: str) -> Dict:
        """
        Capture face from multiple angles and store in database
        
        Args:
            images: Dict with angle as key and image as value
                   e.g., {"front": image1, "left": image2, ...}
            person_name: Name of the person
        
        Returns:
            Dict with success status and person data
        """
        try:
            db = self._get_db()
            person_id = str(uuid.uuid4())[:8]
            
            # Extract embeddings from all angles
            embeddings_data = []
            image_paths = []
            
            for angle in self.required_angles:
                if angle not in images:
                    logger.warning(f"Missing {angle} angle image")
                    continue
                
                image = images[angle]
                
                # Extract embedding for this angle
                embedding_data = self.extract_face_embedding(image, angle)
                
                if embedding_data:
                    embeddings_data.append(embedding_data)
                    
                    # Save image
                    image_filename = f"{person_id}_{angle}.jpg"
                    image_path = os.path.join(self.faces_dir, image_filename)
                    
                    # Extract and save face region
                    facial_area = embedding_data["facial_area"]
                    x = facial_area.get("x", 0)
                    y = facial_area.get("y", 0)
                    w = facial_area.get("w", image.shape[1])
                    h = facial_area.get("h", image.shape[0])
                    
                    # Expand region by 35%
                    expansion = 0.35
                    exp_w = int(w * expansion)
                    exp_h = int(h * expansion)
                    
                    x1 = max(0, x - exp_w)
                    y1 = max(0, y - exp_h)
                    x2 = min(image.shape[1], x + w + exp_w)
                    y2 = min(image.shape[0], y + h + exp_h)
                    
                    face_img = image[y1:y2, x1:x2]
                    cv2.imwrite(image_path, face_img)
                    image_paths.append(image_filename)
            
            if len(embeddings_data) < 2:
                return {
                    "success": False,
                    "error": f"Need at least 2 angles captured, got {len(embeddings_data)}"
                }
            
            # Use front angle as primary, or first available
            primary_embedding = None
            primary_image = None
            
            for i, emb_data in enumerate(embeddings_data):
                if emb_data["angle"] == "front":
                    primary_embedding = emb_data["embedding"]
                    primary_image = image_paths[i]
                    break
            
            if primary_embedding is None:
                primary_embedding = embeddings_data[0]["embedding"]
                primary_image = image_paths[0]
            
            # Store additional embeddings
            backup_embeddings = []
            for emb_data in embeddings_data:
                if emb_data["embedding"] != primary_embedding:
                    backup_embeddings.append({
                        "angle": emb_data["angle"],
                        "embedding": emb_data["embedding"],
                        "confidence": emb_data["confidence"]
                    })
            
            # Save to database
            person = FacePerson(
                id=person_id,
                name=person_name,
                embedding=primary_embedding,
                backup_embeddings=backup_embeddings,
                image_path=primary_image,
                thumbnail_path=primary_image,
                image_paths=image_paths,
                embedding_count=len(embeddings_data),
                detection_count=1,
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(person)
            db.commit()
            db.refresh(person)
            db.close()
            
            return {
                "success": True,
                "person_id": person_id,
                "person_name": person_name,
                "angles_captured": [e["angle"] for e in embeddings_data],
                "total_embeddings": len(embeddings_data),
                "image_paths": image_paths
            }
            
        except Exception as e:
            logger.error(f"Error in multi-angle capture: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_multi_angle_service = None

def get_multi_angle_service() -> MultiAngleCaptureService:
    """Get or create multi-angle capture service singleton"""
    global _multi_angle_service
    if _multi_angle_service is None:
        _multi_angle_service = MultiAngleCaptureService()
    return _multi_angle_service
