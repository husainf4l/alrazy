"""
SafeRoom Detection System Backend
FastAPI + YOLOv8 + ByteTrack + Redis
"""

import asyncio
import base64
import io
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np
import cv2
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
import uvicorn
import redis
from contextlib import asynccontextmanager

# Detection/Tracking
try:
    from ultralytics import YOLO
    import supervision as sv
    from supervision.tracker.byte_tracker.core import ByteTrack
    from supervision.detection.core import Detections
    DETECTION_AVAILABLE = True
    BYTETRACK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ultralytics or supervision not installed. Detection will be limited. Error: {e}")
    YOLO = None
    ByteTrack = None
    Detections = None
    DETECTION_AVAILABLE = False
    BYTETRACK_AVAILABLE = False

# WebRTC support for mobile/remote streaming
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from av import VideoFrame
    WEBRTC_AVAILABLE = True
    print("✅ WebRTC (aiortc) module loaded")
except ImportError as e:
    print(f"⚠️  WebRTC not available: {e}. Using WebSocket only.")
    RTCPeerConnection = None
    RTCSessionDescription = None
    VideoStreamTrack = None
    WEBRTC_AVAILABLE = False

# Enhanced tracking (hybrid with DeepSORT fallback)
try:
    from tracker.deepsort import HybridTracker, EnhancedDetectionTracker
    ENHANCED_TRACKING_AVAILABLE = True
    print("✅ Enhanced tracking module loaded")
except ImportError as e:
    print(f"⚠️  Enhanced tracking not available: {e}. Using standard ByteTrack.")
    HybridTracker = None
    EnhancedDetectionTracker = None
    ENHANCED_TRACKING_AVAILABLE = False

# Person Re-Identification (persistent person labeling)
try:
    from reid.person_reidentifier import PersonReIdentifier
    from reid.storage import PersonRedisStorage, CloudEmbeddingStorage
    REID_AVAILABLE = True
    print("✅ Person re-ID module loaded")
except ImportError as e:
    print(f"⚠️  Person re-ID not available: {e}. Running without re-ID.")
    PersonReIdentifier = None
    PersonRedisStorage = None
    CloudEmbeddingStorage = None
    REID_AVAILABLE = False

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ROOM_ID = os.environ.get("ROOM_ID", "room_safe")
VIOLATION_ACTION_WEBHOOK = os.environ.get("VIOLATION_WEBHOOK", "")
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL", "yolov8n.pt")  # KEPT nano for real-time performance with 4 cameras
MAX_OCCUPANCY = int(os.environ.get("MAX_OCCUPANCY", "1"))
VIOLATION_THRESHOLD = int(os.environ.get("VIOLATION_THRESHOLD", "2"))
USE_ENHANCED_TRACKING = os.environ.get("USE_ENHANCED_TRACKING", "true").lower() in ["true", "1", "yes"]
USE_PERSON_REID = os.environ.get("USE_PERSON_REID", "true").lower() in ["true", "1", "yes"]
REID_SIMILARITY_THRESHOLD = float(os.environ.get("REID_SIMILARITY_THRESHOLD", "0.65"))  # OPTIMIZED: 0.6 → 0.65 (stricter)

# Global state
redis_client = None
yolo_model: Optional[Any] = None
trackers: Dict[str, Any] = {}
enhanced_trackers: Dict[str, Any] = {}  # For enhanced hybrid trackers
person_reidentifiers: Dict[str, Any] = {}  # Per-camera re-ID instances (DEPRECATED: use global_person_reidentifier)
person_storages: Dict[str, Any] = {}  # Per-camera storage instances (DEPRECATED: use global_person_storage)

# GLOBAL cross-camera re-ID (NEW: shared across all cameras)
global_person_reidentifier: Optional[Any] = None  # Shared re-ID gallery for all cameras
global_person_storage: Optional[Any] = None  # Shared Redis storage for all cameras

# WebRTC state for mobile/remote viewing
webrtc_connections: Dict[str, Any] = {}  # Active WebRTC peer connections
camera_frames_cache: Dict[str, bytes] = {}  # Cache latest frame from each camera

# WebRTC Token Authentication System
import secrets
import hashlib
from datetime import datetime, timedelta

WEBRTC_TOKENS: Dict[str, Dict[str, Any]] = {}  # token -> {expires_at, camera_ids, created_at}
TOKEN_EXPIRY_HOURS = int(os.environ.get("WEBRTC_TOKEN_EXPIRY_HOURS", "24"))
MASTER_SECRET = os.environ.get("WEBRTC_MASTER_SECRET", "")  # Set this for token generation

def generate_webrtc_token(camera_ids: List[str] = None, expires_hours: int = None) -> str:
    """Generate a secure WebRTC connection token"""
    if camera_ids is None:
        camera_ids = ["room1", "room2", "room3", "room4"]
    if expires_hours is None:
        expires_hours = TOKEN_EXPIRY_HOURS
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=expires_hours)
    
    WEBRTC_TOKENS[token] = {
        "expires_at": expires_at,
        "camera_ids": camera_ids,
        "created_at": datetime.now(),
        "used_count": 0
    }
    
    return token

def validate_webrtc_token(token: str, camera_id: str = None) -> bool:
    """Validate WebRTC token"""
    if token not in WEBRTC_TOKENS:
        return False
    
    token_data = WEBRTC_TOKENS[token]
    
    # Check expiry
    if datetime.now() > token_data["expires_at"]:
        del WEBRTC_TOKENS[token]
        return False
    
    # Check camera access
    if camera_id and camera_id not in token_data["camera_ids"]:
        return False
    
    # Increment usage counter
    token_data["used_count"] += 1
    
    return True

def revoke_webrtc_token(token: str) -> bool:
    """Revoke a WebRTC token"""
    if token in WEBRTC_TOKENS:
        del WEBRTC_TOKENS[token]
        return True
    return False

# ByteTrack configuration parameters - OPTIMIZED FOR BEST PERFORMANCE
TRACK_ACTIVATION_THRESHOLD = 0.50  # OPTIMIZED: 0.4 → 0.50 (stricter track activation)
LOST_TRACK_BUFFER = 45  # OPTIMIZED: 30 → 45 (1.8s @ 25fps, better for normal walking speed)
MINIMUM_MATCHING_THRESHOLD = 0.85  # OPTIMIZED: 0.8 → 0.85 (stricter matching to prevent ID switching)
FRAME_RATE = 25  # OPTIMIZED: 15 → 25 (matches actual camera FPS for accurate tracking)
MINIMUM_CONSECUTIVE_FRAMES = 2  # OPTIMIZED: 1 → 2 (require 2 frames to start tracking)

