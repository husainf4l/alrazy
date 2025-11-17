"""
People Detection and Tracking Service using YOLO11 + ByteTrack + DeepSORT
Exactly matching BRINKSv2 implementation
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import supervision as sv
from deep_sort_realtime.deepsort_tracker import DeepSort
import logging

logger = logging.getLogger(__name__)


class TrackingService:
    """ByteTrack (30 FPS) + DeepSORT ReID fallback - BRINKSv2 style"""
    
    def __init__(self, conf_threshold: float = 0.5, bytetrack_threshold: float = 0.6):
        logger.info("Initializing tracking service (BRINKSv2 style)...")
        self.device = self._detect_device()
        self.conf_threshold = conf_threshold
        self.bytetrack_threshold = bytetrack_threshold
        self.byte_trackers = {}
        self.deepsort_trackers = {}
        self.camera_tracks = defaultdict(lambda: {
            'count': 0, 'tracks': {}, 'history': deque(maxlen=100),
            'last_update': None, 'bytetrack_confident': 0,
            'deepsort_assisted': 0, 'last_frame': None
        })
        logger.info("✅ Tracking service initialized")
    
    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
                return 'cuda'
        except: pass
        logger.info("Using CPU for tracking")
        return 'cpu'
    
    def _get_bytetrack_tracker(self, camera_id: int) -> sv.ByteTrack:
        if camera_id not in self.byte_trackers:
            self.byte_trackers[camera_id] = sv.ByteTrack(
                track_activation_threshold=0.5,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=30
            )
            logger.info(f"Created ByteTrack tracker for camera {camera_id}")
        return self.byte_trackers[camera_id]
    
    def _get_deepsort_tracker(self, camera_id: int) -> DeepSort:
        if camera_id not in self.deepsort_trackers:
            embedder_gpu = (self.device == 'cuda')
            self.deepsort_trackers[camera_id] = DeepSort(
                max_age=30, n_init=3, nms_max_overlap=0.7,
                max_cosine_distance=0.3, nn_budget=100,
                embedder="mobilenet", embedder_gpu=embedder_gpu,
                embedder_wts=None, polygon=False, today=None
            )
            if embedder_gpu:
                logger.info(f"🎮 DeepSORT using GPU for camera {camera_id}")
            logger.info(f"Created DeepSORT tracker for camera {camera_id}")
        return self.deepsort_trackers[camera_id]
    
    def track_people(self, camera_id: int, frame: np.ndarray, yolo_service) -> Dict:
        """
        Detect and track people using ByteTrack (30 FPS) with DeepSORT fallback
        EXACTLY like brinksv2: does detection + tracking in one call
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            yolo_service: YOLO service instance for detection
            
        Returns:
            Dictionary with tracking information
        """
        # Step 1: Detect people in current frame using YOLO
        person_count, detections_list, detections_sv = yolo_service.detect_people(frame)
        
        logger.info(f"🔍 Camera {camera_id}: YOLO detected {len(detections_sv)} people")
        
        # Step 2: Apply ByteTrack tracking (primary tracker)
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked_detections = byte_tracker.update_with_detections(detections_sv)
        
        logger.info(f"📍 Camera {camera_id}: ByteTrack returned {len(tracked_detections.tracker_id)} tracked objects")
        
        uncertain_detections = []
        confident_tracks = {}
        
        for i, track_id in enumerate(tracked_detections.tracker_id):
            confidence = tracked_detections.confidence[i]
            bbox = tracked_detections.xyxy[i]
            
            if confidence >= self.bytetrack_threshold:
                confident_tracks[int(track_id)] = {
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                    'source': 'bytetrack',
                    'last_seen': datetime.now()
                }
                self.camera_tracks[camera_id]['bytetrack_confident'] += 1
            else:
                uncertain_detections.append({
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'bytetrack_id': int(track_id)
                })
        
        if len(uncertain_detections) > 0:
            deepsort_tracker = self._get_deepsort_tracker(camera_id)
            deepsort_input = []
            for det in uncertain_detections:
                bbox = det['bbox']
                deepsort_bbox = [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]]
                deepsort_input.append((deepsort_bbox, det['confidence'], 'person'))
            
            deepsort_tracks = deepsort_tracker.update_tracks(deepsort_input, frame=frame)
            
            for track in deepsort_tracks:
                if track.is_confirmed():
                    bbox = track.to_ltrb()
                    try:
                        deepsort_key = -int(track.track_id)
                    except:
                        deepsort_key = f"ds_{track.track_id}"
                    
                    confident_tracks[deepsort_key] = {
                        'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                        'confidence': track.get_det_conf() if hasattr(track, 'get_det_conf') else 0.5,
                        'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                        'source': 'deepsort',
                        'last_seen': datetime.now()
                    }
                    self.camera_tracks[camera_id]['deepsort_assisted'] += 1
        
        self.camera_tracks[camera_id]['tracks'] = confident_tracks
        self.camera_tracks[camera_id]['count'] = len(confident_tracks)
        self.camera_tracks[camera_id]['last_update'] = datetime.now()
        self.camera_tracks[camera_id]['last_frame'] = frame  # Store frame for visualization
        self.camera_tracks[camera_id]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'count': len(confident_tracks)
        })
        
        return {
            'camera_id': camera_id,
            'people_count': len(confident_tracks),
            'detections': detections_list,
            'tracks': confident_tracks,
            'timestamp': datetime.now().isoformat(),
            'bytetrack_confident': self.camera_tracks[camera_id]['bytetrack_confident'],
            'deepsort_assisted': self.camera_tracks[camera_id]['deepsort_assisted']
        }
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """
        Draw bounding boxes and IDs on frame - BRINKSv2 style
        Args: frame first, then camera_id (matches brinksv2)
        """
        annotated = frame.copy()
        tracks = self.camera_tracks[camera_id].get('tracks', {})
        people_count = self.camera_tracks[camera_id].get('count', 0)
        
        logger.info(f"📊 Drawing {len(tracks)} tracks for camera {camera_id}, people_count={people_count}")
        
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            source = track_data.get('source', 'unknown')
            color = (0, 255, 0) if source == 'bytetrack' else (255, 165, 0)
            
            # Draw bounding box
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            try:
                abs_track_id = abs(int(track_id)) if not isinstance(track_id, str) else track_id.replace("ds_", "")
            except:
                abs_track_id = "?"
            
            label = f"ID:{abs_track_id}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (label_width, label_height), _ = cv2.getTextSize(label, font, 0.6, 2)
            label_y = max(bbox[1] - 8, label_height + 13)
            
            # Draw label background
            cv2.rectangle(annotated, (bbox[0], label_y - label_height - 5),
                         (bbox[0] + label_width + 10, label_y + 3), color, -1)
            cv2.putText(annotated, label, (bbox[0] + 5, label_y - 1),
                       font, 0.6, (0, 0, 0), 2)
        
        # Draw count overlay
        cv2.rectangle(annotated, (5, 5), (200, 35), (0, 0, 0), -1)
        cv2.putText(annotated, f"Tracks: {people_count}", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        logger.info(f"✅ Drew {len(tracks)} bounding boxes on frame for camera {camera_id}")
        return annotated
    
    def get_statistics(self, camera_id: int) -> Dict:
        if camera_id not in self.camera_tracks:
            return {"total_frames": 0, "active_tracks": 0, "tracks_created": 0, "avg_processing_time": 0.0}
        camera_data = self.camera_tracks[camera_id]
        return {
            "total_frames": len(camera_data['history']),
            "active_tracks": camera_data['count'],
            "tracks_created": camera_data['bytetrack_confident'] + camera_data['deepsort_assisted'],
            "bytetrack_confident": camera_data['bytetrack_confident'],
            "deepsort_assisted": camera_data['deepsort_assisted'],
            "avg_processing_time": 0.03
        }
    
    def reset(self, camera_id: int = None):
        if camera_id:
            for d in [self.byte_trackers, self.deepsort_trackers, self.camera_tracks]:
                d.pop(camera_id, None)
            logger.info(f"Reset tracker for camera {camera_id}")
        else:
            self.byte_trackers = {}
            self.deepsort_trackers = {}
            self.camera_tracks = defaultdict(lambda: {
                'count': 0, 'tracks': {}, 'history': deque(maxlen=100),
                'last_update': None, 'bytetrack_confident': 0,
                'deepsort_assisted': 0, 'last_frame': None
            })
            logger.info("Reset all trackers")
