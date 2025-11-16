#!/usr/bin/env python3
"""
Test face detection on an image
"""

import cv2
import numpy as np
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/husain/alrazy/webcam-app')

from deepface import DeepFace

def test_face_detection(image_path):
    """Test face detection on a single image"""

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return

    print(f"✅ Loaded image: {image.shape}")

    # Test basic face detection
    print("🔍 Testing basic face detection with DeepFace...")
    try:
        faces = DeepFace.extract_faces(
            img_path=image,
            detector_backend="retinaface",
            enforce_detection=False,
            align=True
        )
        print(f"✅ Detected {len(faces)} faces")
        for i, face in enumerate(faces):
            confidence = face.get("confidence", 0)
            print(f"  Face {i+1}: confidence={confidence:.3f}")
    except Exception as e:
        print(f"❌ Face detection failed: {e}")

    # Test embedding extraction
    print("🔍 Testing embedding extraction...")
    try:
        result = DeepFace.represent(
            img_path=image,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=False
        )
        print(f"Result type: {type(result)}")
        if isinstance(result, list) and len(result) > 0:
            print(f"✅ Extracted {len(result)} embeddings")
            embedding = result[0]
            print(f"  First embedding type: {type(embedding)}")
            if isinstance(embedding, list):
                print(f"  First embedding length: {len(embedding)}")
            elif isinstance(embedding, np.ndarray):
                print(f"  First embedding shape: {embedding.shape}")
            else:
                print(f"  First embedding: {embedding}")
        else:
            print("❌ No embeddings extracted")
            print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Embedding extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    image_path = "/home/husain/alrazy/webcam-app/webcam-capture-1.jpg"
    test_face_detection(image_path)