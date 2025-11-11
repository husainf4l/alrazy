"""
YOLO People Detection Service
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os

class YOLOPeopleDetector:
    def __init__(self):
        self.model_path = "yolo-models/yolo11m-pose.pt"
        self.model = None
        self._load_model()
    
    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                print(f"YOLO model loaded: {self.model_path}")
            else:
                print(f"Model not found: {self.model_path}")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None
    
    def detect_people_with_poses(self, image: np.ndarray) -> dict:
        """
        Detect people with pose information for face validation
        Returns detailed information about detected people and their poses
        """
        if self.model is None:
            return {"people_count": 0, "valid_poses": 0, "pose_data": []}
        
        try:
            results = self.model(image, conf=0.75, verbose=False)
            people_data = []
            valid_poses = 0
            
            for result in results:
                if result.boxes is not None and result.keypoints is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    keypoints = result.keypoints.xy.cpu().numpy()
                    
                    for i, cls in enumerate(classes):
                        if int(cls) == 0:  # Person class
                            box = boxes[i]
                            confidence = confidences[i]
                            pose_points = keypoints[i]
                            
                            # Validate pose has key facial landmarks
                            face_landmarks = self._extract_face_landmarks(pose_points)
                            has_valid_pose = self._validate_human_pose(pose_points, face_landmarks)
                            
                            person_data = {
                                "bbox": box.tolist(),
                                "confidence": float(confidence),
                                "pose_points": pose_points.tolist(),
                                "face_landmarks": face_landmarks,
                                "has_valid_pose": has_valid_pose,
                                "head_region": self._get_head_region(pose_points, box)
                            }
                            
                            people_data.append(person_data)
                            if has_valid_pose:
                                valid_poses += 1
            
            return {
                "people_count": len(people_data),
                "valid_poses": valid_poses,
                "pose_data": people_data
            }
            
        except Exception as e:
            print(f"YOLO pose detection error: {e}")
            return {"people_count": 0, "valid_poses": 0, "pose_data": []}
    
    def _extract_face_landmarks(self, pose_points):
        """Extract facial landmarks from YOLO pose points"""
        # YOLO pose keypoints indices for face
        # 0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear
        face_indices = [0, 1, 2, 3, 4]
        face_landmarks = {}
        
        for i, name in enumerate(['nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear']):
            if i < len(pose_points):
                x, y = pose_points[i]
                if x > 0 and y > 0:  # Valid landmark
                    face_landmarks[name] = [float(x), float(y)]
        
        return face_landmarks
    
    def _validate_human_pose(self, pose_points, face_landmarks):
        """Validate if pose indicates a real human with proper facial structure"""
        try:
            # Check if we have essential facial landmarks
            required_landmarks = ['nose', 'left_eye', 'right_eye']
            has_required = all(landmark in face_landmarks for landmark in required_landmarks)
            
            if not has_required:
                return False
            
            # Check facial geometry - eyes should be approximately horizontal
            if 'left_eye' in face_landmarks and 'right_eye' in face_landmarks:
                left_eye = face_landmarks['left_eye']
                right_eye = face_landmarks['right_eye']
                
                # Calculate eye distance and vertical alignment
                eye_distance = abs(left_eye[0] - right_eye[0])
                eye_height_diff = abs(left_eye[1] - right_eye[1])
                
                if eye_distance < 10:  # Eyes too close
                    return False
                
                if eye_height_diff > eye_distance * 0.3:  # Eyes too misaligned
                    return False
            
            # Check if nose is between eyes (basic facial structure)
            if 'nose' in face_landmarks and 'left_eye' in face_landmarks and 'right_eye' in face_landmarks:
                nose = face_landmarks['nose']
                left_eye = face_landmarks['left_eye']
                right_eye = face_landmarks['right_eye']
                
                # Nose should be between eyes horizontally
                if not (min(left_eye[0], right_eye[0]) <= nose[0] <= max(left_eye[0], right_eye[0])):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _get_head_region(self, pose_points, bbox):
        """Extract approximate head region from pose and bounding box"""
        try:
            # Get facial landmarks
            face_landmarks = self._extract_face_landmarks(pose_points)
            
            if len(face_landmarks) >= 2:
                # Calculate head region based on facial landmarks
                x_coords = [pt[0] for pt in face_landmarks.values()]
                y_coords = [pt[1] for pt in face_landmarks.values()]
                
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # Expand region for full head
                width = max_x - min_x
                height = max_y - min_y
                
                # Expand by 50% to include full head
                expansion = 0.5
                head_x = max(0, min_x - width * expansion)
                head_y = max(0, min_y - height * expansion)
                head_w = width * (1 + 2 * expansion)
                head_h = height * (1 + 2 * expansion)
                
                return {
                    "x": head_x,
                    "y": head_y,
                    "w": head_w,
                    "h": head_h
                }
            else:
                # Fallback to upper portion of bounding box
                x, y, x2, y2 = bbox
                head_height = (y2 - y) * 0.3  # Top 30% of person
                return {
                    "x": x,
                    "y": y,
                    "w": x2 - x,
                    "h": head_height
                }
                
        except Exception:
            return None

    def detect_people(self, image: np.ndarray) -> int:
        """Detect number of people in image"""
        if self.model is None:
            return 0
        
        try:
            results = self.model(image, conf=0.75, verbose=False)
            people_count = 0
            
            for result in results:
                if result.boxes is not None:
                    classes = result.boxes.cls.cpu().numpy()
                    people_count += sum(1 for cls in classes if int(cls) == 0)
            
            return people_count
        except:
            return 0

# Global instance
_detector = None

def get_people_count(image: np.ndarray) -> int:
    """Get number of people in image"""
    global _detector
    if _detector is None:
        _detector = YOLOPeopleDetector()
    return _detector.detect_people(image)

def validate_human_poses(image: np.ndarray) -> dict:
    """
    Validate human poses in image for face recognition validation
    Returns pose validation data to help confirm detected faces belong to real humans
    """
    global _detector
    if _detector is None:
        _detector = YOLOPeopleDetector()
    return _detector.detect_people_with_poses(image)