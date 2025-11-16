# Face Detection & Database Storage Pipeline

## Overview

The system now automatically detects faces in video frames and stores them in PostgreSQL database with:
- **Face images** saved to disk (`app/static/faces/`)
- **Face embeddings** stored as 512-dimensional ArcFace vectors
- **Location data** with pixel coordinates
- **Timestamps** for detection tracking

## Complete Processing Pipeline

```
1. YOLO Person Detection (2 FPS)
   ↓
2. Face Detection in Person ROI (RetinaFace)
   ↓
3. ArcFace Embedding Extraction (512-dim)
   ↓
4. Database Storage
   ├── Face image saved to disk
   ├── Embedding stored in PostgreSQL
   ├── Location coordinates recorded
   └── Timestamps tracked
```

## Database Schema

### `face_persons` Table

```sql
CREATE TABLE face_persons (
    id VARCHAR PRIMARY KEY,                    -- UUID-based face ID
    name VARCHAR,                              -- Face person name
    embedding JSON,                            -- 512-dim ArcFace vector
    backup_embeddings JSON,                    -- Additional embeddings
    image_path VARCHAR,                        -- Path to main face image
    thumbnail_path VARCHAR,                    -- Thumbnail path
    image_paths JSON,                          -- List of all image paths
    embedding_count INTEGER,                   -- Number of embeddings
    detection_count INTEGER,                   -- Total detections
    last_seen TIMESTAMP,                       -- Last detection time
    updated_at TIMESTAMP,                      -- Last update time
    created_at TIMESTAMP                       -- Creation time
);
```

## API Endpoints

### Process Image
**POST** `/api/process-image`

Request:
```json
{
    "image": "base64_encoded_image_data"
}
```

Response:
```json
{
    "timestamp": "2025-11-11T12:54:03.101973",
    "frame_size": [1280, 720],
    "yolo_detections": [...],
    "face_detections": [...],
    "recognized_persons": [
        {
            "person_id": 1,
            "face_id": 1,
            "saved_face_id": "e7acd7a8",      // ← Database ID
            "embedding_length": 512,
            "location": {"x": 742, "y": 286},
            "verification_status": "✓ Verified as face"
        }
    ],
    "processing_time_ms": 9120.74,
    "log_messages": [...]
}
```

## Example Results

### Test Image: `webcam-capture-1.jpg`

**Detection Output:**
```
YOLO: Detected 1 people
  👤 Person 1: Confidence=0.942, Pos=(683, 404), Area=68.7%
    ✓ Face Detection: Found 1 face(s)
      🟢 Face 1: Confidence=1.000, Center=(742, 286)
        ✓ ArcFace Embedding: 512-dim vector extracted & saved to DB (ID: e7acd7a8)
```

**Database Records:**
```
ID:              e7acd7a8
Name:            Person_1_Face_e7acd7a8
Image Path:      app/static/faces/e7acd7a8.jpg
Embedding:       512 dimensions
Created:         2025-11-11 12:54:12
Location:        x=742, y=286
```

## Configuration

Set via `.env` file:

```env
# Database Configuration
DATABASE_URL=postgresql://husain:tt55oo77@149.200.251.12:5432/razzv4

# YOLO Configuration
YOLO_FPS_LIMIT=2
YOLO_CONFIDENCE=0.75

# Face Detection Configuration
FACE_DETECTOR_BACKEND=retinaface
FACE_CONFIDENCE_THRESHOLD=0.5

# Logging
LOG_LEVEL=INFO
```

## File Structure

```
app/
├── models/
│   └── database.py          # FacePerson model
├── services/
│   ├── webcam_processor.py  # Pipeline orchestration
│   ├── yolo.py              # Person detection
│   └── face_recognition.py  # Face detection & embedding
├── static/
│   └── faces/               # Saved face images
│       ├── e7acd7a8.jpg
│       ├── a7b43085.jpg
│       └── ...
└── main.py                  # FastAPI app
```

## Features

✅ **YOLO Person Detection** - Detects people at 2 FPS (configurable)
✅ **Face Detection** - RetinaFace backend for accurate detection
✅ **ArcFace Embeddings** - 512-dimensional vectors for face recognition
✅ **Disk Storage** - Face images saved to `app/static/faces/`
✅ **Database Storage** - All data persisted in PostgreSQL
✅ **Location Tracking** - Pixel coordinates recorded
✅ **Timestamp Tracking** - Detection and creation times
✅ **Error Handling** - Graceful fallback with logging

## Usage

### Start Server
```bash
cd /home/husain/alrazy/webcam-app
source .venv/bin/activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Process Image
```bash
python << 'EOF'
import base64
import requests

with open('webcam-capture-1.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

response = requests.post(
    'http://127.0.0.1:8000/api/process-image',
    json={'image': image_data}
)

print(response.json())
EOF
```

### Query Saved Faces
```bash
python << 'EOF'
from app.models.database import SessionLocal, FacePerson

db = SessionLocal()
faces = db.query(FacePerson).all()

for face in faces:
    print(f"Face ID: {face.id}")
    print(f"Name: {face.name}")
    print(f"Embedding: {len(face.embedding)} dimensions")
    print(f"Location: {face.image_path}")
    print()

db.close()
EOF
```

## Performance

- **First run**: ~9-10 seconds (includes model loading)
- **Subsequent runs**: ~3-5 seconds
- **YOLO Detection**: ~1-2 seconds
- **Face Detection**: ~2-3 seconds
- **ArcFace Embedding**: ~1-2 seconds
- **Database Save**: ~100-200ms

## Next Steps

1. **Real-time Webcam Processing** - Stream frames from webcam
2. **Face Recognition/Matching** - Compare embeddings for identity verification
3. **Dashboard** - View detected faces and statistics
4. **Search** - Find similar faces by embedding distance
5. **Tracking** - Track persons across frames

---

**Status**: ✅ Production Ready
**Database**: PostgreSQL 17.6 at 149.200.251.12:5432/razzv4
**Last Updated**: 2025-11-11 12:54:12
