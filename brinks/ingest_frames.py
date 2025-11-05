#!/usr/bin/env python3
"""
Frame Ingestion Client
Connects to camera system and sends frames to the SafeRoom detection backend
"""

import os
import time
import requests
import cv2
import argparse
from datetime import datetime
import sys

# Add parent directory to path for camera_system import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from camera_system import CameraSystem, CameraConfig

class FrameIngestionClient:
    """Client to ingest camera frames to backend"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", room_id: str = "room_safe"):
        self.backend_url = backend_url
        self.room_id = room_id
        self.ingest_endpoint = f"{backend_url}/ingest"
        self.session = requests.Session()
        self.stats = {
            "frames_sent": 0,
            "errors": 0,
            "start_time": time.time()
        }
    
    def test_backend_connection(self) -> bool:
        """Test connection to backend"""
        try:
            resp = self.session.get(f"{self.backend_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"✅ Backend connected: {self.backend_url}")
                return True
        except Exception as e:
            print(f"❌ Backend connection failed: {e}")
        return False
    
    def send_frame(self, frame: bytes, camera_id: str = "room1") -> bool:
        """Send frame to backend"""
        try:
            files = {'file': ('frame.jpg', frame, 'image/jpeg')}
            params = {'camera_id': camera_id, 'room_id': self.room_id}
            
            resp = self.session.post(
                self.ingest_endpoint,
                files=files,
                params=params,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                self.stats["frames_sent"] += 1
                
                # Print status
                occupancy = data.get("occupancy", 0)
                status = data.get("status", "ok")
                
                if status == "violation":
                    print(f"🚨 VIOLATION: {occupancy} people detected")
                else:
                    print(f"✅ Frame sent - Occupancy: {occupancy}")
                
                return True
            else:
                print(f"❌ Backend error: {resp.status_code}")
                self.stats["errors"] += 1
                return False
        
        except Exception as e:
            print(f"❌ Send error: {e}")
            self.stats["errors"] += 1
            return False
    
    def encode_frame_to_jpeg(self, frame) -> bytes:
        """Encode OpenCV frame to JPEG bytes"""
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ok else b''
    
    def ingest_from_camera(self, camera_system: CameraSystem, camera_id: str = "room1", fps: float = 5.0):
        """Stream frames from camera to backend"""
        camera = camera_system.cameras.get(camera_id)
        
        if not camera:
            print(f"❌ Camera {camera_id} not found")
            return
        
        print(f"🎬 Starting ingestion from {camera.name}...")
        print(f"📤 Sending to: {self.backend_url}")
        print(f"⏱️  FPS: {fps}")
        
        if not camera.connect():
            print(f"❌ Failed to connect to camera")
            return
        
        frame_interval = 1.0 / fps
        last_send = 0
        
        try:
            while True:
                frame = camera.get_current_frame()
                
                if frame is None:
                    print("⚠️  Failed to get frame")
                    time.sleep(0.1)
                    continue
                
                # Rate limiting
                now = time.time()
                if now - last_send < frame_interval:
                    time.sleep(0.01)
                    continue
                
                # Encode and send
                jpeg_data = self.encode_frame_to_jpeg(frame)
                if jpeg_data:
                    self.send_frame(jpeg_data, camera_id)
                    last_send = now
                
                # Print stats every 10 frames
                if self.stats["frames_sent"] % 10 == 0:
                    elapsed = time.time() - self.stats["start_time"]
                    rate = self.stats["frames_sent"] / elapsed if elapsed > 0 else 0
                    print(f"📊 Stats: {self.stats['frames_sent']} sent, "
                          f"{self.stats['errors']} errors, {rate:.1f} fps")
        
        except KeyboardInterrupt:
            print("\n🛑 Ingestion stopped by user")
        finally:
            camera.disconnect()
            self._print_summary()
    
    def ingest_from_video_file(self, video_path: str, camera_id: str = "room1", fps: float = 5.0):
        """Stream frames from video file to backend"""
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return
        
        print(f"🎬 Starting ingestion from video: {video_path}")
        print(f"📤 Sending to: {self.backend_url}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("❌ Failed to open video file")
            return
        
        frame_interval = 1.0 / fps
        last_send = 0
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("✅ Video finished")
                    break
                
                frame_count += 1
                
                # Rate limiting
                now = time.time()
                if now - last_send < frame_interval:
                    time.sleep(0.01)
                    continue
                
                # Encode and send
                jpeg_data = self.encode_frame_to_jpeg(frame)
                if jpeg_data:
                    self.send_frame(jpeg_data, camera_id)
                    last_send = now
        
        except KeyboardInterrupt:
            print("\n🛑 Ingestion stopped by user")
        finally:
            cap.release()
            print(f"📹 Processed {frame_count} frames")
            self._print_summary()
    
    def _print_summary(self):
        """Print ingestion summary"""
        elapsed = time.time() - self.stats["start_time"]
        print(f"\n📊 Ingestion Summary:")
        print(f"  Frames sent: {self.stats['frames_sent']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Duration: {elapsed:.1f}s")
        if self.stats["frames_sent"] > 0:
            print(f"  Average FPS: {self.stats['frames_sent'] / elapsed:.1f}")

def main():
    parser = argparse.ArgumentParser(
        description="Send camera frames to SafeRoom detection backend"
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--camera",
        default="room1",
        help="Camera ID (default: room1)"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=5.0,
        help="Frames per second to send (default: 5)"
    )
    parser.add_argument(
        "--room",
        default="room_safe",
        help="Room ID (default: room_safe)"
    )
    parser.add_argument(
        "--video",
        help="Video file to ingest instead of live camera"
    )
    
    args = parser.parse_args()
    
    # Create ingestion client
    client = FrameIngestionClient(args.backend, args.room)
    
    # Test backend connection
    if not client.test_backend_connection():
        print("❌ Cannot connect to backend. Make sure it's running.")
        return
    
    # Ingest frames
    if args.video:
        # From video file
        client.ingest_from_video_file(args.video, args.camera, args.fps)
    else:
        # From live camera
        camera_system = CameraSystem()
        camera_system.initialize_cameras()
        client.ingest_from_camera(camera_system, args.camera, args.fps)

if __name__ == "__main__":
    main()