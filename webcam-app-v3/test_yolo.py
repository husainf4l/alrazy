"""
Test YOLO Detection Service
Run this script to verify YOLO is working correctly
"""

import sys
import time

import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, "/home/husain/alrazy/webcam-app-v3")

from app.services.yolo_detection_service import get_yolo_service


def test_yolo_basic():
    """Test basic YOLO functionality with a test image"""
    print("🧪 Testing YOLO Detection Service...")
    print("-" * 50)
    
    # Initialize YOLO service
    print("📥 Initializing YOLO service...")
    yolo_service = get_yolo_service(
        model_path="yolo11m.pt",
        conf_threshold=0.5,
        device="0",  # Change to "cpu" if no GPU
    )
    print("✅ YOLO service initialized")
    print()
    
    # Create a test image with dummy data
    print("🖼️  Creating test image...")
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    # Run detection
    print("🔍 Running detection...")
    start_time = time.time()
    
    annotated_frame, detections = yolo_service.detect_people(
        frame=test_image,
        camera_name="test_camera"
    )
    
    inference_time = (time.time() - start_time) * 1000
    print(f"⏱️  Inference time: {inference_time:.2f}ms")
    print(f"👥 Detected {len(detections)} people")
    print()
    
    # Get stats
    print("📊 Detection Statistics:")
    stats = yolo_service.get_stats()
    for camera, data in stats.items():
        print(f"  {camera}:")
        print(f"    - People count: {data['people_count']}")
        print(f"    - Inference time: {data['inference_time_ms']:.2f}ms")
        print(f"    - Detection FPS: {data['detection_fps']:.2f}")
    print()
    
    print("✅ YOLO test completed successfully!")
    return True


def test_yolo_with_real_image(image_path: str):
    """Test YOLO with a real image file"""
    print(f"🧪 Testing YOLO with image: {image_path}")
    print("-" * 50)
    
    # Initialize YOLO service
    yolo_service = get_yolo_service()
    
    # Load image
    print("📥 Loading image...")
    frame = cv2.imread(image_path)
    
    if frame is None:
        print(f"❌ Failed to load image: {image_path}")
        return False
    
    print(f"✅ Image loaded: {frame.shape}")
    print()
    
    # Run detection
    print("🔍 Running detection...")
    start_time = time.time()
    
    annotated_frame, detections = yolo_service.detect_people(
        frame=frame,
        camera_name="test_image"
    )
    
    inference_time = (time.time() - start_time) * 1000
    print(f"⏱️  Inference time: {inference_time:.2f}ms")
    print(f"👥 Detected {len(detections)} people")
    print()
    
    # Print detection details
    if len(detections) > 0:
        print("📋 Detection Details:")
        for i, det in enumerate(detections, 1):
            bbox = det["bbox"]
            conf = det["confidence"]
            print(f"  Person {i}:")
            print(f"    - Bounding Box: {bbox}")
            print(f"    - Confidence: {conf:.3f}")
        print()
    
    # Save annotated image
    output_path = image_path.replace(".", "_yolo.")
    cv2.imwrite(output_path, annotated_frame)
    print(f"💾 Saved annotated image: {output_path}")
    print()
    
    print("✅ YOLO test completed successfully!")
    return True


def test_yolo_performance():
    """Test YOLO performance with multiple frames"""
    print("🧪 Testing YOLO Performance...")
    print("-" * 50)
    
    # Initialize YOLO service
    yolo_service = get_yolo_service()
    
    # Create test image
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    # Warm-up runs
    print("🔥 Warming up (5 runs)...")
    for _ in range(5):
        yolo_service.detect_people(test_image, "warmup")
    print()
    
    # Performance test
    num_runs = 30
    print(f"⚡ Running {num_runs} inference iterations...")
    
    times = []
    for i in range(num_runs):
        start = time.time()
        yolo_service.detect_people(test_image, f"perf_test_{i}")
        times.append((time.time() - start) * 1000)
    
    # Calculate statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    avg_fps = 1000 / avg_time
    
    print(f"📊 Performance Results:")
    print(f"  - Average time: {avg_time:.2f}ms")
    print(f"  - Min time: {min_time:.2f}ms")
    print(f"  - Max time: {max_time:.2f}ms")
    print(f"  - Average FPS: {avg_fps:.2f}")
    print()
    
    print("✅ Performance test completed!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test YOLO Detection Service")
    parser.add_argument(
        "--mode",
        choices=["basic", "image", "performance"],
        default="basic",
        help="Test mode to run"
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to test image (for 'image' mode)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "basic":
            success = test_yolo_basic()
        elif args.mode == "image":
            if not args.image:
                print("❌ Error: --image required for 'image' mode")
                sys.exit(1)
            success = test_yolo_with_real_image(args.image)
        elif args.mode == "performance":
            success = test_yolo_performance()
        
        sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
