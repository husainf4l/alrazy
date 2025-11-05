# SafeRoom Detection System v2.2 - Quick Reference Guide

## 🚀 Quick Start

### Start Backend
```bash
cd /home/husain/alrazy/brinks
nohup .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

### Check Status
```bash
curl http://localhost:8000/status | jq .
curl http://localhost:8000/config | jq '.person_reid'
```

## 📊 API Quick Commands

### List All Persons (Global Gallery)
```bash
curl http://localhost:8000/persons | jq '.persons[] | {label, cameras}'
```

### Get Person Details
```bash
curl http://localhost:8000/persons/person_1762344658197_0 | jq .
```

### Get Statistics by Camera
```bash
curl http://localhost:8000/persons/stats | jq '.cameras'
```

### Filter by Camera
```bash
curl http://localhost:8000/persons?camera_id=room1 | jq '.persons[] | {label, cameras}'
```

### Reset Gallery
```bash
curl -X POST http://localhost:8000/persons/reset | jq .
curl -X POST http://localhost:8000/persons/reset?camera_id=room1 | jq .
```

### Merge Identities
```bash
curl -X POST "http://localhost:8000/persons/merge?person_id1=A&person_id2=B" | jq .
```

## 🔍 System Architecture

### Global Cross-Camera Re-ID
```
room1 ┐
room2 ├─→ GLOBAL PersonReIdentifier ──→ Visitor-A (person_1762344658197_0)
room3 │   (Single shared instance)       cameras: [room1, room2, room3, room4]
room4 ┘
```

### Person Object Structure
```json
{
  "person_id": "person_1762344658197_0",
  "label": "Visitor-A",
  "cameras": ["room2", "room3", "room1", "room4"],
  "first_seen": 1762344658.197,
  "last_seen": 1762344708.601,
  "visit_count": 1,
  "num_embeddings": 10,
  "avg_confidence": 0.999
}
```

## 🎯 Key Features

✅ **Global Cross-Camera Re-ID**: Same person labels across all cameras
✅ **Persistent Gallery**: 90-day TTL with Redis storage
✅ **Real-time Updates**: WebSocket broadcasts with person_labels
✅ **Appearance Features**: 512-dim embedding vectors
✅ **Human-Readable Labels**: Visitor-A, Visitor-B, etc.
✅ **Multi-Camera Tracking**: Cameras array shows all detection locations

## 📝 Configuration

### Environment Variables
```bash
USE_PERSON_REID=true                    # Enable/disable person re-ID
REID_SIMILARITY_THRESHOLD=0.6           # Matching threshold (0-1)
REID_TTL_DAYS=90                        # Person gallery TTL
REID_CLOUD_STORAGE=local                # Cloud storage: local|s3|gcs
```

### Redis Namespace
```
saferoom:persons:global:person_ID → Person record (JSON)
```

## 🧪 Testing

### Verify Cross-Camera Sharing
```bash
# Should show same person_id in multiple cameras
curl -s http://localhost:8000/persons | jq '.persons[] | 
  select(.cameras | length > 1) | {label, person_id, cameras}'
```

### Monitor Person Creation
```bash
# Watch live gallery
watch 'curl -s http://localhost:8000/persons | jq ".total, 
  .persons[] | {label, cameras}"'
```

### Check Backend Logs
```bash
tail -f /home/husain/alrazy/brinks/backend.log | grep -E "✅|❌|Person"
```

## 📁 Project Files

### Core Modules
- `backend/main.py` - FastAPI backend with person re-ID integration
- `reid/person_reidentifier.py` - PersonReIdentifier engine
- `reid/storage.py` - Redis and cloud storage
- `tracker/deepsort.py` - Hybrid tracking system

### Documentation
- `PERSON_REID.md` - Complete person re-ID system guide
- `CROSS_CAMERA_REID.md` - Cross-camera implementation details
- `QUICK_START.md` - System setup and running

## 🔧 Troubleshooting

### Person not recognized in different cameras
→ Check `/config` to verify `instance_type: "global_cross_camera"`
→ Verify Redis connection: `redis-cli KEYS "saferoom:persons:global:*"`

### Labels not appearing in API response
→ Check backend logs for person re-ID errors
→ Verify `/ingest` endpoint returns `person_labels` field

### High false positive matches
→ Increase `REID_SIMILARITY_THRESHOLD` to 0.7 or higher
→ Check embedding quality (color, spatial, texture features)

## 📊 Live Metrics

- **Total Persons**: Query `/persons` and check `total` field
- **Per-Camera Counts**: Query `/persons/stats` for breakdown
- **System Health**: Query `/config` for component status
- **Recent Events**: Query `/status` for recent violations/events

## 🔗 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/persons` | List all persons (global) |
| GET | `/persons/{id}` | Get person details |
| GET | `/persons/stats` | Re-ID statistics |
| POST | `/persons/merge` | Merge identities |
| POST | `/persons/reset` | Reset gallery |
| GET | `/config` | System configuration |
| POST | `/ingest` | Frame detection & tracking |
| WebSocket | `/ws` | Real-time updates |

## 💾 Git Commands

### View Recent Commits
```bash
cd /home/husain/alrazy/brinks
git log --oneline -10
```

### Push Changes
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

## 🚀 Production Deployment

The system is production-ready with:
- ✅ Error handling and fallback mechanisms
- ✅ Persistent Redis storage with TTL
- ✅ Real-time WebSocket updates
- ✅ Comprehensive logging
- ✅ Environment-based configuration
- ✅ Docker-compatible structure

---

**Status**: ✅ All systems operational and tested
**Last Updated**: November 5, 2025
**Version**: 2.2 (Global Cross-Camera Re-ID)
