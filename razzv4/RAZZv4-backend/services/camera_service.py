"""
Camera Service for RTSP stream processing
Handles camera connections, frame capture, people counting with tracking
"""

import logging
import threading
import time
from typing import Optional, Dict
import cv2
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session

from services.yolo_service import YOLOService
from services.tracking_service import TrackingService
from models import Camera, VaultRoom

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
        self.last_tracks = {}  # Store tracking data for WebSocket (bbox, id, confidence)
        self.fps = 0  # Current FPS
        self.frame_count = 0  # Total frames processed
        self.frame_skip = 1  # Process frames at reduced rate
        self.frame_counter = 0
        self.last_process_time = 0
        self.last_yolo_time = 0  # Last YOLO detection time
        self.last_deepsort_time = 0  # Last DeepSORT time
        self.yolo_interval = 1.0 / 15  # 15 FPS for YOLO detection
        self.bytetrack_interval = 1.0 / 30  # 30 FPS for ByteTrack updates
        self.deepsort_interval = 1.0 / 2  # 2 FPS for DeepSORT ReID
        self.last_detections = None  # Cache last YOLO detections for ByteTrack interpolation
        
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
            
            # Suppress FFmpeg warnings (harmless H.264 decoding messages from network packet loss)
            import os
            os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Quiet mode
            
            # Open RTSP stream
            self.capture = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size to 1 to get most recent frame
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open RTSP stream for camera {self.camera_id}")
                return False
            
            logger.info(f"Successfully connected to camera {self.camera_id}")
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
                    
                    current_time = time.time()
                    
                    # ByteTrack runs at 30 FPS (every frame)
                    if current_time - self.last_process_time < self.bytetrack_interval:
                        continue  # Skip if not enough time has passed
                    
                    # Process frame with YOLO + Tracking
                    if self.use_tracking and self.tracking_service:
                        # Determine if we should run YOLO (15 FPS) or just ByteTrack (30 FPS)
                        run_yolo = (current_time - self.last_yolo_time >= self.yolo_interval)
                        
                        if run_yolo:
                            # Run YOLO detection at 15 FPS
                            person_count, detections_list, detections_sv = self.yolo_service.detect_people(frame)
                            self.last_detections = detections_sv
                            self.last_yolo_time = current_time
                        else:
                            # Use cached detections for ByteTrack interpolation at 30 FPS
                            detections_sv = self.last_detections
                        
                        # Track people (ByteTrack runs at 30 FPS)
                        if detections_sv is not None and len(detections_sv) > 0:
                            tracking_result = self.tracking_service.track_people(
                                self.camera_id, frame, detections_sv
                            )
                            
                            # Store tracking data for WebSocket
                            camera_state = self.tracking_service.camera_tracks.get(self.camera_id, {})
                            self.last_tracks = camera_state.get('tracks', {})
                            
                            # Draw tracking boxes on frame
                            annotated_frame = self.tracking_service.draw_tracks(frame, self.camera_id)
                            
                            # Store the annotated frame for streaming
                            self.last_annotated_frame = annotated_frame
                            person_count = tracking_result['people_count']
                            
                            # Update FPS counter
                            self.frame_count += 1
                            if self.frame_count % 30 == 0:  # Update FPS every 30 frames
                                elapsed = current_time - self.last_process_time if self.last_process_time > 0 else 1
                                self.fps = 30 / elapsed if elapsed > 0 else 0
                            
                            # Update last process time
                            self.last_process_time = current_time
                            
                            logger.debug(f"Camera {self.camera_id}: {person_count} people tracked (YOLO: {run_yolo})")
                        else:
                            # No detections yet, continue to next frame
                            continue
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
                    
                    # Update vault room total
                    if camera.vault_room_id:
                        vault_room = db.query(VaultRoom).filter(VaultRoom.id == camera.vault_room_id).first()
                        if vault_room:
                            # Sum all cameras in this vault room
                            total_count = sum(cam.current_people_count or 0 for cam in vault_room.cameras)
                            vault_room.current_people_count = total_count
                    
                    db.commit()
                    logger.info(f"Updated camera {self.camera_id} people count: {person_count}")
                    self.last_update_time = datetime.now()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error updating database for camera {self.camera_id}: {e}")


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
