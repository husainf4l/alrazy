"""
AI Vision Analyzer - Corporate FastAPI Application
Clean, minimal implementation with YOLO model switching
"""

import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from ultralytics import YOLO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MODELS_DIR = Path("yolo-models")
MODELS_DIR.mkdir(exist_ok=True)

# COCO Pose Keypoints (17 points)
POSE_KEYPOINTS = [
    "nose",           # 0
    "left_eye",       # 1
    "right_eye",      # 2
    "left_ear",       # 3
    "right_ear",      # 4
    "left_shoulder",  # 5
    "right_shoulder", # 6
    "left_elbow",     # 7
    "right_elbow",    # 8
    "left_wrist",     # 9
    "right_wrist",    # 10
    "left_hip",       # 11
    "right_hip",      # 12
    "left_knee",      # 13
    "right_knee",     # 14
    "left_ankle",     # 15
    "right_ankle"     # 16
]

# Pose skeleton connections for visualization
POSE_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],  # legs
    [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],         # torso to arms
    [8, 10], [9, 11], [2, 3], [1, 2], [1, 3],         # arms and face
    [2, 4], [3, 5], [4, 6], [5, 7]                    # face to shoulders
]

class Settings(BaseModel):
    """Application settings with validation"""
    model_name: str = Field(default="yolo11n.pt", description="YOLO model filename")
    confidence: float = Field(default=0.25, ge=0.1, le=0.9, description="Detection confidence threshold")
    iou_threshold: float = Field(default=0.45, ge=0.1, le=0.9, description="IoU threshold for non-maximum suppression")
    show_labels: bool = Field(default=True, description="Show detection labels")
    show_confidence: bool = Field(default=True, description="Show confidence scores")
    show_pose_keypoints: bool = Field(default=True, description="Show pose keypoints")
    show_pose_skeleton: bool = Field(default=True, description="Show pose skeleton connections")

class SettingsUpdateModel(BaseModel):
    """Model for settings updates"""
    model_name: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.1, le=0.9)
    iou_threshold: Optional[float] = Field(None, ge=0.1, le=0.9)
    show_labels: Optional[bool] = None
    show_confidence: Optional[bool] = None
    show_pose_keypoints: Optional[bool] = None
    show_pose_skeleton: Optional[bool] = None

