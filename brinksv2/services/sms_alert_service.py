"""
SMS Alert Service

Monitors people count changes and sends SMS alerts when threshold is reached
Uses JOSMS service to send notifications
"""

import asyncio
import httpx
from typing import Optional, Dict
from datetime import datetime
import logging
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SMSAlertService:
    """Service for sending SMS alerts when people count changes"""
    
    def __init__(self):
        # JOSMS Configuration
        self.josms_acc_name = "margogroup"
        self.josms_acc_pass = "nR@9g@Z7yV0@sS9bX1y"
        self.josms_sender_id = "MargoGroup"
        self.josms_base_url = "https://www.josms.net"
        self.alert_phone = "+962796026659"
        
        # Track previous counts for each room
        self.previous_counts: Dict[int, int] = {}
        self.alert_threshold = 3  # Alert when 3 or more people leave
        
        # Track if alert was already sent for this decrease event
        self.alert_sent_for_count: Dict[int, int] = {}  # {room_id: count_when_alert_sent}
    
    def check_and_alert_sync(self, room_id: int, current_count: int, room_name: str = None) -> bool:
        """
        Synchronous version - Check if people count has decreased by threshold and send alert
        Sends SMS only ONCE when threshold is crossed, not repeatedly
        
        Args:
            room_id: The room ID being monitored
            current_count: Current number of people in the room
            room_name: Optional room name for better alert messages
            
        Returns:
            bool: True if alert was sent, False otherwise
        """
        try:
            # Get previous count (if first time, set it to current)
            if room_id not in self.previous_counts:
                self.previous_counts[room_id] = current_count
                self.alert_sent_for_count[room_id] = current_count
                logger.info(f"Room {room_id}: Initialized with count={current_count}")
                return False
            
            previous_count = self.previous_counts[room_id]
            
            # Calculate decrease
            people_left = previous_count - current_count
            
            # Log for debugging
            logger.info(f"Room {room_id}: Previous={previous_count}, Current={current_count}, Left={people_left}, Threshold={self.alert_threshold}")
            
            # Check if threshold is met AND we haven't already sent alert for this count
            if people_left >= self.alert_threshold:
                # Check if we already sent alert for this specific count
                last_alert_count = self.alert_sent_for_count.get(room_id, -999)
                
                if current_count != last_alert_count:
                    # This is a NEW decrease event, send alert
                    logger.info(f"🚨 Triggering SMS alert for room {room_id}: {people_left} people left!")
                    
                    # Send alert using thread to avoid blocking
                    import threading
                    thread = threading.Thread(
                        target=self._send_alert_sync,
                        args=(room_id, people_left, previous_count, current_count, room_name)
                    )
                    thread.daemon = True
                    thread.start()
                    
                    # Mark that we sent alert for this count
                    self.alert_sent_for_count[room_id] = current_count
                    
                    # Update previous count
                    self.previous_counts[room_id] = current_count
                    return True
                else:
                    logger.info(f"Alert already sent for room {room_id} at count {current_count}, skipping")
            
            # If count increased (people entered), reset the alert tracking
            if current_count > previous_count:
                logger.info(f"Room {room_id}: Count increased from {previous_count} to {current_count}, resetting alert tracking")
                self.alert_sent_for_count[room_id] = current_count
            
            # Always update previous count
            self.previous_counts[room_id] = current_count
            return False
            
        except Exception as e:
            logger.error(f"Error checking alert for room {room_id}: {e}")
            return False
    
    def _send_alert_sync(
        self, 
        room_id: int, 
        people_left: int, 
        previous_count: int, 
        current_count: int,
        room_name: Optional[str] = None
    ):
        """Send SMS alert via JOSMS (synchronous version for threading)"""
        try:
            import requests
            
            # Format message (English only, under 160 chars for single SMS)
            room_label = room_name or f"Room {room_id}"
            timestamp = datetime.now().strftime("%I:%M %p")
            
            message = (
                f"ALERT: {people_left} people left {room_label}. "
                f"Previous: {previous_count} -> Current: {current_count}. "
                f"Time: {timestamp}"
            )
            
            logger.info(f"Sending SMS alert: {message}")
            
            # Format phone number
            formatted_number = self._format_phone_number(self.alert_phone)
            
            # Encode message
            encoded_message = self._encode_message(message)
            
            # Build URL for General SMS
            url = (
                f"{self.josms_base_url}/SMSServices/Clients/Prof/RestSingleSMS_General/SendSMS"
                f"?senderid={self.josms_sender_id}"
                f"&numbers={formatted_number}"
                f"&accname={self.josms_acc_name}"
                f"&AccPass={self.josms_acc_pass}"
                f"&msg={encoded_message}"
            )
            
            # Send request
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"✅ SMS alert sent successfully to {self.alert_phone}")
                logger.info(f"JOSMS Response: {response.text}")
            else:
                logger.error(f"❌ Failed to send SMS: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
        
    async def check_and_alert(self, room_id: int, current_count: int, room_name: str = None) -> bool:
        """
        Check if people count has decreased by threshold and send alert
        
        Args:
            room_id: The room ID being monitored
            current_count: Current number of people in the room
            room_name: Optional room name for better alert messages
            
        Returns:
            bool: True if alert was sent, False otherwise
        """
        try:
            # Get previous count
            previous_count = self.previous_counts.get(room_id, current_count)
            
            # Calculate decrease
            people_left = previous_count - current_count
            
            # Update previous count
            self.previous_counts[room_id] = current_count
            
            # Check if threshold is met
            if people_left >= self.alert_threshold:
                # Check cooldown
                last_alert = self.last_alert_time.get(room_id)
                if last_alert:
                    time_since_alert = (datetime.now() - last_alert).total_seconds()
                    if time_since_alert < self.alert_cooldown_seconds:
                        logger.info(f"Alert cooldown active for room {room_id}. {self.alert_cooldown_seconds - time_since_alert:.0f}s remaining")
                        return False
                
                # Send alert
                await self._send_alert(room_id, people_left, previous_count, current_count, room_name)
                self.last_alert_time[room_id] = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking alert for room {room_id}: {e}")
            return False
    
    async def _send_alert(
        self, 
        room_id: int, 
        people_left: int, 
        previous_count: int, 
        current_count: int,
        room_name: Optional[str] = None
    ):
        """Send SMS alert via JOSMS"""
        try:
            # Format message (English only, under 160 chars for single SMS)
            room_label = room_name or f"Room {room_id}"
            timestamp = datetime.now().strftime("%I:%M %p")
            
            message = (
                f"ALERT: {people_left} people left {room_label}. "
                f"Previous: {previous_count} -> Current: {current_count}. "
                f"Time: {timestamp}"
            )
            
            logger.info(f"Sending SMS alert: {message}")
            
            # Send via JOSMS
            success = await self._send_sms(self.alert_phone, message)
            
            if success:
                logger.info(f"✅ SMS alert sent successfully to {self.alert_phone}")
            else:
                logger.error(f"❌ Failed to send SMS alert to {self.alert_phone}")
                
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
    
    def _format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to JOSMS format (962XXXXXXXXX)
        Accepts: +962XXXXXXXXX, 962XXXXXXXXX, 07XXXXXXXX, 7XXXXXXXX
        """
        # Remove all non-numeric characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # If starts with 00962, remove 00
        if cleaned.startswith('00962'):
            cleaned = cleaned[2:]
        # If starts with 0, replace with 962
        elif cleaned.startswith('0'):
            cleaned = '962' + cleaned[1:]
        # If doesn't start with 962, add it
        elif not cleaned.startswith('962'):
            cleaned = '962' + cleaned
        
        # Validate: Should be 12 digits starting with 962
        if len(cleaned) != 12 or not cleaned.startswith('962'):
            raise ValueError(f"Invalid phone number format: {phone_number}")
        
        # Validate operator code (77, 78, 79)
        operator_code = cleaned[3:5]
        if operator_code not in ['77', '78', '79']:
            raise ValueError(f"Invalid operator code: {operator_code}. Must be 77, 78, or 79")
        
        return cleaned
    
    def _encode_message(self, message: str) -> str:
        """Encode message for URL (handle special characters)"""
        return quote_plus(message)
    
    async def _send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS via JOSMS API (General Message type)
        
        Args:
            phone_number: Recipient phone number
            message: SMS message content
            
        Returns:
            bool: True if SMS sent successfully
        """
        try:
            # Format phone number
            formatted_number = self._format_phone_number(phone_number)
            
            # Encode message
            encoded_message = self._encode_message(message)
            
            # Build URL for General SMS
            url = (
                f"{self.josms_base_url}/SMSServices/Clients/Prof/RestSingleSMS_General/SendSMS"
                f"?senderid={self.josms_sender_id}"
                f"&numbers={formatted_number}"
                f"&accname={self.josms_acc_name}"
                f"&AccPass={self.josms_acc_pass}"
                f"&msg={encoded_message}"
            )
            
            logger.info(f"Sending SMS to {formatted_number} via JOSMS")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                
                if response.status_code == 200:
                    logger.info(f"JOSMS Response: {response.text}")
                    return True
                else:
                    logger.error(f"JOSMS API error: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error("SMS send timeout")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS via JOSMS: {e}")
            return False
    
    def set_threshold(self, threshold: int):
        """Update the alert threshold"""
        self.alert_threshold = threshold
        logger.info(f"Alert threshold updated to {threshold}")
    
    def set_cooldown(self, seconds: int):
        """Update the alert cooldown period"""
        self.alert_cooldown_seconds = seconds
        logger.info(f"Alert cooldown updated to {seconds} seconds")
    
    def reset_room_tracking(self, room_id: int):
        """Reset tracking for a specific room"""
        if room_id in self.previous_counts:
            del self.previous_counts[room_id]
        if room_id in self.alert_sent_for_count:
            del self.alert_sent_for_count[room_id]
        logger.info(f"Tracking reset for room {room_id}")
    
    async def send_test_sms(self) -> bool:
        """Send a test SMS to verify configuration"""
        message = f"Test SMS from Brinks V2 - {datetime.now().strftime('%I:%M %p')}"
        return await self._send_sms(self.alert_phone, message)


# Global instance
sms_alert_service = SMSAlertService()
