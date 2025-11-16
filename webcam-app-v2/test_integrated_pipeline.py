#!/usr/bin/env python3
"""
Test the complete integrated pipeline:
YOLO → Face Detection → ArcFace Embedding
"""

import cv2
import numpy as np
import sys
import os
import logging

os.environ["CUDA_VISIBLE_DEVICES"] = ""

sys.path.append('/home/husain/alrazy/webcam-app')

from app.services.webcam_processor import WebcamProcessor

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def test_integrated_pipeline(image_path):
    """Test the complete integrated pipeline"""
    
    print("=" * 80)
    print("🎬 INTEGRATED WEBCAM PROCESSING PIPELINE TEST")
    print("=" * 80)
    
    # Load image
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return
    
    print(f"\n📸 Loaded image: {image.shape}")
    
    # Initialize processor
    print("\n🔄 Initializing WebcamProcessor...")
    processor = WebcamProcessor(fps_limit=2)
    
    # Process frame
    print("\n" + "=" * 80)
    print("🚀 PROCESSING FRAME")
    print("=" * 80)
    
    result = processor.process_frame(image)
    
    # Print results
    print("\n" + "=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"\n⏱️  Processing Time: {result['processing_time_ms']:.2f}ms")
    print(f"Frame Size: {result['frame_size']}")
    print(f"Timestamp: {result['timestamp']}")
    
    print(f"\n🔍 YOLO Detections: {len(result['yolo_detections'])} persons")
    for yolo_det in result['yolo_detections']:
        print(f"  Person {yolo_det['person_id']}:")
        print(f"    - Confidence: {yolo_det['yolo_confidence']:.3f}")
        print(f"    - Center: {yolo_det['bbox_center']}")
        print(f"    - Area: {yolo_det['area_percentage']:.1f}%")
    
    print(f"\n😊 Face Detections: {len(result['face_detections'])} faces")
    for face_det in result['face_detections']:
        print(f"  Person {face_det['person_id']}, Face {face_det['face_id']}:")
        print(f"    - Confidence: {face_det['face_confidence']:.3f}")
        print(f"    - Center: {face_det['face_center']}")
    
    print(f"\n✓ Verified Persons (ArcFace): {len(result['recognized_persons'])}")
    for person in result['recognized_persons']:
        print(f"  Person {person['person_id']}, Face {person['face_id']}:")
        print(f"    - Embedding: {person['embedding_length']}-dim vector")
        print(f"    - Location: {person['location']}")
        print(f"    - Status: {person['verification_status']}")
    
    print("\n" + "=" * 80)
    print("📝 DETAILED LOGS")
    print("=" * 80)
    for log in result['log_messages']:
        print(log)
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    image_path = "/home/husain/alrazy/webcam-app/webcam-capture-1.jpg"
    test_integrated_pipeline(image_path)