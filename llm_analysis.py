import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from activity_detection import SuspiciousActivity, SuspiciousActivityType
import base64
import cv2

logger = logging.getLogger(__name__)

@dataclass
class LLMAnalysisResult:
    """Result from LLM analysis of suspicious activity."""
    is_confirmed_suspicious: bool
    confidence_score: float
    reasoning: str
    recommended_action: str
    threat_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    additional_context: Dict[str, Any]
    analysis_timestamp: float

class LLMActivityAnalyzer:
    """LLM-powered analysis service for confirming suspicious activities."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.session = None
        self.analysis_history = []
        
        # Default to OpenAI API format, but configurable for other providers
        self.api_url = llm_config.get("api_url", "https://api.openai.com/v1/chat/completions")
        self.api_key = llm_config.get("api_key", "")
        self.model = llm_config.get("model", "gpt-4o-mini")
        self.max_retries = llm_config.get("max_retries", 3)
        self.timeout = llm_config.get("timeout", 30)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _encode_frame_to_base64(self, frame: Optional[object]) -> Optional[str]:
        """Encode frame to base64 for LLM vision analysis."""
        if frame is None:
            return None
        
        try:
            # Resize frame to reduce payload size
            height, width = frame.shape[:2]
            if width > 800:
                scale = 800 / width
                new_width = 800
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            return frame_b64
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def _create_analysis_prompt(self, activity: SuspiciousActivity, context: Dict[str, Any]) -> str:
        """Create a detailed prompt for LLM analysis."""
        
        activity_descriptions = {
            SuspiciousActivityType.LOITERING: "A person has been standing or moving slowly in the same area for an extended period",
            SuspiciousActivityType.TAKING_WITHOUT_PAYING: "A person appears to have taken items without going through checkout",
            SuspiciousActivityType.MULTIPLE_PEOPLE_RESTRICTED: "Multiple people or unauthorized access detected in restricted pharmacy areas",
            SuspiciousActivityType.UNUSUAL_MOVEMENT: "Erratic, circling, or unusual movement patterns detected",
            SuspiciousActivityType.RAPID_GRABBING: "Rapid movement suggesting quick item grabbing behavior",
            SuspiciousActivityType.CONCEALING_ITEMS: "Person appears to be concealing items on their person",
            SuspiciousActivityType.EXIT_WITHOUT_PAYMENT: "Person leaving the pharmacy without apparent payment",
            SuspiciousActivityType.AFTER_HOURS_ACTIVITY: "Activity detected outside normal business hours"
        }
        
        prompt = f"""
You are an AI security analyst for Al Razy Pharmacy's theft prevention system. Analyze the following suspicious activity detection and determine if it represents a genuine security threat.

**ACTIVITY DETAILS:**
- Type: {activity.activity_type.value}
- Description: {activity_descriptions.get(activity.activity_type, activity.description)}
- System Description: {activity.description}
- Confidence Score: {activity.confidence:.2f}
- Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(activity.timestamp))}
- Location: Camera {activity.camera_id}, Position ({activity.location[0]}, {activity.location[1]})

**CONTEXT INFORMATION:**
- Total people currently in store: {context.get('total_people', 'unknown')}
- Store risk level: {context.get('risk_level', 'unknown')}
- Recent activities count: {context.get('recent_activities', 0)}
- Business hours: {context.get('business_hours', '8:00 AM - 10:00 PM')}
- Current time: {time.strftime('%H:%M', time.localtime())}

**PHARMACY-SPECIFIC CONSIDERATIONS:**
Al Razy Pharmacy sells prescription medications, over-the-counter drugs, health products, and medical supplies. Consider:

1. **High-Value Items**: Prescription medications, especially controlled substances
2. **Common Theft Patterns**: Medication theft, shoplifting of health products, grab-and-run
3. **Legitimate Behaviors**: Customers reading labels, comparing products, waiting for prescriptions
4. **Staff Areas**: Behind-counter areas are restricted to authorized personnel only
5. **Checkout Process**: Customers should pay at the counter before leaving

**ANALYSIS FRAMEWORK:**
Evaluate the activity using these criteria:

