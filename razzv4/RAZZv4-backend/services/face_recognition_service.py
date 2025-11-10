"""
Face Recognition Service using InsightFace (ArcFace)
Best practice implementation for face detection and embedding extraction
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """
    Face recognition using InsightFace (ArcFace embeddings)
    - Detects faces in images
    - Extracts 512-dimensional embeddings
    - Matches faces against gallery database
    """
    
    def __init__(self, model_name: str = "buffalo_l", detection_threshold: float = 0.5):
        """
        Initialize face recognition service
        
        Args:
            model_name: InsightFace model pack ('buffalo_l', 'buffalo_s', etc.)
            detection_threshold: Minimum confidence for face detection (0-1)
        """
        logger.info(f"Initializing InsightFace with model: {model_name}")
        
        self.model_name = model_name
        self.detection_threshold = detection_threshold
        self.app = None
        self.recognition_model = None
        
        try:
            import insightface
            from insightface.app import FaceAnalysis
            
            # Initialize FaceAnalysis app
            self.app = FaceAnalysis(
                name=model_name,
                allowed_modules=['detection', 'recognition'],  # Only need detection + recognition
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']  # Try GPU first
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            
            logger.info("✅ InsightFace initialized successfully")
            logger.info(f"   Model: {model_name}")
            logger.info(f"   Detection threshold: {detection_threshold}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize InsightFace: {str(e)}")
            logger.warning("⚠️  Face recognition will be disabled")
            logger.warning("   To enable, install: pip install insightface onnxruntime")
    
    def is_available(self) -> bool:
        """Check if face recognition is available"""
        return self.app is not None
    
    def detect_faces(self, frame: np.ndarray, min_face_size: int = 30) -> List[Dict]:
        """
        Detect faces in frame
        
        Args:
            frame: Input image (BGR format)
            min_face_size: Minimum face size in pixels
        
        Returns:
            List of detected faces with metadata:
            [
                {
                    'bbox': [x1, y1, x2, y2],
                    'confidence': 0.95,
                    'landmarks': [[x, y], ...],  # 5 landmarks (eyes, nose, mouth)
                    'embedding': np.array(512,),
                    'age': 25,
                    'gender': 'M',
                    'quality_score': 0.85
                },
                ...
            ]
        """
        if not self.is_available():
            return []
        
        try:
            # Detect faces
            faces = self.app.get(frame)
            
            if not faces:
                return []
            
            results = []
            for face in faces:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                
                # Filter small faces
                face_width = x2 - x1
                face_height = y2 - y1
                if face_width < min_face_size or face_height < min_face_size:
                    continue
                
                # Calculate quality score based on:
                # - Detection confidence
                # - Face size
                # - Pose (normalized from face angle)
                quality_score = float(face.det_score)
                
                # Face size factor (larger faces = better quality)
                size_factor = min(face_width * face_height / (100 * 100), 1.0)
                quality_score *= (0.7 + 0.3 * size_factor)
                
                results.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': float(face.det_score),
                    'landmarks': face.kps.astype(int).tolist() if hasattr(face, 'kps') else None,
                    'embedding': face.normed_embedding,  # 512-dim, already normalized
                    'age': int(face.age) if hasattr(face, 'age') else None,
                    'gender': 'M' if hasattr(face, 'gender') and face.gender == 1 else 'F' if hasattr(face, 'gender') else None,
                    'quality_score': float(quality_score)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}")
            return []
    
    def detect_faces_in_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> List[Dict]:
        """
        Detect faces within a person bounding box
        
        Args:
            frame: Full frame image
            bbox: Person bounding box (x1, y1, x2, y2)
        
        Returns:
            List of detected faces (same format as detect_faces)
        """
        if not self.is_available():
            return []
        
        try:
            x1, y1, x2, y2 = bbox
            
            # Expand bbox slightly for better face detection
            height, width = frame.shape[:2]
            margin = 10
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(width, x2 + margin)
            y2 = min(height, y2 + margin)
            
            # Crop person region
            person_crop = frame[y1:y2, x1:x2]
            
            if person_crop.size == 0:
                return []
            
            # Detect faces in crop
            faces = self.detect_faces(person_crop)
            
            # Adjust bbox coordinates to full frame
            for face in faces:
                face['bbox'] = [
                    face['bbox'][0] + x1,
                    face['bbox'][1] + y1,
                    face['bbox'][2] + x1,
                    face['bbox'][3] + y1
                ]
                
                # Adjust landmarks too
                if face['landmarks']:
                    face['landmarks'] = [
                        [kp[0] + x1, kp[1] + y1] 
                        for kp in face['landmarks']
                    ]
            
            return faces
            
        except Exception as e:
            logger.error(f"Error detecting faces in bbox: {str(e)}")
            return []
    
    def extract_embedding(self, frame: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        Extract face embedding from frame
        
        Args:
            frame: Input image
            bbox: Optional face bounding box (x1, y1, x2, y2). If None, detect face first.
        
        Returns:
            512-dimensional embedding vector (normalized) or None if no face found
        """
        if not self.is_available():
            return None
        
        try:
            if bbox:
                # Crop face region
                x1, y1, x2, y2 = bbox
                face_crop = frame[y1:y2, x1:x2]
                
                # Detect face in crop
                faces = self.detect_faces(face_crop)
                if not faces:
                    return None
                
                return faces[0]['embedding']
            else:
                # Detect face in full frame
                faces = self.detect_faces(frame)
                if not faces:
                    return None
                
                # Return embedding of largest/best face
                best_face = max(faces, key=lambda f: f['quality_score'])
                return best_face['embedding']
                
        except Exception as e:
            logger.error(f"Error extracting embedding: {str(e)}")
            return None
    
    def match_against_gallery(
        self, 
        embedding: np.ndarray, 
        gallery_embeddings: List[Tuple[int, np.ndarray]], 
        threshold: float = 0.6
    ) -> Optional[Tuple[int, float]]:
        """
        Match face embedding against gallery
        
        Args:
            embedding: Query embedding (512-dim)
            gallery_embeddings: List of (person_id, embedding) tuples
            threshold: Minimum similarity score (0-1) for match
        
        Returns:
            (person_id, similarity_score) of best match, or None if no match above threshold
        """
        if not gallery_embeddings:
            return None
        
        try:
            best_match = None
            best_score = threshold
            
            for person_id, gallery_emb in gallery_embeddings:
                # Compute cosine similarity
                similarity = self.cosine_similarity(embedding, gallery_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = person_id
            
            if best_match:
                return (best_match, float(best_score))
            return None
            
        except Exception as e:
            logger.error(f"Error matching against gallery: {str(e)}")
            return None
    
    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            emb1, emb2: Normalized embedding vectors
        
        Returns:
            Similarity score (0-1, where 1 = identical)
        """
        # If embeddings are already normalized (InsightFace does this), just dot product
        return float(np.dot(emb1, emb2))
    
    @staticmethod
    def euclidean_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute Euclidean distance between two embeddings
        
        Args:
            emb1, emb2: Embedding vectors
        
        Returns:
            Distance (lower = more similar)
        """
        return float(np.linalg.norm(emb1 - emb2))
    
    def draw_face_detection(
        self, 
        frame: np.ndarray, 
        faces: List[Dict], 
        show_landmarks: bool = True,
        show_info: bool = True
    ) -> np.ndarray:
        """
        Draw face detections on frame
        
        Args:
            frame: Input image
            faces: List of detected faces from detect_faces()
            show_landmarks: Draw facial landmarks
            show_info: Show age, gender, quality
        
        Returns:
            Annotated frame
        """
        frame_copy = frame.copy()
        
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            
            # Draw bbox
            color = (0, 255, 0)  # Green
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, 2)
            
            # Draw landmarks
            if show_landmarks and face['landmarks']:
                for kp in face['landmarks']:
                    cv2.circle(frame_copy, tuple(kp), 2, (0, 0, 255), -1)
            
            # Draw info
            if show_info:
                info_text = []
                if face['age']:
                    info_text.append(f"Age: {face['age']}")
                if face['gender']:
                    info_text.append(f"Gender: {face['gender']}")
                info_text.append(f"Q: {face['quality_score']:.2f}")
                
                y_offset = y1 - 10
                for text in info_text:
                    cv2.putText(frame_copy, text, (x1, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    y_offset -= 20
        
        return frame_copy


# Global instance (singleton)
_face_service_instance = None


def get_face_recognition_service() -> FaceRecognitionService:
    """Get singleton face recognition service"""
    global _face_service_instance
    if _face_service_instance is None:
        _face_service_instance = FaceRecognitionService()
    return _face_service_instance
