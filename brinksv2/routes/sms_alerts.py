"""
SMS Alert API Routes
Configure and test SMS alerts for people tracking
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.sms_alert_service import sms_alert_service

router = APIRouter(prefix="/api/sms-alerts", tags=["SMS Alerts"])


class SMSAlertConfig(BaseModel):
    """SMS alert configuration"""
    threshold: Optional[int] = None
    acc_name: Optional[str] = None
    acc_pass: Optional[str] = None
    sender_id: Optional[str] = None
    phone_number: Optional[str] = None


class SMSTestRequest(BaseModel):
    """Request to send test SMS"""
    phone_number: Optional[str] = None


@router.get("/config")
async def get_config():
    """Get current SMS alert configuration"""
    return {
        "threshold": sms_alert_service.alert_threshold,
        "phone_number": sms_alert_service.alert_phone,
        "josms_base_url": sms_alert_service.josms_base_url,
        "josms_acc_name": sms_alert_service.josms_acc_name,
        "josms_sender_id": sms_alert_service.josms_sender_id
    }


@router.put("/config")
async def update_config(config: SMSAlertConfig):
    """Update SMS alert configuration"""
    try:
        if config.threshold is not None:
            sms_alert_service.set_threshold(config.threshold)
        
        if config.acc_name is not None:
            sms_alert_service.josms_acc_name = config.acc_name
        
        if config.acc_pass is not None:
            sms_alert_service.josms_acc_pass = config.acc_pass
        
        if config.sender_id is not None:
            sms_alert_service.josms_sender_id = config.sender_id
        
        if config.phone_number is not None:
            sms_alert_service.alert_phone = config.phone_number
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "config": {
                "threshold": sms_alert_service.alert_threshold,
                "phone_number": sms_alert_service.alert_phone,
                "josms_acc_name": sms_alert_service.josms_acc_name,
                "josms_sender_id": sms_alert_service.josms_sender_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def send_test_sms(request: SMSTestRequest = None):
    """Send a test SMS to verify configuration"""
    try:
        # Override phone number if provided
        original_phone = sms_alert_service.alert_phone
        if request and request.phone_number:
            sms_alert_service.alert_phone = request.phone_number
        
        success = await sms_alert_service.send_test_sms()
        
        # Restore original phone
        sms_alert_service.alert_phone = original_phone
        
        if success:
            return {
                "success": True,
                "message": f"Test SMS sent successfully to {sms_alert_service.alert_phone}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send test SMS. Check JOSMS API key and configuration."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-tracking/{room_id}")
async def reset_room_tracking(room_id: int):
    """Reset people count tracking for a specific room"""
    try:
        sms_alert_service.reset_room_tracking(room_id)
        return {
            "success": True,
            "message": f"Tracking reset for room {room_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_alert_status():
    """Get current alert status for all rooms"""
    return {
        "previous_counts": dict(sms_alert_service.previous_counts),
        "alert_sent_for_count": dict(sms_alert_service.alert_sent_for_count),
        "config": {
            "threshold": sms_alert_service.alert_threshold,
            "phone_number": sms_alert_service.alert_phone
        }
    }
