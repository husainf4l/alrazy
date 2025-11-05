#!/usr/bin/env python3
"""
High-performance camera streaming with live debugging
- Reduced resolution for faster processing
- Real-time performance metrics
- Detailed error logging
"""
import subprocess
import sys
import time
import requests
import threading
from datetime import datetime

def stream_camera(camera_id, rtsp_url):
    """Stream with performance monitoring"""
    backend = "http://localhost:8000/ingest"
    
    # Balanced: 320x180 @ 10fps for performance
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-vf', 'scale=320:180',
        '-f', 'mjpeg',
        '-q:v', '7',
        '-r', '10',
        'pipe:1'
    ]
    
    print(f"[{camera_id}] Starting stream (320x180@10fps)...")
    sys.stdout.flush()
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=512*1024)
        print(f"[{camera_id}] ✅ FFmpeg PID {proc.pid}")
        sys.stdout.flush()
        
        buffer = b''
        frame_count = 0
        last_report = time.time()
        start_time = time.time()
        bytes_received = 0
        post_times = []
        
        while True:
            try:
                chunk = proc.stdout.read(65536)  # Larger chunks
                if not chunk:
                    print(f"[{camera_id}] Stream ended")
                    sys.stdout.flush()
                    break
                
                buffer += chunk
                bytes_received += len(chunk)
                
                # Extract frames
                while True:
                    start_idx = buffer.find(b'\xff\xd8')
                    if start_idx == -1:
                        if len(buffer) > 50000:
                            buffer = buffer[-10000:]
                        break
                    
                    if start_idx > 0:
                        buffer = buffer[start_idx:]
                    
                    end_idx = buffer.find(b'\xff\xd9', 2)
                    if end_idx == -1:
                        if len(buffer) > 2000000:
                            buffer = b''
                        break
                    
                    jpeg_data = buffer[:end_idx + 2]
                    buffer = buffer[end_idx + 2:]
                    
                    if len(jpeg_data) < 100:
                        continue
                    
                    # Send with timing
                    post_start = time.time()
                    try:
                        r = requests.post(
                            backend,
                            files={'file': ('frame.jpg', jpeg_data, 'image/jpeg')},
                            params={'camera_id': camera_id, 'room_id': 'room_safe'},
                            timeout=5
                        )
                        post_time = time.time() - post_start
                        post_times.append(post_time)
                        
                        if r.status_code == 200:
                            frame_count += 1
                            
                            # Report every 25 frames with detailed stats
                            if frame_count == 1 or frame_count % 25 == 0:
                                now = time.time()
                                elapsed = now - start_time
                                fps = frame_count / elapsed
                                avg_post = sum(post_times[-25:]) / min(len(post_times), 25)
                                bandwidth = (bytes_received / 1024 / 1024) / elapsed  # MB/s
                                
                                print(f"[{camera_id}] Frame #{frame_count} | "
                                      f"FPS: {fps:.1f} | "
                                      f"POST: {avg_post*1000:.0f}ms | "
                                      f"BW: {bandwidth:.2f}MB/s | "
                                      f"JPEG: {len(jpeg_data)/1024:.1f}KB")
                                sys.stdout.flush()
                        else:
                            if frame_count % 10 == 0:
                                print(f"[{camera_id}] HTTP {r.status_code}")
                                sys.stdout.flush()
                    
                    except requests.Timeout:
                        print(f"[{camera_id}] ⚠️ Timeout on frame {frame_count}")
                        sys.stdout.flush()
                    except Exception as e:
                        if frame_count % 10 == 0:
                            print(f"[{camera_id}] ⚠️ {type(e).__name__}")
                            sys.stdout.flush()
            
            except Exception as e:
                print(f"[{camera_id}] ❌ Read error: {e}")
                sys.stdout.flush()
                break
    
    except Exception as e:
        print(f"[{camera_id}] ❌ Startup: {e}")
        sys.stdout.flush()
    finally:
        if 'proc' in locals():
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                try:
                    proc.kill()
                except:
                    pass
        
        if frame_count > 0:
            elapsed = time.time() - start_time
            print(f"[{camera_id}] 🏁 Stopped: {frame_count} frames in {elapsed:.1f}s ({frame_count/elapsed:.1f} fps)")
        else:
            print(f"[{camera_id}] 🏁 Stopped: No frames sent")
        sys.stdout.flush()

# Check backend
try:
    r = requests.get('http://localhost:8000/health', timeout=2)
    if r.status_code != 200:
        print("❌ Backend not responding")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot reach backend: {e}")
    sys.exit(1)

print("✅ Backend OK")
print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
sys.stdout.flush()

# Start cameras
cameras = {
    'room1': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101',
    'room2': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/201',
    'room3': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/301',
    'room4': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/401',
}

threads = []
for cam_id, url in cameras.items():
    t = threading.Thread(target=stream_camera, args=(cam_id, url), daemon=True)
    t.start()
    threads.append(t)
    time.sleep(0.2)

print("🚀 All cameras starting...\n")
sys.stdout.flush()

# Keep alive with periodic status
try:
    while True:
        time.sleep(30)
        print(f"⏰ [{datetime.now().strftime('%H:%M:%S')}] System running...")
        sys.stdout.flush()
except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    sys.exit(0)
