# Multi-Camera Cross-Tracking Solution - Quick Start

## Problem Solved
✅ **Multiple cameras in same room with overlap → Prevents double-counting people**  
✅ **Unique person ID across all cameras → Accurate room occupancy**  
✅ **Real-time cross-camera tracking → No duplicates in person count**

## Solution Architecture

### 3-Layer Tracking System:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Room-Level Tracking (Global Person IDs)          │
│  • Unique count across all cameras in room                  │
│  • Cross-camera person matching                             │
│  • Overlap zone awareness                                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Per-Camera Tracking (ByteTrack + DeepSORT)       │
│  • Real-time tracking at 30 FPS                             │
│  • Local track IDs per camera                               │
│  • Appearance feature extraction                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Object Detection (YOLO11m)                        │
│  • Person detection with bounding boxes                     │
│  • Confidence scores                                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Features Implemented

### 1. Room Model (`models/room.py`)
- Groups cameras by physical space
- Stores overlap zone configuration
- Room capacity and metadata

### 2. Cross-Camera Tracker (`services/cross_camera_tracking.py`)
- **Appearance Matching**: HSV color histograms (114-dim features)
- **Spatial Reasoning**: Overlap zone detection boosts match confidence
- **Temporal Matching**: 3-second time window for cross-camera matching
- **Global Person Registry**: Unique IDs across all cameras in room

### 3. Room Management API (`routes/rooms.py`)
- Create/manage rooms
- Assign cameras to rooms
- Get unique person count per room
- Configure overlap zones

### 4. Room Dashboard UI (`templates/rooms.html`)
- Visual room management
- Real-time unique person counts
- Camera assignment interface
- Multi-camera indicators

## Installation Steps

### 1. Install Dependencies
```bash
cd /home/husain/alrazy/brinksv2
pip install shapely --break-system-packages
```

### 2. Run Database Migration
```bash
python3 migrate_add_rooms.py
```

### 3. Restart Application
```bash
pm2 restart all
```

### 4. Access Room Management
Navigate to: **http://localhost:8000/rooms-page**

## Configuration Guide

### Option A: Use Web UI (Recommended)

1. **Create Room:**
   - Click `+` button
   - Enter: Name, Floor, Capacity
   - Submit

2. **Assign Cameras:**
   - In room card → Click "Add Camera"
   - Select camera from dropdown
   - Repeat for all cameras in that room

### Option B: Use Example Script

```bash
python3 setup_example_room.py
```

This creates a sample room with 2 cameras and overlap configuration.

### Option C: Use API Directly

```bash
# Create room
curl -X POST http://localhost:8000/api/rooms/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Lobby", "floor_level": "Ground", "capacity": 50}'

# Assign cameras
curl -X POST http://localhost:8000/api/rooms/1/cameras/1
curl -X POST http://localhost:8000/api/rooms/1/cameras/2

# Configure overlap zones
curl -X PUT http://localhost:8000/api/rooms/1 \
  -H "Content-Type: application/json" \
  -d '{
    "overlap_config": {
      "overlaps": [{
        "camera_id_1": 1,
        "camera_id_2": 2,
        "polygon": [[100,200], [300,200], [300,400], [100,400]]
      }]
    }
  }'

# Get unique person count
curl http://localhost:8000/api/rooms/1/person-count
```

## How It Works - Technical Flow

### When Person Appears in Room:

```
Camera 1                           Camera 2
   ↓                                  ↓
Person detected                   Person detected
Local Track ID: #5                Local Track ID: #3
   ↓                                  ↓
Extract appearance features       Extract appearance features
(HSV histogram)                   (HSV histogram)
   ↓                                  ↓
        ┌────────────────────────────┐
        │  Global Person Tracker     │
        │  - Compare features        │
        │  - Check overlap zones     │
        │  - Match similarity        │
        │  - Assign Global ID        │
        └────────────────────────────┘
                     ↓
            Global Person #1
                     ↓
        Room Count: 1 unique person
        (Not 2 separate people!)
```

