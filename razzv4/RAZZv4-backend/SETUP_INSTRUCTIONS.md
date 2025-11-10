# Face Recognition System - Setup Instructions

## ✅ What's Been Completed (Local Development Server)

### 1. Dependencies Installed ✅
```bash
✅ insightface>=0.7.3
✅ onnxruntime>=1.16.0
✅ pgvector>=0.2.0 (Python client)
✅ scipy>=1.11.0
```

### 2. Code Implementation ✅
- ✅ **models.py** - Added Person, FaceEmbedding, TrackingEvent models
- ✅ **services/face_recognition_service.py** - Complete face detection & recognition using ArcFace
- ✅ **services/event_logger.py** - Event logging system (entry/exit/motion)
- ✅ **migrate_add_face_recognition.py** - Database migration script
- ✅ **FACE_RECOGNITION_ARCHITECTURE.md** - Complete system documentation
- ✅ **pyproject.toml** - Updated with all dependencies

---

## 🔧 REQUIRED: Database Server Setup (149.200.251.12)

### Step 1: SSH to Database Server
```bash
ssh user@149.200.251.12
```

### Step 2: Install pgvector Extension
```bash
# Update package list
sudo apt-get update

# Install pgvector for PostgreSQL 17
sudo apt-get install -y postgresql-17-pgvector

# Verify installation
ls /usr/share/postgresql/17/extension/vector*
# Should show: vector.control and vector--*.sql files
```

### Step 3: Enable pgvector in Database
```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Switch to your database
\c razzv4

# Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify it's installed
\dx

# You should see 'vector' in the list
# Exit
\q
```

---

## 🚀 After pgvector is Installed on Remote Server

### Run Migration from Development Server
```bash
cd /home/husain/alrazy/razzv4/RAZZv4-backend

# Run the migration
uv run python migrate_add_face_recognition.py
```

### Expected Output:
```
🚀 Starting face recognition database migration...

1️⃣  Enabling pgvector extension...
✅ pgvector extension enabled

2️⃣  Creating persons table...
✅ persons table created

3️⃣  Creating face_embeddings table with vector(512)...
   Creating vector similarity index (this may take a moment)...
✅ face_embeddings table created with vector index

4️⃣  Creating tracking_events table...
✅ tracking_events table created

5️⃣  Creating uploads directory...
✅ uploads/faces directory created

============================================================
✅ Face recognition migration completed successfully!
============================================================

New tables created:
  • persons - Enrolled people in the system
  • face_embeddings - ArcFace embeddings (512-dim vectors)
  • tracking_events - Event logs (entry/exit/motion)
```

---

## 📋 Verify Migration Success

### Check Tables Created:
```bash
# From development server
PGPASSWORD=tt55oo77 psql -h 149.200.251.12 -U husain -d razzv4 -c "\dt"
```

Should show:
- cameras
- companies
- persons ✨ NEW
- face_embeddings ✨ NEW
- tracking_events ✨ NEW
- users
- vault_rooms

### Check pgvector Extension:
```bash
PGPASSWORD=tt55oo77 psql -h 149.200.251.12 -U husain -d razzv4 -c "\dx vector"
```

---

## 🎯 After Migration: Next Steps

### 1. Test Face Recognition Service
```python
# Test file: test_face_recognition.py
from services.face_recognition_service import get_face_recognition_service
import cv2

service = get_face_recognition_service()
print(f"Face recognition available: {service.is_available()}")

# Test with an image
image = cv2.imread("test_face.jpg")
faces = service.detect_faces(image)
print(f"Detected {len(faces)} faces")
```

### 2. Start Implementing Person Enrollment API
```bash
# Create routes/persons.py
# - POST /persons/enroll
# - GET /persons/
# - DELETE /persons/{id}
```

### 3. Integrate Face Recognition with Tracking
```bash
# Update services/tracking_service.py
# - Call face recognition every 30 frames
# - Match against gallery
# - Assign person_id to tracks
```

### 4. Build Person Enrollment UI
```bash
# Create templates/persons.html
# - Upload form
# - Gallery view
# - Face preview
```

---

## 🔍 Troubleshooting

### Issue: "extension 'vector' is not available"
**Solution:** Install pgvector on database server (see Step 2 above)

### Issue: "permission denied to create extension"
**Solution:** Connect as superuser or grant permissions:
```sql
-- As postgres user:
GRANT CREATE ON DATABASE razzv4 TO husain;
-- Or run as superuser:
sudo -u postgres psql -d razzv4 -c "CREATE EXTENSION vector;"
```

### Issue: ArcFace model download fails
**Solution:** Models auto-download to `~/.insightface/models/buffalo_l/`
- Ensure internet connection
- Or manually download from: https://github.com/deepinsight/insightface/releases

### Issue: Face recognition too slow
**Solution:** 
- Use GPU: Install `onnxruntime-gpu` instead of `onnxruntime`
- Reduce face extraction frequency (every 30-60 frames instead of every frame)
- Use smaller model: `buffalo_s` instead of `buffalo_l`

---

## 📞 Summary of What You Need to Do NOW

### On Database Server (149.200.251.12):
```bash
ssh user@149.200.251.12
sudo apt-get update
sudo apt-get install -y postgresql-17-pgvector
sudo -u postgres psql -d razzv4 -c "CREATE EXTENSION vector;"
```

### Then on Development Server:
```bash
cd /home/husain/alrazy/razzv4/RAZZv4-backend
uv run python migrate_add_face_recognition.py
```

That's it! Once pgvector is installed on the remote server, everything else is ready to go.

---

## 📊 Current System Status

### ✅ COMPLETED:
- Research & architecture design
- Database models (Person, FaceEmbedding, TrackingEvent)
- Face recognition service (InsightFace + ArcFace)
- Event logging service
- Migration script
- Documentation

### ⏳ PENDING:
- Install pgvector on database server **← YOU ARE HERE**
- Run database migration
- Person enrollment API
- WebSocket real-time updates
- UI templates updates
- Tracking integration

---

**Need Help?** Check FACE_RECOGNITION_ARCHITECTURE.md for complete system design.
