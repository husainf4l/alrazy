#!/usr/bin/env python3
"""
RTMP to JPEG Stream Converter for Phone Camera #5
Receives RTMP stream from Larix Broadcaster and forwards frames to backend ingest
"""

import subprocess
import sys
import threading
import requests
import time
import cv2
import numpy as np
import argparse
from datetime import datetime

class RTMPReceiver:
    def __init__(self, rtmp_url, camera_id="camera5", backend_url="http://localhost:8000"):
        self.rtmp_url = rtmp_url
        self.camera_id = camera_id
        self.backend_url = backend_url
        self.room_id = "room_safe"
        self.process = None
        self.running = False
        self.frame_count = 0
        self.error_count = 0
        
    def start(self):
        """Start RTMP receiver process"""
        print(f"🎬 Starting RTMP receiver for {self.camera_id}")
        print(f"📍 Listening on: rtmp://0.0.0.0:1935/live/{self.camera_id}")
        print(f"🔄 Forwarding to: {self.backend_url}/ingest?camera_id={self.camera_id}")
        
        self.running = True
        
        # FFmpeg command to listen as RTMP server and output JPEG frames
        # Using -listen 1 to listen for RTMP connections
        ffmpeg_cmd = [
            'ffmpeg',
            '-listen', '1',  # Listen for incoming RTMP connections
            '-i', f'rtmp://0.0.0.0:1935/live/{self.camera_id}',  # Listen on this URL
            '-c:v', 'mjpeg',  # Output codec: Motion JPEG
            '-q:v', '2',  # Quality (1-31, lower is better, 2 is high quality)
            '-f', 'image2pipe',  # Output format: image pipe
            '-'  # Output to stdout
        ]
        
        try:
            print(f"📡 FFmpeg command: {' '.join(ffmpeg_cmd)}")
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )
            
            # Start frame processing thread
            threading.Thread(target=self._process_frames, daemon=True).start()
            
            # Monitor stderr for FFmpeg logs
            threading.Thread(target=self._monitor_ffmpeg_logs, daemon=True).start()
            
            print("✅ RTMP receiver started successfully")
            
        except Exception as e:
            print(f"❌ Failed to start FFmpeg: {e}")
            self.running = False
            raise
    
    def _process_frames(self):
        """Process frames from FFmpeg pipe"""
        print("🎥 Frame processor started")
        
        JPEG_START = bytes([0xFF, 0xD8])  # JPEG SOI marker
        JPEG_END = bytes([0xFF, 0xD9])    # JPEG EOI marker
        
        buffer = b""
        
        try:
            while self.running and self.process:
                chunk = self.process.stdout.read(4096)
                
                if not chunk:
                    print("⚠️  No more frames from RTMP stream")
                    break
                
                buffer += chunk
                
                # Look for complete JPEG frames
                while True:
                    start_idx = buffer.find(JPEG_START)
                    if start_idx == -1:
                        break
                    
                    # Remove data before JPEG start
                    buffer = buffer[start_idx:]
                    
                    end_idx = buffer.find(JPEG_END)
                    if end_idx == -1:
                        break
                    
                    # Extract JPEG frame
                    end_idx += 2
                    jpeg_frame = buffer[:end_idx]
                    buffer = buffer[end_idx:]
                    
                    # Send frame to backend
                    self._send_frame(jpeg_frame)
        
        except Exception as e:
            print(f"❌ Frame processing error: {e}")
            self.error_count += 1
        finally:
            print("⏹️  Frame processor stopped")
    
    def _send_frame(self, jpeg_frame):
        """Send frame to backend ingest endpoint"""
        try:
            files = {'file': ('frame.jpg', jpeg_frame, 'image/jpeg')}
            params = {
                'camera_id': self.camera_id,
                'room_id': self.room_id
            }
            
            response = requests.post(
                f"{self.backend_url}/ingest",
                files=files,
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                self.frame_count += 1
                if self.frame_count % 30 == 0:  # Log every 30 frames
                    print(f"✅ Sent {self.frame_count} frames | "
                          f"Camera: {self.camera_id} | "
                          f"Backend: {response.status_code}")
            else:
                print(f"⚠️  Backend returned {response.status_code}")
                self.error_count += 1
        
        except requests.exceptions.Timeout:
            print(f"⏱️  Request timeout - backend may be slow")
            self.error_count += 1
        except Exception as e:
            print(f"❌ Error sending frame: {e}")
            self.error_count += 1
    
    def _monitor_ffmpeg_logs(self):
        """Monitor FFmpeg stderr for logs"""
        try:
            while self.running and self.process:
                line = self.process.stderr.readline()
                if not line:
                    break
                
                line_str = line.decode('utf-8', errors='ignore').strip()
                
                if line_str:
                    if 'error' in line_str.lower() or 'failed' in line_str.lower():
                        print(f"⚠️  FFmpeg: {line_str}")
                    elif 'Stream' in line_str or 'Duration' in line_str:
                        print(f"📊 {line_str}")
        
        except Exception as e:
            print(f"Monitor error: {e}")
    
    def stop(self):
        """Stop RTMP receiver"""
        print(f"🛑 Stopping RTMP receiver...")
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
        
        print(f"📊 Final stats: {self.frame_count} frames sent, {self.error_count} errors")
        print("✅ RTMP receiver stopped")


def main():
    parser = argparse.ArgumentParser(
        description='RTMP to SafeRoom Backend Converter'
    )
    parser.add_argument(
        '--rtmp-url',
        default='rtmp://0.0.0.0:1935/live/camera5',
        help='RTMP URL to listen on (default: rtmp://0.0.0.0:1935/live/camera5)'
    )
    parser.add_argument(
        '--camera-id',
        default='camera5',
        help='Camera ID for backend (default: camera5)'
    )
    parser.add_argument(
        '--backend-url',
        default='http://localhost:8000',
        help='Backend API URL (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--room-id',
        default='room_safe',
        help='Room ID for backend (default: room_safe)'
    )
    
    args = parser.parse_args()
    
    # Convert RTMP listen URL to full connection URL
    # For local listening, use the full URL
    rtmp_url = args.rtmp_url
    
    receiver = RTMPReceiver(
        rtmp_url=rtmp_url,
        camera_id=args.camera_id,
        backend_url=args.backend_url
    )
    
    try:
        receiver.start()
        
        print("\n✅ RTMP Receiver is running!")
        print(f"📱 Phone should stream to: {rtmp_url}")
        print("🛑 Press Ctrl+C to stop\n")
        
        # Keep process running
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutdown signal received")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        receiver.stop()


if __name__ == '__main__':
    main()
