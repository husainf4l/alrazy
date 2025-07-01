"""
Async Recording Service for the Al Razy Pharmacy Security System.
Refactored to use async/await patterns instead of threading.
"""
import asyncio
import cv2
import numpy as np
import time
import os
import aiofiles
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from app.services.activity_service import SuspiciousActivity
from app.services.llm_service import LLMAnalysisResult

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

class AsyncCameraRecorder:
    """Async records video from a specific camera with circular buffer."""
    
    def __init__(self, camera_id: int, buffer_duration: int = 30, 
                 recordings_dir: str = "recordings", executor: ThreadPoolExecutor = None):
        self.camera_id = camera_id
        self.buffer_duration = buffer_duration
        self.recordings_dir = recordings_dir
        self.executor = executor or ThreadPoolExecutor(max_workers=2)
        
        self.is_recording = False
        self.recording_task = None
        self.buffer_lock = asyncio.Lock()
        
        # Circular buffer for frames
        self.frame_buffer = deque(maxlen=buffer_duration * 10)  # Assuming ~10 FPS
        self.buffer_metadata = deque(maxlen=buffer_duration * 10)
        
        # Current recording state
        self.current_recording = None
        self.recording_writer = None
        
        # Ensure recordings directory exists
        os.makedirs(recordings_dir, exist_ok=True)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_buffering()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_recording()
        
    async def start_buffering(self):
        """Start buffering frames from the camera."""
        if self.recording_task and not self.recording_task.done():
            return
            
        self.is_recording = True
        self.recording_task = asyncio.create_task(self._buffer_frames())
        logger.info(f"📹 Started buffering for camera {self.camera_id}")
    
    async def _buffer_frames(self):
        """Continuously buffer frames from camera."""
        consecutive_failures = 0
        max_failures = 10
        
        while self.is_recording:
            try:
                # Get frame from camera service
                frame = await self._get_camera_frame()
                
                if frame is not None:
                    async with self.buffer_lock:
                        # Add frame to circular buffer
                        timestamp = time.time()
                        self.frame_buffer.append(frame.copy())
                        self.buffer_metadata.append({
                            'timestamp': timestamp,
                            'camera_id': self.camera_id,
                            'frame_index': len(self.frame_buffer)
                        })
                    
                    consecutive_failures = 0
                    await asyncio.sleep(0.1)  # ~10 FPS
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.warning(f"Camera {self.camera_id}: Too many frame failures")
                        await asyncio.sleep(5)  # Longer wait after repeated failures
                        consecutive_failures = 0
                    else:
                        await asyncio.sleep(0.5)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error buffering frames for camera {self.camera_id}: {e}")
                await asyncio.sleep(1)
    
    async def _get_camera_frame(self) -> Optional[np.ndarray]:
        """Get current frame from camera service."""
        try:
            # Import here to avoid circular imports
            from app.core.dependencies import get_camera_service
            
            # This should be replaced with proper async camera service integration
            camera_service = get_camera_service()
            if camera_service:
                # Run in executor to avoid blocking
                return await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: camera_service.get_frame_sync(self.camera_id)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get frame from camera {self.camera_id}: {e}")
            return None
    
    async def trigger_incident_recording(self, activity: SuspiciousActivity, 
                                       duration: int = 60) -> Optional[str]:
        """Trigger incident recording including pre-incident buffer."""
        try:
            incident_id = f"incident_{self.camera_id}_{int(time.time() * 1000)}"
            logger.info(f"🚨 Triggering incident recording: {incident_id}")
            
            # Create recording file path
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"incident_{self.camera_id}_{timestamp_str}_{activity.activity_type.value}.mp4"
            file_path = os.path.join(self.recordings_dir, filename)
            
            # Start recording task
            recording_task = asyncio.create_task(
                self._record_incident(file_path, activity, duration)
            )
            
            return incident_id
            
        except Exception as e:
            logger.error(f"Failed to trigger incident recording: {e}")
            return None
    
    async def _record_incident(self, file_path: str, activity: SuspiciousActivity, 
                             duration: int):
        """Record incident video including buffer."""
        start_time = time.time()
        frames_written = 0
        
        try:
            # Get buffered frames
            async with self.buffer_lock:
                buffered_frames = list(self.frame_buffer)
                buffered_metadata = list(self.buffer_metadata)
            
            if not buffered_frames:
                logger.warning("No buffered frames available for recording")
                return
            
            # Initialize video writer in thread pool
            writer = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._create_video_writer,
                file_path,
                buffered_frames[0] if buffered_frames else None
            )
            
            if writer is None:
                logger.error("Failed to create video writer")
                return
            
            try:
                # Write buffered frames (pre-incident)
                logger.info(f"Writing {len(buffered_frames)} buffered frames")
                for frame in buffered_frames:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        writer.write,
                        frame
                    )
                    frames_written += 1
                
                # Continue recording for specified duration
                end_time = start_time + duration
                while time.time() < end_time and self.is_recording:
                    frame = await self._get_camera_frame()
                    if frame is not None:
                        await asyncio.get_event_loop().run_in_executor(
                            self.executor,
                            writer.write,
                            frame
                        )
                        frames_written += 1
                    
                    await asyncio.sleep(0.1)  # ~10 FPS
                
            finally:
                # Release video writer
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    writer.release
                )
            
            # Get file size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            recording_duration = time.time() - start_time
            
            # Create metadata file
            await self._save_recording_metadata(
                file_path, activity, recording_duration, frames_written, file_size
            )
            
            logger.info(f"✅ Incident recording completed: {file_path}")
            logger.info(f"   Duration: {recording_duration:.1f}s, Frames: {frames_written}, Size: {file_size} bytes")
            
        except Exception as e:
            logger.error(f"Error during incident recording: {e}")
    
    def _create_video_writer(self, file_path: str, sample_frame: Optional[np.ndarray]) -> Optional[cv2.VideoWriter]:
        """Create video writer (runs in thread pool)."""
        try:
            if sample_frame is None:
                return None
                
            height, width = sample_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(file_path, fourcc, 10.0, (width, height))
            
            if not writer.isOpened():
                logger.error(f"Failed to open video writer for {file_path}")
                return None
                
            return writer
            
        except Exception as e:
            logger.error(f"Error creating video writer: {e}")
            return None
    
    async def _save_recording_metadata(self, file_path: str, activity: SuspiciousActivity,
                                     duration: float, frames: int, file_size: int):
        """Save recording metadata to JSON file."""
        try:
            metadata = {
                'incident_id': f"incident_{self.camera_id}_{int(time.time() * 1000)}",
                'camera_id': self.camera_id,
                'trigger_activity': {
                    'type': activity.activity_type.value,
                    'confidence': activity.confidence,
                    'timestamp': activity.timestamp,
                    'bounding_box': activity.bounding_box
                },
                'recording': {
                    'file_path': file_path,
                    'duration': duration,
                    'frames_written': frames,
                    'file_size': file_size,
                    'fps': frames / duration if duration > 0 else 0
                },
                'created_at': time.time()
            }
            
            metadata_path = file_path.replace('.mp4', '_metadata.json')
            
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save recording metadata: {e}")
    
    async def stop_recording(self):
        """Stop recording and cleanup."""
        self.is_recording = False
        
        if self.recording_task and not self.recording_task.done():
            self.recording_task.cancel()
            try:
                await self.recording_task
            except asyncio.CancelledError:
                pass
        
        # Clear buffers
        async with self.buffer_lock:
            self.frame_buffer.clear()
            self.buffer_metadata.clear()
            
        logger.info(f"🛑 Stopped recording for camera {self.camera_id}")

