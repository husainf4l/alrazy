"""
Integrated Webcam Processing Pipeline
- YOLO11 Person Detection (2 FPS)
- Face Detection & Recognition (ArcFace)
- Location & Logging
- Database Storage
"""

import os
import sys

# Configure TensorFlow GPU memory optimization BEFORE importing any ML libraries
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'
os.environ['TF_GPU_THREAD_PER_CORE'] = '2'
os.environ['TF_AUTOGRAPH_VERBOSITY'] = '0'
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'
os.environ['TF_DISABLE_MKL'] = 'false'

# Disable CUDA to avoid libdevice errors - use CPU for embedding extraction
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Fix CUDA libdevice issue (for reference if needed)
cuda_path = '/usr/local/cuda'
if os.path.exists(cuda_path):
    os.environ['XLA_FLAGS'] = f'--xla_gpu_cuda_data_dir={cuda_path}'
    os.environ['CUDA_HOME'] = cuda_path

import cv2
import numpy as np
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import threading
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebcamProcessor:
    def __init__(self, fps_limit=None):
        """
        Initialize webcam processor
        fps_limit: Target FPS for YOLO processing (default from .env or 2)
        """
        from app.services.yolo import YOLOPeopleDetector
        from app.services.face_recognition import FaceRecognitionService
        from app.services.face_matching import FaceMatchingService
        from app.models.database import SessionLocal
        
        self.yolo = YOLOPeopleDetector()
        self.face_service = FaceRecognitionService()
        self.face_matcher = FaceMatchingService(similarity_threshold=0.6)  # 60% similarity threshold
        self.db_session = SessionLocal
        
        # Use FPS from environment or default to 2
        self.fps_limit = fps_limit or int(os.getenv("YOLO_FPS_LIMIT", "2"))
        self.frame_interval = 1.0 / self.fps_limit
        self.last_detection_time = 0
        
        # Detection history for tracking
        self.detection_history = deque(maxlen=30)
        self.person_tracks = {}
        self.next_track_id = 1
        
        # Setup faces directory
        self.faces_dir = "app/static/faces"
        if not os.path.exists(self.faces_dir):
            os.makedirs(self.faces_dir)
        
        logger.info(f"✅ WebcamProcessor initialized with {self.fps_limit} FPS YOLO processing")
    
    def _save_face_to_db(self, face_image: np.ndarray, embedding: List[float], location: Dict, person_id: int) -> Optional[Dict]:
        """
        Save detected face image to disk and database
        Also matches against existing faces to identify same persons
        
        Returns dict with face_id, is_match, match_info if successful, None otherwise
        """
        try:
            face_id = str(uuid.uuid4())[:8]
            filename = f"{face_id}.jpg"
            filepath = os.path.join(self.faces_dir, filename)
            
            # Save image to disk
            cv2.imwrite(filepath, face_image)
            
            # Step 1: Check for matching faces in database
            matches = self.face_matcher.find_matching_faces(embedding)
            is_match = len(matches) > 0
            best_match = matches[0] if matches else None
            
            # Log matching results
            if is_match:
                match_info = f"🎯 Match found: {best_match['name']} (similarity: {best_match['similarity']})"
                logger.info(match_info)
            else:
                match_info = "ℹ️ New person - no matches in database"
                logger.info(match_info)
            
            # Step 2: Save to database
            try:
                from app.models.database import FacePerson
                db = self.db_session()
                
                # If match found, update existing record
                if is_match and best_match:
                    db_face_id = best_match["face_id"]
                    self.face_matcher.update_person_on_match(db_face_id, embedding, filepath)
                    
                    return {
                        "face_id": face_id,
                        "db_face_id": db_face_id,
                        "is_match": True,
                        "match_type": best_match["match_type"],
                        "similarity": best_match["similarity"],
                        "matched_name": best_match["name"],
                        "detection_count": best_match["detection_count"] + 1
                    }
                
                # Otherwise, create new record
                face_record = FacePerson(
                    id=face_id,
                    name=f"Person_{person_id}_Face_{face_id}",
                    embedding=embedding,
                    image_path=filepath,
                    image_paths=[filepath],
                    embedding_count=1,
                    detection_count=1,
                    created_at=datetime.now(),
                    last_seen=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.add(face_record)
                db.commit()
                db.refresh(face_record)
                db.close()
                
                logger.info(f"✅ New face saved to database: {filename} (ID: {face_id})")
                
                return {
                    "face_id": face_id,
                    "db_face_id": face_id,
                    "is_match": False,
                    "match_type": "new_person",
                    "similarity": 0.0,
                    "matched_name": f"Person_{person_id}_Face_{face_id}",
                    "detection_count": 1
                }
                
            except Exception as db_err:
                logger.error(f"❌ Database error saving face: {str(db_err)[:100]}")
                import traceback
                logger.error(traceback.format_exc())
                return None
                
        except Exception as e:
            logger.error(f"❌ Error saving face: {str(e)[:100]}")
            return None
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process a single frame through the complete pipeline
        Returns detection results with location data
        """
        current_time = time.time()
        frame_height, frame_width = frame.shape[:2]
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "frame_size": (frame_width, frame_height),
            "yolo_detections": [],
            "face_detections": [],
            "recognized_persons": [],
            "processing_time_ms": 0,
            "log_messages": []
        }
        
        start_time = time.time()
        
        # ===== STEP 1: YOLO Person Detection (2 FPS) =====
        if current_time - self.last_detection_time >= self.frame_interval:
            logger.info("🔍 YOLO Person Detection starting...")
            self.last_detection_time = current_time
            
            yolo_result = self.yolo.detect_people_with_poses(frame)
            people_count = yolo_result.get("people_count", 0)
            
            log_msg = f"YOLO: Detected {people_count} people"
            logger.info(log_msg)
            result["log_messages"].append(log_msg)
            
            # ===== STEP 2: For each detected person, run face detection =====
            for person_idx, person_data in enumerate(yolo_result.get("pose_data", [])):
                person_bbox = person_data.get("bbox")
                person_confidence = person_data.get("confidence", 0)
                head_region = person_data.get("head_region")
                
                if not person_bbox or not head_region:
                    continue
                
                # Extract region of interest
                x1, y1, x2, y2 = person_bbox
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Ensure coordinates are within frame
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame_width, x2)
                y2 = min(frame_height, y2)
                
                person_roi = frame[y1:y2, x1:x2]
                
                if person_roi.size == 0:
                    continue
                
                location_data = {
                    "person_id": person_idx + 1,
                    "bbox_pixel": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "bbox_center": {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2},
                    "yolo_confidence": float(person_confidence),
                    "frame_width": frame_width,
                    "frame_height": frame_height,
                    "area_percentage": (((x2-x1) * (y2-y1)) / (frame_width * frame_height)) * 100
                }
                
                yolo_log = f"  👤 Person {person_idx + 1}: Confidence={person_confidence:.3f}, " \
                           f"Pos=({location_data['bbox_center']['x']}, {location_data['bbox_center']['y']}), " \
                           f"Area={location_data['area_percentage']:.1f}%"
                logger.info(yolo_log)
                result["log_messages"].append(yolo_log)
                
                # ===== STEP 3: Run Face Detection on Person ROI =====
                try:
                    from deepface import DeepFace
                    
                    # Extract faces with expanded area to capture full facial dimensions
                    faces = DeepFace.extract_faces(
                        img_path=person_roi,
                        detector_backend="retinaface",
                        enforce_detection=False,
                        align=True,
                        expand_percentage=20  # Expand by 20% to capture full face context including hair, ears, chin
                    )
                    
                    if faces:
                        face_log = f"    ✓ Face Detection: Found {len(faces)} face(s)"
                        logger.info(face_log)
                        result["log_messages"].append(face_log)
                        
                        for face_idx, face_data in enumerate(faces):
                            face_confidence = face_data.get("confidence", 0)
                            facial_area = face_data.get("facial_area", {})
                            
                            # Adjust coordinates to frame coordinates
                            face_x = facial_area.get("x", 0) + x1
                            face_y = facial_area.get("y", 0) + y1
                            face_w = facial_area.get("w", 0)
                            face_h = facial_area.get("h", 0)
                            
                            face_detection = {
                                "person_id": person_idx + 1,
                                "face_id": face_idx + 1,
                                "face_confidence": float(face_confidence),
                                "face_bbox": {"x": face_x, "y": face_y, "w": face_w, "h": face_h},
                                "face_center": {"x": face_x + face_w // 2, "y": face_y + face_h // 2},
                                "landmarks": facial_area.get("left_eye") is not None
                            }
                            
                            result["face_detections"].append(face_detection)
                            
                            face_detail = f"      🟢 Face {face_idx + 1}: Confidence={face_confidence:.3f}, " \
                                         f"Center=({face_detection['face_center']['x']}, {face_detection['face_center']['y']})"
                            logger.info(face_detail)
                            result["log_messages"].append(face_detail)
                            
                            # ===== STEP 4: Extract ArcFace Embedding =====
                            try:
                                # Extract the FULL face region with expansion from the original person ROI
                                # This captures the entire head including hair, ears, forehead, and chin
                                face_x_local = facial_area.get("x", 0)
                                face_y_local = facial_area.get("y", 0)
                                face_w_local = facial_area.get("w", 0)
                                face_h_local = facial_area.get("h", 0)
                                
                                if face_w_local == 0 or face_h_local == 0:
                                    logger.warning(f"      ⚠️ Invalid face dimensions for Face {face_idx + 1}")
                                    continue
                                
                                # Expand the bounding box by 30% to capture the entire head region
                                # This ensures we get hair, ears, full forehead, and complete chin
                                expansion_factor = 0.35  # 35% expansion on all sides
                                expand_x = int(face_w_local * expansion_factor)
                                expand_y = int(face_h_local * expansion_factor)
                                
                                # Calculate expanded coordinates
                                expanded_x1 = max(0, face_x_local - expand_x)
                                expanded_y1 = max(0, face_y_local - expand_y)
                                expanded_x2 = min(person_roi.shape[1], face_x_local + face_w_local + expand_x)
                                expanded_y2 = min(person_roi.shape[0], face_y_local + face_h_local + expand_y)
                                
                                # Extract the full face region with expansion
                                full_face_roi = person_roi[expanded_y1:expanded_y2, expanded_x1:expanded_x2].copy()
                                
                                if full_face_roi.size == 0:
                                    logger.warning(f"      ⚠️ Empty face ROI for Face {face_idx + 1}")
                                    continue
                                
                                logger.info(f"      📐 Extracted full face: original={face_w_local}x{face_h_local}, "
                                          f"expanded={full_face_roi.shape[1]}x{full_face_roi.shape[0]} "
                                          f"(+{int(expansion_factor*100)}% expansion)")
                                
                                # Convert to uint8 if needed
                                if full_face_roi.dtype == np.float32 or full_face_roi.dtype == np.float64:
                                    full_face_roi = (full_face_roi * 255).astype(np.uint8)
                                
                                # Generate embedding from the FULL face region (not just aligned crop)
                                embeddings = DeepFace.represent(
                                    img_path=full_face_roi,
                                    model_name="ArcFace",
                                    detector_backend="retinaface",  # Use retinaface to detect within the expanded region
                                    enforce_detection=False,  # Don't enforce since we already detected the face
                                    align=True  # Align for best results
                                )
                                
                                if embeddings:
                                    embedding_data = embeddings[0]
                                    embedding_vector = embedding_data.get("embedding", [])
                                    
                                    # Use the FULL face region (with expansion) for saving
                                    # This ensures we capture the entire head including all facial features
                                    face_roi_to_save = full_face_roi.copy()
                                    
                                    # Ensure the face image has proper dimensions (at least 112x112 for ArcFace)
                                    h, w = face_roi_to_save.shape[:2]
                                    if h < 112 or w < 112:
                                        # Resize to minimum required size maintaining aspect ratio
                                        scale = max(112/h, 112/w)
                                        new_h, new_w = int(h * scale), int(w * scale)
                                        face_roi_to_save = cv2.resize(face_roi_to_save, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                                        logger.info(f"      📐 Resized face from {w}x{h} to {new_w}x{new_h}")
                                    
                                    logger.info(f"      💾 Saving full face region: {face_roi_to_save.shape[1]}x{face_roi_to_save.shape[0]}")
                                    
                                    # Save face to database & check for matches
                                    save_result = self._save_face_to_db(
                                        face_roi_to_save,
                                        embedding_vector,
                                        face_detection["face_center"],
                                        person_idx + 1
                                    )
                                    
                                    if save_result:
                                        # Prepare result data
                                        recognized_person = {
                                            "person_id": person_idx + 1,
                                            "face_id": face_idx + 1,
                                            "saved_face_id": save_result.get("face_id"),
                                            "db_face_id": save_result.get("db_face_id"),
                                            "embedding_length": len(embedding_vector),
                                            "location": face_detection["face_center"],
                                            "verification_status": "✓ Verified as face",
                                            "is_match": save_result.get("is_match", False),
                                            "match_type": save_result.get("match_type"),
                                            "similarity": save_result.get("similarity"),
                                            "matched_name": save_result.get("matched_name"),
                                            "detection_count": save_result.get("detection_count")
                                        }
                                        result["recognized_persons"].append(recognized_person)
                                        
                                        # Log with match information
                                        if save_result.get("is_match"):
                                            match_log = f"        ✅ MATCH FOUND: {save_result['matched_name']} (similarity: {save_result['similarity']:.3f})"
                                            logger.info(match_log)
                                            result["log_messages"].append(match_log)
                                            
                                            detail_log = f"        📊 Detection #{save_result['detection_count']} of same person"
                                            logger.info(detail_log)
                                            result["log_messages"].append(detail_log)
                                        else:
                                            embed_log = f"        ✓ ArcFace Embedding: 512-dim vector extracted & saved to DB (ID: {save_result['face_id']})"
                                            logger.info(embed_log)
                                            result["log_messages"].append(embed_log)
                                    
                            except Exception as e:
                                embed_err = f"        ❌ Embedding failed: {str(e)[:50]}"
                                logger.warning(embed_err)
                                result["log_messages"].append(embed_err)
                    else:
                        no_face_log = f"    ✗ No face detected in person ROI"
                        logger.info(no_face_log)
                        result["log_messages"].append(no_face_log)
                        
                except Exception as e:
                    face_error = f"    ❌ Face detection error: {str(e)[:50]}"
                    logger.error(face_error)
                    result["log_messages"].append(face_error)
                
                result["yolo_detections"].append(location_data)
        
        else:
            skip_log = f"⏭️  Skipping YOLO (next in {self.frame_interval - (current_time - self.last_detection_time):.2f}s)"
            result["log_messages"].append(skip_log)
        
        result["processing_time_ms"] = (time.time() - start_time) * 1000
        
        return result
    
    def get_status(self) -> Dict:
        """Get processor status"""
        return {
            "yolo_model_loaded": self.yolo.model is not None,
            "face_service_ready": self.face_service is not None,
            "fps_limit": self.fps_limit,
            "frame_interval": self.frame_interval,
            "detection_history_size": len(self.detection_history)
        }


# Global instance
_processor = None

def get_webcam_processor(fps_limit=2) -> WebcamProcessor:
    """Get or create global webcam processor"""
    global _processor
    if _processor is None:
        _processor = WebcamProcessor(fps_limit=fps_limit)
    return _processor

def process_webcam_frame(frame: np.ndarray) -> Dict:
    """Process a single webcam frame"""
    processor = get_webcam_processor()
    return processor.process_frame(frame)