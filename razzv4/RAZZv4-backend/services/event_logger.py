"""
Event Logging Service for Tracking Events
Logs entry, exit, motion, and unauthorized access events
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from models import TrackingEvent
from collections import deque

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Handles logging of person tracking events to database
    - Entry events: New person detected
    - Exit events: Person leaves (track lost)
    - Motion events: Person movement updates
    - Unauthorized events: Unknown person in restricted area
    """
    
    def __init__(self, db_session_factory, batch_size: int = 10):
        """
        Initialize event logger
        
        Args:
            db_session_factory: Database session factory
            batch_size: Number of events to batch before writing to DB
        """
        self.db_session_factory = db_session_factory
        self.batch_size = batch_size
        self.event_queue = deque()
        
        logger.info(f"✅ Event logger initialized (batch_size={batch_size})")
    
    def log_entry(
        self,
        room_id: int,
        camera_id: int,
        person_id: Optional[int],
        track_id: int,
        bbox: Dict[str, int],
        confidence: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log person entry event (new track detected)
        
        Args:
            room_id: Vault room ID
            camera_id: Camera ID
            person_id: Person ID (None for unknown)
            track_id: Tracking ID from YOLO
            bbox: Bounding box {x, y, w, h}
            confidence: Recognition confidence (0-1)
            metadata: Additional data
        """
        event = {
            'room_id': room_id,
            'camera_id': camera_id,
            'person_id': person_id,
            'event_type': 'entry',
            'track_id': track_id,
            'confidence': confidence,
            'bbox': bbox,
            'metadata': metadata or {},
            'timestamp': datetime.now()
        }
        
        self._queue_event(event)
        
        person_name = metadata.get('person_name', 'Unknown') if metadata else 'Unknown'
        logger.info(f"📥 ENTRY - Room {room_id}, Camera {camera_id}: {person_name} (track {track_id})")
    
    def log_exit(
        self,
        room_id: int,
        camera_id: int,
        person_id: Optional[int],
        track_id: int,
        metadata: Optional[Dict] = None
    ):
        """
        Log person exit event (track lost/timeout)
        
        Args:
            room_id: Vault room ID
            camera_id: Camera ID
            person_id: Person ID (None for unknown)
            track_id: Tracking ID
            metadata: Additional data (e.g., duration)
        """
        event = {
            'room_id': room_id,
            'camera_id': camera_id,
            'person_id': person_id,
            'event_type': 'exit',
            'track_id': track_id,
            'confidence': None,
            'bbox': None,
            'metadata': metadata or {},
            'timestamp': datetime.now()
        }
        
        self._queue_event(event)
        
        person_name = metadata.get('person_name', 'Unknown') if metadata else 'Unknown'
        logger.info(f"📤 EXIT - Room {room_id}, Camera {camera_id}: {person_name} (track {track_id})")
    
    def log_motion(
        self,
        room_id: int,
        camera_id: int,
        person_id: Optional[int],
        track_id: int,
        bbox: Dict[str, int],
        confidence: Optional[float] = None
    ):
        """
        Log person motion/update event (periodic updates for active tracks)
        
        Args:
            room_id: Vault room ID
            camera_id: Camera ID
            person_id: Person ID
            track_id: Tracking ID
            bbox: Current bounding box
            confidence: Recognition confidence
        """
        # Motion events are logged less frequently to reduce DB load
        # Only log if person is identified (has person_id)
        if person_id is None:
            return
        
        event = {
            'room_id': room_id,
            'camera_id': camera_id,
            'person_id': person_id,
            'event_type': 'motion',
            'track_id': track_id,
            'confidence': confidence,
            'bbox': bbox,
            'metadata': {},
            'timestamp': datetime.now()
        }
        
        self._queue_event(event)
    
    def log_unauthorized(
        self,
        room_id: int,
        camera_id: int,
        person_id: Optional[int],
        track_id: int,
        bbox: Dict[str, int],
        reason: str = "Not in authorized list"
    ):
        """
        Log unauthorized access attempt
        
        Args:
            room_id: Vault room ID
            camera_id: Camera ID
            person_id: Person ID (if recognized)
            track_id: Tracking ID
            bbox: Bounding box
            reason: Reason for unauthorized access
        """
        event = {
            'room_id': room_id,
            'camera_id': camera_id,
            'person_id': person_id,
            'event_type': 'unauthorized',
            'track_id': track_id,
            'confidence': None,
            'bbox': bbox,
            'metadata': {'reason': reason},
            'timestamp': datetime.now()
        }
        
        self._queue_event(event)
        
        logger.warning(f"🚨 UNAUTHORIZED - Room {room_id}, Camera {camera_id}: Person {person_id or 'Unknown'}")
    
    def _queue_event(self, event: Dict):
        """Add event to queue and flush if batch size reached"""
        self.event_queue.append(event)
        
        if len(self.event_queue) >= self.batch_size:
            self.flush_events()
    
    def flush_events(self):
        """Write all queued events to database"""
        if not self.event_queue:
            return
        
        try:
            db = self.db_session_factory()
            
            # Batch insert events
            events_to_insert = []
            while self.event_queue:
                event_data = self.event_queue.popleft()
                event = TrackingEvent(**event_data)
                events_to_insert.append(event)
            
            db.bulk_save_objects(events_to_insert)
            db.commit()
            
            logger.debug(f"💾 Flushed {len(events_to_insert)} events to database")
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to flush events: {str(e)}")
            # Clear queue to avoid memory buildup
            self.event_queue.clear()
    
    def get_recent_events(
        self,
        room_id: int,
        limit: int = 50,
        event_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get recent events for a room
        
        Args:
            room_id: Vault room ID
            limit: Maximum events to return
            event_types: Filter by event types (e.g., ['entry', 'exit'])
        
        Returns:
            List of events
        """
        try:
            db = self.db_session_factory()
            
            query = db.query(TrackingEvent).filter(TrackingEvent.room_id == room_id)
            
            if event_types:
                query = query.filter(TrackingEvent.event_type.in_(event_types))
            
            events = query.order_by(TrackingEvent.timestamp.desc()).limit(limit).all()
            
            result = [
                {
                    'id': event.id,
                    'room_id': event.room_id,
                    'camera_id': event.camera_id,
                    'person_id': event.person_id,
                    'event_type': event.event_type,
                    'track_id': event.track_id,
                    'confidence': event.confidence,
                    'bbox': event.bbox,
                    'metadata': event.metadata,
                    'timestamp': event.timestamp.isoformat()
                }
                for event in events
            ]
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting recent events: {str(e)}")
            return []
    
    def __del__(self):
        """Flush remaining events on shutdown"""
        if hasattr(self, 'event_queue'):
            self.flush_events()


# Global instance
_event_logger_instance = None


def get_event_logger(db_session_factory) -> EventLogger:
    """Get singleton event logger"""
    global _event_logger_instance
    if _event_logger_instance is None:
        _event_logger_instance = EventLogger(db_session_factory)
    return _event_logger_instance