1. **Threat Assessment** (0-10 scale):
   - How likely is this to be actual theft or suspicious behavior?
   - Consider normal pharmacy customer behavior patterns

2. **Context Appropriateness**:
   - Is this behavior normal for a pharmacy setting?
   - Could there be innocent explanations?

3. **Risk Level**:
   - CRITICAL: Immediate theft in progress, security threat
   - HIGH: Very likely theft/suspicious behavior, requires immediate attention
   - MEDIUM: Potentially suspicious, monitor closely
   - LOW: Possibly innocent but worth noting

4. **Recommended Actions**:
   - IMMEDIATE: Call security/police, alert staff immediately
   - ALERT: Notify store manager, increase monitoring
   - MONITOR: Continue observation, document incident
   - LOG: Record for patterns, no immediate action needed

**REQUIRED RESPONSE FORMAT:**
Provide your analysis in this exact JSON format:

{{
    "is_confirmed_suspicious": boolean,
    "confidence_score": float (0.0-1.0),
    "reasoning": "Detailed explanation of your analysis",
    "recommended_action": "IMMEDIATE|ALERT|MONITOR|LOG",
    "threat_level": "CRITICAL|HIGH|MEDIUM|LOW",
    "additional_context": {{
        "likely_innocent_explanation": "explanation if applicable",
        "key_risk_factors": ["factor1", "factor2"],
        "suggested_intervention": "specific action recommendation"
    }}
}}

