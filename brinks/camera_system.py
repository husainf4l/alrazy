#!/usr/bin/env python3
"""
Brinks Camera System
Main camera monitoring and management system
"""

import cv2
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Optional

class CameraConfig:
    """Camera configuration class"""
    
    # Camera RTSP URLs from notes.md
    CAMERAS = {
        'room1': {
            'name': 'Room1',
            'main_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/101',
            'sub_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/102',
            'location': 'room1'
        },
        'room2': {
            'name': 'Room2',
            'main_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/201',
            'sub_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/202',
            'location': 'room2'
        },
        'room3': {
            'name': 'Room3',
            'main_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/301',
            'sub_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/302',
            'location': 'room3'
        },
        'room4': {
            'name': 'Room4',
            'main_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/401',
            'sub_stream': 'rtsp://admin:tt55oo77@192.168.1.186:554/Streaming/Channels/402',
            'location': 'room4'
        }
    }
    
    # System settings
    USE_SUB_STREAMS = True  # Use lower quality streams for better performance
    CAMERA_IP = '192.168.1.186'
    RTSP_PORT = 554
    
    # Streaming Configuration (Professional 2K Video)
    STREAMING_CONFIG = {
        'enabled': True,
        'codec': 'H.265',  # H.265 (HEVC) for better compression
        'resolution': (2560, 1440),  # 2K resolution
        'fps': 30,  # 25-30 fps
        'bitrate_kbps': 6144,  # 6 Mbps (4-8 Mbps range)
        'quality': 'high',  # high, medium, low
    }
    
    # FFmpeg/OpenCV Codec Mapping
    CODEC_PARAMS = {
        'H.265': {
            'fourcc': 'H265',  # OpenCV fourcc code for HEVC
            'preset': 'medium',  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
            'crf': 23,  # 0-51 (lower = better quality, default 28)
        },
        'H.264': {
            'fourcc': 'H264',
            'preset': 'medium',
            'crf': 23,
        }
    }

