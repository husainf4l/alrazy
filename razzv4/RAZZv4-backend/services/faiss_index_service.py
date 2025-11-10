"""
FAISS Index Service for Person Re-Identification
Fast similarity search for person embeddings across cameras
"""

import numpy as np
import logging
from typing import List, Tuple, Optional, Dict
import threading

logger = logging.getLogger(__name__)


class FAISSIndexService:
    """
    FAISS-based similarity search for person embeddings
    - Fast nearest neighbor search (< 1ms for 10K persons)
    - Supports real-time gallery updates
    - Thread-safe operations
    """
    
    def __init__(self, embedding_dim: int = 512, use_gpu: bool = False):
        """
        Initialize FAISS index
        
        Args:
            embedding_dim: Dimension of embeddings (512 for OSNet)
            use_gpu: Use GPU for FAISS (requires faiss-gpu)
        """
        self.embedding_dim = embedding_dim
        self.use_gpu = use_gpu
        self.index = None
        self.global_id_map = {}  # {index_position: global_id}
        self.global_id_to_position = {}  # {global_id: index_position}
        self.lock = threading.RLock()
        
        try:
            import faiss
            self.faiss = faiss
            self._initialize_index()
            logger.info(f"✅ FAISS index initialized (dim={embedding_dim}, gpu={use_gpu})")
        except ImportError:
            logger.error("❌ FAISS not installed. Install with: pip install faiss-cpu")
            logger.warning("⚠️  Falling back to brute-force search")
            self.faiss = None
    
    def _initialize_index(self):
        """Initialize FAISS index for cosine similarity"""
        if not self.faiss:
            return
        
        # Use IndexFlatIP for cosine similarity (Inner Product)
        # Since embeddings are normalized, IP = cosine similarity
        self.index = self.faiss.IndexFlatIP(self.embedding_dim)
        
        if self.use_gpu and self.faiss.get_num_gpus() > 0:
            try:
                res = self.faiss.StandardGpuResources()
                self.index = self.faiss.index_cpu_to_gpu(res, 0, self.index)
                logger.info("🚀 FAISS index moved to GPU")
            except Exception as e:
                logger.warning(f"Failed to move FAISS to GPU: {e}")
    
    def is_available(self) -> bool:
        """Check if FAISS is available"""
        return self.faiss is not None and self.index is not None
    
    def add_embedding(self, global_id: int, embedding: np.ndarray) -> bool:
        """
        Add or update embedding in the index
        
        Args:
            global_id: Global person ID
            embedding: 512-dim normalized embedding
        
        Returns:
            True if added successfully
        """
        if not self.is_available():
            return False
        
        with self.lock:
            try:
                # Check if already exists
                if global_id in self.global_id_to_position:
                    # Remove old embedding first
                    self.remove_embedding(global_id)
                
                # Add to index
                embedding_2d = embedding.reshape(1, -1).astype('float32')
                position = self.index.ntotal
                self.index.add(embedding_2d)
                
                # Update mappings
                self.global_id_map[position] = global_id
                self.global_id_to_position[global_id] = position
                
                logger.debug(f"Added embedding for Global ID {global_id} at position {position}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding embedding: {e}")
                return False
    
    def remove_embedding(self, global_id: int) -> bool:
        """
        Remove embedding from index
        
        Note: FAISS IndexFlatIP doesn't support removal, so we mark as invalid
        and rebuild index periodically
        
        Args:
            global_id: Global person ID
        
        Returns:
            True if removed successfully
        """
        with self.lock:
            if global_id in self.global_id_to_position:
                position = self.global_id_to_position[global_id]
                del self.global_id_map[position]
                del self.global_id_to_position[global_id]
                return True
        return False
    
    def search(self, 
               query_embedding: np.ndarray, 
               k: int = 5,
               threshold: float = 0.5) -> List[Tuple[int, float]]:
        """
        Search for similar embeddings
        
        Args:
            query_embedding: Query embedding (512-dim, normalized)
            k: Number of nearest neighbors to return
            threshold: Minimum similarity threshold (0-1)
        
        Returns:
            List of (global_id, similarity) tuples, sorted by similarity
        """
        if not self.is_available():
            return []
        
        with self.lock:
            try:
                if self.index.ntotal == 0:
                    return []
                
                # Search
                query_2d = query_embedding.reshape(1, -1).astype('float32')
                distances, indices = self.index.search(query_2d, min(k, self.index.ntotal))
                
                # Convert to results
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx == -1:  # Invalid index
                        continue
                    
                    if idx not in self.global_id_map:
                        continue
                    
                    global_id = self.global_id_map[idx]
                    similarity = float(dist)  # Already cosine similarity (normalized embeddings)
                    
                    if similarity >= threshold:
                        results.append((global_id, similarity))
                
                # Sort by similarity (descending)
                results.sort(key=lambda x: x[1], reverse=True)
                
                return results
                
            except Exception as e:
                logger.error(f"Error searching FAISS index: {e}")
                return []
    
    def search_with_fallback(self,
                            query_embedding: np.ndarray,
                            embeddings_dict: Dict[int, np.ndarray],
                            k: int = 5,
                            threshold: float = 0.5) -> List[Tuple[int, float]]:
        """
        Search with fallback to brute-force if FAISS not available
        
        Args:
            query_embedding: Query embedding
            embeddings_dict: {global_id: embedding} for brute-force fallback
            k: Number of results
            threshold: Similarity threshold
        
        Returns:
            List of (global_id, similarity) tuples
        """
        if self.is_available():
            return self.search(query_embedding, k, threshold)
        
        # Fallback to brute-force
        return self._brute_force_search(query_embedding, embeddings_dict, k, threshold)
    
    def _brute_force_search(self,
                           query_embedding: np.ndarray,
                           embeddings_dict: Dict[int, np.ndarray],
                           k: int,
                           threshold: float) -> List[Tuple[int, float]]:
        """Brute-force similarity search (fallback when FAISS not available)"""
        results = []
        
        for global_id, embedding in embeddings_dict.items():
            if embedding is None:
                continue
            
            # Cosine similarity (dot product for normalized vectors)
            similarity = float(np.dot(query_embedding, embedding))
            
            if similarity >= threshold:
                results.append((global_id, similarity))
        
        # Sort and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
    
    def rebuild_index(self, embeddings_dict: Dict[int, np.ndarray]):
        """
        Rebuild entire index from scratch
        Useful after many removals or for cleanup
        
        Args:
            embeddings_dict: {global_id: embedding}
        """
        if not self.is_available():
            return
        
        with self.lock:
            logger.info(f"Rebuilding FAISS index with {len(embeddings_dict)} embeddings...")
            
            # Reset index
            self._initialize_index()
            self.global_id_map.clear()
            self.global_id_to_position.clear()
            
            # Add all embeddings
            for global_id, embedding in embeddings_dict.items():
                if embedding is not None:
                    self.add_embedding(global_id, embedding)
            
            logger.info(f"✅ FAISS index rebuilt: {self.index.ntotal} embeddings")
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        with self.lock:
            return {
                'total_embeddings': self.index.ntotal if self.is_available() else 0,
                'dimension': self.embedding_dim,
                'gpu_enabled': self.use_gpu,
                'faiss_available': self.is_available()
            }


# Global singleton instance
_faiss_service_instance = None


def get_faiss_service() -> FAISSIndexService:
    """Get singleton FAISS service"""
    global _faiss_service_instance
    if _faiss_service_instance is None:
        _faiss_service_instance = FAISSIndexService()
    return _faiss_service_instance