Focus on practical, actionable security analysis that helps pharmacy staff make informed decisions about potential theft or security threats.
"""
        return prompt
    
    async def analyze_suspicious_activity(
        self, 
        activity: SuspiciousActivity, 
        context: Dict[str, Any],
        include_image: bool = True
    ) -> LLMAnalysisResult:
        """Analyze suspicious activity using LLM."""
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(activity, context)
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert security analyst specializing in retail pharmacy theft prevention. Provide accurate, actionable security assessments."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Add image if available and requested
            if include_image and activity.evidence_frame is not None:
                frame_b64 = self._encode_frame_to_base64(activity.evidence_frame)
                if frame_b64:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Here is the security camera frame showing the suspicious activity:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{frame_b64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    })
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.1,  # Low temperature for consistent analysis
                "response_format": {"type": "json_object"}
            }
            
            # Make API request with retries
            for attempt in range(self.max_retries):
                try:
                    async with self.session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            # Extract content from response
                            content = result["choices"][0]["message"]["content"]
                            analysis_data = json.loads(content)
                            
                            # Create analysis result
                            llm_result = LLMAnalysisResult(
                                is_confirmed_suspicious=analysis_data.get("is_confirmed_suspicious", False),
                                confidence_score=float(analysis_data.get("confidence_score", 0.0)),
                                reasoning=analysis_data.get("reasoning", "No reasoning provided"),
                                recommended_action=analysis_data.get("recommended_action", "LOG"),
                                threat_level=analysis_data.get("threat_level", "LOW"),
                                additional_context=analysis_data.get("additional_context", {}),
                                analysis_timestamp=time.time()
                            )
                            
                            # Store in history
                            self.analysis_history.append({
                                "activity": asdict(activity),
                                "analysis": asdict(llm_result),
                                "timestamp": time.time()
                            })
                            
                            logger.info(f"LLM analysis completed: {llm_result.threat_level} threat level")
                            return llm_result
                        
                        else:
                            error_text = await response.text()
                            logger.error(f"LLM API error (attempt {attempt + 1}): {response.status} - {error_text}")
                            
                            if attempt == self.max_retries - 1:
                                # Return default analysis on final failure
                                return self._create_fallback_analysis(activity)
                
                except asyncio.TimeoutError:
                    logger.error(f"LLM API timeout (attempt {attempt + 1})")
                    if attempt == self.max_retries - 1:
                        return self._create_fallback_analysis(activity)
                
                except Exception as e:
                    logger.error(f"LLM API error (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries - 1:
                        return self._create_fallback_analysis(activity)
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            return self._create_fallback_analysis(activity)
    
    def _create_fallback_analysis(self, activity: SuspiciousActivity) -> LLMAnalysisResult:
        """Create fallback analysis when LLM is unavailable."""
        
        # Simple rule-based fallback
        threat_level = "LOW"
        confidence = 0.3
        is_suspicious = False
        recommended_action = "LOG"
        
        if activity.activity_type == SuspiciousActivityType.TAKING_WITHOUT_PAYING:
            threat_level = "HIGH"
            confidence = 0.8
            is_suspicious = True
            recommended_action = "ALERT"
        elif activity.activity_type == SuspiciousActivityType.MULTIPLE_PEOPLE_RESTRICTED:
            threat_level = "MEDIUM"
            confidence = 0.6
            is_suspicious = True
            recommended_action = "MONITOR"
        elif activity.confidence > 0.8:
            threat_level = "MEDIUM"
            confidence = 0.5
            is_suspicious = True
            recommended_action = "MONITOR"
        
        return LLMAnalysisResult(
            is_confirmed_suspicious=is_suspicious,
            confidence_score=confidence,
            reasoning=f"Fallback analysis - LLM unavailable. Activity type: {activity.activity_type.value}",
            recommended_action=recommended_action,
            threat_level=threat_level,
            additional_context={"fallback_mode": True},
            analysis_timestamp=time.time()
        )
    
    async def batch_analyze_activities(
        self, 
        activities: List[SuspiciousActivity], 
        context: Dict[str, Any]
    ) -> List[LLMAnalysisResult]:
        """Analyze multiple activities in batch for efficiency."""
        
        # For now, analyze sequentially to avoid rate limits
        # In production, this could be optimized with proper batching
        results = []
        
        for activity in activities:
            try:
                result = await self.analyze_suspicious_activity(activity, context, include_image=False)
                results.append(result)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error analyzing activity {activity.person_id}: {e}")
                results.append(self._create_fallback_analysis(activity))
        
        return results
    
    def get_analysis_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get analysis history for the last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        return [
            entry for entry in self.analysis_history
            if entry["timestamp"] >= cutoff_time
        ]
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics about LLM analysis performance."""
        if not self.analysis_history:
            return {"total_analyses": 0}
        
        recent_analyses = self.get_analysis_history(24)  # Last 24 hours
        
        threat_levels = [entry["analysis"]["threat_level"] for entry in recent_analyses]
        threat_counts = {level: threat_levels.count(level) for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        
        confirmed_suspicious = [
            entry for entry in recent_analyses 
            if entry["analysis"]["is_confirmed_suspicious"]
        ]
        
        return {
            "total_analyses": len(self.analysis_history),
            "recent_analyses": len(recent_analyses),
            "threat_level_distribution": threat_counts,
            "confirmed_suspicious_count": len(confirmed_suspicious),
            "average_confidence": sum(
                entry["analysis"]["confidence_score"] for entry in recent_analyses
            ) / len(recent_analyses) if recent_analyses else 0,
            "fallback_analyses": len([
                entry for entry in recent_analyses 
                if entry["analysis"]["additional_context"].get("fallback_mode", False)
            ])
        }

# Global LLM analyzer instance
llm_analyzer: Optional[LLMActivityAnalyzer] = None

def initialize_llm_analyzer(config: Dict[str, Any]) -> LLMActivityAnalyzer:
    """Initialize the global LLM analyzer."""
    global llm_analyzer
    llm_analyzer = LLMActivityAnalyzer(config)
    return llm_analyzer

async def analyze_activity_with_llm(
    activity: SuspiciousActivity,
    context: Dict[str, Any]
) -> Optional[LLMAnalysisResult]:
    """Convenience function to analyze activity with LLM."""
    if not llm_analyzer:
        logger.error("LLM analyzer not initialized")
        return None
    
    async with llm_analyzer as analyzer:
        return await analyzer.analyze_suspicious_activity(activity, context)

def get_llm_analyzer() -> Optional[LLMActivityAnalyzer]:
    """Get the global LLM analyzer instance."""
    return llm_analyzer