### Matching Algorithm:

```python
similarity = cosine_similarity(camera1_features, camera2_features)

# Boost if person is in overlap zone
if person_in_overlap_zone:
    similarity += 0.2

# Match if above threshold and within time window
if similarity >= 0.6 and time_diff < 3_seconds:
    assign_same_global_id()
else:
    create_new_global_id()
```

## Verification

### Test Cross-Camera Tracking:

1. **Start application**: `pm2 restart all`
2. **Open room page**: http://localhost:8000/rooms-page
3. **Check individual cameras**: 
   - Camera 1 shows: 2 people
   - Camera 2 shows: 2 people
4. **Check room count**: 
   - Room shows: **3 unique people** ✅ (not 4!)

### Expected Results:

| Scenario | Camera 1 | Camera 2 | Room Count | Status |
|----------|----------|----------|------------|--------|
| No overlap | 2 people | 3 people | 5 people | ✅ |
| Partial overlap | 3 people | 3 people | 4 people | ✅ |
| Full overlap | 2 people | 2 people | 2 people | ✅ |

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rooms/` | GET | List all rooms |
| `/api/rooms/` | POST | Create room |
| `/api/rooms/{id}` | GET | Get room details |
| `/api/rooms/{id}` | PUT | Update room |
| `/api/rooms/{id}` | DELETE | Delete room |
| `/api/rooms/{id}/cameras/{cid}` | POST | Assign camera |
| `/api/rooms/{id}/cameras/{cid}` | DELETE | Remove camera |
| `/api/rooms/{id}/person-count` | GET | **Get unique count** |

## Performance Tuning

### Adjust Matching Sensitivity:

Edit `main.py`:
```python
global_person_tracker = GlobalPersonTracker(
    similarity_threshold=0.6,  # 0.5-0.8 (lower = more matches)
    time_window=3              # 2-5 seconds
)
```

**Recommendations:**
- **High traffic areas**: `similarity=0.7, time_window=2`
- **Low traffic areas**: `similarity=0.5, time_window=5`
- **Similar uniforms**: `similarity=0.7` (more strict)
- **Diverse clothing**: `similarity=0.5` (more lenient)

## Troubleshooting

### Room count = sum of cameras?
**Cause**: No cross-camera matching happening  
**Fix**: 
1. Configure overlap zones
2. Lower similarity threshold
3. Check cameras are in same room

### Room count too low?
**Cause**: Too many false matches  
**Fix**:
1. Increase similarity threshold
2. Reduce time window
3. Verify cameras are correctly assigned

### No person count showing?
**Cause**: Tracking service not initialized  
**Fix**:
```bash
pm2 logs
# Check for errors
pm2 restart all
```

## Benefits of This Solution

✅ **Accurate Occupancy**: No double-counting  
✅ **Real-time**: 30 FPS tracking per camera  
✅ **Scalable**: Add unlimited cameras per room  
✅ **Configurable**: Adjust for your environment  
✅ **Visual**: Room dashboard shows everything  
✅ **API-First**: Integrate with other systems  

## Future Enhancements

🔮 **Planned Features:**
- Visual overlap zone editor (draw on camera feed)
- Person trajectory tracking across cameras
- Historical analytics and reports
- Alert system for capacity violations
- Deep learning ReID (more accurate matching)

## Documentation Files

- 📘 **MULTI_CAMERA_TRACKING.md** - Detailed technical guide
- 📗 **This file (QUICK_START.md)** - Quick setup guide
- 📕 **TRACKING_IMPLEMENTATION.md** - Original tracking docs
- 📙 **BYTETRACK_IMPLEMENTATION.md** - ByteTrack details

## Support

**Check Health:**
```bash
curl http://localhost:8000/health
pm2 status
pm2 logs
```

**Test Endpoints:**
- Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- Rooms UI: http://localhost:8000/rooms-page

---

**Ready to use!** 🚀

Navigate to http://localhost:8000/rooms-page to get started.
