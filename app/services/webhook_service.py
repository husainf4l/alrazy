import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from activity_detection import SuspiciousActivity
from llm_analysis import LLMAnalysisResult
import base64
import os

logger = logging.getLogger(__name__)

@dataclass
class WebhookConfig:
    """Configuration for webhook endpoints."""
    name: str
    url: str
    secret_token: Optional[str] = None
    headers: Dict[str, str] = None
    enabled: bool = True
    retry_attempts: int = 3
    timeout: int = 30
    trigger_conditions: List[str] = None  # Threat levels that trigger this webhook

@dataclass
class AlertPayload:
    """Standard alert payload for webhooks."""
    alert_id: str
    timestamp: float
    pharmacy_name: str
    camera_id: int
    alert_type: str
    threat_level: str
    confidence_score: float
    activity_description: str
    llm_reasoning: Optional[str]
    recommended_action: str
    location: Dict[str, int]
    incident_id: Optional[str] = None
    recording_available: bool = False
    evidence_urls: List[str] = None
    additional_data: Dict[str, Any] = None

@dataclass
class WebhookDeliveryResult:
    """Result of webhook delivery attempt."""
    webhook_name: str
    success: bool
    status_code: Optional[int]
    response_data: Optional[str]
    error_message: Optional[str]
    delivery_time: float
    attempt_number: int