class AsyncRecordingService:
    """Async recording service managing multiple camera recorders."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.recordings_dir = config.get('recordings_dir', 'recordings')
        self.buffer_duration = config.get('buffer_duration', 30)
        self.recording_duration = config.get('recording_duration', 60)
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.camera_recorders: Dict[int, AsyncCameraRecorder] = {}
        self.active_recordings: Dict[str, IncidentRecording] = {}
        
        # Ensure recordings directory exists
        os.makedirs(self.recordings_dir, exist_ok=True)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize_camera_recorder(self, camera_id: int) -> bool:
        """Initialize recorder for a specific camera."""
        try:
            if camera_id in self.camera_recorders:
                return True
                
            recorder = AsyncCameraRecorder(
                camera_id=camera_id,
                buffer_duration=self.buffer_duration,
                recordings_dir=self.recordings_dir,
                executor=self.executor
            )
            
            await recorder.start_buffering()
            self.camera_recorders[camera_id] = recorder
            
            logger.info(f"📹 Initialized recorder for camera {camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize recorder for camera {camera_id}: {e}")
            return False
    
    async def trigger_incident_recording(self, camera_id: int, 
                                       activity: SuspiciousActivity) -> Optional[str]:
        """Trigger incident recording for a specific camera."""
        try:
            # Initialize recorder if not exists
            if camera_id not in self.camera_recorders:
                if not await self.initialize_camera_recorder(camera_id):
                    return None
            
            recorder = self.camera_recorders[camera_id]
            incident_id = await recorder.trigger_incident_recording(
                activity, self.recording_duration
            )
            
            if incident_id:
                # Create incident recording entry
                incident_recording = IncidentRecording(
                    incident_id=incident_id,
                    trigger_activity=activity,
                    llm_analysis=None,
                    recording_segments=[],
                    start_time=time.time(),
                    end_time=0,
                    total_duration=0,
                    status="recording"
                )
                
                self.active_recordings[incident_id] = incident_recording
            
            return incident_id
            
        except Exception as e:
            logger.error(f"Failed to trigger recording for camera {camera_id}: {e}")
            return None
    
    async def get_recording_status(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific recording."""
        if incident_id in self.active_recordings:
            recording = self.active_recordings[incident_id]
            return {
                'incident_id': incident_id,
                'status': recording.status,
                'camera_id': recording.trigger_activity.camera_id,
                'activity_type': recording.trigger_activity.activity_type.value,
                'start_time': recording.start_time,
                'duration': time.time() - recording.start_time if recording.status == 'recording' else recording.total_duration
            }
        return None
    
    async def list_recordings(self) -> List[Dict[str, Any]]:
        """List all recordings with their metadata."""
        recordings = []
        
        try:
            # Scan recordings directory for metadata files
            for filename in os.listdir(self.recordings_dir):
                if filename.endswith('_metadata.json'):
                    metadata_path = os.path.join(self.recordings_dir, filename)
                    
                    async with aiofiles.open(metadata_path, 'r') as f:
                        content = await f.read()
                        metadata = json.loads(content)
                        recordings.append(metadata)
                        
        except Exception as e:
            logger.error(f"Error listing recordings: {e}")
        
        return recordings
    
    async def cleanup(self):
        """Cleanup all recorders and resources."""
        logger.info("🧹 Cleaning up async recording service")
        
        # Stop all camera recorders
        cleanup_tasks = []
        for recorder in self.camera_recorders.values():
            cleanup_tasks.append(recorder.stop_recording())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.camera_recorders.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=False)


# Global instance
_recording_service = None

async def initialize_async_recording_service(config: Dict[str, Any]) -> AsyncRecordingService:
    """Initialize the async recording service."""
    global _recording_service
    
    if _recording_service is None:
        _recording_service = AsyncRecordingService(config)
    
    return _recording_service

def get_async_recording_service() -> Optional[AsyncRecordingService]:
    """Get the current async recording service instance."""
    return _recording_service
