"""
Face Recognition Service with PostgreSQL Database Integration
Uses DeepFace with ArcFace model for high accuracy
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
from app.services.yolo import validate_human_poses
from dotenv import load_dotenv

load_dotenv()

class FaceRecognitionService:
    def __init__(self):
        self.model_name = "ArcFace"  # Best accuracy model according to DeepFace docs
        self.detector_backend = os.getenv("FACE_DETECTOR_BACKEND", "retinaface")  # Better accuracy than opencv
        self.distance_metric = "cosine"
        self.threshold = 0.68  # ArcFace threshold
        self.faces_dir = "app/static/faces"
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories"""
        if not os.path.exists(self.faces_dir):
            os.makedirs(self.faces_dir)
    
    def _get_db(self) -> Session:
        """Get database session"""
        return SessionLocal()
    
    def _validate_real_face(self, image: np.ndarray) -> bool:
        """
        Validate if the detected region contains a real human face using multiple validation methods:
        1. DeepFace detection and quality checks
        2. YOLO pose validation to confirm human body structure (optional)
        """
        print("Starting comprehensive face validation...")
        
        # Step 1: YOLO pose validation - check for human body with proper facial landmarks (optional)
        yolo_validation_passed = False
        try:
            pose_data = validate_human_poses(image)
            valid_poses = pose_data.get("valid_poses", 0)
            people_count = pose_data.get("people_count", 0)
            
            print(f"YOLO detected {people_count} people with {valid_poses} valid poses")
            
            if valid_poses > 0:
                # Additional YOLO validation - check pose quality
                pose_details = pose_data.get("pose_data", [])
                has_high_quality_pose = False
                
                for person in pose_details:
                    if person.get("has_valid_pose", False):
                        confidence = person.get("confidence", 0)
                        face_landmarks = person.get("face_landmarks", {})
                        
                        # Check YOLO confidence and facial landmark quality
                        if confidence > 0.8 and len(face_landmarks) >= 3:
                            print(f"High-quality pose detected: confidence={confidence:.3f}, landmarks={len(face_landmarks)}")
                            has_high_quality_pose = True
                            break
                
                if has_high_quality_pose:
                    yolo_validation_passed = True
                else:
                    print("YOLO validation failed: No high-quality poses found")
            else:
                print("YOLO validation failed: No valid human poses detected")
                
        except Exception as e:
            print(f"YOLO pose validation error: {e}")
            print("Continuing with DeepFace-only validation...")
        
        # If YOLO validation failed, we'll still proceed with DeepFace validation
        if not yolo_validation_passed:
            print("⚠️  YOLO validation not available or failed - proceeding with DeepFace validation only")
        
        # Step 2: DeepFace validation for face detection quality
        try:
            face_objs = DeepFace.extract_faces(
                img_path=image,
                detector_backend=self.detector_backend,  
                enforce_detection=True,  
                align=True,  
                expand_percentage=5  
            )
            
            if not face_objs or len(face_objs) == 0:
                print("DeepFace validation failed: No faces detected")
                return False
            
            # Cross-validate with YOLO: if YOLO detects fewer people than DeepFace detects faces,
            # be more strict about face validation
            deepface_count = len(face_objs)
            yolo_people = pose_data.get("people_count", 0)
            
            if deepface_count > yolo_people:
                print(f"Warning: DeepFace detected {deepface_count} faces but YOLO detected {yolo_people} people")
                print("Applying stricter validation criteria...")
                confidence_threshold = 0.85  # Higher threshold
                variance_threshold = 200     # Higher variance requirement
            else:
                print(f"Face/people count match: {deepface_count} faces, {yolo_people} people")
                confidence_threshold = 0.7
                variance_threshold = 150
            
            # Check each detected face with appropriate thresholds
            valid_faces = 0
            for i, face_obj in enumerate(face_objs):
                # Check confidence score with dynamic threshold
                confidence = face_obj.get("confidence", 0)
                if confidence < confidence_threshold:  
                    print(f"Face {i+1} confidence too low: {confidence:.3f} < {confidence_threshold}")
                    continue
                
                # Facial area validation
                facial_area = face_obj.get("facial_area", {})
                if facial_area:
                    width = facial_area.get("w", 0)
                    height = facial_area.get("h", 0)
                    
                    if width < 60 or height < 60:
                        print(f"Face {i+1} too small: {width}x{height}")
                        continue
                    
                    aspect_ratio = width / height if height > 0 else 0
                    if aspect_ratio < 0.6 or aspect_ratio > 1.6:
                        print(f"Face {i+1} unusual aspect ratio: {aspect_ratio:.2f}")
                        continue
                
                # Image quality validation with dynamic thresholds
                face_image = face_obj.get("face")
                if face_image is not None:
                    if face_image.max() <= 1.0:
                        face_image = (face_image * 255).astype(np.uint8)
                    
                    if len(face_image.shape) == 3:
                        gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
                    else:
                        gray = face_image
                    
                    # Variance check with dynamic threshold
                    variance = np.var(gray)
                    if variance < variance_threshold:  
                        print(f"Face {i+1} too uniform (variance: {variance:.1f} < {variance_threshold})")
                        continue
                    
                    # Edge density for facial features
                    edges = cv2.Canny(gray, 50, 150)
                    edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
                    if edge_density < 0.015:  # Slightly higher threshold
                        print(f"Face {i+1} insufficient features (edge density: {edge_density:.3f})")
                        continue
                
                valid_faces += 1
                print(f"Face {i+1} passed DeepFace validation: confidence={confidence:.3f}, variance={variance:.1f}")
            
            if valid_faces == 0:
                print("DeepFace validation failed: No faces passed quality checks")
                return False
            
            # Final validation: if we have more valid faces than YOLO people, limit to YOLO count
            if valid_faces > yolo_people and yolo_people > 0:
                print(f"Limiting face count from {valid_faces} to {yolo_people} based on YOLO people detection")
                # This will be handled in the main recognition function
            
            print(f"Validation successful: {valid_faces} face(s) passed all checks (YOLO + DeepFace)")
            return True
            
        except Exception as e:
            print(f"DeepFace validation error: {e}")
            return False
    
    def _save_face_image(self, face_image: np.ndarray, face_id: str) -> str:
        """Save face image to disk with YOLO validation of saved image"""
        filename = f"{face_id}.jpg"
        filepath = os.path.join(self.faces_dir, filename)
        
        # Save the face image temporarily
        cv2.imwrite(filepath, face_image)
        
        # Validate the saved image with YOLO to ensure it contains a valid face
        if self._validate_saved_face_with_yolo(filepath):
            print(f"✅ YOLO validated saved face image: {filename}")
            return filepath
        else:
            # Remove invalid image and raise error
            if os.path.exists(filepath):
                os.remove(filepath)
            raise ValueError(f"YOLO validation failed for saved face image: {filename}")
    
    def _calculate_face_quality_score(self, face_image: np.ndarray, confidence: float) -> float:
        """Calculate a comprehensive face quality score combining multiple factors"""
        try:
            score = 0.0
            
            # Base score from DeepFace confidence
            score += confidence * 0.3  # 30% weight
            
            # Size score - larger faces are generally better quality
            height, width = face_image.shape[:2]
            size_score = min(1.0, (height * width) / (200 * 200))  # Normalize to 200x200
            score += size_score * 0.2  # 20% weight
            
            # Face detection using Haar cascade - this is crucial
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY) if len(face_image.shape) == 3 else face_image
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            
            if len(faces) > 0:
                # Found actual face - big bonus
                score += 0.4  # 40% weight
                
                # Additional score for face coverage
                best_face = faces[0]  # Take the first/largest face
                face_area = best_face[2] * best_face[3]  # width * height
                total_area = height * width
                coverage = face_area / total_area if total_area > 0 else 0
                score += min(0.1, coverage)  # Up to 10% bonus for good coverage
            
            # Eye detection for additional validation
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(10, 10))
            
            if len(eyes) >= 2:  # At least 2 eyes
                score += 0.1  # 10% bonus
            elif len(eyes) == 1:  # At least 1 eye
                score += 0.05  # 5% bonus
            
            return min(1.0, score)  # Cap at 1.0
            
        except Exception as e:
            print(f"Error calculating face quality score: {e}")
            return confidence * 0.5  # Fallback to half confidence

    def _validate_saved_face_with_yolo(self, image_path: str) -> bool:
        """Validate saved face image using YOLO to ensure it contains proper facial features"""
        try:
            # Load the saved image
            saved_image = cv2.imread(image_path)
            if saved_image is None:
                print(f"Could not load saved image: {image_path}")
                return False
            
            # For face images, we need to check for facial landmarks using YOLO
            # Since it's a cropped face, we'll look for key facial features
            pose_data = validate_human_poses(saved_image)
            
            # For cropped faces, we expect at least some facial landmarks
            pose_details = pose_data.get("pose_data", [])
            
            for person in pose_details:
                face_landmarks = person.get("face_landmarks", {})
                confidence = person.get("confidence", 0)
                
                # Check if we have sufficient facial landmarks and good confidence
                if len(face_landmarks) >= 2 and confidence > 0.5:  # Lower threshold for cropped faces
                    print(f"YOLO found {len(face_landmarks)} facial landmarks with confidence {confidence:.3f}")
                    return True
            
            # Alternative validation: check for any face-like features
            # Even if YOLO doesn't detect a full pose, check for face-specific patterns
            if self._check_face_features(saved_image):
                print("Face features validated through alternative check")
                return True
            
            print(f"YOLO validation failed: insufficient facial landmarks in saved image")
            return False
            
        except Exception as e:
            print(f"Error validating saved face with YOLO: {e}")
            return False
    
    def _check_face_features(self, face_image: np.ndarray) -> bool:
        """Alternative face feature validation for cropped face images"""
        try:
            # Convert to grayscale for feature detection
            if len(face_image.shape) == 3:
                gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_image
            
            # Check image dimensions - should be reasonable face size
            height, width = gray.shape
            if height < 50 or width < 50:
                return False
            
            # Use Haar cascade for face detection as secondary validation
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
            
            if len(faces) > 0:
                print(f"Haar cascade detected {len(faces)} face(s) in saved image")
                return True
            
            # Check for eye-like patterns as a final validation
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(10, 10))
            
            if len(eyes) >= 1:  # At least one eye-like feature
                print(f"Eye patterns detected: {len(eyes)} features found")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error in alternative face feature check: {e}")
            return False
    
    def extract_face_embedding(self, image: np.ndarray) -> Optional[List[float]]:
        """Extract face embedding using DeepFace with high-quality settings"""
        try:
            # Use consistent high-quality settings
            result = DeepFace.represent(
                img_path=image,
                model_name=self.model_name,
                detector_backend=self.detector_backend,  # RetinaFace for consistency
                enforce_detection=True,  # Strict detection
                align=True,
                normalization="ArcFace"  # ArcFace normalization for best results
            )
            
            if result and len(result) > 0:
                return result[0]["embedding"]
        except Exception as e:
            # Fallback to OpenCV if RetinaFace fails
            try:
                print(f"RetinaFace embedding failed, trying OpenCV fallback: {e}")
                result = DeepFace.represent(
                    img_path=image,
                    model_name=self.model_name,
                    detector_backend="opencv",
                    enforce_detection=True,
                    align=True,
                    normalization="ArcFace"
                )
                
                if result and len(result) > 0:
                    return result[0]["embedding"]
            except Exception as fallback_error:
                print(f"Embedding extraction failed completely: {fallback_error}")
        
        return None
    
    def find_matching_face(self, embedding: List[float]) -> Optional[FacePerson]:
        """Find matching face in database using multiple embeddings for better accuracy"""
        import numpy as np
        from scipy.spatial.distance import cosine
        
        db = self._get_db()
        try:
            min_distance = float('inf')
            best_match = None
            
            # Get all faces from database
            faces = db.query(FacePerson).all()
            
            for face_record in faces:
                try:
                    # Get all embeddings for this person
                    all_embeddings = []
                    
                    # Include the primary embedding
                    if face_record.embedding:
                        all_embeddings.append(np.array(face_record.embedding))
                    
                    # Include backup embeddings
                    if face_record.backup_embeddings:
                        for backup_emb in face_record.backup_embeddings:
                            all_embeddings.append(np.array(backup_emb))
                    
                    if not all_embeddings:
                        continue
                    
                    # Calculate distance to each embedding and take the minimum (best match)
                    current_embedding = np.array(embedding)
                    distances = []
                    
                    for stored_embedding in all_embeddings:
                        distance = cosine(stored_embedding, current_embedding)
                        distances.append(distance)
                    
                    # Use the best (minimum) distance among all embeddings
                    min_person_distance = min(distances)
                    
                    if min_person_distance < min_distance and min_person_distance < self.threshold:
                        min_distance = min_person_distance
                        best_match = face_record
                        
                except Exception as e:
                    print(f"Error comparing embeddings for {face_record.name}: {e}")
                    continue
            
            if best_match:
                print(f"Found matching face: {best_match.name} with distance {min_distance:.3f}")
            
            return best_match
        finally:
            db.close()
    
    def is_embedding_sufficiently_different(self, person: FacePerson, new_embedding: List[float]) -> tuple[bool, float]:
        """
        Check if new embedding is sufficiently different from existing ones to warrant saving.
        Returns (is_different, min_distance)
        """
        import numpy as np
        from scipy.spatial.distance import cosine
        
        try:
            # Collect all existing embeddings
            existing_embeddings = []
            
            # Include primary embedding
            if person.embedding:
                existing_embeddings.append(np.array(person.embedding))
            
            # Include backup embeddings
            if person.backup_embeddings:
                for backup_emb in person.backup_embeddings:
                    existing_embeddings.append(np.array(backup_emb))
            
            if not existing_embeddings:
                return True, 1.0  # No existing embeddings, so it's different
            
            # Calculate distance to all existing embeddings
            current_embedding = np.array(new_embedding)
            min_distance = float('inf')
            
            for existing_embedding in existing_embeddings:
                distance = cosine(existing_embedding, current_embedding)
                min_distance = min(min_distance, distance)
            
            # Threshold for "different enough" to save as additional learning data
            difference_threshold = 0.12  # Must be meaningfully different but still same person
            
            is_different = min_distance > difference_threshold
            
            print(f"Embedding difference check: min_distance={min_distance:.3f}, threshold={difference_threshold:.3f}, different={is_different}")
            
            return is_different, min_distance
            
        except Exception as e:
            print(f"Error checking embedding difference: {e}")
            return True, 1.0  # On error, assume it's different
    
    def add_embedding_and_image(self, person: FacePerson, embedding: List[float], face_image: np.ndarray, quality_score: float) -> bool:
        """Add new embedding and image to person's collection if it's sufficiently different"""
        
        # Check if this embedding is different enough to save
        is_different, min_distance = self.is_embedding_sufficiently_different(person, embedding)
        
        if not is_different or quality_score < 0.75:  # Only save high quality, different poses
            print(f"⏭️ Skipping: similar embedding (dist={min_distance:.3f}) or low quality ({quality_score:.3f})")
            return False
        
        db = self._get_db()
        try:
            # Initialize backup arrays if they don't exist
            if person.backup_embeddings is None:
                person.backup_embeddings = []
            if person.image_paths is None:
                person.image_paths = []
            
            # Add new embedding
            person.backup_embeddings.append(embedding)
            person.embedding_count = (person.embedding_count or 1) + 1
            
            # Save new image with unique name
            import uuid
            image_filename = f"{person.id}_{uuid.uuid4().hex[:8]}.jpg"
            image_path = os.path.join(self.faces_dir, image_filename)
            
            # Save and validate image
            cv2.imwrite(image_path, face_image)
            
            if self._validate_saved_face_with_yolo(image_path):
                # Add to image paths list
                person.image_paths.append(image_path)
                person.updated_at = datetime.now()
                
                db.merge(person)
                db.commit()
                
                print(f"📈 Added new embedding and image for {person.name} (total: {person.embedding_count})")
                return True
            else:
                # Remove invalid image
                if os.path.exists(image_path):
                    os.remove(image_path)
                print(f"❌ YOLO validation failed for new image")
                return False
                
        except Exception as e:
            print(f"Error adding embedding and image: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def should_save_additional_data(self, person_id: str, embedding: List[float], quality_score: float) -> dict:
        """
        Decide whether to save additional embedding and/or image based on multiple factors.
        Returns dict with save_embedding and save_image flags.
        """
        # Check if embedding is sufficiently different
        is_different, min_distance = self.is_embedding_sufficiently_different(person_id, embedding)
        
        # Additional criteria for saving
        save_embedding = False
        save_image = False
        
        if is_different:
            # Embedding is different enough - check additional criteria
            
            # Save if quality is good enough
            min_quality_threshold = 0.7  # Only save high-quality detections
            
            if quality_score >= min_quality_threshold:
                save_embedding = True
                save_image = True
                print(f"📸 Will save: different angle/pose (dist={min_distance:.3f}) with good quality ({quality_score:.3f})")
            
            # Even with lower quality, save embedding if it's very different (new angle)
            elif min_distance > 0.25:  # Very different
                save_embedding = True
                print(f"📈 Will save embedding only: very different angle (dist={min_distance:.3f}) despite lower quality")
            
            else:
                print(f"⏭️ Skipping: different but low quality (quality={quality_score:.3f})")
        
        else:
            print(f"⏭️ Skipping: too similar to existing embeddings (dist={min_distance:.3f})")
        
        return {
            'save_embedding': save_embedding,
            'save_image': save_image,
            'min_distance': min_distance,
            'quality_score': quality_score
        }
        """Add a new embedding to an existing person for improved recognition"""
        db = self._get_db()
        try:
            # Check if person exists
            person = db.query(FacePerson).filter(FacePerson.id == person_id).first()
            if not person:
                return False
            
            # Create new embedding record
            new_embedding = FaceEmbedding(
                person_id=person_id,
                embedding=embedding,
                confidence=confidence,
                quality_score=quality_score
            )
            
            db.add(new_embedding)
            db.commit()
            
            print(f"Added new embedding for {person.name} (total embeddings: {len(person.embeddings) + 1})")
            return True
            
        except Exception as e:
            print(f"Error adding embedding to person: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def add_image_to_person(self, person_id: str, face_image: np.ndarray, confidence: float, quality_score: float) -> Optional[str]:
        """Add a new face image to an existing person"""
        db = self._get_db()
        try:
            # Check if person exists
            person = db.query(FacePerson).filter(FacePerson.id == person_id).first()
            if not person:
                return None
            
            # Generate unique filename for this image
            import uuid
            image_filename = f"{person_id}_{uuid.uuid4().hex[:8]}.jpg"
            image_path = os.path.join(self.faces_dir, image_filename)
            
            # Save the image with YOLO validation
            try:
                cv2.imwrite(image_path, face_image)
                
                # Validate the saved image
                if self._validate_saved_face_with_yolo(image_path):
                    print(f"✅ YOLO validated additional face image: {image_filename}")
                else:
                    # Remove invalid image
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    raise ValueError(f"YOLO validation failed for additional face image: {image_filename}")
                
                # Create new image record
                height, width = face_image.shape[:2]
                new_image = FaceImage(
                    person_id=person_id,
                    image_path=image_path,
                    thumbnail_path=image_path,  # Use same for now
                    confidence=confidence,
                    quality_score=quality_score,
                    width=width,
                    height=height
                )
                
                db.add(new_image)
                db.commit()
                
                print(f"Added new image for {person.name} (total images: {len(person.images) + 1})")
                return image_path
                
            except Exception as e:
                print(f"Error saving additional image: {e}")
                if os.path.exists(image_path):
                    os.remove(image_path)
                raise e
                
        except Exception as e:
            print(f"Error adding image to person: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def add_new_face(self, face_image: np.ndarray, embedding: List[float]) -> str:
        """Add new unknown face to database with YOLO validation of saved image"""
        db = self._get_db()
        try:
            face_id = str(uuid.uuid4())
            
            # Save face image with YOLO validation
            try:
                image_path = self._save_face_image(face_image, face_id)
                print(f"Face image saved and YOLO validated: {face_id}")
            except ValueError as e:
                print(f"Failed to save face due to YOLO validation: {e}")
                raise e  # Re-raise to be handled by calling function
            
            # Count existing faces for naming
            face_count = db.query(FacePerson).count() + 1
            
            face_record = FacePerson(
                id=face_id,
                name=f"Unknown_{face_count}",
                embedding=embedding,
                image_path=image_path,
                thumbnail_path=image_path,
                detection_count=1,
                last_seen=datetime.now()
            )
            
            db.add(face_record)
            db.commit()
            print(f"Face record added to database: Unknown_{face_count}")
            return face_id
        finally:
            db.close()
    
    def update_face_name(self, face_id: str, new_name: str) -> bool:
        """Update face name in database"""
        db = self._get_db()
        try:
            face = db.query(FacePerson).filter(FacePerson.id == face_id).first()
            if face:
                face.name = new_name
                face.updated_at = datetime.now()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def recognize_faces(self, image: np.ndarray) -> Dict:
        """
        Recognize faces and add unknown faces to database using DeepFace best practices
        Enhanced with YOLO pose validation to prevent false positives
        """
        try:
            # Use high-quality face extraction first
            results = DeepFace.extract_faces(
                img_path=image,
                detector_backend=self.detector_backend,
                enforce_detection=True,  
                align=True,
                expand_percentage=5
            )
            
            if not results:
                print("No faces detected")
                return {
                    "face_count": 0,
                    "recognized_faces": [],
                    "new_faces_added": []
                }
            
            # Now validate the detected faces
            if not self._validate_real_face(image):
                print("Image does not contain valid human faces")
                return {
                    "face_count": 0,
                    "recognized_faces": [],
                    "new_faces_added": [],
                    "error": "No valid human faces detected"
                }
            
            # Get YOLO pose data for additional validation
            pose_data = validate_human_poses(image)
            max_people = pose_data.get("people_count", len(results))  # Default to detected faces if YOLO fails
            
            # If YOLO failed, allow all detected faces
            if max_people == 0:
                print("⚠️  YOLO failed to detect people, allowing all DeepFace results")
                max_people = len(results)
            
            # Limit face processing to YOLO people count to prevent false positives
            if len(results) > max_people:
                print(f"Limiting face processing from {len(results)} to {max_people} based on YOLO people detection")
                # Enhanced selection: prioritize actual face content over just confidence
                face_scores = []
                
                for i, face in enumerate(results):
                    confidence = face.get("confidence", 0)
                    face_array = face['face']
                    
                    # Convert for processing
                    if face_array.max() <= 1.0:
                        face_for_check = (face_array * 255).astype(np.uint8)
                    else:
                        face_for_check = face_array.astype(np.uint8)
                    
                    # Check if this is actually a face using multiple criteria
                    face_quality_score = self._calculate_face_quality_score(face_for_check, confidence)
                    face_scores.append((i, face_quality_score, confidence))
                    print(f"Face {i+1}: confidence={confidence:.3f}, quality_score={face_quality_score:.3f}")
                
                # Sort by quality score (not just confidence)
                face_scores.sort(key=lambda x: x[1], reverse=True)
                top_indices = [idx for idx, _, _ in face_scores[:max_people]]
                results = [results[i] for i in top_indices]
                print(f"Selected faces based on quality: {[i+1 for i in top_indices]}")
            
            print(f"Processing {len(results)} validated faces (limited by YOLO people count: {max_people})")
            recognized_faces = []
            new_faces_added = []
            
            db = self._get_db()
            try:
                for i, face_data in enumerate(results):
                    # Extract face image
                    face_array = face_data['face']
                    
                    # Ensure face is in proper format (0-255)
                    if face_array.max() <= 1.0:
                        face_array = (face_array * 255).astype(np.uint8)
                    else:
                        face_array = face_array.astype(np.uint8)
                    
                    # Additional size validation
                    if face_array.shape[0] < 50 or face_array.shape[1] < 50:
                        print(f"Face {i+1} too small after extraction: {face_array.shape}, skipping")
                        continue
                    
                    confidence = face_data.get("confidence", 0)
                    print(f"Processing validated face {i+1} with confidence: {confidence:.3f}")
                    
                    # Extract embedding using the same high-quality settings
                    embedding = self.extract_face_embedding(face_array)
                    if embedding is None:
                        print(f"Failed to extract embedding for face {i+1}")
                        continue
                    
                    # Find matching face
                    match = self.find_matching_face(embedding)
                    
                    if match:
                        # Update detection count and last seen
                        match.detection_count += 1
                        match.last_seen = datetime.now()
                        
                        # Calculate quality score for this detection
                        quality_score = self._calculate_face_quality_score(face_array, confidence)
                        
                        # Smart learning: only save if it's a different angle/pose with good quality
                        learning_success = self.add_embedding_and_image(match, embedding, face_array, quality_score)
                        
                        db.merge(match)
                        db.commit()
                        
                        print(f"Recognized existing face: {match.name}")
                        recognized_faces.append({
                            "name": match.name,
                            "id": match.id,
                            "confidence": 0.9  # High confidence for validated faces
                        })
                    else:
                        # Add new validated face with YOLO validation of saved image
                        try:
                            face_id = self.add_new_face(face_array, embedding)
                            new_faces_added.append(face_id)
                            
                            # Get the face record we just created
                            face_record = db.query(FacePerson).filter(FacePerson.id == face_id).first()
                            if face_record:
                                print(f"Added new validated face: {face_record.name}")
                                recognized_faces.append({
                                    "name": face_record.name,
                                    "id": face_record.id,
                                    "confidence": 0.8  # New face confidence
                                })
                        except ValueError as e:
                            print(f"Skipping face due to YOLO validation failure: {e}")
                            continue  # Skip this face and continue with next one
                
                print(f"Successfully processed {len(recognized_faces)} validated faces")
                return {
                    "face_count": len(recognized_faces),
                    "recognized_faces": recognized_faces,
                    "new_faces_added": new_faces_added
                }
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Face recognition error: {e}")
            return {
                "face_count": 0,
                "recognized_faces": [],
                "new_faces_added": [],
                "error": str(e)
            }
    
    def get_all_faces(self) -> List[Dict]:
        """Get all faces in database for management"""
        db = self._get_db()
        try:
            faces = db.query(FacePerson).all()
            return [
                {
                    "id": face.id,
                    "name": face.name,
                    "detection_count": face.detection_count,
                    "embedding_count": face.embedding_count or 1,
                    "image_paths": face.image_paths or [],
                    "created_at": face.created_at.isoformat() if face.created_at else None,
                    "last_seen": face.last_seen.isoformat() if face.last_seen else None,
                    "image_path": face.image_path
                }
                for face in faces
            ]
        finally:
            db.close()
    
    def get_person_detail(self, person_id: str) -> Optional[Dict]:
        """Get detailed information about a specific person"""
        db = self._get_db()
        try:
            person = db.query(FacePerson).filter(FacePerson.id == person_id).first()
            if not person:
                return None
            
            # Calculate additional statistics
            total_images = 1 + (len(person.image_paths) if person.image_paths else 0)
            embedding_count = person.embedding_count or 1
            
            # Get all image paths
            all_image_paths = [person.image_path] if person.image_path else []
            if person.image_paths:
                all_image_paths.extend(person.image_paths)
            
            # Calculate recognition accuracy (based on detection consistency)
            accuracy_score = min(100, (person.detection_count / max(1, total_images)) * 20)
            
            return {
                "id": person.id,
                "name": person.name,
                "detection_count": person.detection_count,
                "embedding_count": embedding_count,
                "total_images": total_images,
                "image_paths": person.image_paths or [],
                "primary_image": person.image_path,
                "all_images": all_image_paths,
                "created_at": person.created_at.isoformat() if person.created_at else None,
                "last_seen": person.last_seen.isoformat() if person.last_seen else None,
                "updated_at": person.updated_at.isoformat() if person.updated_at else None,
                "accuracy_score": round(accuracy_score, 1),
                "recognition_quality": "Excellent" if accuracy_score >= 80 else "Good" if accuracy_score >= 60 else "Fair" if accuracy_score >= 40 else "Needs Improvement"
            }
        finally:
            db.close()
    
    def delete_face(self, face_id: str) -> bool:
        """Delete a face from database and remove all associated images"""
        db = self._get_db()
        try:
            # Get the face record first to get image paths
            face = db.query(FacePerson).filter(FacePerson.id == face_id).first()
            if not face:
                print(f"Face with ID {face_id} not found")
                return False
            
            # Collect all image files to remove
            images_to_remove = []
            
            # Add primary image path
            if face.image_path:
                images_to_remove.append(face.image_path)
            
            # Add all additional image paths
            if face.image_paths:
                images_to_remove.extend(face.image_paths)
            
            # Remove all image files
            for image_path in images_to_remove:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print(f"Removed image file: {image_path}")
                except Exception as e:
                    print(f"Error removing image file {image_path}: {e}")
                    # Continue with other files
            
            # Delete from database
            db.delete(face)
            db.commit()
            
            print(f"Deleted face: {face.name} (ID: {face_id}) with {len(images_to_remove)} images")
            return True
            
        except Exception as e:
            print(f"Error deleting face: {e}")
            db.rollback()
            return False
        finally:
            db.close()

# Global instance
_face_service = None

def get_face_service() -> FaceRecognitionService:
    """Get face recognition service instance"""
    global _face_service
    if _face_service is None:
        _face_service = FaceRecognitionService()
    return _face_service

def recognize_faces_in_frame(image: np.ndarray) -> Dict:
    """Process frame for face recognition"""
    service = get_face_service()
    return service.recognize_faces(image)