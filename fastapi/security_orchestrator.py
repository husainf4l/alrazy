import asyncio
import time
import threading
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import json

from activity_detection import (
    analyze_camera_activity, 
    get_pharmacy_risk_assessment,
    SuspiciousActivity,
    get_activity_detector
)
from llm_analysis import (
    initialize_llm_analyzer,
    analyze_activity_with_llm,
    get_llm_analyzer,
    LLMAnalysisResult
)
from video_recording import (
    initialize_recording_service,
    get_recording_service
)
from webhook_alerts import (
    initialize_webhook_service,
    get_webhook_service,
    WebhookConfig
)

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Complete security event with all analysis data."""
    event_id: str
    activity: SuspiciousActivity
    llm_analysis: Optional[LLMAnalysisResult]
    incident_id: Optional[str]
    webhook_results: List[Any]
    timestamp: float
    processing_time: float

class SecurityOrchestrator:
    """Central orchestrator for the Al Razy pharmacy security system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_running = False
        self.processing_thread = None
        self.event_queue = asyncio.Queue()
        self.security_events: List[SecurityEvent] = []
        self.event_counter = 0
        
        # System status
        self.system_status = {
            "initialized": False,
            "activity_detection": False,
            "llm_analysis": False,
            "video_recording": False,
            "webhook_alerts": False,
            "last_update": time.time()
        }
        
        # Processing statistics
        self.stats = {
            "total_activities_detected": 0,
            "confirmed_threats": 0,
            "false_positives": 0,
            "recordings_created": 0,
            "alerts_sent": 0,
            "system_uptime": time.time()
        }
    
    async def initialize(self) -> bool:
        """Initialize all security system components."""
        try:
            logger.info("Initializing Al Razy Pharmacy Security System...")
            
            # Initialize LLM analyzer
            if "llm_config" in self.config:
                initialize_llm_analyzer(self.config["llm_config"])
                self.system_status["llm_analysis"] = True
                logger.info("✓ LLM analysis service initialized")
            
            # Initialize recording service
            recording_config = self.config.get("recording_config", {})
            initialize_recording_service(
                recordings_dir=recording_config.get("recordings_dir", "recordings"),
                buffer_duration=recording_config.get("buffer_duration", 30)
            )
            self.system_status["video_recording"] = True
            logger.info("✓ Video recording service initialized")
            
            # Initialize webhook service
            webhook_config = self.config.get("webhook_config", {})
            initialize_webhook_service(
                pharmacy_name=webhook_config.get("pharmacy_name", "Al Razy Pharmacy")
            )
            
            # Add configured webhooks
            webhook_service = get_webhook_service()
            if webhook_service and "webhooks" in webhook_config:
                for webhook_cfg in webhook_config["webhooks"]:
                    webhook = WebhookConfig(**webhook_cfg)
                    webhook_service.add_webhook(webhook)
            
            self.system_status["webhook_alerts"] = True
            logger.info("✓ Webhook alert service initialized")
            
            # Activity detection is always available
            self.system_status["activity_detection"] = True
            logger.info("✓ Activity detection service ready")
            
            self.system_status["initialized"] = True
            self.system_status["last_update"] = time.time()
            
            logger.info("🔒 Al Razy Pharmacy Security System READY")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize security system: {e}")
            return False
    
    async def process_camera_frame(self, camera_id: int, frame) -> List[SuspiciousActivity]:
        """Process a camera frame for suspicious activities."""
        try:
            # Add frame to recording buffer
            recording_service = get_recording_service()
            if recording_service:
                recording_service.add_frame_to_buffer(camera_id, frame)
            
            # Analyze frame for suspicious activities
            activities = analyze_camera_activity(camera_id, frame)
            
            if activities:
                logger.info(f"Detected {len(activities)} suspicious activities on camera {camera_id}")
                
                # Queue activities for processing
                for activity in activities:
                    await self.event_queue.put(activity)
                    self.stats["total_activities_detected"] += 1
            
            return activities
            
        except Exception as e:
            logger.error(f"Error processing camera {camera_id} frame: {e}")
            return []
    
    async def _process_security_event(self, activity: SuspiciousActivity) -> SecurityEvent:
        """Process a single suspicious activity through the complete security pipeline."""
        start_time = time.time()
        self.event_counter += 1
        event_id = f"event_{int(time.time())}_{self.event_counter}"
        
        logger.info(f"Processing security event {event_id}: {activity.activity_type.value}")
        
        # Step 1: LLM Analysis
        llm_analysis = None
        llm_analyzer = get_llm_analyzer()
        if llm_analyzer:
            try:
                # Get current pharmacy context
                risk_assessment = get_pharmacy_risk_assessment()
                context = {
                    "total_people": risk_assessment.get("total_active_people", 0),
                    "risk_level": risk_assessment.get("pharmacy_risk_level", "UNKNOWN"),
                    "recent_activities": risk_assessment.get("total_recent_activities", 0),
                    "business_hours": "8:00 AM - 10:00 PM",
                }
                
                llm_analysis = await analyze_activity_with_llm(activity, context)
                
                if llm_analysis and llm_analysis.is_confirmed_suspicious:
                    self.stats["confirmed_threats"] += 1
                else:
                    self.stats["false_positives"] += 1
                    
                logger.info(f"LLM Analysis: {llm_analysis.threat_level if llm_analysis else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
        
        # Step 2: Video Recording
        incident_id = None
        recording_service = get_recording_service()
        if recording_service:
            try:
                incident_id = await recording_service.handle_suspicious_activity(activity, llm_analysis)
                if incident_id:
                    self.stats["recordings_created"] += 1
                    logger.info(f"Recording started: {incident_id}")
            except Exception as e:
                logger.error(f"Recording failed: {e}")
        
        # Step 3: Webhook Alerts
        webhook_results = []
        webhook_service = get_webhook_service()
        if webhook_service:
            try:
                async with webhook_service:
                    webhook_results = await webhook_service.send_security_alert(
                        activity=activity,
                        llm_analysis=llm_analysis,
                        incident_id=incident_id,
                        recording_available=incident_id is not None
                    )
                
                successful_alerts = sum(1 for r in webhook_results if r.success)
                self.stats["alerts_sent"] += successful_alerts
                logger.info(f"Alerts sent: {successful_alerts}/{len(webhook_results)}")
                
            except Exception as e:
                logger.error(f"Webhook alerts failed: {e}")
        
        # Create security event
        processing_time = time.time() - start_time
        event = SecurityEvent(
            event_id=event_id,
            activity=activity,
            llm_analysis=llm_analysis,
            incident_id=incident_id,
            webhook_results=webhook_results,
            timestamp=activity.timestamp,
            processing_time=processing_time
        )
        
        self.security_events.append(event)
        
        logger.info(f"Security event {event_id} processed in {processing_time:.2f}s")
        return event
    
    async def _event_processor(self):
        """Background processor for security events."""
        logger.info("Security event processor started")
        
        while self.is_running:
            try:
                # Wait for activity with timeout
                activity = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Process the activity
                await self._process_security_event(activity)
                
                # Mark task done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Normal timeout, check if still running
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop
    
    def start(self):
        """Start the security system."""
        if self.is_running:
            logger.warning("Security system is already running")
            return
        
        self.is_running = True
        
        # Start event processor in background thread
        def run_processor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._event_processor())
            loop.close()
        
        self.processing_thread = threading.Thread(target=run_processor)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("🔒 Security system started and monitoring")
    
    def stop(self):
        """Stop the security system."""
        if not self.is_running:
            return
        
        logger.info("Stopping security system...")
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        # Stop all recordings
        recording_service = get_recording_service()
        if recording_service:
            recording_service.stop_all_recordings()
        
        logger.info("Security system stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        # Update status
        self.system_status["last_update"] = time.time()
        
        # Get component statuses
        recording_service = get_recording_service()
        webhook_service = get_webhook_service()
        
        return {
            "system": self.system_status,
            "running": self.is_running,
            "uptime_hours": (time.time() - self.stats["system_uptime"]) / 3600,
            "statistics": self.stats.copy(),
            "event_queue_size": self.event_queue.qsize() if hasattr(self.event_queue, 'qsize') else 0,
            "recent_events": len([
                e for e in self.security_events[-10:]  # Last 10 events
            ]),
            "components": {
                "activity_detection": True,  # Always available
                "llm_analysis": get_llm_analyzer() is not None,
                "video_recording": recording_service is not None,
                "webhook_alerts": webhook_service is not None
            },
            "pharmacy_risk": get_pharmacy_risk_assessment()
        }
    
    def get_recent_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent security events."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_events = []
        for event in self.security_events:
            if event.timestamp >= cutoff_time:
                recent_events.append({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "camera_id": event.activity.camera_id,
                    "activity_type": event.activity.activity_type.value,
                    "confidence": event.activity.confidence,
                    "threat_level": event.llm_analysis.threat_level if event.llm_analysis else "UNKNOWN",
                    "confirmed_suspicious": event.llm_analysis.is_confirmed_suspicious if event.llm_analysis else None,
                    "recording_created": event.incident_id is not None,
                    "alerts_sent": len(event.webhook_results),
                    "processing_time": event.processing_time
                })
        
        return sorted(recent_events, key=lambda x: x["timestamp"], reverse=True)
    
    def get_security_analytics(self) -> Dict[str, Any]:
        """Get security analytics and insights."""
        recent_events = self.get_recent_events(24)  # Last 24 hours
        
        if not recent_events:
            return {"message": "No recent security events"}
        
        # Activity analysis
        activity_types = [e["activity_type"] for e in recent_events]
        activity_distribution = {
            activity: activity_types.count(activity) 
            for activity in set(activity_types)
        }
        
        # Threat analysis
        threat_levels = [e["threat_level"] for e in recent_events if e["threat_level"] != "UNKNOWN"]
        threat_distribution = {
            level: threat_levels.count(level)
            for level in set(threat_levels)
        }
        
        # Camera analysis
        camera_activity = {}
        for event in recent_events:
            camera_id = event["camera_id"]
            if camera_id not in camera_activity:
                camera_activity[camera_id] = 0
            camera_activity[camera_id] += 1
        
        # Performance metrics
        avg_processing_time = sum(e["processing_time"] for e in recent_events) / len(recent_events)
        confirmed_threats = [e for e in recent_events if e.get("confirmed_suspicious", False)]
        
        return {
            "period": "24 hours",
            "total_events": len(recent_events),
            "confirmed_threats": len(confirmed_threats),
            "false_positive_rate": (len(recent_events) - len(confirmed_threats)) / len(recent_events),
            "activity_distribution": activity_distribution,
            "threat_distribution": threat_distribution,
            "camera_activity": camera_activity,
            "most_active_camera": max(camera_activity.items(), key=lambda x: x[1])[0] if camera_activity else None,
            "recordings_created": sum(1 for e in recent_events if e["recording_created"]),
            "average_processing_time": avg_processing_time,
            "peak_activity_hour": self._get_peak_activity_hour(recent_events)
        }
    
    def _get_peak_activity_hour(self, events: List[Dict[str, Any]]) -> Optional[int]:
        """Get the hour of day with most activity."""
        if not events:
            return None
        
        hours = [int(time.strftime("%H", time.localtime(e["timestamp"]))) for e in events]
        hour_counts = {hour: hours.count(hour) for hour in set(hours)}
        
        return max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None

# Global security orchestrator
security_orchestrator: Optional[SecurityOrchestrator] = None

def initialize_security_system(config: Dict[str, Any]) -> SecurityOrchestrator:
    """Initialize the complete security system."""
    global security_orchestrator
    security_orchestrator = SecurityOrchestrator(config)
    return security_orchestrator

def get_security_orchestrator() -> Optional[SecurityOrchestrator]:
    """Get the global security orchestrator."""
    return security_orchestrator

# Default configuration for Al Razy Pharmacy
def get_default_config() -> Dict[str, Any]:
    """Get default configuration for Al Razy Pharmacy."""
    return {
        "pharmacy_name": "Al Razy Pharmacy",
        "llm_config": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "",  # Must be provided
            "model": "gpt-4o-mini",
            "max_retries": 3,
            "timeout": 30
        },
        "recording_config": {
            "recordings_dir": "recordings",
            "buffer_duration": 30,  # seconds of pre-incident footage
            "auto_record_on_threat_levels": ["HIGH", "CRITICAL"],
            "default_recording_duration": 60,
            "max_concurrent_recordings": 4
        },
        "webhook_config": {
            "pharmacy_name": "Al Razy Pharmacy",
            "webhooks": [
                # Example webhook configurations
                # {
                #     "name": "slack_security",
                #     "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                #     "trigger_conditions": ["MEDIUM", "HIGH", "CRITICAL"],
                #     "enabled": True
                # },
                # {
                #     "name": "management_api",
                #     "url": "https://your-api.com/security-alerts",
                #     "secret_token": "your-secret-token",
                #     "trigger_conditions": ["HIGH", "CRITICAL"],
                #     "enabled": True
                # }
            ]
        },
        "activity_detection": {
            "loiter_threshold": 45.0,  # seconds
            "movement_threshold": 50.0,  # pixels
            "rapid_movement_threshold": 200.0,  # pixels per second
            "max_people_per_zone": 2
        }
    }
