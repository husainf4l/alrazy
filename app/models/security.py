"""
Security models and schemas for the Al Razy Pharmacy Security System.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum
import time


class ThreatLevel(str, Enum):
    """Threat level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SuspiciousActivityType(str, Enum):
    """Suspicious activity type enumeration."""
    LOITERING = "LOITERING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    SUSPICIOUS_BEHAVIOR = "SUSPICIOUS_BEHAVIOR"
    CROWD_FORMATION = "CROWD_FORMATION"
    OBJECT_LEFT_BEHIND = "OBJECT_LEFT_BEHIND"
    VIOLENCE = "VIOLENCE"
    THEFT_ATTEMPT = "THEFT_ATTEMPT"


class SecurityEvent(BaseModel):
    """Security event schema."""
    event_id: str
    camera_id: int
    activity_type: SuspiciousActivityType
    threat_level: ThreatLevel
    confidence: float
    description: str
    location: tuple
    timestamp: float
    person_id: Optional[int] = None
    evidence_frame: Optional[str] = None  # Base64 encoded
    is_confirmed: bool = False
    llm_analysis: Optional[Dict[str, Any]] = None


class SecurityStatus(BaseModel):
    """Security system status schema."""
    system_status: str
    active_cameras: int
    total_events_today: int
    current_threat_level: ThreatLevel
    active_recordings: int
    llm_enabled: bool
    last_update: float
    alerts_sent: int


class RiskAssessment(BaseModel):
    """Risk assessment schema."""
    overall_risk: ThreatLevel
    risk_factors: List[str]
    people_count: int
    suspicious_activities: int
    recommendation: str
    confidence: float
    timestamp: float


class SecurityAnalytics(BaseModel):
    """Security analytics schema."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_threat_level: Dict[str, int]
    peak_activity_hours: List[int]
    most_active_camera: Optional[int]
    average_response_time: Optional[float]
    false_positive_rate: Optional[float]


class LLMAnalysisResult(BaseModel):
    """LLM analysis result schema."""
    is_confirmed_suspicious: bool
    confidence_score: float
    reasoning: str
    threat_level: ThreatLevel
    recommended_action: str
    response_time_ms: float
    timestamp: float


class WebhookAlert(BaseModel):
    """Webhook alert schema."""
    alert_id: str
    event: SecurityEvent
    pharmacy_name: str
    timestamp: float
    priority: str
    webhook_urls: List[str]


class RecordingInfo(BaseModel):
    """Recording information schema."""
    recording_id: str
    camera_id: int
    start_time: float
    duration: Optional[float] = None
    file_path: Optional[str] = None
    trigger_event: Optional[str] = None
    status: str  # active, completed, failed
    file_size: Optional[int] = None
