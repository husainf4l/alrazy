# Clean Architecture Plan for RAZZv4 Backend

## Current Issues
- All code mixed in root directory
- Services tightly coupled
- No clear separation of concerns
- Logs are too verbose

## Proposed Structure

```
RAZZv4-backend/
├── src/
│   ├── domain/                    # Core business logic (entities, value objects)
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── person.py         # Person entity with tracking info
│   │   │   ├── camera.py         # Camera entity
│   │   │   ├── room.py           # Room entity
│   │   │   └── vault_room.py     # Vault room entity
│   │   └── value_objects/
│   │       ├── __init__.py
│   │       ├── bbox.py           # Bounding box value object
│   │       ├── track_id.py       # Track ID value object
│   │       └── feature_vector.py # ReID feature vector
│   │
│   ├── application/               # Use cases / business logic
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── track_people.py   # Track people use case
│   │   │   ├── count_people.py   # Count people use case
│   │   │   ├── deduplicate.py    # Deduplication use case
│   │   │   └── assign_global_ids.py # Global ID assignment use case
│   │   └── interfaces/           # Abstract interfaces
│   │       ├── __init__.py
│   │       ├── tracker_interface.py
│   │       ├── detector_interface.py
│   │       └── camera_interface.py
│   │
│   ├── infrastructure/            # External dependencies & implementations
│   │   ├── __init__.py
│   │   ├── tracking/
│   │   │   ├── __init__.py
│   │   │   ├── yolo_detector.py      # YOLO implementation
│   │   │   ├── bytetrack_tracker.py  # ByteTrack implementation
│   │   │   └── deepsort_tracker.py   # DeepSORT implementation
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # SQLAlchemy models
│   │   │   └── repositories.py   # Database repositories
│   │   ├── camera/
│   │   │   ├── __init__.py
│   │   │   └── rtsp_camera.py    # RTSP camera implementation
│   │   └── logging/
│   │       ├── __init__.py
│   │       └── logger_config.py  # Centralized logging config
│   │
│   └── presentation/              # API layer (FastAPI routes)
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── v1/
│       │   │   ├── __init__.py
│       │   │   ├── auth.py
│       │   │   ├── health.py
│       │   │   ├── cameras.py
│       │   │   ├── rooms.py
│       │   │   └── tracking.py
│       │   └── dependencies.py   # Dependency injection
│       ├── schemas/              # Pydantic schemas
│       │   ├── __init__.py
│       │   ├── person_schema.py
│       │   ├── camera_schema.py
│       │   └── room_schema.py
│       └── websockets/
│           ├── __init__.py
│           └── tracking_ws.py
│
├── main.py                       # Application entry point
├── config.py                     # Configuration management
├── pyproject.toml
└── README.md
```

## Benefits

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Testability**: Easy to mock interfaces and test business logic
3. **Maintainability**: Changes in one layer don't affect others
4. **Scalability**: Easy to add new features
5. **Clean Code**: Better organized and readable

## Migration Strategy

### Phase 1: Logging Cleanup ✅
- Reduce verbose logs in tracking service
- Keep only essential INFO logs
- Move DEBUG logs to debug mode only

### Phase 2: Create Clean Structure (In Progress)
- Create new directory structure
- Define domain entities
- Define use case interfaces
- Keep current code working during migration

### Phase 3: Gradual Migration
- Move tracking logic to infrastructure layer
- Create use cases for business logic
- Update routes to use new structure
- Maintain backward compatibility

### Phase 4: Final Cleanup
- Remove old files
- Update documentation
- Add unit tests

## Notes

- The logic is working correctly, we're just reorganizing for maintainability
- Global ID system is functioning properly
- Deduplication is accurate
- No functional changes, only structural improvements
