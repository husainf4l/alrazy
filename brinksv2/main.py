from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import threading
import time

from routes.dashboard import router as pages_router
from routes.cameras import router as cameras_router
from routes.detections import router as detections_router
from routes.visualization import router as visualization_router
from routes.rooms import router as rooms_router
from routes.sms_alerts import router as sms_alerts_router
from routes import visualization
from database import engine, Base, SessionLocal
from services.people_detection import PeopleDetector, RTSPPeopleCounter
from services.cross_camera_tracking import GlobalPersonTracker
from gpu_optimization import enable_gpu_optimization, print_gpu_status

# Import ALL models before creating tables (order matters for foreign keys)
from models.room import Room
from models.camera import Camera, DetectionCount

# Global detection service instances
people_detector = None
people_counter = None
global_person_tracker = None


def start_detection_service():
    """Initialize and start people detection service with GPU acceleration"""
    global people_detector, people_counter, global_person_tracker
    
    print("🚀 Initializing people detection service...")
    
    # Enable GPU optimizations
    print("🎮 Enabling GPU acceleration...")
    enable_gpu_optimization()
    print_gpu_status()
    
    # Initialize cross-camera tracker first
    global_person_tracker = GlobalPersonTracker(
        similarity_threshold=0.4,  # Lower threshold for more aggressive matching across cameras
        time_window=5  # 5 seconds for matching across cameras (increased for person movement)
    )
    
    # Initialize detector with YOLO11m (ONNX) + YuNet Face + ByteTrack + DeepSORT + Global Tracker
    # GPU Acceleration enabled for RTX 4070
    people_detector = PeopleDetector(
        model_size="yolo11m.onnx", 
        conf_threshold=0.5,
        bytetrack_threshold=0.6,  # Threshold for ByteTrack confidence
        global_tracker=global_person_tracker,  # Pass global tracker
        use_gpu=True  # Enable GPU acceleration
    )
    
    # Initialize counter with 30 FPS processing (ByteTrack requirement)
    people_counter = RTSPPeopleCounter(people_detector, process_fps=30)
    
    # Load cameras and rooms from database
    db = SessionLocal()
    cameras_list = db.query(Camera).all()
    rooms_list = db.query(Room).all()
    
    # Configure overlap zones from room configuration
    for room in rooms_list:
        if room.overlap_config:
            for overlap in room.overlap_config.get('overlaps', []):
                global_person_tracker.configure_overlap_zone(
                    room.id,
                    overlap['camera_id_1'],
                    overlap['camera_id_2'],
                    overlap['polygon']
                )
    
    # Set room_id for cameras to enable cross-camera tracking
    for camera in cameras_list:
        if camera.room_id:
            people_detector.set_camera_room(camera.id, camera.room_id)
    
    db.close()
    
    print(f"📹 Starting detection on {len(cameras_list)} cameras in {len(rooms_list)} rooms...")
    for camera in cameras_list:
        people_counter.start_stream(camera.id, camera.rtsp_main)
        time.sleep(1)  # Stagger stream starts
    
    print("✅ People detection service running")


def save_detection_counts():
    """Background task to save detection counts to database every 5 minutes"""
    global people_counter
    
    while True:
        time.sleep(300)  # 5 minutes
        
        if people_counter is None:
            continue
        
        try:
            stats = people_counter.get_stats()
            db = SessionLocal()
            
            for stat in stats:
                detection = DetectionCount(
                    camera_id=stat['camera_id'],
                    people_count=stat['current_count'],
                    average_count=stat['average_count']
                )
                db.add(detection)
            
            db.commit()
            db.close()
            print(f"💾 Saved detection counts for {len(stats)} cameras")
        except Exception as e:
            print(f"❌ Error saving detection counts: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup - Clear and refresh metadata to ensure latest schema
    Base.metadata.clear()
    Base.metadata.reflect(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Start detection service in background thread
    detection_thread = threading.Thread(target=start_detection_service, daemon=True)
    detection_thread.start()
    
    # Wait a bit for detection service to initialize
    time.sleep(2)
    
    # Inject detection service into visualization router
    visualization.set_detection_service(people_detector, people_counter)
    
    # Start periodic saving thread
    save_thread = threading.Thread(target=save_detection_counts, daemon=True)
    save_thread.start()
    
    yield
    
    # Shutdown
    if people_counter:
        db = SessionLocal()
        cameras_list = db.query(Camera).all()
        db.close()
        
        for camera in cameras_list:
            people_counter.stop_stream(camera.id)


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Brinks V2 - Security Camera System with AI Detection",
    description="Modern security camera management and monitoring system with WebRTC and YOLO11m people detection",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pages_router)
app.include_router(cameras_router)
app.include_router(detections_router)
app.include_router(visualization_router)
app.include_router(rooms_router)
app.include_router(sms_alerts_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {
        "message": "Brinks V2 Security Camera System with YOLO11m AI Detection",
        "version": "2.0.0",
        "status": "online",
        "detection_service": "active" if people_counter else "initializing"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Brinks V2",
        "detection_active": people_counter is not None
    }
