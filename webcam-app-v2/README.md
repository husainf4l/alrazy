# Webcam Face Detection & Recognition System v2.0

**Version 2.0 - Enhanced Pipeline with YOLO11 + ArcFace Matching**

## Overview

Complete face detection and recognition system with real-time person tracking and identification using state-of-the-art computer vision models.

## Features

### Core Capabilities
- 🎯 **YOLO11 Person Detection** - 2 FPS rate-limited high-accuracy detection
- 👤 **RetinaFace Detection** - Robust face detection with facial landmarks
- 🧠 **ArcFace Embeddings** - 512-dimensional face representation vectors
- 🔍 **Intelligent Face Matching** - Cosine similarity-based person identification (60% threshold)
- 📊 **PostgreSQL Database** - Persistent face storage with detection tracking
- 🎥 **Live Webcam Interface** - Real-time streaming with manual capture
- 🔐 **JWT Authentication** - Secure user sessions

### Detection Pipeline
```
Webcam Frame → YOLO Person Detection → Face Detection (RetinaFace) 
→ ArcFace Embedding → Face Matching → Database Update
```

### Face Matching System
- **Automatic Person Identification**: Matches new faces against database
- **Detection Count Tracking**: Increments count for identified persons (#1, #2, #3...)
- **Similarity Threshold**: 60% (0.6) cosine similarity
- **Backup Embeddings**: Historical embedding storage for analysis

## Technology Stack

- **Backend**: FastAPI 0.121.1
- **ML Models**: 
  - YOLO11m-pose (51MB)
  - RetinaFace (DeepFace backend)
  - ArcFace (512-dim embeddings)
- **Database**: PostgreSQL 17.6 + SQLAlchemy 2.0.44
- **Computer Vision**: OpenCV 4.10, Ultralytics 8.3, DeepFace 0.0.95
- **Authentication**: JWT (python-jose)
- **Configuration**: python-dotenv

## Project Structure

```
webcam-app-v2/
├── app/
│   ├── services/
│   │   ├── yolo_person_detector.py    # YOLO11 person detection
│   │   ├── face_recognition.py        # RetinaFace + ArcFace
│   │   ├── face_matching.py           # Cosine similarity matching
│   │   ├── webcam_processor.py        # Integrated pipeline
│   │   └── auth.py                    # JWT authentication
│   ├── models/
│   │   ├── database.py                # SQLAlchemy models
│   │   └── schemas.py                 # Pydantic schemas
│   ├── templates/
│   │   └── webcam.html                # Webcam UI with capture button
│   └── static/faces/                  # Saved face images
├── main.py                            # FastAPI application
├── .env                               # Configuration (DB, YOLO, Face settings)
├── pyproject.toml                     # Dependencies
└── yolo-models/
    └── yolo11m-pose.pt               # YOLO model weights

Documentation:
├── FACE_MATCHING_README.md           # Complete matching system docs
├── FACE_MATCHING_IMPLEMENTATION.md   # Technical implementation
├── FACE_MATCHING_VERIFICATION.md     # Test results & verification
├── INTEGRATED_PIPELINE_README.md     # Full pipeline documentation
├── WEBCAM_CAPTURE_GUIDE.md           # UI usage guide
├── DATABASE_STORAGE_README.md        # Database integration
└── SYSTEM_CHECKLIST.md               # System verification
```

## Quick Start

### 1. Setup Environment
```bash
cd webcam-app-v2
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure Database
Create `.env` file:
```env
DATABASE_URL=postgresql://user:password@host:port/database
YOLO_FPS_LIMIT=2
YOLO_CONFIDENCE=0.75
FACE_DETECTOR_BACKEND=retinaface
FACE_CONFIDENCE_THRESHOLD=0.5
SECRET_KEY=your-secret-key
```

### 3. Run Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access: http://localhost:8000

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and receive JWT token

### Webcam
- `GET /webcam` - Webcam interface
- `POST /process-frame` - Process captured frame through pipeline

### Faces
- `GET /faces` - View all detected faces
- `GET /faces/{face_id}` - View specific face details

## Detection Results

The system provides real-time feedback:
- **Green Badge**: New person detected and saved
- **Yellow Badge**: Existing person identified (shows similarity %)
- **Detection Count**: Tracks how many times person detected (#1, #2, #3...)
- **Confidence Scores**: YOLO confidence + Face detection confidence

## Configuration Options

### YOLO Settings
- `YOLO_FPS_LIMIT`: Processing rate (default: 2)
- `YOLO_CONFIDENCE`: Detection threshold (default: 0.75)

### Face Recognition
- `FACE_DETECTOR_BACKEND`: Detection model (default: retinaface)
- `FACE_CONFIDENCE_THRESHOLD`: Face detection threshold (default: 0.5)
- `FACE_MATCHING_THRESHOLD`: Similarity threshold (default: 0.6)

## Database Schema

### Faces Table
```sql
- id (UUID, primary key)
- person_name (String, nullable)
- image_path (String, face image location)
- embedding (JSON, 512-dim ArcFace vector)
- backup_embeddings (JSON, historical embeddings)
- detection_count (Integer, increments on match)
- created_at (DateTime)
- last_seen (DateTime, updates on match)
- updated_at (DateTime)
- user_id (Integer, FK to users)
```

## Testing

```bash
# Test face detection
python test_face_detection.py

# Test integrated pipeline
python test_integrated_pipeline.py
```

## v2.0 Enhancements

### New in Version 2.0
- ✨ Intelligent face matching system with cosine similarity
- ✨ Automatic person identification across multiple captures
- ✨ Detection count tracking for identified persons
- ✨ Backup embeddings for historical analysis
- ✨ Enhanced UI with match status indicators
- ✨ Comprehensive documentation suite
- ✨ Environment-based configuration (.env)
- ✨ Improved timestamp tracking (created/last_seen/updated)

### Performance Metrics
- **YOLO Detection**: 0.942 confidence (94.2%)
- **Face Detection**: 1.0 confidence with 5 landmarks
- **Face Matching**: 73.51% similarity for same person at different angles
- **Processing Speed**: ~2 FPS (configurable)

## Future Roadmap

- [ ] Real-time continuous webcam streaming
- [ ] Face clustering and grouping
- [ ] Advanced search and filtering
- [ ] Export face database
- [ ] Multi-camera support
- [ ] Performance analytics dashboard

## License

MIT License

## Version History

- **v2.0.0** (Nov 11, 2025) - Face matching system, detection tracking, enhanced UI
- **v1.0.0** - Initial YOLO + Face detection pipeline

---

**Built with ❤️ using FastAPI, YOLO11, RetinaFace & ArcFace**
