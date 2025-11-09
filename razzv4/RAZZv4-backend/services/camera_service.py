"""
Camera Service for RTSP stream processing
Handles camera connections, frame capture, people counting with tracking
"""

import logging
import threading
import time
import os
from typing import Optional, Dict
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session

from services.yolo_service import YOLOService
from services.tracking_service import TrackingService
from models import Camera, VaultRoom

# Suppress FFmpeg/OpenCV H.264 decoding warnings
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'

logger = logging.getLogger(__name__)


class CameraProcessor:
    """
    Processes a single camera stream
    Captures frames, runs YOLO detection with ByteTrack tracking, updates database
    """
    
    def __init__(self, camera_id: int, rtsp_url: str, yolo_service: YOLOService, tracking_service: 'TrackingService', db_session_factory, use_tracking: bool = True):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.yolo_service = yolo_service
        self.tracking_service = tracking_service
        self.db_session_factory = db_session_factory
        self.use_tracking = use_tracking
        
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.capture: Optional[cv2.VideoCapture] = None
        self.last_person_count = 0
        self.last_update_time = datetime.now()
        self.last_annotated_frame = None  # Store latest annotated frame
        self.frame_skip = 1  # Process EVERY frame (30 FPS like brinksv2)
        self.frame_counter = 0
        self.last_process_time = 0
        self.frame_interval = 1.0 / 30  # 30 FPS target (same as brinksv2)
        
        logger.info(f"CameraProcessor initialized for camera {camera_id} with tracking={'enabled' if use_tracking else 'disabled'}")
        
    def start(self):
        """Start processing this camera in a background thread"""
        if self.is_running:
            logger.warning(f"Camera {self.camera_id} is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream, daemon=True)
        self.thread.start()
        logger.info(f"Started processing camera {self.camera_id}")
    
    def stop(self):
        """Stop processing this camera"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.capture:
            self.capture.release()
        logger.info(f"Stopped processing camera {self.camera_id}")
    
    def _connect_to_stream(self) -> bool:
        """Attempt to connect to RTSP stream"""
        try:
            # Release existing capture if any
            if self.capture:
                self.capture.release()
            
            # Open RTSP stream with TCP transport (more reliable than UDP)
            self.capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Set buffer size to 1 to get most recent frame
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Force TCP transport for reliable delivery
            self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open RTSP stream for camera {self.camera_id}")
                return False
            
            logger.info(f"Successfully connected to camera {self.camera_id} (TCP transport)")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to camera {self.camera_id}: {e}")
            return False
    
    def _process_stream(self):
        """Main processing loop for the camera stream"""
        reconnect_delay = 5  # seconds
        max_consecutive_failures = 10
        consecutive_failures = 0
        
        while self.is_running:
            try:
                # Connect to stream
                if not self._connect_to_stream():
                    time.sleep(reconnect_delay)
                    continue
                
                # Process frames
                while self.is_running:
                    ret, frame = self.capture.read()
                    
                    if not ret:
                        logger.warning(f"Failed to read frame from camera {self.camera_id}")
                        consecutive_failures += 1
                        
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"Too many consecutive failures for camera {self.camera_id}, reconnecting...")
                            break
                        
                        time.sleep(1)
                        continue
                    
                    # Reset failure counter on successful frame
                    consecutive_failures = 0
                    
                    # Time-based throttling (30 FPS target - EXACTLY like brinksv2)
                    current_time = time.time()
                    if current_time - self.last_process_time < self.frame_interval:
                        continue  # Skip if not enough time has passed
                    
                    # Process frame with YOLO + Tracking (BRINKSv2 style: all in one call)
                    if self.use_tracking and self.tracking_service:
                        # Track people (does YOLO detection + ByteTrack + DeepSORT internally)
                        tracking_result = self.tracking_service.track_people(
                            self.camera_id, frame, self.yolo_service
                        )
                        
                        # Draw tracking boxes on frame (BRINKSv2: frame first, camera_id second)
                        annotated_frame = self.tracking_service.draw_tracks(frame, self.camera_id)
                        
                        # Store the annotated frame for streaming
                        self.last_annotated_frame = annotated_frame
                        person_count = tracking_result['people_count']
                        
                        # Update last process time
                        self.last_process_time = current_time
                        
                        logger.debug(f"📹 Camera {self.camera_id}: {person_count} people tracked")
                    else:
                        # Fallback to simple counting (with annotation for visualization)
                        person_count, detections_list, detections_sv = self.yolo_service.detect_people(frame)
                        annotated = self.yolo_service.model(frame, verbose=False)[0].plot()
                        self.last_annotated_frame = annotated
                        logger.debug(f"Camera {self.camera_id}: YOLO-only mode, {person_count} people")
                    
                    # Update database if count changed
                    if person_count != self.last_person_count:
                        self._update_database(person_count)
                        self.last_person_count = person_count
                
            except Exception as e:
                logger.error(f"Error in camera {self.camera_id} processing loop: {e}")
                time.sleep(reconnect_delay)
        
        # Cleanup
        if self.capture:
            self.capture.release()
    
    def _update_database(self, person_count: int):
        """Update the database with new person count"""
        try:
            db = self.db_session_factory()
            try:
                # Update camera
                camera = db.query(Camera).filter(Camera.id == self.camera_id).first()
                if camera:
                    camera.current_people_count = person_count
                    logger.debug(f"💾 Camera {self.camera_id}: Updating DB with {person_count} people")
                    
                    # Update vault room total with cross-camera deduplication
                    if camera.vault_room_id:
                        vault_room = db.query(VaultRoom).filter(VaultRoom.id == camera.vault_room_id).first()
                        if vault_room:
                            # Get all camera IDs in this vault room
                            camera_ids = [cam.id for cam in vault_room.cameras]
                            logger.info(f"🏛️ Vault Room {vault_room.id} ({vault_room.name}): Starting cross-camera deduplication for cameras {camera_ids}")
                            
                            # Use ReID-based cross-camera deduplication
                            unique_count = self.tracking_service.get_unique_people_count_across_cameras(camera_ids)
                            vault_room.current_people_count = unique_count
                            logger.info(f"✅ Vault Room {vault_room.id}: Updated to {unique_count} unique people")
                    
                    db.commit()
                    logger.debug(f"✅ Updated camera {self.camera_id} people count: {person_count}")
                    self.last_update_time = datetime.now()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Error updating database for camera {self.camera_id}: {e}")


class CameraService:
    """
    Main camera service
    Manages multiple camera processors
    """
    
    def __init__(self, yolo_service: YOLOService, tracking_service: 'TrackingService', db_session_factory):
        self.yolo_service = yolo_service
        self.tracking_service = tracking_service
        self.db_session_factory = db_session_factory
        self.processors: Dict[int, CameraProcessor] = {}
        logger.info("Camera service initialized")
    
    def start_camera(self, camera_id: int, rtsp_url: str):
        """Start processing a specific camera"""
        if camera_id in self.processors:
            logger.warning(f"Camera {camera_id} is already being processed")
            return
        
        processor = CameraProcessor(camera_id, rtsp_url, self.yolo_service, self.tracking_service, self.db_session_factory)
        self.processors[camera_id] = processor
        processor.start()
    
    def stop_camera(self, camera_id: int):
        """Stop processing a specific camera"""
        if camera_id in self.processors:
            self.processors[camera_id].stop()
            del self.processors[camera_id]
    
    def start_all_cameras(self):
        """Start processing all active cameras from database"""
        db = self.db_session_factory()
        try:
            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            logger.info(f"Starting {len(cameras)} active cameras")
            
            for camera in cameras:
                self.start_camera(camera.id, camera.rtsp_url)
        finally:
            db.close()
    
    def stop_all_cameras(self):
        """Stop processing all cameras"""
        logger.info("Stopping all cameras")
        for camera_id in list(self.processors.keys()):
            self.stop_camera(camera_id)
    
    def get_camera_status(self, camera_id: int) -> dict:
        """Get status of a specific camera"""
        if camera_id in self.processors:
            processor = self.processors[camera_id]
            return {
                "camera_id": camera_id,
                "is_running": processor.is_running,
                "last_person_count": processor.last_person_count,
                "last_update": processor.last_update_time.isoformat()
            }
        return {
            "camera_id": camera_id,
            "is_running": False,
            "last_person_count": 0,
            "last_update": None
        }
