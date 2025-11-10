"""
Service Layer for Brinks V2 People Detection System
"""
from services.people_detection import PeopleDetector, RTSPPeopleCounter
from services.cross_camera_tracking import GlobalPersonTracker

__all__ = [
    "PeopleDetector",
    "RTSPPeopleCounter",
    "GlobalPersonTracker",
]