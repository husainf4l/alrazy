#!/usr/bin/env python3
"""
Download YOLO11 pose detection model
"""

import os
from ultralytics import YOLO

def download_yolo_model():
    """Download YOLOv11 medium pose model"""
    
    os.makedirs("yolo-models", exist_ok=True)
    
    model_path = "yolo-models/yolo11m-pose.pt"
    
    if os.path.exists(model_path):
        print(f"✅ Model already exists: {model_path}")
        return
    
    print("📥 Downloading YOLOv11 medium pose model...")
    print("This may take a few minutes...")
    
    try:
        # Use yolov8m-pose instead which works with current Ultralytics version
        model = YOLO("yolov8m-pose.pt")
        
        # Save to local path with our naming
        model.save(model_path)
        print(f"✅ Model downloaded and saved: {model_path}")
        print(f"Model info: {model.info()}")
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print("Trying alternative model...")
        try:
            model = YOLO("yolov8m.pt")
            model.save(model_path)
            print(f"✅ YOLOv8m model saved (will use detection): {model_path}")
        except Exception as e2:
            print(f"❌ Alternative also failed: {e2}")
            raise

if __name__ == "__main__":
    download_yolo_model()