"""
People Detection and Tracking Service using YOLO11m + ByteTrack + DeepSORT
- ByteTrack: Real-time tracking at 30 FPS
- DeepSORT ReID: Re-identification for uncertain or lost tracks
"""

import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict, deque
from datetime import datetime
import threading
import time
from typing import Dict, List, Tuple
import supervision as sv
from deep_sort_realtime.deepsort_tracker import DeepSort


class PeopleDetector:
    """
    Advanced people detector with ByteTrack (30 FPS) + DeepSORT ReID fallback
    """
    
    def __init__(self, model_size: str = "yolo11m.pt", conf_threshold: float = 0.5, 
                 bytetrack_threshold: float = 0.6):
        """
        Initialize the people detector with ByteTrack and DeepSORT
        
        Args:
            model_size: YOLO model size (yolo11n, yolo11s, yolo11m, yolo11l, yolo11x)
            conf_threshold: Confidence threshold for detections (0.0-1.0)
            bytetrack_threshold: Confidence threshold for ByteTrack certainty (0.0-1.0)
        """
        print(f"Loading {model_size} model...")
        
        # Initialize YOLO with GPU
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🎮 Using device: {self.device.upper()}")
        
        if self.device == 'cuda':
            print(f"🚀 GPU: {torch.cuda.get_device_name(0)}")
            print(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        
        self.model = YOLO(model_size)
        self.model.to(self.device)  # Move model to GPU
        
        self.conf_threshold = conf_threshold
        self.bytetrack_threshold = bytetrack_threshold
        
        # Initialize ByteTrack tracker per camera
        self.byte_trackers = {}
        
        # Initialize DeepSORT tracker per camera (for uncertain tracks)
        self.deepsort_trackers = {}
        
        # Tracking data for each camera
        self.camera_tracks = defaultdict(lambda: {
            'count': 0,
            'tracks': {},
            'history': deque(maxlen=100),  # Store last 100 counts
            'last_update': None,
            'bytetrack_confident': 0,
            'deepsort_assisted': 0
        })
        
        print(f"✅ {model_size} loaded successfully")
        print(f"🚀 ByteTrack initialized (30 FPS tracking)")
        print(f"🔍 DeepSORT ReID initialized (fallback for uncertain tracks)")
    
    def _get_bytetrack_tracker(self, camera_id: int) -> sv.ByteTrack:
        """Get or create ByteTrack tracker for camera"""
        if camera_id not in self.byte_trackers:
            self.byte_trackers[camera_id] = sv.ByteTrack(
                track_activation_threshold=0.5,  # Higher threshold for activation
                lost_track_buffer=30,  # Frames to keep lost tracks (1 second at 30 FPS)
                minimum_matching_threshold=0.8,  # High matching threshold
                frame_rate=30  # 30 FPS processing
            )
        return self.byte_trackers[camera_id]
    
    def _get_deepsort_tracker(self, camera_id: int) -> DeepSort:
        """Get or create DeepSORT tracker for camera with GPU acceleration"""
        if camera_id not in self.deepsort_trackers:
            # Use GPU for DeepSORT ReID embeddings if available
            import torch
            embedder_gpu = torch.cuda.is_available()
            
            self.deepsort_trackers[camera_id] = DeepSort(
                max_age=30,  # Maximum frames to keep lost tracks
                n_init=3,  # Minimum consecutive detections for track initialization
                nms_max_overlap=0.7,  # Non-max suppression overlap threshold
                max_cosine_distance=0.3,  # Maximum cosine distance for ReID matching
                nn_budget=100,  # Maximum size of appearance descriptor gallery
                embedder="mobilenet",  # Use MobileNet for ReID embeddings
                embedder_gpu=embedder_gpu,  # Use GPU for embeddings
                embedder_wts=None,  # Use default weights
                polygon=False,  # Use bounding boxes, not polygons
                today=None
            )
            if embedder_gpu:
                print(f"🎮 DeepSORT using GPU for camera {camera_id}")
        return self.deepsort_trackers[camera_id]
    
    def detect_people(self, frame: np.ndarray, camera_id: int = None) -> Tuple[sv.Detections, List[Dict]]:
        """
        Detect people in a frame using YOLO11m on GPU
        
        Args:
            frame: Input frame (numpy array)
            camera_id: Camera identifier (optional, for tracking stats)
            
        Returns:
            Tuple of (supervision Detections, detections list for compatibility)
        """
        # Run YOLO detection on GPU - only detect persons (class 0)
        results = self.model.predict(
            frame,
            classes=[0],  # Person class only
            conf=self.conf_threshold,
            iou=0.7,  # IoU threshold for NMS
            verbose=False,
            device=self.device,  # Use GPU
            half=True if self.device == 'cuda' else False  # FP16 for faster inference on GPU
        )
        
        # Convert to supervision Detections format for ByteTrack
        detections_sv = sv.Detections.from_ultralytics(results[0])
        
        # Also create legacy format for compatibility
        detections_list = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                # Extract box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                
                detection = {
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': confidence,
                    'center': (int((x1 + x2) / 2), int((y1 + y2) / 2))
                }
                detections_list.append(detection)
        
        return detections_sv, detections_list
    
    def track_people(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Detect and track people using ByteTrack (30 FPS) with DeepSORT fallback
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            
        Returns:
            Dictionary with tracking information
        """
        # Step 1: Detect people in current frame
        detections_sv, detections_list = self.detect_people(frame, camera_id)
        
        # Step 2: Apply ByteTrack tracking (primary tracker)
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked_detections = byte_tracker.update_with_detections(detections_sv)
        
        # Step 3: Identify uncertain tracks (low confidence or new tracks)
        uncertain_detections = []
        confident_tracks = {}
        
        for i, track_id in enumerate(tracked_detections.tracker_id):
            confidence = tracked_detections.confidence[i]
            bbox = tracked_detections.xyxy[i]
            
            # Check if ByteTrack is confident about this track
            if confidence >= self.bytetrack_threshold:
                # ByteTrack is confident - use it directly
                confident_tracks[int(track_id)] = {
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                    'source': 'bytetrack',
                    'last_seen': datetime.now()
                }
                self.camera_tracks[camera_id]['bytetrack_confident'] += 1
            else:
                # ByteTrack is uncertain - prepare for DeepSORT ReID
                uncertain_detections.append({
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'bytetrack_id': int(track_id)
                })
        
        # Step 4: Apply DeepSORT ReID for uncertain tracks
        if len(uncertain_detections) > 0:
            deepsort_tracker = self._get_deepsort_tracker(camera_id)
            
            # Prepare detections for DeepSORT (needs [bbox, confidence, class])
            deepsort_input = []
            for det in uncertain_detections:
                bbox = det['bbox']
                # DeepSORT expects [left, top, width, height]
                deepsort_bbox = [bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]]
                deepsort_input.append((deepsort_bbox, det['confidence'], 'person'))
            
            # Update DeepSORT tracker
            deepsort_tracks = deepsort_tracker.update_tracks(deepsort_input, frame=frame)
            
            # Add DeepSORT tracks to results
            for track in deepsort_tracks:
                if track.is_confirmed():
                    bbox = track.to_ltrb()  # Get [left, top, right, bottom]
                    track_id = track.track_id
                    
                    # Convert track_id to int and use negative IDs to distinguish DeepSORT from ByteTrack
                    try:
                        numeric_track_id = int(track_id)
                        deepsort_key = -numeric_track_id
                    except (ValueError, TypeError):
                        # If conversion fails, use a hash-based approach
                        deepsort_key = f"ds_{track_id}"
                    
                    confident_tracks[deepsort_key] = {
                        'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                        'confidence': track.get_det_conf() if hasattr(track, 'get_det_conf') else 0.5,
                        'center': (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2)),
                        'source': 'deepsort',
                        'last_seen': datetime.now()
                    }
                    self.camera_tracks[camera_id]['deepsort_assisted'] += 1
        
        # Step 5: Update tracking data
        people_count = len(confident_tracks)
        self.camera_tracks[camera_id]['count'] = people_count
        self.camera_tracks[camera_id]['tracks'] = confident_tracks
        self.camera_tracks[camera_id]['last_update'] = datetime.now()
        self.camera_tracks[camera_id]['last_frame'] = frame  # Store frame for visualization
        self.camera_tracks[camera_id]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'count': people_count
        })
        
        return {
            'camera_id': camera_id,
            'people_count': people_count,
            'detections': detections_list,
            'tracks': confident_tracks,
            'timestamp': datetime.now().isoformat(),
            'bytetrack_confident': self.camera_tracks[camera_id]['bytetrack_confident'],
            'deepsort_assisted': self.camera_tracks[camera_id]['deepsort_assisted']
        }
    
    def get_camera_stats(self, camera_id: int) -> Dict:
        """
        Get statistics for a specific camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Statistics dictionary
        """
        data = self.camera_tracks[camera_id]
        
        # Calculate average count from history
        avg_count = 0
        if len(data['history']) > 0:
            avg_count = sum(h['count'] for h in data['history']) / len(data['history'])
        
        return {
            'camera_id': camera_id,
            'current_count': data['count'],
            'average_count': round(avg_count, 2),
            'active_tracks': len(data['tracks']),
            'last_update': data['last_update'].isoformat() if data['last_update'] else None,
            'history_size': len(data['history'])
        }
    
    def get_all_stats(self) -> List[Dict]:
        """
        Get statistics for all cameras
        
        Returns:
            List of statistics for each camera
        """
        return [self.get_camera_stats(cam_id) for cam_id in self.camera_tracks.keys()]
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """
        Draw bounding boxes and track IDs on frame - minimal clean overlay
        
        Args:
            frame: Input frame
            camera_id: Camera identifier
            
        Returns:
            Annotated frame with tracking visualization
        """
        annotated = frame.copy()
        
        # Get tracks for this camera
        tracks = self.camera_tracks[camera_id].get('tracks', {})
        people_count = self.camera_tracks[camera_id].get('count', 0)
        
        # Draw each track with minimal design
        for track_id, track_data in tracks.items():
            bbox = track_data['bbox']
            confidence = track_data.get('confidence', 0.0)
            source = track_data.get('source', 'unknown')
            
            # Color coding: Green for ByteTrack, Blue for DeepSORT
            if source == 'bytetrack':
                color = (0, 255, 0)  # Green for ByteTrack
            elif source == 'deepsort':
                color = (255, 165, 0)  # Orange for DeepSORT
            else:
                color = (255, 255, 255)  # White for unknown
            
            # Draw bounding box with clean line
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Prepare minimal label - just the ID number
            try:
                if isinstance(track_id, str):
                    if track_id.startswith("ds_"):
                        abs_track_id = track_id[3:]
                    else:
                        abs_track_id = track_id
                else:
                    abs_track_id = abs(int(track_id))
            except (ValueError, TypeError):
                abs_track_id = "?"
            
            label = f"#{abs_track_id}"
            
            # Draw small label above bounding box
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (label_width, label_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Position label above box
            label_y = bbox[1] - 8
            if label_y < label_height + 5:
                label_y = bbox[1] + label_height + 8
            
            # Draw label background (small, rounded)
            cv2.rectangle(annotated, 
                         (bbox[0], label_y - label_height - 3),
                         (bbox[0] + label_width + 6, label_y + 2),
                         color, -1)
            
            # Draw label text in black for contrast
            cv2.putText(annotated, label, (bbox[0] + 3, label_y - 1),
                       font, font_scale, (0, 0, 0), thickness)
        
        return annotated
    
    def get_annotated_frame(self, camera_id: int) -> Tuple[bool, np.ndarray]:
        """
        Get the latest annotated frame for a camera
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Tuple of (success, annotated_frame)
        """
        if camera_id not in self.camera_tracks:
            return False, None
        
        # Return the last processed frame if available
        last_frame = self.camera_tracks[camera_id].get('last_frame', None)
        if last_frame is None:
            return False, None
        
        return True, last_frame


class RTSPPeopleCounter:
    """
    Real-time people counter for RTSP streams at 30 FPS
    """
    
    def __init__(self, detector: PeopleDetector, process_fps: int = 30):
        """
        Initialize RTSP people counter with 30 FPS processing
        
        Args:
            detector: PeopleDetector instance
            process_fps: Frames per second to process (30 FPS for ByteTrack)
        """
        self.detector = detector
        self.process_fps = process_fps
        self.frame_interval = 1.0 / process_fps
        
        self.streams = {}
        self.running = {}
        
        print(f"📹 RTSPPeopleCounter initialized at {process_fps} FPS")
    
    def start_stream(self, camera_id: int, rtsp_url: str):
        """
        Start processing an RTSP stream
        
        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
        """
        if camera_id in self.running and self.running[camera_id]:
            print(f"Camera {camera_id} already running")
            return
        
        self.running[camera_id] = True
        thread = threading.Thread(
            target=self._process_stream,
            args=(camera_id, rtsp_url),
            daemon=True
        )
        thread.start()
        self.streams[camera_id] = thread
        print(f"✅ Started people detection on camera {camera_id}")
    
    def stop_stream(self, camera_id: int):
        """
        Stop processing an RTSP stream
        
        Args:
            camera_id: Camera identifier
        """
        if camera_id in self.running:
            self.running[camera_id] = False
            print(f"⏹️ Stopped people detection on camera {camera_id}")
    
    def _process_stream(self, camera_id: int, rtsp_url: str):
        """
        Process RTSP stream at 30 FPS with ByteTrack + DeepSORT
        
        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
        """
        cap = cv2.VideoCapture(rtsp_url)
        
        # Configure for optimal performance
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
        
        if not cap.isOpened():
            print(f"❌ Failed to open RTSP stream for camera {camera_id}")
            self.running[camera_id] = False
            return
        
        print(f"📹 Processing camera {camera_id} at {self.process_fps} FPS (ByteTrack + DeepSORT)")
        
        last_process_time = 0
        frame_count = 0
        
        while self.running.get(camera_id, False):
            ret, frame = cap.read()
            
            if not ret:
                print(f"⚠️ Failed to read frame from camera {camera_id}, reconnecting...")
                time.sleep(1)
                cap.release()
                cap = cv2.VideoCapture(rtsp_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            
            frame_count += 1
            
            # Process at specified FPS (30 FPS for ByteTrack)
            current_time = time.time()
            if current_time - last_process_time >= self.frame_interval:
                try:
                    # Detect and track people with ByteTrack + DeepSORT
                    result = self.detector.track_people(camera_id, frame)
                    
                    # Log tracking stats every 300 frames (10 seconds at 30 FPS)
                    if frame_count % 300 == 0:
                        print(f"📊 Camera {camera_id}: {result['people_count']} people | "
                              f"ByteTrack: {result.get('bytetrack_confident', 0)} | "
                              f"DeepSORT: {result.get('deepsort_assisted', 0)}")
                    
                    last_process_time = current_time
                except Exception as e:
                    print(f"⚠️ Error processing camera {camera_id}: {e}")
        
        cap.release()
        print(f"📹 Released camera {camera_id}")
    
    def get_stats(self) -> List[Dict]:
        """
        Get current statistics for all streams
        
        Returns:
            List of statistics dictionaries
        """
        return self.detector.get_all_stats()