class Camera:
    """Individual camera handler"""
    
    def __init__(self, camera_id: str, config: Dict):
        self.camera_id = camera_id
        self.config = config
        self.name = config['name']
        self.is_connected = False
        self.cap = None
        self.thread = None
        self.running = False
        
        # Use sub-stream by default for better performance
        self.stream_url = config['sub_stream'] if CameraConfig.USE_SUB_STREAMS else config['main_stream']
        
        # Streaming configuration
        self.streaming_enabled = CameraConfig.STREAMING_CONFIG['enabled']
        self.codec = CameraConfig.STREAMING_CONFIG['codec']
        self.resolution = CameraConfig.STREAMING_CONFIG['resolution']
        self.fps = CameraConfig.STREAMING_CONFIG['fps']
        self.bitrate_kbps = CameraConfig.STREAMING_CONFIG['bitrate_kbps']
        
    def get_streaming_config(self) -> Dict:
        """Return streaming configuration"""
        return {
            'enabled': self.streaming_enabled,
            'codec': self.codec,
            'resolution': self.resolution,
            'fps': self.fps,
            'bitrate_kbps': self.bitrate_kbps,
            'bitrate_mbps': self.bitrate_kbps / 1024,
        }
        
    def connect(self) -> bool:
        """Connect to camera stream"""
        try:
            self.cap = cv2.VideoCapture(self.stream_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for real-time
            
            # Test connection
            ret, frame = self.cap.read()
            if ret:
                self.is_connected = True
                print(f"✅ {self.name} connected successfully")
                return True
            else:
                print(f"❌ {self.name} failed to connect")
                return False
                
        except Exception as e:
            print(f"❌ {self.name} connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from camera"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        if self.cap:
            self.cap.release()
        self.is_connected = False
        print(f"🔌 {self.name} disconnected")
    
    def start_monitoring(self):
        """Start camera monitoring in separate thread"""
        if not self.is_connected:
            if not self.connect():
                return False
                
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running and self.is_connected:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # Process frame here (motion detection, recording, etc.)
                    self._process_frame(frame)
                else:
                    print(f"⚠️  {self.name} lost connection")
                    break
                    
            except Exception as e:
                print(f"❌ {self.name} monitoring error: {e}")
                break
                
        self.is_connected = False
    
    def _process_frame(self, frame):
        """Process individual frame - override this for specific functionality"""
        # Placeholder for frame processing
        # Add motion detection, face recognition, recording, etc. here
        pass
    
    def get_current_frame(self):
        """Get current frame from camera"""
        if self.is_connected and self.cap:
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

class CameraSystem:
    """Main camera system manager"""
    
    def __init__(self):
        self.cameras = {}
        self.system_running = False
        
    def initialize_cameras(self):
        """Initialize all cameras"""
        print("🚀 Initializing Brinks Camera System...")
        
        for camera_id, config in CameraConfig.CAMERAS.items():
            camera = Camera(camera_id, config)
            self.cameras[camera_id] = camera
            
        print(f"📹 Initialized {len(self.cameras)} cameras")
    
    def test_all_connections(self):
        """Test connection to all cameras"""
        print("\n🔍 Testing camera connections...")
        
        results = {}
        for camera_id, camera in self.cameras.items():
            results[camera_id] = camera.connect()
            if results[camera_id]:
                camera.disconnect()  # Disconnect after test
                
        return results
    
    def start_system(self):
        """Start the entire camera system"""
        print("\n🎬 Starting camera system...")
        
        success_count = 0
        for camera_id, camera in self.cameras.items():
            if camera.start_monitoring():
                success_count += 1
                
        self.system_running = success_count > 0
        print(f"✅ Started {success_count}/{len(self.cameras)} cameras")
        
        return self.system_running
    
    def stop_system(self):
        """Stop the entire camera system"""
        print("\n🛑 Stopping camera system...")
        
        for camera in self.cameras.values():
            camera.disconnect()
            
        self.system_running = False
        print("✅ Camera system stopped")
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        status = {
            'system_running': self.system_running,
            'timestamp': datetime.now().isoformat(),
            'cameras': {}
        }
        
        for camera_id, camera in self.cameras.items():
            status['cameras'][camera_id] = {
                'name': camera.name,
                'connected': camera.is_connected,
                'running': camera.running,
                'stream_url': camera.stream_url
            }
            
        return status
    
    def display_live_feed(self, camera_id: str = None):
        """Display live feed from camera(s)"""
        if camera_id:
            # Display single camera
            if camera_id in self.cameras:
                self._display_single_camera(self.cameras[camera_id])
            else:
                print(f"❌ Camera {camera_id} not found")
        else:
            # Display all cameras
            self._display_all_cameras()
    
    def _display_single_camera(self, camera: Camera):
        """Display single camera feed"""
        print(f"📺 Displaying {camera.name} - Press 'q' to quit")
        
        while True:
            frame = camera.get_current_frame()
            if frame is not None:
                cv2.imshow(f"{camera.name}", frame)
                
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cv2.destroyAllWindows()
    
    def _display_all_cameras(self):
        """Display all camera feeds in a grid"""
        print("📺 Displaying all cameras - Press 'q' to quit")
        
        while True:
            frames = {}
            for camera_id, camera in self.cameras.items():
                frame = camera.get_current_frame()
                if frame is not None:
                    # Resize frame for grid display
                    frame = cv2.resize(frame, (320, 240))
                    frames[camera_id] = frame
            
            if frames:
                # Create 2x2 grid
                if len(frames) >= 4:
                    top_row = cv2.hconcat([frames.get('room1', frames[list(frames.keys())[0]]), 
                                         frames.get('room2', frames[list(frames.keys())[1]])])
                    bottom_row = cv2.hconcat([frames.get('room3', frames[list(frames.keys())[2]]), 
                                            frames.get('room4', frames[list(frames.keys())[3]])])
                    grid = cv2.vconcat([top_row, bottom_row])
                    cv2.imshow("All Cameras", grid)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cv2.destroyAllWindows()

def main():
    """Main function to run the camera system"""
    system = CameraSystem()
    
    try:
        # Initialize cameras
        system.initialize_cameras()
        
        # Test connections
        results = system.test_all_connections()
        
        # Display test results
        print("\n📊 Connection Test Results:")
        for camera_id, success in results.items():
            status = "✅ Connected" if success else "❌ Failed"
            camera_name = CameraConfig.CAMERAS[camera_id]['name']
            print(f"  {camera_name}: {status}")
        
        # Start system if any cameras are working
        working_cameras = sum(results.values())
        if working_cameras > 0:
            print(f"\n🎯 {working_cameras} cameras are working!")
            
            # Uncomment to start the system
            # system.start_system()
            # system.display_live_feed()  # Display all cameras
            
        else:
            print("\n❌ No cameras are working. Please check connections.")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    finally:
        system.stop_system()

if __name__ == "__main__":
    main()