# Services
class ModelService:
    """Service for managing YOLO models with proper error handling"""
    
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.current_model: Optional[str] = None
        self.settings = Settings()
        logger.info("ModelService initialized")
    
    def get_available_models(self) -> Dict[str, Dict]:
        """Get available YOLO models from models directory"""
        models = {}
        
        if not MODELS_DIR.exists():
            logger.warning(f"Models directory {MODELS_DIR} does not exist")
            return models
            
        try:
            for model_file in MODELS_DIR.glob("*.pt"):
                name = model_file.name
                models[name] = {
                    "name": name,
                    "type": self._get_model_type(name),
                    "size": self._get_file_size(model_file)
                }
            logger.info(f"Found {len(models)} available models")
        except Exception as e:
            logger.error(f"Error scanning models directory: {e}")
            
        return models
    
    def _get_model_type(self, filename: str) -> str:
        """Determine model type from filename"""
        filename_lower = filename.lower()
        if "seg" in filename_lower:
            return "segmentation"
        elif "pose" in filename_lower:
            return "pose"
        else:
            return "detection"
    
    def _draw_pose_keypoints(self, frame: np.ndarray, result) -> np.ndarray:
        """Draw pose keypoints and skeleton on frame using settings confidence threshold"""
        if result is None or not hasattr(result, 'keypoints') or result.keypoints is None:
            return frame
            
        try:
            keypoints = result.keypoints
            
            # Use the actual confidence threshold from settings
            actual_threshold = self.settings.confidence
            logger.info(f"Using confidence threshold: {actual_threshold}")
            
            # Handle different keypoint formats
            if hasattr(keypoints, 'xy') and hasattr(keypoints, 'conf'):
                # YOLO format with separate xy and confidence
                xy = keypoints.xy.cpu().numpy()  # Shape: (batch, 17, 2)
                conf = keypoints.conf.cpu().numpy()  # Shape: (batch, 17)
                
                if len(xy.shape) == 3 and xy.shape[0] > 0:  # Has detections
                    for person_idx in range(min(xy.shape[0], 5)):  # Limit to 5 people max
                        person_xy = xy[person_idx]  # Shape: (17, 2)
                        person_conf = conf[person_idx]  # Shape: (17,)
                        
                        # Draw keypoints
                        if self.settings.show_pose_keypoints:
                            for i in range(len(person_xy)):
                                if i < len(person_conf) and person_conf[i] > actual_threshold:
                                    x, y = int(person_xy[i][0]), int(person_xy[i][1])
                                    if x > 0 and y > 0:  # Valid coordinates
                                        # Color-code keypoints based on confidence
                                        confidence = person_conf[i]
                                        if confidence >= 0.8:
                                            color = (0, 255, 0)  # Bright green for high confidence
                                        elif confidence >= 0.6:
                                            color = (0, 255, 255)  # Yellow for medium confidence
                                        else:
                                            color = (0, 165, 255)  # Orange for lower confidence
                                        
                                        # Draw keypoint circle
                                        cv2.circle(frame, (x, y), 3, color, -1)
                                        cv2.circle(frame, (x, y), 4, (255, 255, 255), 1)  # White border
                                        
                                        # Draw keypoint label with confidence if enabled
                                        if self.settings.show_labels and i < len(POSE_KEYPOINTS):
                                            if self.settings.show_confidence:
                                                label = f"{POSE_KEYPOINTS[i]}"
                                                conf_text = f"{confidence:.0%}"
                                            else:
                                                label = POSE_KEYPOINTS[i]
                                                conf_text = ""
                                            
                                            # Calculate text dimensions for proper positioning
                                            font = cv2.FONT_HERSHEY_SIMPLEX
                                            font_scale = 0.25
                                            thickness = 1
                                            
                                            label_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                                            conf_size = cv2.getTextSize(conf_text, font, font_scale, thickness)[0] if conf_text else (0, 0)
                                            
                                            # Position label above keypoint
                                            label_x = max(1, min(x - label_size[0] // 2, frame.shape[1] - max(label_size[0], conf_size[0]) - 1))
                                            label_y = max(15, y - 8)
                                            
                                            # Draw tiny background
                                            padding = 1
                                            bg_x1 = label_x - padding
                                            bg_y1 = label_y - label_size[1] - padding
                                            bg_x2 = label_x + max(label_size[0], conf_size[0]) + padding
                                            bg_y2 = label_y + padding + (conf_size[1] if conf_text else 0)
                                            
                                            # Semi-transparent background
                                            cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
                                            
                                            # Draw text
                                            cv2.putText(frame, label, (label_x, label_y),
                                                      font, font_scale, (255, 255, 255), thickness)
                                            
                                            # Draw confidence if enabled
                                            if conf_text:
                                                conf_y = label_y + conf_size[1] + 1
                                                cv2.putText(frame, conf_text, (label_x, conf_y),
                                                          font, font_scale, color, thickness)
                        
                        # Draw skeleton connections
                        if self.settings.show_pose_skeleton:
                            for connection in POSE_SKELETON:
                                pt1_idx, pt2_idx = connection[0] - 1, connection[1] - 1  # Convert to 0-based
                                if (0 <= pt1_idx < len(person_xy) and 0 <= pt2_idx < len(person_xy) and
                                    pt1_idx < len(person_conf) and pt2_idx < len(person_conf)):
                                    
                                    if (person_conf[pt1_idx] > actual_threshold and 
                                        person_conf[pt2_idx] > actual_threshold):
                                        
                                        x1, y1 = int(person_xy[pt1_idx][0]), int(person_xy[pt1_idx][1])
                                        x2, y2 = int(person_xy[pt2_idx][0]), int(person_xy[pt2_idx][1])
                                        
                                        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:  # Valid coordinates
                                            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)
            else:
                # Alternative format - try to handle as combined array
                keypoints_data = keypoints.cpu().numpy() if hasattr(keypoints, 'cpu') else keypoints
                if len(keypoints_data.shape) >= 2:
                    logger.info(f"Keypoints shape: {keypoints_data.shape}")
                    
        except Exception as e:
            logger.error(f"Error drawing pose keypoints: {e}")
            logger.error(f"Keypoints type: {type(keypoints) if 'keypoints' in locals() else 'undefined'}")
            
        return frame

    def _enhance_detection_labels(self, frame: np.ndarray, result) -> np.ndarray:
        """Enhance detection labels with better styling"""
        try:
            if hasattr(result, 'boxes') and result.boxes is not None:
                boxes = result.boxes
                if len(boxes) > 0:
                    for box in boxes:
                        # Get box coordinates and info
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        
                        # Only show if above confidence threshold
                        if conf >= self.settings.confidence:
                            # Get class name
                            class_name = result.names[cls] if hasattr(result, 'names') else f"Class {cls}"
                            
                            # Create simple label
                            if self.settings.show_confidence:
                                label = f"{class_name} {conf:.0%}"
                            else:
                                label = class_name
                            
                            # Draw minimal bounding box
                            color = self._get_class_color(cls)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
                            
                            # Draw enhanced label
                            if self.settings.show_labels:
                                self._draw_enhanced_label(frame, label, (x1, y1), color)
                                
        except Exception as e:
            logger.error(f"Error enhancing detection labels: {e}")
        
        return frame
    
    def _get_class_color(self, class_id: int) -> tuple:
        """Get consistent color for each class"""
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
            (0, 255, 255), (255, 165, 0), (255, 20, 147), (0, 191, 255), (34, 139, 34)
        ]
        return colors[class_id % len(colors)]
    
    def _draw_enhanced_label(self, frame: np.ndarray, label: str, position: tuple, color: tuple):
        """Draw tiny, minimal label"""
        x, y = position
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.3
        thickness = 1
        
        # Get text dimensions
        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        
        # Position label above box
        label_y = max(text_h + 5, y - 5)
        label_x = max(0, min(x, frame.shape[1] - text_w - 2))
        
        # Draw tiny background
        padding = 1
        bg_x1 = label_x - padding
        bg_y1 = label_y - text_h - padding
        bg_x2 = label_x + text_w + padding
        bg_y2 = label_y + padding
        
        # Semi-transparent background
        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        
        # Draw text
        cv2.putText(frame, label, (label_x, label_y), font, font_scale, (255, 255, 255), thickness)
    
    def _get_file_size(self, filepath: Path) -> str:
        """Get human readable file size"""
        try:
            size_bytes = filepath.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.1f}MB"
        except Exception as e:
            logger.error(f"Error getting file size for {filepath}: {e}")
            return "Unknown"
    
    def load_model(self, model_name: str) -> bool:
        """Load YOLO model with proper error handling"""
        if not model_name:
            logger.error("Model name cannot be empty")
            return False
            
        try:
            model_path = MODELS_DIR / model_name
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
            
            if self.current_model != model_name:
                logger.info(f"Loading YOLO model: {model_name}")
                self.model = YOLO(str(model_path))
                self.current_model = model_name
                logger.info(f"Model {model_name} loaded successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            self.model = None
            self.current_model = None
            return False
    
    def update_settings(self, new_settings: Dict) -> bool:
        """Update model settings with validation"""
        try:
            old_model = self.settings.model_name
            
            # Create new settings object with validation
            settings_data = self.settings.model_dump()
            settings_data.update({k: v for k, v in new_settings.items() if v is not None})
            
            self.settings = Settings(**settings_data)
            
            # Load new model if changed
            if old_model != self.settings.model_name:
                if not self.load_model(self.settings.model_name):
                    # Revert settings if model loading failed
                    self.settings.model_name = old_model
                    return False
            
            logger.info(f"Settings updated: {self.settings}")
            return True
            
        except Exception as e:
            logger.error(f"Settings update failed: {e}")
            return False

class CameraService:
    """Service for camera operations with proper resource management"""
    
    def __init__(self):
        self.video: Optional[cv2.VideoCapture] = None
        self.frame_width = 640
        self.frame_height = 480
        self._initialize_camera()
    
    def _initialize_camera(self) -> None:
        """Initialize camera with error handling"""
        try:
            self.video = cv2.VideoCapture(0)
            if self.video and self.video.isOpened():
                # Configure camera properties
                self.video.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.video.set(cv2.CAP_PROP_FPS, 30)
                logger.info("Camera initialized successfully")
            else:
                logger.warning("Camera not available - using placeholder")
                self.video = None
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            self.video = None
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get camera frame with fallback to placeholder"""
        if not self.video or not self.video.isOpened():
            return self._create_placeholder_frame()
        
        try:
            ret, frame = self.video.read()
            if ret and frame is not None:
                return frame
            else:
                logger.warning("Failed to read frame from camera")
                return self._create_placeholder_frame()
        except Exception as e:
            logger.error(f"Error reading camera frame: {e}")
            return self._create_placeholder_frame()
    
    def _create_placeholder_frame(self) -> np.ndarray:
        """Create placeholder frame when camera is unavailable"""
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame[:] = (64, 64, 64)  # Dark gray background
        
        # Add text
        text = "Camera Not Available"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        color = (255, 255, 255)
        thickness = 2
        
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        x = (self.frame_width - text_size[0]) // 2
        y = (self.frame_height + text_size[1]) // 2
        
        cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
        
        return frame
    
    def release(self) -> None:
        """Properly release camera resources"""
        if self.video:
            try:
                self.video.release()
                logger.info("Camera resources released")
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")
            finally:
                self.video = None
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (45, 45, 45)
        
        cv2.putText(frame, "Camera Not Available", (180, 220), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, "Check camera permissions", (190, 260), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def __del__(self):
        if self.video:
            self.video.release()

# Global services
model_service: Optional[ModelService] = None
camera_service: Optional[CameraService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global model_service, camera_service
    
    # Startup
    logger.info("Starting AI Vision Analyzer...")
    
    # Initialize services
    model_service = ModelService()
    camera_service = CameraService()
    
    # Load initial model if available
    models = model_service.get_available_models()
    if models:
        first_model = next(iter(models))
        model_service.load_model(first_model)
        logger.info(f"Loaded initial model: {first_model}")
    else:
        logger.warning("No models found in models directory")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Vision Analyzer...")
    if camera_service:
        camera_service.release()
    logger.info("Shutdown complete")

# FastAPI Application
app = FastAPI(
    title="AI Vision Analyzer",
    description="Corporate AI Vision System with YOLO Integration",
    version="1.0.0",
    lifespan=lifespan
)

templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve main application page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/pose-keypoints")
async def get_pose_keypoints():
    """Get the 17 COCO pose keypoint labels"""
    return {
        "keypoints": POSE_KEYPOINTS,
        "total_count": len(POSE_KEYPOINTS),
        "skeleton_connections": POSE_SKELETON
    }

@app.get("/api/models")
async def get_models():
    """Get available YOLO models"""
    if not model_service:
        raise HTTPException(status_code=500, detail="Model service not initialized")
        
    try:
        models = model_service.get_available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")

@app.get("/api/settings")
async def get_settings():
    """Get current settings"""
    if not model_service:
        raise HTTPException(status_code=500, detail="Model service not initialized")
        
    try:
        return model_service.settings.model_dump()
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdateModel):
    """Update detection settings"""
    if not model_service:
        raise HTTPException(status_code=500, detail="Model service not initialized")
        
    try:
        # Convert to dict for update
        update_data = settings.model_dump(exclude_none=True)
        
        if model_service.update_settings(update_data):
            logger.info(f"Settings updated successfully: {update_data}")
            return {"status": "success", "message": "Settings updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update settings")
            
    except Exception as e:
        logger.error(f"Settings update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video_feed")
async def video_feed():
    """Video streaming endpoint with AI processing"""
    if not camera_service:
        raise HTTPException(status_code=500, detail="Camera service not initialized")
    
    def generate():
        """Generate video frames with AI detection"""
        while True:
            try:
                frame = camera_service.get_frame()
                if frame is None:
                    logger.warning("No frame received from camera")
                    break
                
                # Process with AI if model is loaded
                if model_service and model_service.model is not None:
                    try:
                        results = model_service.model(
                            frame,
                            conf=model_service.settings.confidence,
                            iou=model_service.settings.iou_threshold,
                            verbose=False
                        )
                        
                        # Handle different model types
                        current_model_type = model_service._get_model_type(model_service.current_model or "")
                        
                        if current_model_type == "pose":
                            # Custom pose visualization
                            for result in results:
                                if hasattr(result, 'keypoints') and result.keypoints is not None:
                                    frame = model_service._draw_pose_keypoints(frame, result)
                                    break
                                    
                                # Fallback to YOLO's built-in visualization
                                if hasattr(result, 'plot'):
                                    frame = result.plot(
                                        conf=model_service.settings.show_confidence,
                                        labels=model_service.settings.show_labels
                                    )
                                    break
                        else:
                            # Enhanced detection/segmentation visualization
                            for result in results:
                                # Use custom enhanced labels instead of default YOLO plot
                                if model_service.settings.show_labels or model_service.settings.show_confidence:
                                    frame = model_service._enhance_detection_labels(frame, result)
                                else:
                                    # Use YOLO's built-in visualization without labels
                                    if hasattr(result, 'plot'):
                                        frame = result.plot(
                                            conf=False,
                                            labels=False
                                        )
                                        break
                                    
                    except Exception as e:
                        logger.error(f"AI processing error: {e}")
                        # Continue with unprocessed frame
                
                # Encode frame as JPEG
                try:
                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ret:
                        logger.error("Failed to encode frame")
                        continue
                        
                    frame_bytes = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                           
                except Exception as e:
                    logger.error(f"Frame encoding error: {e}")
                    continue
                    
            except Exception as e:
                logger.error(f"Video feed error: {e}")
                break
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Production-ready server configuration
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Only for development
        log_level="info",
        access_log=True
    )