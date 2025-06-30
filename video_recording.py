import cv2
import numpy as np
import threading
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging
import json
from activity_detection import SuspiciousActivity
from llm_analysis import LLMAnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class RecordingSegment:
    """Represents a recorded video segment."""
    camera_id: int
    start_time: float
    end_time: float
    file_path: str
    activity_type: str
    threat_level: str
    file_size: int
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IncidentRecording:
    """Complete incident recording with all related segments."""
    incident_id: str
    trigger_activity: SuspiciousActivity
    llm_analysis: Optional[LLMAnalysisResult]
    recording_segments: List[RecordingSegment]
    start_time: float
    end_time: float
    total_duration: float
    evidence_package_path: Optional[str] = None
    status: str = "recording"  # recording, completed, archived, deleted

class CameraRecorder:
    """Records video from a specific camera with circular buffer."""
    
    def __init__(self, camera_id: int, buffer_duration: int = 30, recordings_dir: str = "recordings"):
        self.camera_id = camera_id
        self.buffer_duration = buffer_duration  # seconds of pre-incident footage
        self.recordings_dir = recordings_dir
        self.is_recording = False
        self.recording_thread = None
        self.frame_buffer = deque(maxlen=buffer_duration * 30)  # Assume 30 FPS
        self.buffer_lock = threading.Lock()
        
        # Create recordings directory
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Video settings
        self.fps = 30
        self.codec = cv2.VideoWriter_fourcc(*'H264')
        self.frame_width = 1280
        self.frame_height = 720
        
        # Current recording state
        self.current_recording = None
        self.recording_writer = None
        
    def add_frame_to_buffer(self, frame: np.ndarray, timestamp: float):
        """Add frame to circular buffer for pre-incident recording."""
        with self.buffer_lock:
            # Resize frame to standard size
            if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            
            self.frame_buffer.append((frame.copy(), timestamp))
    
    def start_incident_recording(
        self, 
        activity: SuspiciousActivity, 
        llm_analysis: Optional[LLMAnalysisResult] = None,
        duration: int = 60
    ) -> str:
        """Start recording an incident."""
        if self.is_recording:
            logger.warning(f"Camera {self.camera_id} is already recording")
            return None
        
        # Generate incident ID
        incident_id = f"incident_{self.camera_id}_{int(time.time())}"
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(activity.timestamp))
        filename = f"{incident_id}_{timestamp_str}.mp4"
        filepath = os.path.join(self.recordings_dir, filename)
        
        try:
            # Initialize video writer
            self.recording_writer = cv2.VideoWriter(
                filepath, 
                self.codec, 
                self.fps, 
                (self.frame_width, self.frame_height)
            )
            
            if not self.recording_writer.isOpened():
                logger.error(f"Failed to initialize video writer for {filepath}")
                return None
            
            # Write pre-incident buffer
            with self.buffer_lock:
                logger.info(f"Writing {len(self.frame_buffer)} buffered frames")
                for frame, _ in list(self.frame_buffer):
                    self.recording_writer.write(frame)
            
            # Create recording metadata
            self.current_recording = IncidentRecording(
                incident_id=incident_id,
                trigger_activity=activity,
                llm_analysis=llm_analysis,
                recording_segments=[],
                start_time=activity.timestamp - self.buffer_duration,  # Include buffer time
                end_time=activity.timestamp + duration,
                total_duration=duration + self.buffer_duration,
                status="recording"
            )
            
            # Start recording thread
            self.is_recording = True
            self.recording_thread = threading.Thread(
                target=self._recording_worker,
                args=(duration, filepath)
            )
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info(f"Started incident recording: {incident_id}")
            return incident_id
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            if self.recording_writer:
                self.recording_writer.release()
                self.recording_writer = None
            return None
    
    def _recording_worker(self, duration: int, filepath: str):
        """Worker thread for recording incident."""
        start_time = time.time()
        frame_count = 0
        
        try:
            while self.is_recording and (time.time() - start_time) < duration:
                # Get current frame from camera
                # This would be integrated with the camera service
                time.sleep(1/self.fps)  # Control frame rate
                frame_count += 1
            
            # Finalize recording
            self._finalize_recording(filepath, frame_count)
            
        except Exception as e:
            logger.error(f"Error in recording worker: {e}")
        finally:
            self.is_recording = False
            if self.recording_writer:
                self.recording_writer.release()
                self.recording_writer = None
    
    def _finalize_recording(self, filepath: str, frame_count: int):
        """Finalize and save recording metadata."""
        if not self.current_recording:
            return
        
        try:
            # Get file info
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            actual_duration = frame_count / self.fps
            
            # Create recording segment
            segment = RecordingSegment(
                camera_id=self.camera_id,
                start_time=self.current_recording.start_time,
                end_time=time.time(),
                file_path=filepath,
                activity_type=self.current_recording.trigger_activity.activity_type.value,
                threat_level=self.current_recording.llm_analysis.threat_level if self.current_recording.llm_analysis else "UNKNOWN",
                file_size=file_size,
                duration=actual_duration,
                metadata={
                    "frame_count": frame_count,
                    "fps": self.fps,
                    "resolution": f"{self.frame_width}x{self.frame_height}",
                    "codec": "H264"
                }
            )
            
            self.current_recording.recording_segments.append(segment)
            self.current_recording.end_time = time.time()
            self.current_recording.status = "completed"
            
            # Save metadata
            metadata_path = filepath.replace('.mp4', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump({
                    "incident": {
                        "incident_id": self.current_recording.incident_id,
                        "camera_id": self.camera_id,
                        "start_time": self.current_recording.start_time,
                        "end_time": self.current_recording.end_time,
                        "total_duration": self.current_recording.total_duration,
                        "status": self.current_recording.status
                    },
                    "trigger_activity": {
                        "activity_type": self.current_recording.trigger_activity.activity_type.value,
                        "timestamp": self.current_recording.trigger_activity.timestamp,
                        "location": self.current_recording.trigger_activity.location,
                        "confidence": self.current_recording.trigger_activity.confidence,
                        "description": self.current_recording.trigger_activity.description
                    },
                    "llm_analysis": {
                        "is_confirmed_suspicious": self.current_recording.llm_analysis.is_confirmed_suspicious if self.current_recording.llm_analysis else None,
                        "threat_level": self.current_recording.llm_analysis.threat_level if self.current_recording.llm_analysis else None,
                        "confidence_score": self.current_recording.llm_analysis.confidence_score if self.current_recording.llm_analysis else None,
                        "reasoning": self.current_recording.llm_analysis.reasoning if self.current_recording.llm_analysis else None,
                        "recommended_action": self.current_recording.llm_analysis.recommended_action if self.current_recording.llm_analysis else None
                    },
                    "recording_info": {
                        "file_path": filepath,
                        "file_size": file_size,
                        "duration": actual_duration,
                        "frame_count": frame_count,
                        "fps": self.fps,
                        "resolution": f"{self.frame_width}x{self.frame_height}"
                    }
                }, f, indent=2)
            
            logger.info(f"Recording completed: {self.current_recording.incident_id}")
            
        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")
    
    def stop_recording(self):
        """Stop current recording."""
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join(timeout=5)
    
    def get_current_recording_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current recording."""
        if not self.current_recording:
            return None
        
        return {
            "incident_id": self.current_recording.incident_id,
            "is_recording": self.is_recording,
            "start_time": self.current_recording.start_time,
            "elapsed_time": time.time() - self.current_recording.start_time if self.is_recording else 0,
            "activity_type": self.current_recording.trigger_activity.activity_type.value,
            "threat_level": self.current_recording.llm_analysis.threat_level if self.current_recording.llm_analysis else "UNKNOWN"
        }

class VideoRecordingService:
    """Central video recording service for all cameras."""
    
    def __init__(self, recordings_dir: str = "recordings", buffer_duration: int = 30):
        self.recordings_dir = recordings_dir
        self.buffer_duration = buffer_duration
        self.camera_recorders: Dict[int, CameraRecorder] = {}
        self.active_recordings: Dict[str, IncidentRecording] = {}
        self.recording_history: List[IncidentRecording] = []
        
        # Ensure recordings directory exists
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Recording settings
        self.auto_record_on_threat_levels = ["HIGH", "CRITICAL"]
        self.default_recording_duration = 60  # seconds
        self.max_concurrent_recordings = 4
        
    def get_camera_recorder(self, camera_id: int) -> CameraRecorder:
        """Get or create camera recorder."""
        if camera_id not in self.camera_recorders:
            self.camera_recorders[camera_id] = CameraRecorder(
                camera_id, 
                self.buffer_duration, 
                self.recordings_dir
            )
        return self.camera_recorders[camera_id]
    
    def add_frame_to_buffer(self, camera_id: int, frame: np.ndarray):
        """Add frame to camera's circular buffer."""
        recorder = self.get_camera_recorder(camera_id)
        recorder.add_frame_to_buffer(frame, time.time())
    
    async def handle_suspicious_activity(
        self, 
        activity: SuspiciousActivity, 
        llm_analysis: Optional[LLMAnalysisResult] = None
    ) -> Optional[str]:
        """Handle suspicious activity and decide whether to record."""
        
        # Check if recording is warranted
        should_record = False
        recording_duration = self.default_recording_duration
        
        if llm_analysis:
            # Use LLM analysis to decide
            if llm_analysis.threat_level in self.auto_record_on_threat_levels:
                should_record = True
                
                # Adjust duration based on threat level
                if llm_analysis.threat_level == "CRITICAL":
                    recording_duration = 120  # 2 minutes for critical threats
                elif llm_analysis.threat_level == "HIGH":
                    recording_duration = 90   # 1.5 minutes for high threats
                    
        else:
            # Fallback decision based on activity type
            high_priority_activities = [
                "taking_without_paying",
                "multiple_people_restricted", 
                "exit_without_payment",
                "after_hours_activity"
            ]
            
            if activity.activity_type.value in high_priority_activities:
                should_record = True
        
        if not should_record:
            logger.info(f"Activity {activity.activity_type.value} does not warrant recording")
            return None
        
        # Check recording limits
        active_count = len([r for r in self.active_recordings.values() if r.status == "recording"])
        if active_count >= self.max_concurrent_recordings:
            logger.warning("Maximum concurrent recordings reached")
            return None
        
        # Start recording
        recorder = self.get_camera_recorder(activity.camera_id)
        incident_id = recorder.start_incident_recording(activity, llm_analysis, recording_duration)
        
        if incident_id:
            self.active_recordings[incident_id] = recorder.current_recording
            logger.info(f"Started recording for incident: {incident_id}")
            
        return incident_id
    
    def stop_recording(self, incident_id: str) -> bool:
        """Stop a specific recording."""
        if incident_id not in self.active_recordings:
            return False
        
        recording = self.active_recordings[incident_id]
        recorder = self.get_camera_recorder(recording.trigger_activity.camera_id)
        recorder.stop_recording()
        
        # Move to history
        self.recording_history.append(recording)
        del self.active_recordings[incident_id]
        
        return True
    
    def stop_all_recordings(self):
        """Stop all active recordings."""
        for incident_id in list(self.active_recordings.keys()):
            self.stop_recording(incident_id)
    
    def get_active_recordings(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active recordings."""
        active_info = {}
        
        for incident_id, recording in self.active_recordings.items():
            recorder = self.get_camera_recorder(recording.trigger_activity.camera_id)
            active_info[incident_id] = recorder.get_current_recording_info()
        
        return active_info
    
    def get_recording_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recording history for the last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_recordings = []
        for recording in self.recording_history:
            if recording.start_time >= cutoff_time:
                recent_recordings.append({
                    "incident_id": recording.incident_id,
                    "camera_id": recording.trigger_activity.camera_id,
                    "activity_type": recording.trigger_activity.activity_type.value,
                    "threat_level": recording.llm_analysis.threat_level if recording.llm_analysis else "UNKNOWN",
                    "start_time": recording.start_time,
                    "duration": recording.total_duration,
                    "status": recording.status,
                    "file_count": len(recording.recording_segments)
                })
        
        return recent_recordings
    
    def get_recording_statistics(self) -> Dict[str, Any]:
        """Get recording system statistics."""
        total_recordings = len(self.recording_history)
        active_recordings = len(self.active_recordings)
        
        # Calculate storage usage
        total_size = 0
        for recording in self.recording_history:
            for segment in recording.recording_segments:
                total_size += segment.file_size
        
        # Activity type distribution
        activity_types = [r.trigger_activity.activity_type.value for r in self.recording_history]
        activity_counts = {activity: activity_types.count(activity) for activity in set(activity_types)}
        
        return {
            "total_recordings": total_recordings,
            "active_recordings": active_recordings,
            "total_storage_mb": total_size / (1024 * 1024),
            "recordings_today": len([
                r for r in self.recording_history 
                if time.time() - r.start_time < 24 * 3600
            ]),
            "activity_type_distribution": activity_counts,
            "average_recording_duration": sum(
                r.total_duration for r in self.recording_history
            ) / total_recordings if total_recordings > 0 else 0
        }
    
    def cleanup_old_recordings(self, days: int = 30):
        """Clean up recordings older than specified days."""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        removed_count = 0
        for recording in list(self.recording_history):
            if recording.start_time < cutoff_time:
                # Delete video files
                for segment in recording.recording_segments:
                    try:
                        if os.path.exists(segment.file_path):
                            os.remove(segment.file_path)
                        
                        # Also remove metadata file
                        metadata_path = segment.file_path.replace('.mp4', '_metadata.json')
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                        
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Error removing recording file {segment.file_path}: {e}")
                
                # Remove from history
                self.recording_history.remove(recording)
        
        logger.info(f"Cleaned up {removed_count} old recording files")
        return removed_count

# Global recording service
recording_service: Optional[VideoRecordingService] = None

def initialize_recording_service(recordings_dir: str = "recordings", buffer_duration: int = 30) -> VideoRecordingService:
    """Initialize the global recording service."""
    global recording_service
    recording_service = VideoRecordingService(recordings_dir, buffer_duration)
    return recording_service

def get_recording_service() -> Optional[VideoRecordingService]:
    """Get the global recording service."""
    return recording_service