# Image Quality Configuration (for high-quality camera output)
IMAGE_QUALITY_CONFIG = {
    "jpeg_quality": int(os.environ.get("JPEG_QUALITY", "98")),  # 98 for maximum quality (0-100)
    "enable_auto_contrast": os.environ.get("AUTO_CONTRAST", "true").lower() in ["true", "1", "yes"],
    "enable_histogram_equalization": os.environ.get("HISTOGRAM_EQ", "false").lower() in ["true", "1", "yes"],
    "enable_denoise": os.environ.get("ENABLE_DENOISE", "false").lower() in ["true", "1", "yes"],  # Disabled by default (reduces detail)
    "denoise_strength": int(os.environ.get("DENOISE_STRENGTH", "5")),  # 3-15, higher = more denoising
    "enable_clahe": os.environ.get("ENABLE_CLAHE", "true").lower() in ["true", "1", "yes"],  # Contrast-limited adaptive histogram equalization
    "clahe_clip_limit": float(os.environ.get("CLAHE_CLIP_LIMIT", "2.0")),  # Recommended: 2.0-4.0
    "clahe_tile_size": int(os.environ.get("CLAHE_TILE_SIZE", "8")),  # Tile grid size
    "enable_sharpening": os.environ.get("ENABLE_SHARPENING", "true").lower() in ["true", "1", "yes"],
    "sharpening_strength": float(os.environ.get("SHARPENING_STRENGTH", "1.2")),  # 1.0 = no sharpening, 2.0 = strong
    "resize_to_max": int(os.environ.get("MAX_IMAGE_SIZE", "0")),  # 0 = no resize, otherwise max dimension
}

# Professional Streaming Configuration (2K Video)
STREAMING_CONFIG = {
    "enabled": os.environ.get("STREAMING_ENABLED", "true").lower() in ["true", "1", "yes"],
    "codec": os.environ.get("STREAMING_CODEC", "H.265"),  # H.265 (HEVC) or H.264
    "resolution": tuple(map(int, os.environ.get("STREAMING_RESOLUTION", "2560,1440").split(","))),  # 2560x1440 (2K)
    "fps": int(os.environ.get("STREAMING_FPS", "30")),  # 25-30 fps
    "bitrate_kbps": int(os.environ.get("STREAMING_BITRATE_KBPS", "6144")),  # 6144 kbps = 6 Mbps (4-8 Mbps range)
    "quality": os.environ.get("STREAMING_QUALITY", "high"),  # high, medium, low
}

# Enhanced tracking configuration - OPTIMIZED FOR BEST PERFORMANCE
ENHANCED_TRACK_CONFIG = {
    "use_deepsort": USE_ENHANCED_TRACKING and ENHANCED_TRACKING_AVAILABLE,
    "max_age": 45,  # OPTIMIZED: 30 → 45 (match LOST_TRACK_BUFFER for consistency)
    "n_init": 3,  # Keep reasonable (3 frames before track confirmed)
    "confidence_threshold": 0.55,  # OPTIMIZED: 0.45 → 0.55 (stricter detections, fewer false positives)
    "nms_threshold": 0.55  # OPTIMIZED: 0.5 → 0.55 (better suppression of overlapping boxes)
}

# Person Re-ID configuration
REID_CONFIG = {
    "enabled": USE_PERSON_REID and REID_AVAILABLE,
    "similarity_threshold": REID_SIMILARITY_THRESHOLD,
    "cloud_storage": os.environ.get("CLOUD_STORAGE_TYPE", "local"),  # local, s3, gcs
    "ttl_days": int(os.environ.get("REID_TTL_DAYS", "90"))
}