class WebhookAlertService:
    """Service for sending security alerts via webhooks."""
    
    def __init__(self, pharmacy_name: str = "Al Razy Pharmacy"):
        self.pharmacy_name = pharmacy_name
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.delivery_history: List[Dict[str, Any]] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Alert configuration
        self.alert_counter = 0
        self.rate_limit_cache: Dict[str, List[float]] = {}  # For rate limiting
        self.max_alerts_per_minute = 10
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def add_webhook(self, config: WebhookConfig):
        """Add a webhook endpoint."""
        self.webhooks[config.name] = config
        logger.info(f"Added webhook: {config.name} -> {config.url}")
    
    def remove_webhook(self, name: str) -> bool:
        """Remove a webhook endpoint."""
        if name in self.webhooks:
            del self.webhooks[name]
            logger.info(f"Removed webhook: {name}")
            return True
        return False
    
    def _should_trigger_webhook(self, webhook: WebhookConfig, threat_level: str) -> bool:
        """Check if webhook should be triggered for this threat level."""
        if not webhook.enabled:
            return False
        
        if webhook.trigger_conditions is None:
            return True  # Trigger for all if no conditions specified
        
        return threat_level in webhook.trigger_conditions
    
    def _check_rate_limit(self, webhook_name: str) -> bool:
        """Check if webhook is within rate limits."""
        current_time = time.time()
        
        if webhook_name not in self.rate_limit_cache:
            self.rate_limit_cache[webhook_name] = []
        
        # Clean old entries (older than 1 minute)
        self.rate_limit_cache[webhook_name] = [
            t for t in self.rate_limit_cache[webhook_name]
            if current_time - t < 60
        ]
        
        # Check if under limit
        if len(self.rate_limit_cache[webhook_name]) >= self.max_alerts_per_minute:
            return False
        
        # Add current time
        self.rate_limit_cache[webhook_name].append(current_time)
        return True
    
    def _create_alert_payload(
        self,
        activity: SuspiciousActivity,
        llm_analysis: Optional[LLMAnalysisResult] = None,
        incident_id: Optional[str] = None,
        recording_available: bool = False
    ) -> AlertPayload:
        """Create standardized alert payload."""
        
        self.alert_counter += 1
        alert_id = f"alert_{int(time.time())}_{self.alert_counter}"
        
        return AlertPayload(
            alert_id=alert_id,
            timestamp=activity.timestamp,
            pharmacy_name=self.pharmacy_name,
            camera_id=activity.camera_id,
            alert_type=activity.activity_type.value,
            threat_level=llm_analysis.threat_level if llm_analysis else "UNKNOWN",
            confidence_score=llm_analysis.confidence_score if llm_analysis else activity.confidence,
            activity_description=activity.description,
            llm_reasoning=llm_analysis.reasoning if llm_analysis else None,
            recommended_action=llm_analysis.recommended_action if llm_analysis else "MONITOR",
            location={"x": activity.location[0], "y": activity.location[1]},
            incident_id=incident_id,
            recording_available=recording_available,
            evidence_urls=[],
            additional_data={
                "person_id": activity.person_id,
                "camera_id": activity.camera_id,
                "additional_activity_data": activity.additional_data
            }
        )
    
    async def _send_webhook(
        self,
        webhook: WebhookConfig,
        payload: AlertPayload,
        include_image: bool = True,
        evidence_frame: Optional[object] = None
    ) -> WebhookDeliveryResult:
        """Send alert to a specific webhook."""
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AlRazy-SecuritySystem/1.0"
        }
        
        if webhook.headers:
            headers.update(webhook.headers)
        
        if webhook.secret_token:
            headers["Authorization"] = f"Bearer {webhook.secret_token}"
        
        # Prepare payload
        payload_dict = asdict(payload)
        
        # Add evidence image if available
        if include_image and evidence_frame is not None:
            try:
                # Encode frame to base64
                import cv2
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                _, buffer = cv2.imencode('.jpg', evidence_frame, encode_param)
                image_b64 = base64.b64encode(buffer).decode('utf-8')
                payload_dict["evidence_image"] = {
                    "format": "jpeg",
                    "data": image_b64,
                    "timestamp": payload.timestamp
                }
            except Exception as e:
                logger.error(f"Error encoding evidence image: {e}")
        
        # Attempt delivery with retries
        for attempt in range(webhook.retry_attempts):
            try:
                async with self.session.post(
                    webhook.url,
                    headers=headers,
                    json=payload_dict,
                    timeout=aiohttp.ClientTimeout(total=webhook.timeout)
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status < 400:
                        logger.info(f"Webhook {webhook.name} delivered successfully (attempt {attempt + 1})")
                        return WebhookDeliveryResult(
                            webhook_name=webhook.name,
                            success=True,
                            status_code=response.status,
                            response_data=response_text[:500],  # Limit response data
                            error_message=None,
                            delivery_time=time.time(),
                            attempt_number=attempt + 1
                        )
                    else:
                        logger.warning(f"Webhook {webhook.name} failed with status {response.status} (attempt {attempt + 1})")
                        if attempt == webhook.retry_attempts - 1:  # Last attempt
                            return WebhookDeliveryResult(
                                webhook_name=webhook.name,
                                success=False,
                                status_code=response.status,
                                response_data=response_text[:500],
                                error_message=f"HTTP {response.status}",
                                delivery_time=time.time(),
                                attempt_number=attempt + 1
                            )
            
            except asyncio.TimeoutError:
                logger.warning(f"Webhook {webhook.name} timeout (attempt {attempt + 1})")
                if attempt == webhook.retry_attempts - 1:
                    return WebhookDeliveryResult(
                        webhook_name=webhook.name,
                        success=False,
                        status_code=None,
                        response_data=None,
                        error_message="Timeout",
                        delivery_time=time.time(),
                        attempt_number=attempt + 1
                    )
            
            except Exception as e:
                logger.error(f"Webhook {webhook.name} error (attempt {attempt + 1}): {e}")
                if attempt == webhook.retry_attempts - 1:
                    return WebhookDeliveryResult(
                        webhook_name=webhook.name,
                        success=False,
                        status_code=None,
                        response_data=None,
                        error_message=str(e),
                        delivery_time=time.time(),
                        attempt_number=attempt + 1
                    )
            
            # Wait before retry (exponential backoff)
            if attempt < webhook.retry_attempts - 1:
                await asyncio.sleep(2 ** attempt)
        
        # Should not reach here, but just in case
        return WebhookDeliveryResult(
            webhook_name=webhook.name,
            success=False,
            status_code=None,
            response_data=None,
            error_message="Unknown error",
            delivery_time=time.time(),
            attempt_number=webhook.retry_attempts
        )
    
    async def send_security_alert(
        self,
        activity: SuspiciousActivity,
        llm_analysis: Optional[LLMAnalysisResult] = None,
        incident_id: Optional[str] = None,
        recording_available: bool = False,
        include_evidence_image: bool = True
    ) -> List[WebhookDeliveryResult]:
        """Send security alert to all applicable webhooks."""
        
        # Create alert payload
        payload = self._create_alert_payload(
            activity, llm_analysis, incident_id, recording_available
        )
        
        # Determine threat level for webhook filtering
        threat_level = llm_analysis.threat_level if llm_analysis else "UNKNOWN"
        
        # Send to applicable webhooks
        delivery_results = []
        webhook_tasks = []
        
        for webhook in self.webhooks.values():
            # Check if webhook should be triggered
            if not self._should_trigger_webhook(webhook, threat_level):
                continue
            
            # Check rate limits
            if not self._check_rate_limit(webhook.name):
                logger.warning(f"Rate limit exceeded for webhook: {webhook.name}")
                continue
            
            # Add to tasks
            task = self._send_webhook(
                webhook,
                payload,
                include_evidence_image,
                activity.evidence_frame
            )
            webhook_tasks.append(task)
        
        # Execute all webhook deliveries concurrently
        if webhook_tasks:
            delivery_results = await asyncio.gather(*webhook_tasks, return_exceptions=True)
            
            # Handle exceptions
            valid_results = []
            for result in delivery_results:
                if isinstance(result, Exception):
                    logger.error(f"Webhook delivery exception: {result}")
                else:
                    valid_results.append(result)
            
            delivery_results = valid_results
        
        # Store delivery history
        for result in delivery_results:
            self.delivery_history.append({
                "alert_id": payload.alert_id,
                "webhook_name": result.webhook_name,
                "success": result.success,
                "timestamp": result.delivery_time,
                "threat_level": threat_level,
                "activity_type": activity.activity_type.value
            })
        
        # Log summary
        successful_deliveries = sum(1 for r in delivery_results if r.success)
        total_deliveries = len(delivery_results)
        logger.info(f"Alert sent: {successful_deliveries}/{total_deliveries} webhooks delivered successfully")
        
        return delivery_results
    
    async def send_test_alert(self, webhook_name: Optional[str] = None) -> List[WebhookDeliveryResult]:
        """Send test alert to verify webhook configuration."""
        
        # Create test activity
        from activity_detection import SuspiciousActivityType
        test_activity = SuspiciousActivity(
            activity_type=SuspiciousActivityType.LOITERING,
            person_id=999,
            camera_id=1,
            timestamp=time.time(),
            confidence=0.8,
            description="Test alert - system check",
            location=(100, 100),
            additional_data={"test": True}
        )
        
        # Create test LLM analysis
        test_analysis = LLMAnalysisResult(
            is_confirmed_suspicious=False,
            confidence_score=0.5,
            reasoning="This is a test alert to verify webhook configuration",
            recommended_action="LOG",
            threat_level="LOW",
            additional_context={"test_mode": True},
            analysis_timestamp=time.time()
        )
        
        # Send to specific webhook or all
        if webhook_name:
            if webhook_name not in self.webhooks:
                logger.error(f"Webhook not found: {webhook_name}")
                return []
            
            # Temporarily enable webhook for test
            webhook = self.webhooks[webhook_name]
            original_conditions = webhook.trigger_conditions
            webhook.trigger_conditions = ["LOW"]  # Ensure test triggers
            
            try:
                results = await self.send_security_alert(test_activity, test_analysis)
            finally:
                webhook.trigger_conditions = original_conditions
            
            return results
        else:
            # Test all webhooks
            return await self.send_security_alert(test_activity, test_analysis)
    
    def get_webhook_statistics(self) -> Dict[str, Any]:
        """Get webhook delivery statistics."""
        if not self.delivery_history:
            return {"total_deliveries": 0}
        
        recent_deliveries = [
            entry for entry in self.delivery_history
            if time.time() - entry["timestamp"] < 24 * 3600  # Last 24 hours
        ]
        
        total_deliveries = len(recent_deliveries)
        successful_deliveries = sum(1 for entry in recent_deliveries if entry["success"])
        
        # Webhook performance
        webhook_stats = {}
        for webhook_name in self.webhooks.keys():
            webhook_deliveries = [e for e in recent_deliveries if e["webhook_name"] == webhook_name]
            webhook_success = sum(1 for e in webhook_deliveries if e["success"])
            webhook_stats[webhook_name] = {
                "total_deliveries": len(webhook_deliveries),
                "successful_deliveries": webhook_success,
                "success_rate": webhook_success / len(webhook_deliveries) if webhook_deliveries else 0
            }
        
        # Threat level distribution
        threat_levels = [entry["threat_level"] for entry in recent_deliveries]
        threat_distribution = {level: threat_levels.count(level) for level in set(threat_levels)}
        
        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "success_rate": successful_deliveries / total_deliveries if total_deliveries > 0 else 0,
            "webhook_performance": webhook_stats,
            "threat_level_distribution": threat_distribution,
            "configured_webhooks": len(self.webhooks),
            "enabled_webhooks": len([w for w in self.webhooks.values() if w.enabled])
        }
    
    def get_delivery_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get webhook delivery history."""
        cutoff_time = time.time() - (hours * 3600)
        return [
            entry for entry in self.delivery_history
            if entry["timestamp"] >= cutoff_time
        ]

# Global webhook service
webhook_service: Optional[WebhookAlertService] = None

def initialize_webhook_service(pharmacy_name: str = "Al Razy Pharmacy") -> WebhookAlertService:
    """Initialize the global webhook service."""
    global webhook_service
    webhook_service = WebhookAlertService(pharmacy_name)
    return webhook_service

def get_webhook_service() -> Optional[WebhookAlertService]:
    """Get the global webhook service."""
    return webhook_service

# Common webhook configurations for different services
def create_slack_webhook(webhook_url: str, channel: str = "#security") -> WebhookConfig:
    """Create Slack webhook configuration."""
    return WebhookConfig(
        name="slack",
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        trigger_conditions=["MEDIUM", "HIGH", "CRITICAL"],
        retry_attempts=2
    )

def create_teams_webhook(webhook_url: str) -> WebhookConfig:
    """Create Microsoft Teams webhook configuration."""
    return WebhookConfig(
        name="teams",
        url=webhook_url,
        headers={"Content-Type": "application/json"},
        trigger_conditions=["HIGH", "CRITICAL"],
        retry_attempts=3
    )

def create_custom_webhook(name: str, url: str, secret_token: Optional[str] = None) -> WebhookConfig:
    """Create custom webhook configuration."""
    return WebhookConfig(
        name=name,
        url=url,
        secret_token=secret_token,
        headers={"Content-Type": "application/json"},
        trigger_conditions=["MEDIUM", "HIGH", "CRITICAL"],
        retry_attempts=3
    )
