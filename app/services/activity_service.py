import cv2
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import logging
import threading
from enum import Enum

logger = logging.getLogger(__name__)

class SuspiciousActivityType(Enum):
    """Types of suspicious activities for pharmacy theft detection."""
    LOITERING = "loitering"
    TAKING_WITHOUT_PAYING = "taking_without_paying"
    MULTIPLE_PEOPLE_RESTRICTED = "multiple_people_restricted"
    UNUSUAL_MOVEMENT = "unusual_movement"
    RAPID_GRABBING = "rapid_grabbing"
    CONCEALING_ITEMS = "concealing_items"
    EXIT_WITHOUT_PAYMENT = "exit_without_payment"
    AFTER_HOURS_ACTIVITY = "after_hours_activity"

@dataclass
class Person:
    """Represents a tracked person in the pharmacy."""
    id: int
    last_position: Tuple[int, int]
    positions: deque = field(default_factory=lambda: deque(maxlen=30))  # Last 30 positions
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    time_in_area: float = 0.0
    total_movement: float = 0.0
    is_in_restricted_area: bool = False
    has_taken_items: bool = False
    movement_pattern: List[str] = field(default_factory=list)
    suspicious_actions: List[str] = field(default_factory=list)
    risk_score: float = 0.0

@dataclass
class PharmacyZone:
    """Defines different zones in the pharmacy with specific rules."""
    name: str
    coordinates: Tuple[int, int, int, int]  # x1, y1, x2, y2
    zone_type: str  # "checkout", "medicine", "restricted", "entrance", "exit"
    max_loiter_time: float = 30.0  # seconds
    max_people: int = 3

@dataclass
class SuspiciousActivity:
    """Represents a detected suspicious activity."""
    activity_type: SuspiciousActivityType
    person_id: int
    camera_id: int
    timestamp: float
    confidence: float
    description: str
    location: Tuple[int, int]
    threat_level: str = "MEDIUM"  # MINIMAL, LOW, MEDIUM, HIGH, CRITICAL
    evidence_frame: Optional[np.ndarray] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

