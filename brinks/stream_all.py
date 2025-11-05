#!/usr/bin/env python3
"""
Production Camera Streaming - Simplified Direct Approach
Uses FFmpeg MJPEG with robust frame extraction
"""
import subprocess
import sys
import time
import requests
import threading
import io

def stream_camera(camera_id, rtsp_url):
    """Stream camera with direct JPEG extraction from MJPEG"""
    backend = "http://localhost:8000/ingest"
    
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-f', 'mjpeg',
        '-q:v', '5',
        'pipe:1'
    ]
    
    print(f"[{camera_id}] Starting...")
    sys.stdout.flush()
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=256*1024)
        print(f"[{camera_id}] ✅ FFmpeg PID {proc.pid}")
        sys.stdout.flush()
        
        buffer = b''
        frame_count = 0
        last_report = time.time()
        
        while True:
            try:
                # Read one chunk
                chunk = proc.stdout.read(32768)
                if not chunk:
                    print(f"[{camera_id}] ⚠️  Stream ended")
                    break
                
                buffer += chunk
                
                # Extract JPEG frames from buffer
                while True:
                    # Find JPEG start marker
                    start_idx = buffer.find(b'\xff\xd8')
                    if start_idx == -1:
                        # Trim old data to avoid huge buffers
                        if len(buffer) > 10000:
                            buffer = buffer[-5000:]
                        break
                    
                    # Skip to start marker
                    if start_idx > 0:
                        buffer = buffer[start_idx:]
                    
                    # Find JPEG end marker
                    end_idx = buffer.find(b'\xff\xd9', 2)
                    if end_idx == -1:
                        # Incomplete frame, need more data
                        if len(buffer) > 1000000:
                            buffer = b''
                        break
                    
                    # Extract complete JPEG frame
                    jpeg_data = buffer[:end_idx + 2]
                    buffer = buffer[end_idx + 2:]
                    
                    # Validate frame size
                    if len(jpeg_data) < 100:
                        continue
                    
                    # Send to backend
                    try:
                        r = requests.post(
                            backend,
                            files={'file': ('frame.jpg', jpeg_data, 'image/jpeg')},
                            params={'camera_id': camera_id, 'room_id': 'room_safe'},
                            timeout=3
                        )
                        
                        if r.status_code == 200:
                            frame_count += 1
                            # Report every 50 frames
                            if frame_count == 1 or frame_count % 50 == 0:
                                now = time.time()
                                if frame_count > 1:
                                    fps = 50 / (now - last_report)
                                    print(f"[{camera_id}] ✅ {frame_count} frames ({fps:.1f} fps)")
                                else:
                                    print(f"[{camera_id}] ✅ First frame sent!")
                                sys.stdout.flush()
                                last_report = now
                    
                    except requests.Timeout:
                        pass
                    except Exception as e:
                        pass
                    
                    except requests.Timeout:
                        error_count += 1
                    except Exception as e:
                        error_count += 1
                        if error_count == 1:
                            print(f"[{camera_id}] ⚠️  Send error: {type(e).__name__}")
            
            except Exception as e:
                print(f"[{camera_id}] ❌ Read error: {e}")
                break
    
    except Exception as e:
        print(f"[{camera_id}] ❌ Startup error: {e}")
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
        print(f"[{camera_id}] 🔌 Stopped ({frame_count} frames sent)")

# Check backend
try:
    r = requests.get('http://localhost:8000/health', timeout=2)
    if r.status_code != 200:
        print("❌ Backend not responding")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot reach backend: {e}")
    sys.exit(1)

print("✅ Backend OK\n")

# Start all cameras in threads
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

print("🚀 All cameras streaming...\n")

# Keep alive
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    sys.exit(0)