# ============= WebSocket Manager =============
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        print(f"✅ Client connected. Total: {len(self.active)}")

    async def disconnect(self, ws: WebSocket):
        try:
            self.active.remove(ws)
            print(f"🔌 Client disconnected. Total: {len(self.active)}")
        except ValueError:
            pass

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients"""
        disconnected = []
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"⚠️  WebSocket send error: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            await self.disconnect(ws)

manager = ConnectionManager()

# ============= Startup/Shutdown Events =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global redis_client, yolo_model
    
    # Startup
    print("🚀 Starting SafeRoom Detection System...")
    
    # Connect to Redis
    try:
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print(f"✅ Connected to Redis: {REDIS_URL}")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        redis_client = None
    
    # Load YOLO model
    try:
        yolo_model = YOLO(YOLO_MODEL_PATH)
        print(f"✅ Loaded YOLO model: {YOLO_MODEL_PATH}")
    except Exception as e:
        print(f"⚠️  YOLO model load failed: {e}. Using mock detection.")
        yolo_model = None
    
    # Initialize room state
    if redis_client:
        redis_client.hset(f"room:{ROOM_ID}:state", mapping={
            "occupancy": "0",
            "last_update": str(time.time()),
            "status": "initialized"
        })
        print(f"✅ Initialized room state: {ROOM_ID}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down SafeRoom Detection System...")
    if redis_client:
        redis_client.close()
    print("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="SafeRoom Detection (YOLOv8 + ByteTrack)",
    description="Real-time occupancy detection with violation alerts",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Helper Functions =============
def enhance_image_quality(img_bgr: np.ndarray) -> np.ndarray:
    """
    Enhance image quality using best practices.
    Focus on preserving detail while improving contrast and clarity.
    """
    img = img_bgr.copy().astype(np.float32) / 255.0
    
    # 1. Apply CLAHE (Contrast-Limited Adaptive Histogram Equalization)
    # This improves local contrast without damaging edges
    if IMAGE_QUALITY_CONFIG["enable_clahe"]:
        # Convert to LAB color space for better contrast enhancement
        img_lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2LAB)
        l_channel = img_lab[:, :, 0]
        
        # Apply CLAHE only to L channel (brightness)
        clahe = cv2.createCLAHE(
            clipLimit=IMAGE_QUALITY_CONFIG["clahe_clip_limit"],
            tileGridSize=(IMAGE_QUALITY_CONFIG["clahe_tile_size"], IMAGE_QUALITY_CONFIG["clahe_tile_size"])
        )
        l_channel_enhanced = clahe.apply(l_channel)
        
        # Merge back
        img_lab[:, :, 0] = l_channel_enhanced
        img = cv2.cvtColor(img_lab, cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
    
    # 2. Apply unsharp masking for controlled sharpening (preserves detail better than naive sharpening)
    if IMAGE_QUALITY_CONFIG["enable_sharpening"]:
        # Create a blurred version
        blurred = cv2.GaussianBlur(img, (0, 0), 2.0)
        
        # Unsharp mask: Original + (Original - Blurred) * strength
        sharpened = img + (img - blurred) * (IMAGE_QUALITY_CONFIG["sharpening_strength"] - 1.0)
        
        # Clip to valid range
        img = np.clip(sharpened, 0, 1)
    
    # 3. Optional: Apply light denoising only if explicitly enabled
    # WARNING: Heavy denoising reduces image quality for detection
    if IMAGE_QUALITY_CONFIG["enable_denoise"]:
        img_uint8 = (img * 255).astype(np.uint8)
        # Non-local means denoising (better than bilateral for preserving edges)
        img_uint8 = cv2.fastNlMeansDenoisingColored(
            img_uint8,
            h=IMAGE_QUALITY_CONFIG["denoise_strength"],
            hForColorComponents=IMAGE_QUALITY_CONFIG["denoise_strength"],
            templateWindowSize=7,
            searchWindowSize=21
        )
        img = img_uint8.astype(np.float32) / 255.0
    
    # 4. Auto-contrast adjustment (improves visibility)
    if IMAGE_QUALITY_CONFIG["enable_auto_contrast"]:
        # Stretch the contrast to use full range
        img_min = img.min(axis=(0, 1), keepdims=True)
        img_max = img.max(axis=(0, 1), keepdims=True)
        img_range = img_max - img_min
        img_range[img_range == 0] = 1  # Avoid division by zero
        img = (img - img_min) / img_range
    
    # Convert back to uint8
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def resize_image_if_needed(img_bgr: np.ndarray) -> np.ndarray:
    """Resize image if max size is configured, preserving aspect ratio"""
    if IMAGE_QUALITY_CONFIG["resize_to_max"] <= 0:
        return img_bgr
    
    max_dim = IMAGE_QUALITY_CONFIG["resize_to_max"]
    h, w = img_bgr.shape[:2]
    
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    return img_bgr

def jpeg_b64(img_bgr: np.ndarray) -> str:
    """Convert image to base64 JPEG for transmission (high quality)"""
    try:
        # Apply image enhancement
        img_enhanced = enhance_image_quality(img_bgr)
        
        # Encode with high quality
        jpeg_quality = IMAGE_QUALITY_CONFIG["jpeg_quality"]
        ok, buf = cv2.imencode(".jpg", img_enhanced, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        
        if ok:
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")
        else:
            print(f"⚠️  JPEG encoding failed (ok={ok})")
    except Exception as e:
        print(f"⚠️  Image encoding error: {e}")
    return ""

def jpeg_b64_thumbnail(img_bgr: np.ndarray, thumb_width: int = 320) -> str:
    """Convert image to base64 JPEG thumbnail (smaller, faster loading)"""
    try:
        # Resize to thumbnail size
        h, w = img_bgr.shape[:2]
        if w > thumb_width:
            scale = thumb_width / w
            new_h = int(h * scale)
            img_thumb = cv2.resize(img_bgr, (thumb_width, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            img_thumb = img_bgr.copy()
        
        # Apply lighter enhancement for thumbnails
        img_enhanced = enhance_image_quality(img_thumb)
        
        # Encode with slightly lower quality for thumbnail (faster transmission)
        thumbnail_quality = max(85, IMAGE_QUALITY_CONFIG["jpeg_quality"] - 5)  # 5% reduction
        ok, buf = cv2.imencode(".jpg", img_enhanced, [cv2.IMWRITE_JPEG_QUALITY, thumbnail_quality])
        
        if ok:
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")
    except Exception as e:
        print(f"⚠️  Thumbnail encoding error: {e}")
    return ""

def jpeg_b64_hq(img_bgr: np.ndarray) -> str:
    """Convert image to base64 JPEG high-quality (for large display, uses maximum quality)"""
    try:
        # Apply image enhancement
        img_enhanced = enhance_image_quality(img_bgr)
        
        # Encode with MAXIMUM quality for large displays
        ok, buf = cv2.imencode(".jpg", img_enhanced, [cv2.IMWRITE_JPEG_QUALITY, 99])  # Maximum quality
        
        if ok:
            return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")
    except Exception as e:
        print(f"⚠️  HQ encoding error: {e}")
    return ""

def ensure_tracker(camera_id: str) -> Any:
    """Get or create tracker for camera (standard ByteTrack)"""
    if camera_id not in trackers:
        trackers[camera_id] = ByteTrack(
            track_activation_threshold=TRACK_ACTIVATION_THRESHOLD,
            lost_track_buffer=LOST_TRACK_BUFFER,
            minimum_matching_threshold=MINIMUM_MATCHING_THRESHOLD,
            frame_rate=FRAME_RATE,
            minimum_consecutive_frames=MINIMUM_CONSECUTIVE_FRAMES
        )
    return trackers[camera_id]

def ensure_enhanced_tracker(camera_id: str) -> Any:
    """Get or create enhanced hybrid tracker (DeepSORT + ByteTrack)"""
    if not ENHANCED_TRACKING_AVAILABLE:
        return ensure_tracker(camera_id)
    
    if camera_id not in enhanced_trackers:
        enhanced_trackers[camera_id] = EnhancedDetectionTracker(
            confidence_threshold=ENHANCED_TRACK_CONFIG["confidence_threshold"],
            nms_threshold=ENHANCED_TRACK_CONFIG["nms_threshold"],
            use_deepsort=ENHANCED_TRACK_CONFIG["use_deepsort"]
        )
        print(f"✅ Initialized enhanced tracker for {camera_id}")
    return enhanced_trackers[camera_id]

def draw_boxes_on_image(
    img_bgr: np.ndarray,
    detections: Any,
    tracker_ids: Optional[np.ndarray] = None,
    thickness: int = 2
) -> np.ndarray:
    """Draw detection boxes with optional tracker IDs"""
    img_copy = img_bgr.copy()
    
    if detections.xyxy is not None and len(detections.xyxy) > 0:
        for idx, (x1, y1, x2, y2) in enumerate(detections.xyxy.astype(int)):
            # Draw bounding box
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), thickness)
            
            # Draw tracker ID if available
            if tracker_ids is not None and idx < len(tracker_ids):
                track_id = int(tracker_ids[idx])
                cv2.putText(
                    img_copy,
                    f"ID: {track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )
            
            # Draw confidence
            if detections.confidence is not None and idx < len(detections.confidence):
                conf = float(detections.confidence[idx])
                cv2.putText(
                    img_copy,
                    f"Conf: {conf:.2f}",
                    (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 0),
                    1
                )
    
    return img_copy

# ============= Person Re-ID Helpers =============
def ensure_global_person_reidentifier() -> Optional[Any]:
    """Get or create GLOBAL person re-identifier (cross-camera)"""
    global global_person_reidentifier
    
    if not REID_CONFIG["enabled"]:
        return None
    
    if global_person_reidentifier is None:
        try:
            global_person_reidentifier = PersonReIdentifier(
                similarity_threshold=REID_CONFIG["similarity_threshold"]
            )
            print(f"✅ Initialized GLOBAL cross-camera person re-ID")
        except Exception as e:
            print(f"⚠️  Failed to initialize global person re-ID: {e}")
            return None
    
    return global_person_reidentifier

def ensure_global_person_storage() -> Optional[Any]:
    """Get or create GLOBAL person storage (cross-camera Redis)"""
    global global_person_storage
    
    if not REID_CONFIG["enabled"]:
        return None
    
    if global_person_storage is None and redis_client:
        try:
            global_person_storage = PersonRedisStorage(
                redis_client,
                namespace="saferoom:persons:global",  # Global namespace
                ttl_days=REID_CONFIG["ttl_days"]
            )
            print(f"✅ Initialized GLOBAL cross-camera person storage")
        except Exception as e:
            print(f"⚠️  Failed to initialize global person storage: {e}")
            return None
    
    return global_person_storage

def ensure_person_reidentifier(camera_id: str) -> Optional[Any]:
    """DEPRECATED: Get or create person re-identifier for camera
    Now uses global instance instead of per-camera"""
    return ensure_global_person_reidentifier()

def ensure_person_storage(camera_id: str) -> Optional[Any]:
    """DEPRECATED: Get or create person storage for camera
    Now uses global instance instead of per-camera"""
    return ensure_global_person_storage()

def process_person_detection(
    frame: np.ndarray,
    bbox: List[int],
    tracker_id: int,
    camera_id: str
) -> Optional[str]:
    """
    Process detection for person re-identification
    Returns person label if matched, or creates new person
    """
    if not REID_CONFIG["enabled"]:
        return None
    
    try:
        reidentifier = ensure_person_reidentifier(camera_id)
        storage = ensure_person_storage(camera_id)
        
        if not reidentifier or not storage:
            return None
        
        # Extract embedding
        embedding = reidentifier.extract_person_embedding(frame, tuple(bbox))
        if embedding is None:
            return None
        
        # Try to match with known persons
        person_id, confidence = reidentifier.match_person(
            embedding, camera_id, bbox
        )
        
        if person_id and confidence > REID_CONFIG["similarity_threshold"]:
            # Found matching person
            label = reidentifier.persons[person_id].label
            
            # Update person info
            reidentifier.update_person(
                person_id, embedding, frame, bbox, camera_id, confidence
            )
            
            # Update Redis storage
            storage.update_last_seen(person_id, time.time())
            storage.increment_visit_count(person_id)
            
            return label
        else:
            # New person
            person_id = reidentifier.register_person(
                embedding, frame, bbox, camera_id
            )
            
            # Store in Redis
            person_info = reidentifier.get_person_info(person_id)
            storage.save_person(person_info)
            
            return reidentifier.persons[person_id].label
    
    except Exception as e:
        print(f"⚠️  Person detection failed: {e}")
        return None

# ============= Violation Handler =============
async def on_violation(occupants_ids: List[int], frame_b64: str = ""):
    """Handle violation: log event, trigger webhook, broadcast alert"""
    event = {
        "type": "violation",
        "timestamp": datetime.utcnow().isoformat(),
        "occupants": occupants_ids,
        "count": len(occupants_ids),
        "room_id": ROOM_ID
    }
    
    # Log to Redis
    if redis_client:
        try:
            redis_client.lpush(f"room:{ROOM_ID}:events", json.dumps(event))
            # Keep only last 1000 events
            redis_client.ltrim(f"room:{ROOM_ID}:events", 0, 999)
        except Exception as e:
            print(f"⚠️  Failed to log event: {e}")
    
    # Trigger webhook
    if VIOLATION_ACTION_WEBHOOK:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    VIOLATION_ACTION_WEBHOOK,
                    json=event,
                    timeout=aiohttp.ClientTimeout(total=3)
                )
                print(f"✅ Violation webhook sent")
        except Exception as e:
            print(f"⚠️  Violation webhook failed: {e}")
    
    # Broadcast to all connected clients
    alert_payload = {
        "event": "violation",
        "occupants": occupants_ids,
        "count": len(occupants_ids),
        "message": f"⚠️ VIOLATION: {len(occupants_ids)} people in room!",
        "timestamp": event["timestamp"]
    }
    
    if frame_b64:
        alert_payload["frame_b64"] = frame_b64
    
    await manager.broadcast_json(alert_payload)
    print(f"🚨 VIOLATION: {len(occupants_ids)} occupants detected")

# ============= WebRTC Video Track =============

class CameraVideoTrack(VideoStreamTrack):
    """WebRTC video track that streams from camera"""
    def __init__(self, camera_id: str):
        super().__init__()
        self.camera_id = camera_id
        self.counter = 0

    async def recv(self):
        """Receive video frame from cache and send via WebRTC"""
        pts, time_base = await self.next_timestamp()
        
        # Get latest frame from cache
        if self.camera_id in camera_frames_cache:
            frame_bytes = camera_frames_cache[self.camera_id]
            if frame_bytes:
                # Decode frame
                nparr = np.frombuffer(frame_bytes, np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img_bgr is not None:
                    # Convert to RGB for WebRTC
                    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    
                    # Create video frame
                    frame = VideoFrame.from_ndarray(img_rgb, format="rgb24")
                    frame.pts = pts
                    frame.time_base = time_base
                    return frame
        
        # Return blank frame if no camera data
        blank = np.zeros((360, 640, 3), dtype=np.uint8)
        frame = VideoFrame.from_ndarray(blank, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

# ============= WebRTC Handlers =============

async def handle_webrtc_offer(offer_dict: dict, camera_id: str) -> dict:
    """Handle WebRTC offer and return answer"""
    if not WEBRTC_AVAILABLE:
        return {"error": "WebRTC not available"}
    
    try:
        pc = RTCPeerConnection()
        webrtc_connections[f"{camera_id}_{id(pc)}"] = pc
        
        # Add video track
        video_track = CameraVideoTrack(camera_id)
        pc.addTrack(video_track)
        
        # Set remote description
        offer = RTCSessionDescription(
            sdp=offer_dict.get("sdp", ""),
            type=offer_dict.get("type", "offer")
        )
        await pc.setRemoteDescription(offer)
        
        # Create and set answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return {
            "type": pc.localDescription.type,
            "sdp": pc.localDescription.sdp
        }
    except Exception as e:
        print(f"❌ WebRTC error: {e}")
        return {"error": str(e)}

# ============= API Endpoints =============

@app.post("/ingest")
async def ingest_frame(
    file: UploadFile = File(...),
    camera_id: str = Query("room1"),
    room_id: str = Query(ROOM_ID)
):
    """
    Ingest frame from camera: detect, track, check violations.
    Uses enhanced hybrid tracking (DeepSORT + ByteTrack) if available.
    Returns detection results and broadcasts to WebSocket clients.
    """
    try:
        data = await file.read()
        pil = Image.open(io.BytesIO(data)).convert("RGB")
        img = np.array(pil)  # RGB
        img_bgr = img[:, :, ::-1].copy()  # BGR for OpenCV
        
        # Default empty results
        tracker_ids = []
        occupancy = 0
        rects = []
        frame_b64_annotated = ""
        frame_b64_hq_annotated = ""
        frame_b64_thumb_annotated = ""
        tracking_method = "none"
        person_labels = {}  # Initialize person_labels outside YOLO block
        
        # Run YOLO if model is loaded
        if yolo_model is not None:
            try:
                # Resize for faster YOLO inference (640x640 is YOLO default, but we can go smaller)
                h, w = img.shape[:2]
                if max(h, w) > 320:
                    # Resize to max 320px for faster processing
                    scale = 320 / max(h, w)
                    new_w, new_h = int(w * scale), int(h * scale)
                    img_yolo = cv2.resize(img, (new_w, new_h))
                else:
                    img_yolo = img
                
                results = yolo_model.predict(source=img_yolo, verbose=False, classes=[0], imgsz=320)  # person only, 320x320
                r = results[0]
                
                # Scale boxes back to original size
                if r.boxes is not None and len(r.boxes) > 0 and img_yolo is not img:
                    scale_x = w / img_yolo.shape[1]
                    scale_y = h / img_yolo.shape[0]
                    xyxy = r.boxes.xyxy.cpu().numpy()
                    xyxy[:, [0, 2]] *= scale_x
                    xyxy[:, [1, 3]] *= scale_y
                elif r.boxes is not None and len(r.boxes) > 0:
                    xyxy = r.boxes.xyxy.cpu().numpy()
                else:
                    xyxy = None
                
                if xyxy is not None and len(xyxy) > 0:
                    conf = r.boxes.conf.cpu().numpy()
                    cls = r.boxes.cls.cpu().numpy().astype(int)
                else:
                    xyxy = np.empty((0, 4), dtype=float)
                    conf = np.empty((0,), dtype=float)
                    cls = np.empty((0,), dtype=int)
                
                # Use enhanced tracking if available, otherwise use standard ByteTrack
                if USE_ENHANCED_TRACKING and ENHANCED_TRACKING_AVAILABLE:
                    try:
                        enhanced_tracker = ensure_enhanced_tracker(camera_id)
                        tracked_ids, tracked_xyxy = enhanced_tracker.process_detections(
                            xyxy, conf, img_bgr
                        )
                        tracker_ids = tracked_ids.tolist() if len(tracked_ids) > 0 else []
                        occupancy = len(tracker_ids)
                        rects = tracked_xyxy.astype(int).tolist() if len(tracked_xyxy) > 0 else []
                        tracking_method = "enhanced_hybrid"
                    except Exception as e:
                        # Fallback to standard ByteTrack
                        print(f"⚠️  Enhanced tracking failed: {e}. Falling back to ByteTrack.")
                        dets = Detections(xyxy=xyxy, confidence=conf, class_id=cls)
                        tracker = ensure_tracker(camera_id)
                        tracked = tracker.update_with_detections(dets)
                        tracker_ids = [] if tracked.tracker_id is None else tracked.tracker_id.tolist()
                        occupancy = len(tracker_ids)
                        rects = xyxy.astype(int).tolist() if len(xyxy) > 0 else []
                        tracking_method = "bytetrack_fallback"
                else:
                    # Standard ByteTrack tracking
                    dets = Detections(xyxy=xyxy, confidence=conf, class_id=cls)
                    tracker = ensure_tracker(camera_id)
                    tracked = tracker.update_with_detections(dets)
                    tracker_ids = [] if tracked.tracker_id is None else tracked.tracker_id.tolist()
                    occupancy = len(tracker_ids)
                    rects = xyxy.astype(int).tolist() if len(xyxy) > 0 else []
                    tracking_method = "bytetrack"
                
                # Draw boxes on frame for preview (using standard method)
                if len(xyxy) > 0:
                    dets_display = Detections(
                        xyxy=xyxy, 
                        confidence=conf, 
                        class_id=cls,
                        tracker_id=np.array(tracker_ids[:len(xyxy)]) if tracker_ids else None
                    )
                    img_annotated = draw_boxes_on_image(img_bgr, dets_display, 
                                                       tracker_ids=np.array(tracker_ids[:len(xyxy)]) if tracker_ids else None)
                else:
                    img_annotated = img_bgr.copy()
                
                # Process person re-ID and get labels for each tracked person
                if REID_CONFIG["enabled"] and len(tracker_ids) > 0 and len(rects) > 0:
                    for idx, (track_id, rect) in enumerate(zip(tracker_ids, rects)):
                        try:
                            bbox = [int(x) for x in rect]  # [x1, y1, x2, y2]
                            label = process_person_detection(
                                img_bgr, bbox, track_id, camera_id
                            )
                            if label:
                                person_labels[int(track_id)] = label
                        except Exception as e:
                            print(f"⚠️  Person labeling failed for track {track_id}: {e}")
                
                # Generate different quality versions for display
                frame_b64_annotated = jpeg_b64(img_annotated)  # Standard quality
                frame_b64_hq_annotated = jpeg_b64_hq(img_annotated)  # High quality for large display
                frame_b64_thumb_annotated = jpeg_b64_thumbnail(img_annotated)  # Thumbnail for grid
                
                # Cache frame for WebRTC streaming (raw JPEG bytes)
                ok, frame_jpeg = cv2.imencode(".jpg", img_annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
                if ok:
                    camera_frames_cache[camera_id] = frame_jpeg.tobytes()
                
            except Exception as e:
                print(f"⚠️  YOLO inference error: {e}")
        
        # Update room state
        if redis_client:
            redis_client.hset(f"room:{ROOM_ID}:state", mapping={
                "occupancy": str(occupancy),
                "last_update": str(time.time()),
                "camera_id": camera_id,
                "tracking_method": tracking_method,
                "last_tracker_ids": ",".join(map(str, tracker_ids))
            })
        
        # Prepare broadcast payload with person labels and multiple quality versions
        payload = {
            "event": "frame",
            "camera_id": camera_id,
            "room_id": room_id,
            "occupancy": occupancy,
            "objects": tracker_ids,
            "person_labels": person_labels,  # NEW: Person labels mapped by tracker_id
            "rects": rects,
            "ts": time.time(),
            "tracking_method": tracking_method,
            "reid_enabled": REID_CONFIG["enabled"],
            "frame_b64": frame_b64_annotated,  # Standard quality
            "frame_b64_hq": frame_b64_hq_annotated,  # High quality for main display
            "frame_b64_thumbnail": frame_b64_thumb_annotated  # Thumbnail for grid preview
        }
        
        await manager.broadcast_json(payload)
        
        # Check violation
        if occupancy > MAX_OCCUPANCY:
            await on_violation(tracker_ids, frame_b64_annotated)
        
        return {
            "ok": True,
            "occupancy": occupancy,
            "objects": tracker_ids,
            "person_labels": person_labels,  # NEW
            "count_boxes": len(rects),
            "tracking_method": tracking_method,
            "reid_enabled": REID_CONFIG["enabled"],
            "status": "violation" if occupancy > MAX_OCCUPANCY else "ok"
        }
    
    except Exception as e:
        print(f"❌ Ingest error: {e}")
        return {"ok": False, "error": str(e)}, 400

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await manager.connect(ws)
    try:
        # Send initial state
        if redis_client:
            state = redis_client.hgetall(f"room:{ROOM_ID}:state")
            await ws.send_json({
                "event": "init",
                "room_id": ROOM_ID,
                "state": state,
                "config": {
                    "max_occupancy": MAX_OCCUPANCY,
                    "violation_threshold": VIOLATION_THRESHOLD
                }
            })
        
        # Keep connection alive and receive messages
        while True:
            data = await ws.receive_text()
            # Echo any received messages (optional for keep-alive)
            await ws.send_json({"event": "echo", "received": data})
    
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception as e:
        print(f"⚠️  WebSocket error: {e}")
        await manager.disconnect(ws)

@app.get("/status")
async def get_status():
    """Get current room status"""
    if not redis_client:
        return {"error": "Redis not connected"}
    
    try:
        state = redis_client.hgetall(f"room:{ROOM_ID}:state")
        events = redis_client.lrange(f"room:{ROOM_ID}:events", 0, 9)
        
        return {
            "room_id": ROOM_ID,
            "state": state,
            "recent_events": [json.loads(e) for e in events if e],
            "config": {
                "max_occupancy": MAX_OCCUPANCY,
                "violation_threshold": VIOLATION_THRESHOLD,
                "yolo_model": YOLO_MODEL_PATH
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/clear_violations")
async def clear_violations():
    """Clear violation log"""
    if not redis_client:
        return {"error": "Redis not connected"}
    
    try:
        redis_client.delete(f"room:{ROOM_ID}:events")
        return {"ok": True, "message": "Violations cleared"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "redis": "connected" if redis_client else "disconnected",
        "yolo": "loaded" if yolo_model else "not loaded",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/config")
async def get_config():
    """Get system configuration and tracking info"""
    return {
        "tracking": {
            "method": "enhanced_hybrid" if (USE_ENHANCED_TRACKING and ENHANCED_TRACKING_AVAILABLE) else "standard_bytetrack",
            "enhanced_available": ENHANCED_TRACKING_AVAILABLE,
            "enhanced_enabled": USE_ENHANCED_TRACKING and ENHANCED_TRACKING_AVAILABLE,
            "deepsort_available": ENHANCED_TRACKING_AVAILABLE,
            "bytetrack_available": BYTETRACK_AVAILABLE,
            "config": {
                "confidence_threshold": ENHANCED_TRACK_CONFIG["confidence_threshold"],
                "nms_threshold": ENHANCED_TRACK_CONFIG["nms_threshold"],
                "max_age": ENHANCED_TRACK_CONFIG["max_age"],
                "n_init": ENHANCED_TRACK_CONFIG["n_init"]
            }
        },
        "person_reid": {
            "enabled": REID_CONFIG["enabled"],
            "available": REID_AVAILABLE,
            "similarity_threshold": REID_CONFIG["similarity_threshold"],
            "cloud_storage": REID_CONFIG["cloud_storage"],
            "ttl_days": REID_CONFIG["ttl_days"],
            "instance_type": "global_cross_camera",
            "total_persons": len(ensure_global_person_reidentifier().persons) if ensure_global_person_reidentifier() else 0,
            "per_camera_trackers": len(enhanced_trackers)
        },
        "detection": {
            "model": YOLO_MODEL_PATH,
            "confidence_threshold": TRACK_ACTIVATION_THRESHOLD,
            "yolo_loaded": yolo_model is not None
        },
        "occupancy": {
            "max_allowed": MAX_OCCUPANCY,
            "violation_threshold": VIOLATION_THRESHOLD
        },
        "active_trackers": {
            "standard": len(trackers),
            "enhanced": len(enhanced_trackers)
        },
        "camera_quality": {
            "jpeg_quality": IMAGE_QUALITY_CONFIG["jpeg_quality"],
            "enable_clahe": IMAGE_QUALITY_CONFIG["enable_clahe"],
            "clahe_clip_limit": IMAGE_QUALITY_CONFIG["clahe_clip_limit"],
            "enable_sharpening": IMAGE_QUALITY_CONFIG["enable_sharpening"],
            "sharpening_strength": IMAGE_QUALITY_CONFIG["sharpening_strength"],
            "enable_auto_contrast": IMAGE_QUALITY_CONFIG["enable_auto_contrast"],
            "enable_denoise": IMAGE_QUALITY_CONFIG["enable_denoise"],
            "denoise_strength": IMAGE_QUALITY_CONFIG["denoise_strength"],
            "max_image_size": IMAGE_QUALITY_CONFIG["resize_to_max"]
        },
        "streaming": {
            "enabled": STREAMING_CONFIG["enabled"],
            "codec": STREAMING_CONFIG["codec"],
            "resolution": STREAMING_CONFIG["resolution"],
            "resolution_2k": f"{STREAMING_CONFIG['resolution'][0]}x{STREAMING_CONFIG['resolution'][1]}",
            "fps": STREAMING_CONFIG["fps"],
            "bitrate_kbps": STREAMING_CONFIG["bitrate_kbps"],
            "bitrate_mbps": STREAMING_CONFIG["bitrate_kbps"] / 1024,
            "quality": STREAMING_CONFIG["quality"]
        },
        "system": {
            "room_id": ROOM_ID,
            "redis_connected": redis_client is not None
        }
    }

# ============= WebRTC API Endpoints =============

@app.post("/webrtc/offer")
async def webrtc_offer(camera_id: str = Query("room1"), token: str = Query(None), offer: dict = None):
    """
    Handle WebRTC offer for low-latency mobile streaming
    
    Example Usage (without token):
    POST /webrtc/offer?camera_id=room1
    {
        "type": "offer",
        "sdp": "v=0\r\no=- ..."
    }
    
    Example Usage (with token):
    POST /webrtc/offer?camera_id=room1&token=<your-webrtc-token>
    """
    if not WEBRTC_AVAILABLE:
        return {
            "error": "WebRTC not available",
            "available": False,
            "info": "Install aiortc: pip install aiortc"
        }
    
    # Optional token validation (if token provided, validate it)
    if token:
        if not validate_webrtc_token(token, camera_id):
            return {
                "error": "Invalid or expired token",
                "code": "INVALID_TOKEN",
                "camera_id": camera_id
            }
    
    answer = await handle_webrtc_offer(offer, camera_id)
    return answer

@app.get("/webrtc/cameras")
async def webrtc_cameras():
    """Get available cameras for WebRTC streaming"""
    return {
        "webrtc_available": WEBRTC_AVAILABLE,
        "cameras": [
            {"id": "room1", "name": "Room 1", "url": f"http://{os.environ.get('HOST', 'localhost')}:8000/webrtc/offer?camera_id=room1"},
            {"id": "room2", "name": "Room 2", "url": f"http://{os.environ.get('HOST', 'localhost')}:8000/webrtc/offer?camera_id=room2"},
            {"id": "room3", "name": "Room 3", "url": f"http://{os.environ.get('HOST', 'localhost')}:8000/webrtc/offer?camera_id=room3"},
            {"id": "room4", "name": "Room 4", "url": f"http://{os.environ.get('HOST', 'localhost')}:8000/webrtc/offer?camera_id=room4"},
        ],
        "latency": "50-100ms (WebRTC P2P)",
        "instructions": "Use WebRTC client library to connect",
        "authentication": "Optional token support available"
    }

@app.post("/webrtc/token/generate")
async def generate_token(camera_ids: List[str] = None, expires_hours: int = None):
    """
    Generate a new WebRTC connection token
    
    Example Usage:
    POST /webrtc/token/generate
    {
        "camera_ids": ["room1", "room2"],
        "expires_hours": 24
    }
    """
    token = generate_webrtc_token(camera_ids, expires_hours)
    token_data = WEBRTC_TOKENS[token]
    
    return {
        "token": token,
        "expires_at": token_data["expires_at"].isoformat(),
        "camera_ids": token_data["camera_ids"],
        "expires_in_hours": expires_hours or TOKEN_EXPIRY_HOURS,
        "usage": {
            "example": f"POST /webrtc/offer?camera_id=room1&token={token}",
            "webrtc_html": f"/webrtc.html?token={token}"
        }
    }

@app.get("/webrtc/token/validate")
async def validate_token(token: str = Query(...)):
    """
    Validate a WebRTC token
    
    Example Usage:
    GET /webrtc/token/validate?token=<your-webrtc-token>
    """
    if token not in WEBRTC_TOKENS:
        return {"valid": False, "error": "Token not found"}
    
    token_data = WEBRTC_TOKENS[token]
    
    if datetime.now() > token_data["expires_at"]:
        del WEBRTC_TOKENS[token]
        return {"valid": False, "error": "Token expired"}
    
    return {
        "valid": True,
        "expires_at": token_data["expires_at"].isoformat(),
        "camera_ids": token_data["camera_ids"],
        "used_count": token_data["used_count"],
        "created_at": token_data["created_at"].isoformat()
    }

@app.delete("/webrtc/token/revoke")
async def revoke_token(token: str = Query(...)):
    """
    Revoke a WebRTC token
    
    Example Usage:
    DELETE /webrtc/token/revoke?token=<your-webrtc-token>
    """
    if revoke_webrtc_token(token):
        return {"success": True, "message": "Token revoked"}
    else:
        return {"success": False, "error": "Token not found"}

@app.get("/webrtc/tokens")
async def list_tokens():
    """
    List all active WebRTC tokens (admin only)
    """
    tokens_list = []
    for token, data in WEBRTC_TOKENS.items():
        tokens_list.append({
            "token": token,
            "expires_at": data["expires_at"].isoformat(),
            "camera_ids": data["camera_ids"],
            "created_at": data["created_at"].isoformat(),
            "used_count": data["used_count"]
        })
    
    return {
        "total_tokens": len(tokens_list),
        "tokens": tokens_list
    }


# ============= Person Re-ID APIs =============

@app.get("/persons")
async def list_persons(camera_id: Optional[str] = None):
    """List all known persons (optionally filtered by camera)"""
    if not REID_CONFIG["enabled"]:
        return {"error": "Person re-ID not enabled"}, 400
    
    try:
        reidentifier = ensure_global_person_reidentifier()
        if not reidentifier:
            return {"error": "Re-ID not initialized"}, 500
        
        persons = reidentifier.list_persons()
        
        # Filter by camera if specified
        if camera_id:
            persons = [p for p in persons if camera_id in p.get("cameras", [])]
        
        return {
            "camera_id": camera_id,
            "total": len(persons),
            "persons": persons
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/persons/stats")
async def person_stats(camera_id: Optional[str] = None):
    """Get re-ID statistics (global across all cameras)"""
    if not REID_CONFIG["enabled"]:
        return {"error": "Person re-ID not enabled"}, 400
    
    try:
        reidentifier = ensure_global_person_reidentifier()
        if not reidentifier:
            return {"error": "Re-ID not initialized"}, 500
        
        stats = reidentifier.get_stats()
        
        # If camera filter requested, show breakdown per camera
        if camera_id:
            persons = [p for p in reidentifier.list_persons() 
                      if camera_id in p.get("cameras", [])]
            camera_stats = {
                "total_persons": len(persons),
                "total_embeddings": sum(p.get("num_embeddings", 0) for p in persons),
                "avg_visits": sum(p.get("visit_count", 0) for p in persons) / len(persons) if persons else 0,
                "cameras": [camera_id]
            }
            return {"cameras": {camera_id: camera_stats}}
        else:
            # Return global stats grouped by camera
            persons_by_camera = {}
            for person in reidentifier.list_persons():
                for cam in person.get("cameras", []):
                    if cam not in persons_by_camera:
                        persons_by_camera[cam] = []
                    persons_by_camera[cam].append(person)
            
            camera_stats = {}
            for cam, persons_list in persons_by_camera.items():
                camera_stats[cam] = {
                    "total_persons": len(persons_list),
                    "total_embeddings": sum(p.get("num_embeddings", 0) for p in persons_list),
                    "avg_visits": sum(p.get("visit_count", 0) for p in persons_list) / len(persons_list) if persons_list else 0,
                    "cameras": [cam]
                }
            
            return {"cameras": camera_stats if camera_stats else {}}
    
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/persons/{person_id}")
async def get_person(person_id: str, camera_id: Optional[str] = None):
    """Get details for specific person"""
    if not REID_CONFIG["enabled"]:
        return {"error": "Person re-ID not enabled"}, 400
    
    try:
        reidentifier = ensure_global_person_reidentifier()
        if not reidentifier:
            return {"error": "Re-ID not initialized"}, 500
        
        # Get person from global gallery
        if person_id in reidentifier.persons:
            person_info = reidentifier.get_person_info(person_id)
            
            # Filter by camera if specified
            if camera_id and camera_id not in person_info.get("cameras", []):
                return {"error": "Person not found in specified camera"}, 404
            
            return person_info
        
        return {"error": "Person not found"}, 404
    
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/persons/merge")
async def merge_persons(person_id1: str, person_id2: str, camera_id: Optional[str] = None):
    """Merge two persons (combine their embeddings and visits) - GLOBAL"""
    if not REID_CONFIG["enabled"]:
        return {"error": "Person re-ID not enabled"}, 400
    
    try:
        reidentifier = ensure_global_person_reidentifier()
        storage = ensure_global_person_storage()
        
        if not reidentifier:
            return {"error": "Re-ID not initialized"}, 500
        
        if reidentifier.merge_persons(person_id1, person_id2):
            # Update storage
            if storage:
                person_info = reidentifier.get_person_info(person_id1)
                storage.save_person(person_info)
                storage.delete_person(person_id2)
            
            return {"ok": True, "message": f"Merged {person_id2} into {person_id1}"}
        else:
            return {"error": "Failed to merge persons"}, 400
    
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/persons/reset")
async def reset_persons(camera_id: Optional[str] = None):
    """Reset persons gallery (global or for specific camera)"""
    if not REID_CONFIG["enabled"]:
        return {"error": "Person re-ID not enabled"}, 400
    
    try:
        reidentifier = ensure_global_person_reidentifier()
        storage = ensure_global_person_storage()
        
        if not reidentifier:
            return {"error": "Re-ID not initialized"}, 500
        
        if camera_id:
            # Reset only persons from specific camera
            persons_to_remove = [
                p["person_id"] for p in reidentifier.list_persons()
                if camera_id in p.get("cameras", [])
            ]
            for person_id in persons_to_remove:
                if person_id in reidentifier.persons:
                    reidentifier.persons.pop(person_id, None)
                if storage:
                    storage.delete_person(person_id)
            cameras_reset = [camera_id]
        else:
            # Reset all
            reidentifier.reset()
            if storage:
                storage.reset_all()
            cameras_reset = ["ALL"]
        
        return {"ok": True, "message": f"Reset persons for {len(cameras_reset)} cameras"}
    
    except Exception as e:
        return {"error": str(e)}, 500
        
        return {"ok": True, "message": f"Reset persons for {len(cameras_reset)} cameras"}
    
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/")
async def root():
    """Serve dashboard"""
    dashboard_paths = [
        "/home/husain/alrazy/brinks/dashboard/app.html",
        "/home/husain/alrazy/brinks/dashboard/dist/index.html",
        "/home/husain/alrazy/brinks/dashboard/index.html"
    ]
    
    for path in dashboard_paths:
        if os.path.exists(path):
            return FileResponse(path)
    
    return HTMLResponse("""
    <h2>SafeRoom Detection API</h2>
    <p>Backend is running successfully!</p>
    <ul>
        <li><a href="/docs">API Documentation (Swagger)</a></li>
        <li><a href="/status">Current Status</a></li>
        <li><a href="/health">Health Check</a></li>
    </ul>
    """)

@app.get("/dashboard/app.html")
async def dashboard_app():
    """Serve app dashboard"""
    app_path = "/home/husain/alrazy/brinks/dashboard/app.html"
    if os.path.exists(app_path):
        return FileResponse(app_path, media_type="text/html")
    return {"error": "Dashboard not found"}, 404

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )