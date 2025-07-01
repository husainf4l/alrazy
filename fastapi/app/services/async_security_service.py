"""
Async Security Service for the Al Razy Pharmacy Security System.
Refactored to use async/await patterns instead of threading.
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from contextlib import asynccontextmanager

from app.services.activity_service import (
    analyze_camera_activity, 
    get_pharmacy_risk_assessment,
    SuspiciousActivity,
    get_activity_detector
)
from app.services.llm_service import (
    LLMActivityAnalyzer,
    get_llm_analyzer,
    LLMAnalysisResult
)
from app.services.recording_service import (
    get_recording_service
)
from app.services.webhook_service import (
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

class AsyncSecurityOrchestrator:
    """Async central orchestrator for the Al Razy pharmacy security system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_running = False
        self.processing_task = None
        self.event_queue = asyncio.Queue()
        self.recent_events: List[SecurityEvent] = []
        self.max_recent_events = 100
        
        # Service instances
        self.llm_analyzer = None
        self.recording_service = None
        self.webhook_service = None
        self.activity_detector = None
        
        # Statistics
        self.stats = {
            'total_events_processed': 0,
            'suspicious_activities_detected': 0,
            'llm_confirmations': 0,
            'recordings_triggered': 0,
            'webhooks_sent': 0,
            'false_positives': 0,
            'system_start_time': time.time()
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        
    async def initialize(self):
        """Initialize all security system components asynchronously."""
        logger.info("🔒 Initializing Async Security Orchestrator...")
        
        try:
            # Initialize LLM analyzer if configured
            llm_config = None
            if hasattr(self.config, 'llm_config'):
                llm_config = self.config.llm_config
            elif isinstance(self.config, dict):
                llm_config = self.config.get('llm_config')
            
            if llm_config:
                # Handle both dictionary config and LLMConfig object
                if hasattr(llm_config, 'enabled'):
                    # It's an LLMConfig object
                    if llm_config.enabled:
                        # Convert to dictionary for LLMActivityAnalyzer
                        llm_dict = {
                            'api_url': llm_config.api_url,
                            'api_key': llm_config.api_key,
                            'model': llm_config.model,
                            'max_retries': llm_config.max_retries,
                            'timeout': llm_config.timeout,
                            'enabled': llm_config.enabled
                        }
                        self.llm_analyzer = LLMActivityAnalyzer(llm_dict)
                        logger.info("🤖 LLM analyzer initialized")
                elif isinstance(llm_config, dict) and llm_config.get('enabled', False):
                    # It's a dictionary config
                    self.llm_analyzer = LLMActivityAnalyzer(llm_config)
                    logger.info("🤖 LLM analyzer initialized")
            
            # Initialize recording service
            self.recording_service = get_recording_service()
            if self.recording_service:
                logger.info("📹 Recording service initialized")
            
            # Initialize webhook service
            webhook_config = None
            if hasattr(self.config, 'webhook_config'):
                webhook_config = self.config.webhook_config
            elif isinstance(self.config, dict):
                webhook_config = self.config.get('webhook_config')
            
            if webhook_config:
                self.webhook_service = get_webhook_service()
                if self.webhook_service:
                    logger.info("🔗 Webhook service initialized")
            
            # Initialize activity detector
            # Note: Activity detectors are created per camera as needed
            # We don't initialize a global detector here since it needs camera_id
            logger.info("🔍 Activity detection service ready")
                
            logger.info("✅ Security Orchestrator initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize security orchestrator: {e}")
            raise
    
    async def start(self):
        """Start the security system processing loop."""
        if self.is_running:
            logger.warning("Security system is already running")
            return
            
        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_events_loop())
        logger.info("🚀 Security system started - monitoring for suspicious activities")
    
    async def stop(self):
        """Stop the security system processing loop."""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Cancel processing task
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Close LLM analyzer if it's an async context manager
        if self.llm_analyzer and hasattr(self.llm_analyzer, '__aexit__'):
            try:
                await self.llm_analyzer.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing LLM analyzer: {e}")
        
        logger.info("🛑 Security system stopped")
    
    async def _process_events_loop(self):
        """Main event processing loop using asyncio."""
        logger.info("📡 Starting security event processing loop")
        
        while self.is_running:
            try:
                # Wait for events with timeout to allow graceful shutdown
                try:
                    activity = await asyncio.wait_for(
                        self.event_queue.get(), 
                        timeout=1.0
                    )
                    await self._process_suspicious_activity(activity)
                except asyncio.TimeoutError:
                    # Timeout is normal, just continue the loop
                    continue
                    
            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying
    
    async def _process_suspicious_activity(self, activity: SuspiciousActivity):
        """Process a suspicious activity asynchronously."""
        start_time = time.time()
        event_id = f"event_{int(start_time * 1000)}"
        
        logger.info(f"🚨 Processing suspicious activity: {activity.activity_type.value}")
        
        try:
            # Create tasks for concurrent processing
            tasks = []
            
            # LLM analysis task
            llm_task = None
            if self.llm_analyzer:
                llm_task = asyncio.create_task(
                    self._analyze_with_llm(activity)
                )
                tasks.append(llm_task)
            
            # Recording task
            recording_task = None
            if self.recording_service:
                recording_task = asyncio.create_task(
                    self._trigger_recording(activity)
                )
                tasks.append(recording_task)
            
            # Wait for all tasks to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Extract results
                llm_analysis = None
                incident_id = None
                
                if llm_task and not isinstance(results[0], Exception):
                    llm_analysis = results[0]
                    if llm_analysis and llm_analysis.is_confirmed_suspicious:
                        self.stats['llm_confirmations'] += 1
                
                if recording_task and len(results) > 1 and not isinstance(results[1], Exception):
                    incident_id = results[1]
                    if incident_id:
                        self.stats['recordings_triggered'] += 1
            
            # Send webhooks if confirmed suspicious
            webhook_results = []
            if llm_analysis and llm_analysis.is_confirmed_suspicious and self.webhook_service:
                webhook_results = await self._send_webhooks(activity, llm_analysis)
                if webhook_results:
                    self.stats['webhooks_sent'] += len(webhook_results)
            
            # Create security event
            processing_time = time.time() - start_time
            security_event = SecurityEvent(
                event_id=event_id,
                activity=activity,
                llm_analysis=llm_analysis,
                incident_id=incident_id,
                webhook_results=webhook_results,
                timestamp=start_time,
                processing_time=processing_time
            )
            
            # Store event
            self.recent_events.append(security_event)
            if len(self.recent_events) > self.max_recent_events:
                self.recent_events.pop(0)
            
            # Update statistics
            self.stats['total_events_processed'] += 1
            self.stats['suspicious_activities_detected'] += 1
            
            logger.info(f"✅ Event processed in {processing_time:.2f}s: {event_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing suspicious activity: {e}")
    
    async def _analyze_with_llm(self, activity: SuspiciousActivity) -> Optional[LLMAnalysisResult]:
        """Analyze activity with LLM asynchronously."""
        try:
            if not self.llm_analyzer:
                return None
                
            # Use async context manager if available
            if hasattr(self.llm_analyzer, '__aenter__'):
                async with self.llm_analyzer:
                    return await self.llm_analyzer.analyze_activity_async(activity)
            else:
                # Fallback for non-async LLM analyzer
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.llm_analyzer.analyze_activity(activity)
                )
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None
    
    async def _trigger_recording(self, activity: SuspiciousActivity) -> Optional[str]:
        """Trigger recording asynchronously."""
        try:
            if not self.recording_service:
                return None
                
            # Run recording trigger in executor if not async
            return await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.recording_service.trigger_incident_recording(
                    activity.camera_id, activity
                )
            )
        except Exception as e:
            logger.error(f"Recording trigger failed: {e}")
            return None
    
    async def _send_webhooks(self, activity: SuspiciousActivity, 
                           llm_analysis: LLMAnalysisResult) -> List[Any]:
        """Send webhook notifications asynchronously."""
        try:
            if not self.webhook_service:
                return []
                
            # Prepare webhook data
            # Handle both dictionary config and Settings object
            pharmacy_name = 'Al Razy Pharmacy'  # default
            if hasattr(self.config, 'pharmacy_name'):
                pharmacy_name = self.config.pharmacy_name
            elif isinstance(self.config, dict):
                pharmacy_name = self.config.get('pharmacy_name', 'Al Razy Pharmacy')
                
            webhook_data = {
                'activity': activity.__dict__,
                'llm_analysis': llm_analysis.__dict__,
                'timestamp': time.time(),
                'pharmacy_location': pharmacy_name
            }
            
            # Send webhooks concurrently
            webhook_tasks = []
            for webhook_config in self.webhook_service.get_active_webhooks():
                task = asyncio.create_task(
                    self._send_single_webhook(webhook_config, webhook_data)
                )
                webhook_tasks.append(task)
            
            if webhook_tasks:
                results = await asyncio.gather(*webhook_tasks, return_exceptions=True)
                return [r for r in results if not isinstance(r, Exception)]
            
            return []
            
        except Exception as e:
            logger.error(f"Webhook sending failed: {e}")
            return []
    
    async def _send_single_webhook(self, webhook_config: WebhookConfig, 
                                 data: Dict[str, Any]) -> Any:
        """Send a single webhook asynchronously."""
        try:
            # Use aiohttp for async HTTP requests
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_config.url,
                    json=data,
                    headers=webhook_config.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        'url': webhook_config.url,
                        'status': response.status,
                        'response': await response.text()
                    }
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_config.url}: {e}")
            return {'url': webhook_config.url, 'error': str(e)}
    
    async def queue_suspicious_activity(self, activity: SuspiciousActivity):
        """Queue a suspicious activity for processing."""
        await self.event_queue.put(activity)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        uptime = time.time() - self.stats['system_start_time']
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'uptime_seconds': uptime,
            'queue_size': self.event_queue.qsize(),
            'recent_events_count': len(self.recent_events),
            'services': {
                'llm_analyzer': self.llm_analyzer is not None,
                'recording_service': self.recording_service is not None,
                'webhook_service': self.webhook_service is not None,
                'activity_detection': True  # Activity detectors are created per camera as needed
            },
            'statistics': self.stats.copy()
        }
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent security events."""
        recent = self.recent_events[-limit:] if limit > 0 else self.recent_events
        return [
            {
                'event_id': event.event_id,
                'activity_type': event.activity.activity_type.value,
                'camera_id': event.activity.camera_id,
                'threat_level': event.llm_analysis.threat_level if event.llm_analysis else 'UNKNOWN',
                'confirmed_suspicious': event.llm_analysis.is_confirmed_suspicious if event.llm_analysis else False,
                'timestamp': event.timestamp,
                'processing_time': event.processing_time
            }
            for event in recent
        ]


# Global instance
_security_orchestrator = None

async def initialize_async_security_system(config: Dict[str, Any]) -> AsyncSecurityOrchestrator:
    """Initialize the async security system."""
    global _security_orchestrator
    
    if _security_orchestrator is None:
        _security_orchestrator = AsyncSecurityOrchestrator(config)
        await _security_orchestrator.initialize()
    
    return _security_orchestrator

def get_async_security_system() -> Optional[AsyncSecurityOrchestrator]:
    """Get the current async security system instance."""
    return _security_orchestrator