class AdvancedActivityDetector:
    """Advanced activity detection system for pharmacy security."""
    
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self.people_tracker = {}  # Dict[int, Person]
        self.next_person_id = 1
        self.pharmacy_zones = self._setup_pharmacy_zones()
        self.suspicious_activities = deque(maxlen=100)
        self.detection_lock = threading.Lock()
        
        # Detection parameters
        self.loiter_threshold = 45.0  # seconds
        self.movement_threshold = 50.0  # pixels
        self.rapid_movement_threshold = 200.0  # pixels in 1 second
        self.max_people_per_zone = 2
        
        # Computer vision setup
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        # Note: OpenCV tracker not currently used in this implementation
        self.tracker = None  # Placeholder for future tracker integration
        self.tracking_boxes = {}
        
        # Activity analysis
        self.frame_count = 0
        self.analysis_interval = 30  # frames
        
    def _setup_pharmacy_zones(self) -> Dict[str, PharmacyZone]:
        """Setup pharmacy zones based on camera position."""
        # These coordinates would be adjusted based on actual camera view
        zones = {
            "entrance": PharmacyZone("entrance", (0, 0, 200, 400), "entrance", 10.0, 5),
            "checkout": PharmacyZone("checkout", (500, 300, 800, 500), "checkout", 120.0, 3),
            "medicine_aisle": PharmacyZone("medicine_aisle", (200, 100, 600, 300), "medicine", 60.0, 4),
            "restricted_medicine": PharmacyZone("restricted_medicine", (600, 50, 800, 200), "restricted", 20.0, 1),
            "exit": PharmacyZone("exit", (800, 0, 1000, 400), "exit", 15.0, 3),
            "behind_counter": PharmacyZone("behind_counter", (300, 0, 700, 100), "restricted", 5.0, 1)
        }
        return zones
    
    def detect_people(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect people in the frame using OpenCV."""
        # Use HOG descriptor for person detection
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Detect people
        boxes, weights = hog.detectMultiScale(frame, winStride=(8, 8), padding=(32, 32), scale=1.05)
        
        # Filter out weak detections
        filtered_boxes = []
        for i, (box, weight) in enumerate(zip(boxes, weights)):
            if weight > 0.5:  # Confidence threshold
                x, y, w, h = box
                filtered_boxes.append((x, y, x + w, y + h))
        
        return filtered_boxes
    
    def update_person_tracking(self, frame: np.ndarray, detected_boxes: List[Tuple[int, int, int, int]]):
        """Update person tracking with new detections."""
        current_time = time.time()
        
        # Match detections to existing tracks
        matched_people = {}
        
        for box in detected_boxes:
            x1, y1, x2, y2 = box
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Find closest existing person
            closest_person = None
            min_distance = float('inf')
            
            for person_id, person in self.people_tracker.items():
                if person_id in matched_people:
                    continue
                    
                last_x, last_y = person.last_position
                distance = np.sqrt((center_x - last_x)**2 + (center_y - last_y)**2)
                
                if distance < min_distance and distance < 100:  # 100 pixel threshold
                    min_distance = distance
                    closest_person = person_id
            
            if closest_person:
                # Update existing person
                person = self.people_tracker[closest_person]
                person.last_position = (center_x, center_y)
                person.positions.append((center_x, center_y))
                person.last_seen = current_time
                person.time_in_area = current_time - person.first_seen
                
                # Calculate movement
                if len(person.positions) > 1:
                    prev_x, prev_y = person.positions[-2]
                    movement = np.sqrt((center_x - prev_x)**2 + (center_y - prev_y)**2)
                    person.total_movement += movement
                
                matched_people[closest_person] = True
            else:
                # Create new person
                new_person = Person(
                    id=self.next_person_id,
                    last_position=(center_x, center_y)
                )
                new_person.positions.append((center_x, center_y))
                self.people_tracker[self.next_person_id] = new_person
                self.next_person_id += 1
        
        # Remove people who haven't been seen for a while
        people_to_remove = []
        for person_id, person in self.people_tracker.items():
            if current_time - person.last_seen > 5.0:  # 5 seconds
                people_to_remove.append(person_id)
        
        for person_id in people_to_remove:
            del self.people_tracker[person_id]
    
    def analyze_person_behavior(self, person: Person) -> List[SuspiciousActivity]:
        """Analyze a person's behavior for suspicious activities."""
        suspicious_activities = []
        current_time = time.time()
        
        # Check for loitering
        if person.time_in_area > self.loiter_threshold:
            threat_level = "HIGH" if person.time_in_area > 120 else "MEDIUM"
            activity = SuspiciousActivity(
                activity_type=SuspiciousActivityType.LOITERING,
                person_id=person.id,
                camera_id=self.camera_id,
                timestamp=current_time,
                confidence=min(0.9, person.time_in_area / 60.0),
                description=f"Person {person.id} has been loitering for {person.time_in_area:.1f} seconds",
                location=person.last_position,
                threat_level=threat_level,
                additional_data={"time_in_area": person.time_in_area}
            )
            suspicious_activities.append(activity)
        
        # Check for rapid movement (potentially grabbing items quickly)
        if len(person.positions) > 10:
            recent_positions = list(person.positions)[-10:]
            total_recent_movement = 0
            for i in range(1, len(recent_positions)):
                x1, y1 = recent_positions[i-1]
                x2, y2 = recent_positions[i]
                total_recent_movement += np.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            if total_recent_movement > self.rapid_movement_threshold:
                activity = SuspiciousActivity(
                    activity_type=SuspiciousActivityType.RAPID_GRABBING,
                    person_id=person.id,
                    camera_id=self.camera_id,
                    timestamp=current_time,
                    confidence=0.7,
                    description=f"Person {person.id} showing rapid movement pattern (potential item grabbing)",
                    location=person.last_position,
                    threat_level="HIGH",
                    additional_data={"recent_movement": total_recent_movement}
                )
                suspicious_activities.append(activity)
        
        # Check if person is in restricted area
        person_zone = self._get_person_zone(person.last_position)
        if person_zone and person_zone.zone_type == "restricted":
            if not person.is_in_restricted_area:
                person.is_in_restricted_area = True
                activity = SuspiciousActivity(
                    activity_type=SuspiciousActivityType.MULTIPLE_PEOPLE_RESTRICTED,
                    person_id=person.id,
                    camera_id=self.camera_id,
                    timestamp=current_time,
                    confidence=0.8,
                    description=f"Person {person.id} entered restricted area: {person_zone.name}",
                    location=person.last_position,
                    threat_level="CRITICAL",
                    additional_data={"zone": person_zone.name}
                )
                suspicious_activities.append(activity)
        else:
            person.is_in_restricted_area = False
        
        # Check for unusual movement patterns
        if len(person.positions) > 20:
            movement_pattern = self._analyze_movement_pattern(person.positions)
            if "erratic" in movement_pattern or "circling" in movement_pattern:
                threat_level = "MEDIUM" if "erratic" in movement_pattern else "LOW"
                activity = SuspiciousActivity(
                    activity_type=SuspiciousActivityType.UNUSUAL_MOVEMENT,
                    person_id=person.id,
                    camera_id=self.camera_id,
                    timestamp=current_time,
                    confidence=0.6,
                    description=f"Person {person.id} showing unusual movement pattern: {movement_pattern}",
                    location=person.last_position,
                    threat_level=threat_level,
                    additional_data={"pattern": movement_pattern}
                )
                suspicious_activities.append(activity)
        
        return suspicious_activities
    
    def _get_person_zone(self, position: Tuple[int, int]) -> Optional[PharmacyZone]:
        """Determine which zone a person is currently in."""
        x, y = position
        
        for zone in self.pharmacy_zones.values():
            x1, y1, x2, y2 = zone.coordinates
            if x1 <= x <= x2 and y1 <= y <= y2:
                return zone
        
        return None
    
    def _analyze_movement_pattern(self, positions: deque) -> str:
        """Analyze movement pattern to detect suspicious behavior."""
        positions_list = list(positions)
        
        if len(positions_list) < 10:
            return "normal"
        
        # Calculate direction changes
        direction_changes = 0
        for i in range(2, len(positions_list)):
            x1, y1 = positions_list[i-2]
            x2, y2 = positions_list[i-1]
            x3, y3 = positions_list[i]
            
            # Calculate vectors
            v1 = (x2 - x1, y2 - y1)
            v2 = (x3 - x2, y3 - y2)
            
            # Calculate angle between vectors
            if v1 != (0, 0) and v2 != (0, 0):
                dot_product = v1[0]*v2[0] + v1[1]*v2[1]
                mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
                mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
                
                if mag1 > 0 and mag2 > 0:
                    cos_angle = dot_product / (mag1 * mag2)
                    cos_angle = max(-1, min(1, cos_angle))  # Clamp to [-1, 1]
                    angle = np.arccos(cos_angle)
                    
                    if angle > np.pi/2:  # Sharp direction change
                        direction_changes += 1
        
        # Analyze pattern
        change_ratio = direction_changes / len(positions_list)
        
        if change_ratio > 0.3:
            return "erratic"
        elif self._is_circling(positions_list):
            return "circling"
        elif self._is_back_and_forth(positions_list):
            return "back_and_forth"
        else:
            return "normal"
    
    def _is_circling(self, positions: List[Tuple[int, int]]) -> bool:
        """Check if the person is moving in circles."""
        if len(positions) < 15:
            return False
        
        # Check if the person returns to similar positions multiple times
        start_pos = positions[0]
        returns = 0
        
        for i, pos in enumerate(positions[5:], 5):  # Skip first 5 positions
            distance = np.sqrt((pos[0] - start_pos[0])**2 + (pos[1] - start_pos[1])**2)
            if distance < 50:  # Within 50 pixels of start
                returns += 1
        
        return returns >= 2
    
    def _is_back_and_forth(self, positions: List[Tuple[int, int]]) -> bool:
        """Check if the person is moving back and forth."""
        if len(positions) < 10:
            return False
        
        # Check for repeated reversals along the same axis
        x_reversals = 0
        y_reversals = 0
        
        for i in range(2, len(positions)):
            x_prev = positions[i-1][0] - positions[i-2][0]
            x_curr = positions[i][0] - positions[i-1][0]
            
            y_prev = positions[i-1][1] - positions[i-2][1]
            y_curr = positions[i][1] - positions[i-1][1]
            
            if x_prev * x_curr < 0:  # Sign change in x direction
                x_reversals += 1
            if y_prev * y_curr < 0:  # Sign change in y direction
                y_reversals += 1
        
        return max(x_reversals, y_reversals) > len(positions) * 0.3
    
    def analyze_frame(self, frame: np.ndarray) -> List[SuspiciousActivity]:
        """Main method to analyze a frame for suspicious activities."""
        with self.detection_lock:
            self.frame_count += 1
            
            # Detect people in the frame
            detected_boxes = self.detect_people(frame)
            
            # Update person tracking
            self.update_person_tracking(frame, detected_boxes)
            
            # Analyze behavior every N frames
            if self.frame_count % self.analysis_interval == 0:
                suspicious_activities = []
                
                for person in self.people_tracker.values():
                    activities = self.analyze_person_behavior(person)
                    suspicious_activities.extend(activities)
                
                # Store activities
                for activity in suspicious_activities:
                    activity.evidence_frame = frame.copy()
                    self.suspicious_activities.append(activity)
                
                return suspicious_activities
            
            return []
    
    def get_recent_activities(self, time_window: float = 300.0) -> List[SuspiciousActivity]:
        """Get suspicious activities from the last time_window seconds."""
        current_time = time.time()
        recent_activities = [
            activity for activity in self.suspicious_activities
            if current_time - activity.timestamp <= time_window
        ]
        return recent_activities
    
    def get_risk_assessment(self) -> Dict[str, Any]:
        """Get overall risk assessment for the pharmacy."""
        current_time = time.time()
        recent_activities = self.get_recent_activities(300.0)  # Last 5 minutes
        
        # Count activities by type
        activity_counts = {}
        for activity in recent_activities:
            activity_type = activity.activity_type.value
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
        
        # Calculate risk score
        risk_score = 0.0
        risk_factors = []
        
        if activity_counts.get("loitering", 0) > 2:
            risk_score += 0.3
            risk_factors.append("Multiple loitering incidents")
        
        if activity_counts.get("taking_without_paying", 0) > 0:
            risk_score += 0.5
            risk_factors.append("Potential theft detected")
        
        if activity_counts.get("multiple_people_restricted", 0) > 0:
            risk_score += 0.4
            risk_factors.append("Unauthorized access to restricted areas")
        
        if len(self.people_tracker) > 8:  # Too many people
            risk_score += 0.2
            risk_factors.append("High customer density")
        
        return {
            "risk_score": min(1.0, risk_score),
            "risk_level": self._get_risk_level(risk_score),
            "active_people": len(self.people_tracker),
            "recent_activities": len(recent_activities),
            "activity_breakdown": activity_counts,
            "risk_factors": risk_factors,
            "timestamp": current_time
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to human-readable level."""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        elif risk_score >= 0.2:
            return "LOW"
        else:
            return "MINIMAL"

# Global activity detectors for all cameras
activity_detectors: Dict[int, AdvancedActivityDetector] = {}

def get_activity_detector(camera_id: int) -> AdvancedActivityDetector:
    """Get or create activity detector for a camera."""
    if camera_id not in activity_detectors:
        activity_detectors[camera_id] = AdvancedActivityDetector(camera_id)
    return activity_detectors[camera_id]

def analyze_camera_activity(camera_id: int, frame: np.ndarray) -> List[SuspiciousActivity]:
    """Analyze a frame for suspicious activities."""
    detector = get_activity_detector(camera_id)
    return detector.analyze_frame(frame)

def get_pharmacy_risk_assessment() -> Dict[str, Any]:
    """Get overall pharmacy risk assessment from all cameras."""
    overall_risk = {
        "pharmacy_risk_score": 0.0,
        "pharmacy_risk_level": "MINIMAL",
        "total_active_people": 0,
        "total_recent_activities": 0,
        "camera_assessments": {},
        "combined_risk_factors": [],
        "timestamp": time.time()
    }
    
    if not activity_detectors:
        return overall_risk
    
    total_risk = 0.0
    all_risk_factors = []
    
    for camera_id, detector in activity_detectors.items():
        assessment = detector.get_risk_assessment()
        overall_risk["camera_assessments"][camera_id] = assessment
        overall_risk["total_active_people"] += assessment["active_people"]
        overall_risk["total_recent_activities"] += assessment["recent_activities"]
        
        total_risk += assessment["risk_score"]
        all_risk_factors.extend(assessment["risk_factors"])
    
    # Calculate average risk
    overall_risk["pharmacy_risk_score"] = total_risk / len(activity_detectors)
    overall_risk["pharmacy_risk_level"] = activity_detectors[1]._get_risk_level(overall_risk["pharmacy_risk_score"])
    overall_risk["combined_risk_factors"] = list(set(all_risk_factors))  # Remove duplicates
    
    return overall_risk
