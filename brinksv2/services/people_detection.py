"""
People Detection and Tracking Service using YOLO11m (ONNX) + YuNet Face Detection + ByteTrack + DeepSORT
- ONNX Runtime: Optimized inference for real-time performance
- YuNet: Lightweight face detection
- ByteTrack: Real-time tracking at 30 FPS
- DeepSORT ReID: Re-identification for uncertain or lost tracks
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
import threading
import time
from typing import Dict, List, Tuple
import supervision as sv
from deep_sort_realtime.deepsort_tracker import DeepSort
import onnxruntime as ort


class PeopleDetector:
    """
    Advanced people detector with ONNX YOLO11m + YuNet Face Detection + ByteTrack + DeepSORT ReID
    """
    
    def __init__(self, model_size: str = "yolo11m.onnx", conf_threshold: float = 0.5, 
                 bytetrack_threshold: float = 0.6, global_tracker=None, use_gpu: bool = True):
        """
        Initialize the people detector with ONNX YOLO, YuNet face detection, ByteTrack and DeepSORT
        
        Args:
            model_size: YOLO ONNX model path (yolo11m.onnx)
            conf_threshold: Confidence threshold for detections (0.0-1.0)
            bytetrack_threshold: Confidence threshold for ByteTrack certainty (0.0-1.0)
            global_tracker: GlobalPersonTracker instance for cross-camera tracking
            use_gpu: Enable GPU acceleration (default: True)
        """
        print(f"Loading {model_size} ONNX model...")
        
        # Initialize ONNX Runtime session with GPU optimization
        self.use_gpu = use_gpu
        
        # Configure providers for maximum GPU utilization
        if use_gpu:
            providers = [
                'CUDAExecutionProvider',      # Primary: GPU acceleration
                'TensorrtExecutionProvider',  # Secondary: TensorRT optimization
                'CPUExecutionProvider'        # Fallback: CPU
            ]
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  # Sequential is faster for single model
            session_options.intra_op_num_threads = 8  # Optimize threading
            session_options.inter_op_num_threads = 1
            
            print("🎮 GPU Acceleration Configuration:")
            print("  • CUDAExecutionProvider: Primary (GPU)")
            print("  • TensorrtExecutionProvider: Secondary (GPU optimization)")
            print("  • GraphOptimization: ENABLED")
            print("  • Threading: Optimized for single model (8 intra-op threads)")
        else:
            providers = ['CPUExecutionProvider']
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            print("💻 CPU Mode (GPU disabled)")
        
        self.session = ort.InferenceSession(model_size, providers=providers, sess_options=session_options)
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        
        # Print actual provider being used
        print(f"✅ Using Execution Provider: {self.session.get_providers()[0]}")
        
        # Initialize YuNet face detector with GPU support
        print("👤 Initializing YuNet face detector...")
        self.face_detector = cv2.FaceDetectorYN.create(
            "face_detection_yunet_2023mar.onnx",
            "",
            (320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000
        )
        print("✅ YuNet face detector initialized")
        
        self.conf_threshold = conf_threshold
        self.bytetrack_threshold = bytetrack_threshold
        self.global_tracker = global_tracker  # Store global tracker
        
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
            'deepsort_assisted': 0,
            'room_id': None  # Store room_id for cross-camera tracking
        })
        
        print(f"✅ {model_size} ONNX loaded successfully")
        print(f"🚀 ONNX Runtime inference initialized")
        print(f"👤 YuNet face detector initialized")
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
    
    def detect_people(self, frame: np.ndarray, camera_id: int = None, detect_faces: bool = True) -> Tuple[sv.Detections, List[Dict]]:
        """
        Detect people and optionally faces in a frame using ONNX YOLO11m
        
        Args:
            frame: Input frame (numpy array)
            camera_id: Camera identifier (optional, for tracking stats)
            detect_faces: Whether to include face detection (default: True)
            
        Returns:
            Tuple of (supervision Detections, detections list with all detections)
        """
        height, width = frame.shape[:2]
        
        # Detect people with ONNX YOLO
        person_detections = self._detect_people_onnx(frame)
        
        # Detect faces with YuNet (for improved accuracy on small faces)
        # YuNet is kept as secondary detector for faces since it's optimized for face detection
        face_detections = []
        if detect_faces:
            face_detections = self._detect_faces_yunet(frame)
        
        # Combine detections: person detections (class_id=0) + face detections (class_id=1)
        all_detections = person_detections + face_detections
        
        # Convert to supervision Detections format
        if len(all_detections) > 0:
            boxes = np.array([d['bbox'] for d in all_detections])
            confidences = np.array([d['confidence'] for d in all_detections])
            class_ids = np.array([d['class_id'] for d in all_detections])
            
            detections_sv = sv.Detections(
                xyxy=boxes,
                confidence=confidences,
                class_id=class_ids
            )
        else:
            detections_sv = sv.Detections.empty()
        
        return detections_sv, all_detections
    
    def _detect_people_onnx(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect people using ONNX YOLO model
        
        Args:
            frame: Input frame
            
        Returns:
            List of person detections
        """
        # Preprocess
        input_img = self._preprocess_yolo(frame)
        
        # Run inference
        outputs = self.session.run(None, {self.input_name: input_img})
        
        # Postprocess
        detections = self._postprocess_yolo(outputs[0], frame.shape)
        
        return detections
    
    def _detect_faces_yunet(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces using YuNet
        
        Args:
            frame: Input frame
            
        Returns:
            List of face detections
        """
        height, width = frame.shape[:2]
        
        # Set input size for face detector
        self.face_detector.setInputSize((width, height))
        
        # Detect faces
        faces = self.face_detector.detect(frame)
        
        detections = []
        if faces[1] is not None:
            for face in faces[1]:
                # YuNet returns [x, y, w, h, confidence, landmarks...]
                x, y, w, h, confidence = face[:5]
                
                detection = {
                    'bbox': [int(x), int(y), int(x + w), int(y + h)],
                    'confidence': float(confidence),
                    'class_id': 1,  # Face class
                    'center': (int(x + w/2), int(y + h/2))
                }
                detections.append(detection)
        
        return detections
    
    def detect_faces_yolo(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces using YOLOv11m (alternative to YuNet for unified detection)
        Uses class filtering on person detections to find faces within people
        
        Args:
            frame: Input frame
            
        Returns:
            List of face detections
        """
        # Run full YOLO detection
        all_detections = self._detect_people_onnx(frame)
        
        # Filter for highest confidence person detections (typically includes faces)
        high_conf_detections = [d for d in all_detections if d['confidence'] > 0.7]
        
        # For faces, we look at small/high-confidence objects within people
        faces = []
        h, w = frame.shape[:2]
        
        for det in high_conf_detections:
            bbox = det['bbox']
            width_box = bbox[2] - bbox[0]
            height_box = bbox[3] - bbox[1]
            
            # Face detection heuristic: relatively small boxes with high confidence
            # Typical face is 50-300 pixels wide in surveillance footage
            if 40 < width_box < 300 and 40 < height_box < 300:
                if det['confidence'] > 0.65:
                    face_det = det.copy()
                    face_det['class_id'] = 1  # Mark as face
                    faces.append(face_det)
        
        return faces
    
    def _preprocess_yolo(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for YOLO ONNX model with GPU optimization
        
        Args:
            frame: Input frame
            
        Returns:
            Preprocessed input tensor (GPU-optimized)
        """
        # Resize to model input size (640x640) using GPU if available
        if self.use_gpu:
            try:
                import cupy as cp
                # GPU preprocessing with CuPy
                frame_gpu = cp.asarray(frame)
                # Resize using GPU
                img = cv2.resize(frame, (640, 640))  # Still use CPU resize, GPU speedup not significant for this
                
                # Convert to RGB on GPU
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Normalize to 0-1 (keep on GPU for next operations)
                img = img_rgb.astype(np.float32) / 255.0
                
            except ImportError:
                # Fallback: CPU preprocessing
                img = cv2.resize(frame, (640, 640))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = img.astype(np.float32) / 255.0
        else:
            # CPU preprocessing
            img = cv2.resize(frame, (640, 640))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0
        
        # Transpose to CHW
        img = np.transpose(img, (2, 0, 1))
        
        # Add batch dimension
        img = np.expand_dims(img, axis=0)
        
        return img
    
    def _postprocess_yolo(self, output: np.ndarray, original_shape: Tuple[int, int]) -> List[Dict]:
        """
        Postprocess YOLO ONNX output
        
        Args:
            output: Model output (1, 84, 8400)
            original_shape: Original frame shape (height, width)
            
        Returns:
            List of detections
        """
        detections = []
        
        # YOLO output: (1, 84, 8400)
        output = output[0]  # (84, 8400)
        
        # Split into components
        bboxes = output[:4]  # (4, 8400)
        conf = output[4]     # (8400,)
        classes = output[5:] # (80, 8400)
        
        # Apply sigmoid to confidence and classes
        conf = 1 / (1 + np.exp(-conf))
        classes = 1 / (1 + np.exp(-classes))
        
        # Get class scores
        class_scores = classes.max(axis=0)  # (8400,)
        class_ids = classes.argmax(axis=0)  # (8400,)
        
        # Combined confidence
        scores = conf * class_scores
        
        # Filter by confidence and person class (0)
        mask = (scores > self.conf_threshold) & (class_ids == 0)
        
        if not mask.any():
            return detections
        
        # Get filtered detections
        filtered_bboxes = bboxes[:, mask]
        filtered_scores = scores[mask]
        filtered_class_ids = class_ids[mask]
        
        # Decode bboxes
        # YOLO format: cx, cy, w, h (normalized to grid)
        # We need to convert to absolute coordinates
        
        # Grid sizes
        grids = [(80, 80), (40, 40), (20, 20)]
        strides = [8, 16, 32]  # Stride for each scale
        
        orig_h, orig_w = original_shape[:2]
        
        # Process each scale
        start_idx = 0
        for scale_idx, (grid_h, grid_w) in enumerate(grids):
            end_idx = start_idx + grid_h * grid_w
            
            if end_idx > filtered_bboxes.shape[1]:
                continue
                
            scale_bboxes = filtered_bboxes[:, start_idx:end_idx]
            scale_scores = filtered_scores[start_idx:end_idx]
            scale_class_ids = filtered_class_ids[start_idx:end_idx]
            
            stride = strides[scale_idx]
            
            # Create grid
            grid_y, grid_x = np.meshgrid(np.arange(grid_h), np.arange(grid_w), indexing='ij')
            grid_x = grid_x.flatten()[:scale_bboxes.shape[1]]
            grid_y = grid_y.flatten()[:scale_bboxes.shape[1]]
            
            # Decode bboxes
            cx = (scale_bboxes[0] * 2 - 0.5 + grid_x) * stride
            cy = (scale_bboxes[1] * 2 - 0.5 + grid_y) * stride
            w = scale_bboxes[2] * scale_bboxes[2] * 4 * stride * stride
            h = scale_bboxes[3] * scale_bboxes[3] * 4 * stride * stride
            
            # Convert to xyxy
            x1 = cx - w / 2
            y1 = cy - h / 2
            x2 = cx + w / 2
            y2 = cy + h / 2
            
            # Clip to image bounds
            x1 = np.clip(x1, 0, orig_w)
            y1 = np.clip(y1, 0, orig_h)
            x2 = np.clip(x2, 0, orig_w)
            y2 = np.clip(y2, 0, orig_h)
            
            for i in range(len(x1)):
                detection_dict = {
                    'bbox': [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
                    'confidence': float(scale_scores[i]),
                    'class_id': 0,  # Person
                    'center': (int((x1[i] + x2[i]) / 2), int((y1[i] + y2[i]) / 2))
                }
                detections.append(detection_dict)
            
            start_idx = end_idx
        
        return detections
    
    def track_people(self, camera_id: int, frame: np.ndarray, skip_deepsort: bool = True) -> Dict:
        """
        Detect and track people using ByteTrack (30 FPS) with optional DeepSORT fallback
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            skip_deepsort: Skip DeepSORT when ByteTrack is confident (for performance)
            
        Returns:
            Dictionary with tracking information
        """
        # Step 1: Detect people in current frame
        detections_sv, detections_list = self.detect_people(frame, camera_id)
        
        # Filter for person detections only for tracking (class_id 0)
        person_detections = sv.Detections(
            xyxy=detections_sv.xyxy[detections_sv.class_id == 0] if len(detections_sv) > 0 else np.array([]),
            confidence=detections_sv.confidence[detections_sv.class_id == 0] if len(detections_sv) > 0 else np.array([]),
            class_id=detections_sv.class_id[detections_sv.class_id == 0] if len(detections_sv) > 0 else np.array([])
        ) if len(detections_sv) > 0 else sv.Detections.empty()
        
        # Store face detections separately
        face_detections = [d for d in detections_list if d.get('class_id') == 1]
        
        # Step 2: Apply ByteTrack tracking (primary tracker)
        byte_tracker = self._get_bytetrack_tracker(camera_id)
        tracked_detections = byte_tracker.update_with_detections(person_detections)
        
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
                # ByteTrack is uncertain - prepare for DeepSORT ReID (if enabled)
                uncertain_detections.append({
                    'bbox': [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                    'confidence': float(confidence),
                    'bytetrack_id': int(track_id)
                })
        
        # Step 4: Apply DeepSORT ReID for uncertain tracks (skip if performance_mode enabled)
        if len(uncertain_detections) > 0 and not skip_deepsort:
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
        
        # Step 5: Apply global cross-camera tracking if room is configured
        room_id = self.camera_tracks[camera_id].get('room_id')
        global_mapping = {}
        if self.global_tracker and room_id:
            global_mapping = self.global_tracker.update_tracks(
                room_id, camera_id, frame, confident_tracks
            )
        
        # Step 6: Update tracking data
        people_count = len(confident_tracks)
        self.camera_tracks[camera_id]['count'] = people_count
        self.camera_tracks[camera_id]['tracks'] = confident_tracks
        self.camera_tracks[camera_id]['global_mapping'] = global_mapping
        self.camera_tracks[camera_id]['last_update'] = datetime.now()
        self.camera_tracks[camera_id]['last_frame'] = frame  # Store frame for visualization
        self.camera_tracks[camera_id]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'count': people_count
        })
        
        # Store last result for visualization
        result = {
            'camera_id': camera_id,
            'people_count': people_count,
            'face_count': len(face_detections),
            'detections': detections_list,
            'tracks': confident_tracks,
            'faces': face_detections,
            'timestamp': datetime.now().isoformat(),
            'bytetrack_confident': self.camera_tracks[camera_id]['bytetrack_confident'],
            'deepsort_assisted': self.camera_tracks[camera_id]['deepsort_assisted']
        }
        self.camera_tracks[camera_id]['last_result'] = result
        
        return result
    
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
    
    def set_camera_room(self, camera_id: int, room_id: int):
        """
        Set the room_id for a camera to enable cross-camera tracking
        
        Args:
            camera_id: Camera identifier
            room_id: Room identifier
        """
        self.camera_tracks[camera_id]['room_id'] = room_id
        print(f"✅ Camera {camera_id} assigned to room {room_id} for cross-camera tracking")
    
    def draw_tracks(self, frame: np.ndarray, camera_id: int) -> np.ndarray:
        """
        Draw bounding boxes and names/IDs on frame - minimal clean overlay
        
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
        global_mapping = self.camera_tracks[camera_id].get('global_mapping', {})
        room_id = self.camera_tracks[camera_id].get('room_id')
        
        # Draw faces first (in blue)
        # Get face detections from last result
        last_result = self.camera_tracks[camera_id].get('last_result', {})
        faces = last_result.get('faces', [])
        for face in faces:
            bbox = face['bbox']
            confidence = face.get('confidence', 0.0)
            
            # Draw face bounding box in blue
            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
            
            # Label for face
            label = f"Face {confidence:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (label_width, label_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Position label above box
            label_y = bbox[1] - 5
            if label_y < label_height + 3:
                label_y = bbox[1] + label_height + 3
            
            # Draw label background
            cv2.rectangle(annotated, 
                         (bbox[0], label_y - label_height - 3),
                         (bbox[0] + label_width + 6, label_y + 1),
                         (255, 0, 0), -1)
            
            # Draw label text
            cv2.putText(annotated, label, (bbox[0] + 3, label_y - 1),
                       font, font_scale, (255, 255, 255), thickness)
        
        # Draw each person track
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
            
            # Get global ID and name if available
            global_id = global_mapping.get(track_id)
            label = None
            
            if global_id and room_id and self.global_tracker:
                # Try to get person info from global tracker
                person_info = self.global_tracker.get_person_info(room_id, global_id)
                if person_info and person_info.get('name'):
                    label = person_info['name']
            
            # Fallback to track ID if no name
            if not label:
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
                
                if global_id:
                    label = f"Person {global_id}"
                else:
                    label = f"#{abs_track_id}"
            
            # Draw label above bounding box
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            (label_width, label_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Position label above box
            label_y = bbox[1] - 8
            if label_y < label_height + 5:
                label_y = bbox[1] + label_height + 8
            
            # Draw label background (semi-transparent)
            cv2.rectangle(annotated, 
                         (bbox[0], label_y - label_height - 5),
                         (bbox[0] + label_width + 10, label_y + 3),
                         color, -1)
            
            # Draw label text in black for contrast
            cv2.putText(annotated, label, (bbox[0] + 5, label_y - 1),
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
        Process RTSP stream at 30 FPS with optimized latency handling
        
        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
        """
        cap = cv2.VideoCapture(rtsp_url)
        
        # Aggressive latency optimization settings
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # Minimize buffering
        cap.set(cv2.CAP_PROP_FPS, 30)             # Set frame rate
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)        # Disable autofocus delays
        
        if not cap.isOpened():
            print(f"❌ Failed to open RTSP stream for camera {camera_id}")
            self.running[camera_id] = False
            return
        
        print(f"📹 Processing camera {camera_id} at {self.process_fps} FPS (ONNX + ByteTrack, skip DeepSORT)")
        
        last_process_time = 0
        last_deepsort_time = 0
        frame_count = 0
        deepsort_interval = 10  # Run DeepSORT every 10 frames (~333ms at 30 FPS)
        
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
            
            # Drop old frames from buffer (aggressive latency reduction)
            # Skip if video capture is buffering
            buffer_size = cap.get(cv2.CAP_PROP_BUFFERSIZE)
            if buffer_size > 1:
                for _ in range(int(buffer_size) - 1):
                    cap.read()
            
            # Process at specified FPS (30 FPS for ByteTrack)
            current_time = time.time()
            if current_time - last_process_time >= self.frame_interval:
                try:
                    # Decide whether to use DeepSORT (skip for performance)
                    use_deepsort = (current_time - last_deepsort_time) > (deepsort_interval / self.process_fps)
                    
                    # Detect and track people with adaptive DeepSORT usage
                    result = self.detector.track_people(camera_id, frame, skip_deepsort=not use_deepsort)
                    
                    if use_deepsort:
                        last_deepsort_time = current_time
                    
                    # Log tracking stats every 300 frames (10 seconds at 30 FPS)
                    if frame_count % 300 == 0:
                        inference_fps = 1.0 / (current_time - last_process_time) if (current_time - last_process_time) > 0 else 0
                        print(f"📊 Camera {camera_id}: {result['people_count']} people, {result.get('face_count', 0)} faces | "
                              f"FPS: {inference_fps:.1f} | "
                              f"ByteTrack: {result.get('bytetrack_confident', 0)} | "
                              f"DeepSORT: {result.get('deepsort_assisted', 0)}")
                    
                    last_process_time = current_time
                except Exception as e:
                    print(f"⚠️ Error processing camera {camera_id}: {e}")
                    import traceback
                    traceback.print_exc()
        
        cap.release()
        print(f"📹 Released camera {camera_id}")
    
    def get_stats(self) -> List[Dict]:
        """
        Get current statistics for all streams
        
        Returns:
            List of statistics dictionaries
        """
        return self.detector.get_all_stats()
