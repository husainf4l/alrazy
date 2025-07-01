"""
Security API endpoints for the Al Razy Pharmacy Security System.
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from app.models.security import (
    SecurityEvent, SecurityStatus, RiskAssessment, 
    SecurityAnalytics, LLMAnalysisResult
)
from app.core.dependencies import get_security_service

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/status", response_model=SecurityStatus)
async def get_security_status(security_service=Depends(get_security_service)):
    """Get comprehensive security system status."""
    try:
        if security_service:
            return security_service.get_system_status()
        else:
            return SecurityStatus(
                system_status="not_initialized",
                active_cameras=0,
                total_events_today=0,
                current_threat_level="LOW",
                active_recordings=0,
                llm_enabled=False,
                last_update=time.time(),
                alerts_sent=0
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting security status: {str(e)}"
        )


@router.get("/risk-assessment", response_model=Dict[str, Any])
async def get_risk_assessment():
    """Get current pharmacy risk assessment."""
    try:
        from app.services.activity_service import get_pharmacy_risk_assessment
        risk_assessment = get_pharmacy_risk_assessment()
        return {
            "success": True,
            "risk_assessment": risk_assessment
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting risk assessment: {str(e)}"
        )


@router.get("/events", response_model=Dict[str, Any])
async def get_security_events(
    hours: int = 24, 
    security_service=Depends(get_security_service)
):
    """Get recent security events."""
    try:
        if security_service:
            events = security_service.get_recent_events(hours)
            return {
                "success": True,
                "events": events,
                "total_events": len(events),
                "time_period_hours": hours
            }
        else:
            return {
                "success": False,
                "message": "Security system not initialized"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting security events: {str(e)}"
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_security_analytics(security_service=Depends(get_security_service)):
    """Get security analytics and insights."""
    try:
        if security_service:
            analytics = security_service.get_security_analytics()
            return {
                "success": True,
                "analytics": analytics
            }
        else:
            return {
                "success": False,
                "message": "Security system not initialized"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error getting security analytics: {str(e)}"
        )


@router.post("/process-frame/{camera_id}", response_model=Dict[str, Any])
async def process_security_frame(
    camera_id: int, 
    security_service=Depends(get_security_service)
):
    """Manually trigger security analysis on current camera frame."""
    try:
        if not security_service:
            raise HTTPException(
                status_code=503, 
                detail="Security system not initialized"
            )
        
        # Get current frame from camera
        from app.services.camera_service import cameras
        if camera_id not in cameras:
            raise HTTPException(
                status_code=404, 
                detail=f"Camera {camera_id} not found"
            )
        
        frame = cameras[camera_id].get_current_frame()
        if frame is None:
            raise HTTPException(
                status_code=404, 
                detail=f"No frame available from camera {camera_id}"
            )
        
        # Process frame for suspicious activities
        activities = await security_service.process_camera_frame(camera_id, frame)
        
        return {
            "success": True,
            "camera_id": camera_id,
            "activities_detected": len(activities),
            "activities": [
                {
                    "activity_type": activity.activity_type.value,
                    "confidence": activity.confidence,
                    "description": activity.description,
                    "location": activity.location
                }
                for activity in activities
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing security frame: {str(e)}"
        )


@router.post("/test-llm", response_model=Dict[str, Any])
async def test_llm_analysis():
    """Test LLM analysis functionality."""
    try:
        from app.services.activity_service import SuspiciousActivity, SuspiciousActivityType
        from app.services.llm_service import get_llm_analyzer
        
        # Create a test suspicious activity
        test_activity = SuspiciousActivity(
            activity_type=SuspiciousActivityType.LOITERING,
            location=(100, 200),
            confidence=0.85,
            description="Person standing in the same location for 60 seconds",
            person_id=1,
            camera_id=1,
            timestamp=time.time(),
            evidence_frame=None  # No image for this test
        )
        
        # Get LLM analyzer
        llm_analyzer = get_llm_analyzer()
        
        if not llm_analyzer:
            return {"success": False, "error": "LLM analyzer not available"}
        
        # Test context
        context = {
            "total_people": 2,
            "risk_level": "MEDIUM", 
            "recent_activities": 1,
            "business_hours": "8:00 AM - 10:00 PM"
        }
        
        # Analyze with LLM
        result = await llm_analyzer.analyze_suspicious_activity(
            test_activity, context, include_image=False
        )
        
        if result:
            return {
                "success": True,
                "llm_enabled": True,
                "analysis": {
                    "is_confirmed_suspicious": result.is_confirmed_suspicious,
                    "confidence_score": result.confidence_score,
                    "reasoning": result.reasoning,
                    "threat_level": result.threat_level,
                    "recommended_action": result.recommended_action
                }
            }
        else:
            return {"success": False, "error": "LLM analysis returned no result"}
            
    except Exception as e:
        return {"success": False, "error": f"LLM test failed: {str(e)}"}
