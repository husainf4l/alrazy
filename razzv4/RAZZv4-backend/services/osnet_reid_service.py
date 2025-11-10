"""
OSNet Person Re-Identification Service
Uses OSNet model for full-body person embedding extraction
Best practice for cross-camera person tracking
"""

import torch
import torch.nn as nn
import torchvision.transforms as T
import numpy as np
from PIL import Image
import logging
from typing import Optional, Tuple
from pathlib import Path
import cv2

logger = logging.getLogger(__name__)


class OSNetReIDService:
    """
    Person Re-Identification using OSNet
    - Extracts 512-dimensional embeddings from full-body crops
    - Works better than face recognition for person tracking
    - Handles varying poses, occlusion, and viewing angles
    """
    
    def __init__(self, model_name: str = "osnet_x1_0", device: str = "auto"):
        """
        Initialize OSNet Re-ID service
        
        Args:
            model_name: OSNet variant ('osnet_x1_0', 'osnet_x0_75', 'osnet_x0_5')
            device: 'cuda', 'cpu', or 'auto' (auto-detect)
        """
        logger.info(f"Initializing OSNet Re-ID with model: {model_name}")
        
        self.model_name = model_name
        self.device = self._setup_device(device)
        self.model = None
        self.transform = None
        
        try:
            self._load_model()
            logger.info(f"✅ OSNet initialized successfully on {self.device}")
            logger.info(f"   Model: {model_name}")
            logger.info(f"   Output: 512-dimensional embeddings")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OSNet: {e}")
            logger.warning("⚠️  Person Re-ID will be disabled")
            logger.warning("   To enable, install: pip install torchreid")
    
    def _setup_device(self, device: str) -> torch.device:
        """Setup computation device"""
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                logger.info(f"🚀 GPU detected: {torch.cuda.get_device_name(0)}")
            else:
                device = "cpu"
                logger.info("Using CPU for OSNet")
        
        return torch.device(device)
    
    def _load_model(self):
        """Load pre-trained OSNet model"""
        try:
            import torchreid
            
            # Load pre-trained OSNet model
            self.model = torchreid.models.build_model(
                name=self.model_name,
                num_classes=1000,  # Will be ignored (feature extraction mode)
                loss='softmax',
                pretrained=True
            )
            
            # Set to evaluation mode
            self.model.eval()
            self.model.to(self.device)
            
            # Setup image preprocessing
            self.transform = T.Compose([
                T.Resize((256, 128)),  # OSNet input size (height, width)
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
        except ImportError:
            raise ImportError(
                "torchreid not installed. Install with: pip install torchreid"
            )
    
    def is_available(self) -> bool:
        """Check if Re-ID service is available"""
        return self.model is not None
    
    def extract_embedding(self, 
                         frame: np.ndarray, 
                         bbox: Tuple[int, int, int, int],
                         min_size: int = 64) -> Optional[np.ndarray]:
        """
        Extract 512-dim embedding from person bounding box
        
        Args:
            frame: Full frame (BGR format from OpenCV)
            bbox: Person bounding box [x1, y1, x2, y2]
            min_size: Minimum bbox size (pixels) to process
        
        Returns:
            512-dimensional embedding vector (normalized), or None if extraction fails
        """
        if not self.is_available():
            return None
        
        try:
            x1, y1, x2, y2 = bbox
            
            # Validate bbox
            if x2 <= x1 or y2 <= y1:
                return None
            
            width = x2 - x1
            height = y2 - y1
            
            # Skip small bboxes (likely false detections)
            if width < min_size or height < min_size:
                return None
            
            # Crop person region
            height_img, width_img = frame.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(width_img, x2)
            y2 = min(height_img, y2)
            
            person_crop = frame[y1:y2, x1:x2]
            
            if person_crop.size == 0:
                return None
            
            # Convert BGR to RGB
            person_crop_rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(person_crop_rgb)
            
            # Apply transforms
            input_tensor = self.transform(pil_image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(input_batch)
            
            # Convert to numpy and normalize
            embedding = features.cpu().numpy()[0]
            
            # L2 normalization
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting OSNet embedding: {e}")
            return None
    
    def compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            emb1, emb2: Normalized embedding vectors
        
        Returns:
            Similarity score (0-1, where 1 = identical)
        """
        # For normalized vectors, cosine similarity = dot product
        return float(np.dot(emb1, emb2))
    
    def euclidean_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute Euclidean distance between two embeddings
        
        Args:
            emb1, emb2: Embedding vectors
        
        Returns:
            Distance (lower = more similar)
        """
        return float(np.linalg.norm(emb1 - emb2))
    
    def batch_extract_embeddings(self, 
                                 frame: np.ndarray,
                                 bboxes: list) -> list:
        """
        Extract embeddings for multiple persons in batch (faster)
        
        Args:
            frame: Full frame
            bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
        
        Returns:
            List of embeddings (same order as bboxes)
        """
        if not self.is_available():
            return [None] * len(bboxes)
        
        embeddings = []
        
        try:
            # Prepare batch
            batch_images = []
            valid_indices = []
            
            for idx, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = bbox
                
                # Validate and crop
                if x2 <= x1 or y2 <= y1:
                    continue
                
                height_img, width_img = frame.shape[:2]
                x1 = max(0, int(x1))
                y1 = max(0, int(y1))
                x2 = min(width_img, int(x2))
                y2 = min(height_img, int(y2))
                
                person_crop = frame[y1:y2, x1:x2]
                
                if person_crop.size == 0:
                    continue
                
                # Convert and transform
                person_crop_rgb = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(person_crop_rgb)
                input_tensor = self.transform(pil_image)
                
                batch_images.append(input_tensor)
                valid_indices.append(idx)
            
            if not batch_images:
                return [None] * len(bboxes)
            
            # Batch inference
            batch_tensor = torch.stack(batch_images).to(self.device)
            
            with torch.no_grad():
                features = self.model(batch_tensor)
            
            # Normalize embeddings
            features_np = features.cpu().numpy()
            norms = np.linalg.norm(features_np, axis=1, keepdims=True)
            normalized_features = features_np / (norms + 1e-8)
            
            # Map back to original indices
            result = [None] * len(bboxes)
            for i, idx in enumerate(valid_indices):
                result[idx] = normalized_features[i]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in batch embedding extraction: {e}")
            return [None] * len(bboxes)


# Global singleton instance
_osnet_service_instance = None


def get_osnet_service() -> OSNetReIDService:
    """Get singleton OSNet Re-ID service"""
    global _osnet_service_instance
    if _osnet_service_instance is None:
        _osnet_service_instance = OSNetReIDService()
    return _osnet_service_instance
