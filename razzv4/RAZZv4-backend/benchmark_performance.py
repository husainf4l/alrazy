#!/usr/bin/env python3
"""
Performance profiling script to identify bottlenecks in tracking pipeline
"""

import time
import numpy as np
from services.yolo_service import YOLOService
from services.tracking_service import TrackingService
import supervision as sv

def benchmark_pipeline():
    """Benchmark the entire tracking pipeline"""
    print("\n" + "="*80)
    print("TRACKING PIPELINE PERFORMANCE BENCHMARK")
    print("="*80)
    
    # Initialize services
    print("\n1. Initializing services...")
    start = time.time()
    yolo = YOLOService()
    tracker = TrackingService()
    print(f"   ✅ Initialization: {(time.time() - start)*1000:.1f}ms")
    
    # Create test frames (1080p)
    print("\n2. Creating test frames...")
    frames = []
    for i in range(10):
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        frames.append(frame)
    print(f"   ✅ Created 10 test frames (1920x1080)")
    
    # Benchmark YOLO detection
    print("\n3. Benchmarking YOLO detection...")
    yolo_times = []
    for i, frame in enumerate(frames):
        start = time.time()
        detections_sv = yolo.detect_people(frame)
        duration = (time.time() - start) * 1000
        yolo_times.append(duration)
        print(f"   Frame {i+1}: {duration:.1f}ms ({len(detections_sv)} detections)")
    
    print(f"\n   YOLO Performance:")
    print(f"   Average: {np.mean(yolo_times):.1f}ms")
    print(f"   Min: {np.min(yolo_times):.1f}ms")
    print(f"   Max: {np.max(yolo_times):.1f}ms")
    print(f"   FPS: {1000/np.mean(yolo_times):.1f}")
    
    # Benchmark tracking (with detections)
    print("\n4. Benchmarking tracking with 3 simulated people...")
    
    # Create fake detections (3 people)
    fake_detections = sv.Detections(
        xyxy=np.array([
            [100, 100, 300, 500],  # Person 1
            [500, 100, 700, 500],  # Person 2
            [1000, 100, 1200, 500],  # Person 3
        ], dtype=np.float32),
        class_id=np.array([0, 0, 0]),
        confidence=np.array([0.9, 0.85, 0.88])
    )
    
    tracking_times = []
    for i, frame in enumerate(frames):
        start = time.time()
        result = tracker.track_people(camera_id=10, frame=frame, detections_sv=fake_detections)
        duration = (time.time() - start) * 1000
        tracking_times.append(duration)
        print(f"   Frame {i+1}: {duration:.1f}ms ({result['count']} people tracked)")
    
    print(f"\n   Tracking Performance (3 people):")
    print(f"   Average: {np.mean(tracking_times):.1f}ms")
    print(f"   Min: {np.min(tracking_times):.1f}ms")
    print(f"   Max: {np.max(tracking_times):.1f}ms")
    print(f"   FPS: {1000/np.mean(tracking_times):.1f}")
    
    # Benchmark combined pipeline
    print("\n5. Benchmarking COMBINED pipeline (YOLO + Tracking)...")
    
    combined_times = []
    for i, frame in enumerate(frames):
        start = time.time()
        
        # YOLO detection
        detections_sv = yolo.detect_people(frame)
        
        # Tracking
        result = tracker.track_people(camera_id=10, frame=frame, detections_sv=detections_sv)
        
        duration = (time.time() - start) * 1000
        combined_times.append(duration)
        print(f"   Frame {i+1}: {duration:.1f}ms ({result['count']} people)")
    
    print(f"\n   Combined Performance:")
    print(f"   Average: {np.mean(combined_times):.1f}ms")
    print(f"   Min: {np.min(combined_times):.1f}ms")
    print(f"   Max: {np.max(combined_times):.1f}ms")
    print(f"   FPS: {1000/np.mean(combined_times):.1f}")
    
    # Analysis
    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS")
    print("="*80)
    
    total_time = np.mean(yolo_times) + np.mean(tracking_times)
    yolo_percent = (np.mean(yolo_times) / total_time) * 100
    tracking_percent = (np.mean(tracking_times) / total_time) * 100
    
    print(f"\nTime breakdown:")
    print(f"  YOLO detection:     {np.mean(yolo_times):6.1f}ms ({yolo_percent:5.1f}%)")
    print(f"  Tracking:           {np.mean(tracking_times):6.1f}ms ({tracking_percent:5.1f}%)")
    print(f"  Total:              {total_time:6.1f}ms")
    print(f"  Expected FPS:       {1000/total_time:6.1f}")
    
    # Recommendations
    print(f"\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if np.mean(combined_times) > 66:  # Below 15 FPS
        print("⚠️  System is running slower than 15 FPS target")
        if np.mean(yolo_times) > 50:
            print("   - YOLO detection is slow (>50ms)")
            print("   - Consider: Smaller YOLO model (yolo11n instead of yolo11m)")
            print("   - Consider: Lower resolution input")
            print("   - Consider: GPU acceleration")
        if np.mean(tracking_times) > 20:
            print("   - Tracking is slow (>20ms)")
            print("   - Consider: Reducing Re-ID extraction frequency")
            print("   - Consider: Batch Re-ID processing")
    else:
        print(f"✅ System performance is good ({1000/np.mean(combined_times):.1f} FPS)")
        print(f"   Target is 15 FPS for YOLO, 30 FPS for tracking")

if __name__ == "__main__":
    benchmark_pipeline()
