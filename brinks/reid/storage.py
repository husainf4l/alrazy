"""
Redis-based Person Storage
Persistent storage for person identities and embeddings with cloud sync support
"""

import json
import redis
import numpy as np
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PersonRedisStorage:
    """
    Redis-backed persistent storage for persons
    Handles serialization, TTL, and cloud sync
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        namespace: str = "saferoom:persons",
        ttl_days: int = 90
    ):
        """
        Initialize Redis storage
        
        Args:
            redis_client: Redis connection
            namespace: Key prefix
            ttl_days: Expiration time for person records (None = no expiry)
        """
        self.redis = redis_client
        self.namespace = namespace
        self.ttl = ttl_days * 86400 if ttl_days else None
        
        self._init_indices()
    
    def _init_indices(self):
        """Initialize Redis indices for fast lookups"""
        try:
            # Check if Redis supports streams (for audit trail)
            self.redis.xinfo_stream(f"{self.namespace}:audit")
        except:
            # Redis version doesn't support streams, that's OK
            pass
    
    def _get_person_key(self, person_id: str) -> str:
        """Get Redis key for person"""
        return f"{self.namespace}:{person_id}"
    
    def _get_label_key(self, label: str) -> str:
        """Get Redis key for label index"""
        return f"{self.namespace}:label:{label}"
    
    def _get_camera_key(self, camera_id: str) -> str:
        """Get Redis key for camera index"""
        return f"{self.namespace}:camera:{camera_id}"
    
    def save_person(self, person_data: Dict[str, Any]) -> bool:
        """
        Save person to Redis
        
        Args:
            person_data: Person dict with person_id, label, embeddings, etc.
        
        Returns:
            True if successful
        """
        try:
            person_id = person_data["person_id"]
            label = person_data["label"]
            
            # Prepare data (embeddings are numpy arrays, need to serialize)
            data_to_save = person_data.copy()
            
            # Convert embeddings if present (keep metadata only for Redis storage)
            if "embeddings" in data_to_save:
                # Keep embedding metadata but drop actual arrays (too large for Redis)
                # Full embeddings stored locally or in cloud
                embeddings_meta = [
                    {k: v for k, v in emb.items() if k != "embedding"}
                    for emb in data_to_save["embeddings"]
                ]
                data_to_save["embeddings_count"] = len(embeddings_meta)
                data_to_save["last_embedding_meta"] = embeddings_meta[-1] if embeddings_meta else None
            
            # Store in Redis
            key = self._get_person_key(person_id)
            self.redis.hset(
                key,
                mapping=self._flatten_dict(data_to_save)
            )
            
            # Set TTL
            if self.ttl:
                self.redis.expire(key, self.ttl)
            
            # Update indices
            self.redis.sadd(self._get_label_key(label), person_id)
            if "cameras" in person_data:
                for cam_id in person_data["cameras"]:
                    self.redis.sadd(self._get_camera_key(cam_id), person_id)
            
            # Update global index
            self.redis.sadd(f"{self.namespace}:all", person_id)
            
            logger.debug(f"Saved person {label} ({person_id}) to Redis")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save person to Redis: {e}")
            return False
    
    def load_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """
        Load person from Redis
        
        Args:
            person_id: Person to load
        
        Returns:
            Person dict or None
        """
        try:
            key = self._get_person_key(person_id)
            data = self.redis.hgetall(key)
            
            if not data:
                return None
            
            # Reconstruct nested dict
            person_data = self._unflatten_dict(data)
            return person_data
        
        except Exception as e:
            logger.error(f"Failed to load person from Redis: {e}")
            return None
    
    def list_persons(self) -> List[Dict[str, Any]]:
        """List all persons"""
        try:
            all_ids = self.redis.smembers(f"{self.namespace}:all")
            persons = []
            
            for person_id in all_ids:
                person = self.load_person(person_id.decode() if isinstance(person_id, bytes) else person_id)
                if person:
                    persons.append(person)
            
            return persons
        
        except Exception as e:
            logger.error(f"Failed to list persons: {e}")
            return []
    
    def delete_person(self, person_id: str) -> bool:
        """Delete person from Redis"""
        try:
            person = self.load_person(person_id)
            if not person:
                return False
            
            key = self._get_person_key(person_id)
            self.redis.delete(key)
            
            # Update indices
            self.redis.srem(f"{self.namespace}:all", person_id)
            self.redis.srem(self._get_label_key(person["label"]), person_id)
            
            if "cameras" in person:
                for cam_id in person["cameras"]:
                    self.redis.srem(self._get_camera_key(cam_id), person_id)
            
            logger.info(f"Deleted person {person_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete person: {e}")
            return False
    
    def find_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        """Find person by label"""
        try:
            person_ids = self.redis.smembers(self._get_label_key(label))
            
            if person_ids:
                person_id = list(person_ids)[0].decode() if isinstance(list(person_ids)[0], bytes) else list(person_ids)[0]
                return self.load_person(person_id)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to find person by label: {e}")
            return None
    
    def find_by_camera(self, camera_id: str) -> List[Dict[str, Any]]:
        """Find all persons detected on specific camera"""
        try:
            person_ids = self.redis.smembers(self._get_camera_key(camera_id))
            persons = []
            
            for person_id in person_ids:
                person_id_str = person_id.decode() if isinstance(person_id, bytes) else person_id
                person = self.load_person(person_id_str)
                if person:
                    persons.append(person)
            
            return persons
        
        except Exception as e:
            logger.error(f"Failed to find persons by camera: {e}")
            return []
    
    def update_last_seen(self, person_id: str, timestamp: float):
        """Update person's last_seen timestamp"""
        try:
            key = self._get_person_key(person_id)
            self.redis.hset(key, "last_seen", timestamp)
            
            if self.ttl:
                self.redis.expire(key, self.ttl)
        
        except Exception as e:
            logger.error(f"Failed to update last_seen: {e}")
    
    def increment_visit_count(self, person_id: str):
        """Increment person's visit count"""
        try:
            key = self._get_person_key(person_id)
            current = self.redis.hget(key, "visit_count")
            count = int(current) if current else 1
            self.redis.hset(key, "visit_count", count + 1)
        
        except Exception as e:
            logger.error(f"Failed to increment visit count: {e}")
    
    def reset_all(self):
        """Delete all persons"""
        try:
            pattern = f"{self.namespace}:*"
            keys = self.redis.keys(pattern)
            
            if keys:
                self.redis.delete(*keys)
            
            logger.info("Reset all persons in Redis")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reset persons: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            all_ids = self.redis.smembers(f"{self.namespace}:all")
            
            return {
                "total_persons": len(all_ids),
                "memory_used_mb": self._get_memory_usage(),
                "namespace": self.namespace,
                "ttl_days": self.ttl // 86400 if self.ttl else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def _get_memory_usage(self) -> float:
        """Get Redis memory usage in MB"""
        try:
            info = self.redis.info("memory")
            return info.get("used_memory", 0) / (1024 * 1024)
        except:
            return 0.0
    
    @staticmethod
    def _flatten_dict(d: Dict, parent_key: str = "") -> Dict[str, str]:
        """Flatten nested dict for Redis hset"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}:{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(PersonRedisStorage._flatten_dict(v, new_key).items())
            elif isinstance(v, (list, tuple)):
                items.append((new_key, json.dumps(v)))
            elif isinstance(v, (int, float)):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, str(v)))
        
        return dict(items)
    
    @staticmethod
    def _unflatten_dict(d: Dict[bytes, bytes]) -> Dict:
        """Reconstruct nested dict from Redis hgetall"""
        result = {}
        
        for k, v in d.items():
            key = k.decode() if isinstance(k, bytes) else k
            val = v.decode() if isinstance(v, bytes) else v
            
            # Try to parse JSON for lists/dicts
            try:
                parsed_val = json.loads(val)
                result[key] = parsed_val
            except:
                # Try to parse as number
                try:
                    if "." in val:
                        result[key] = float(val)
                    else:
                        result[key] = int(val)
                except:
                    result[key] = val
        
        return result


class CloudEmbeddingStorage:
    """
    Optional cloud storage for full embeddings (S3, GCS, etc.)
    Reduces Redis memory usage, enables backup and sharing
    """
    
    def __init__(self, provider: str = "local", config: Optional[Dict] = None):
        """
        Initialize cloud storage
        
        Args:
            provider: 'local', 's3', 'gcs', or 'azure'
            config: Provider-specific configuration
        """
        self.provider = provider
        self.config = config or {}
        self.bucket = self.config.get("bucket", "saferoom-embeddings")
        self.local_cache = {}  # Local memory cache
    
    def save_embedding(
        self,
        person_id: str,
        embedding: np.ndarray,
        timestamp: float
    ) -> bool:
        """
        Save embedding to cloud storage
        
        Args:
            person_id: Person identifier
            embedding: Embedding vector
            timestamp: When embedding was captured
        
        Returns:
            True if successful
        """
        try:
            if self.provider == "local":
                return self._save_local(person_id, embedding, timestamp)
            elif self.provider == "s3":
                return self._save_s3(person_id, embedding, timestamp)
            elif self.provider == "gcs":
                return self._save_gcs(person_id, embedding, timestamp)
            else:
                logger.warning(f"Unknown provider: {self.provider}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            return False
    
    def load_embedding(self, person_id: str, embedding_id: int = 0) -> Optional[np.ndarray]:
        """Load embedding from cloud storage"""
        try:
            if self.provider == "local":
                return self._load_local(person_id, embedding_id)
            elif self.provider == "s3":
                return self._load_s3(person_id, embedding_id)
            elif self.provider == "gcs":
                return self._load_gcs(person_id, embedding_id)
        
        except Exception as e:
            logger.error(f"Failed to load embedding: {e}")
            return None
    
    def _save_local(self, person_id: str, embedding: np.ndarray, timestamp: float) -> bool:
        """Save to local memory cache"""
        if person_id not in self.local_cache:
            self.local_cache[person_id] = []
        
        self.local_cache[person_id].append({
            "embedding": embedding,
            "timestamp": timestamp
        })
        
        return True
    
    def _load_local(self, person_id: str, embedding_id: int = 0) -> Optional[np.ndarray]:
        """Load from local memory cache"""
        if person_id in self.local_cache and embedding_id < len(self.local_cache[person_id]):
            return self.local_cache[person_id][embedding_id]["embedding"]
        return None
    
    def _save_s3(self, person_id: str, embedding: np.ndarray, timestamp: float) -> bool:
        """Save to AWS S3 (requires boto3)"""
        try:
            import boto3
            s3 = boto3.client('s3')
            
            # Save as NPZ for efficiency
            import io
            buffer = io.BytesIO()
            np.savez_compressed(buffer, embedding=embedding)
            buffer.seek(0)
            
            key = f"{self.bucket}/{person_id}/{int(timestamp)}.npz"
            s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.getvalue())
            
            return True
        except ImportError:
            logger.error("boto3 not installed for S3 support")
            return False
        except Exception as e:
            logger.error(f"S3 save failed: {e}")
            return False
    
    def _load_s3(self, person_id: str, embedding_id: int = 0) -> Optional[np.ndarray]:
        """Load from AWS S3"""
        try:
            import boto3
            s3 = boto3.client('s3')
            
            # List embeddings for person
            response = s3.list_objects_v2(Bucket=self.bucket, Prefix=f"{person_id}/")
            
            if "Contents" not in response:
                return None
            
            # Get embedding by index
            objects = sorted(response["Contents"], key=lambda x: x["Key"])
            if embedding_id >= len(objects):
                return None
            
            obj = s3.get_object(Bucket=self.bucket, Key=objects[embedding_id]["Key"])
            buffer = io.BytesIO(obj["Body"].read())
            data = np.load(buffer)
            
            return data["embedding"]
        except Exception as e:
            logger.error(f"S3 load failed: {e}")
            return None
    
    def _save_gcs(self, person_id: str, embedding: np.ndarray, timestamp: float) -> bool:
        """Save to Google Cloud Storage (requires google-cloud-storage)"""
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(self.bucket)
            
            import io
            buffer = io.BytesIO()
            np.savez_compressed(buffer, embedding=embedding)
            buffer.seek(0)
            
            blob = bucket.blob(f"{person_id}/{int(timestamp)}.npz")
            blob.upload_from_string(buffer.getvalue())
            
            return True
        except ImportError:
            logger.error("google-cloud-storage not installed for GCS support")
            return False
        except Exception as e:
            logger.error(f"GCS save failed: {e}")
            return False
    
    def _load_gcs(self, person_id: str, embedding_id: int = 0) -> Optional[np.ndarray]:
        """Load from Google Cloud Storage"""
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(self.bucket)
            
            # List embeddings for person
            blobs = list(bucket.list_blobs(prefix=f"{person_id}/"))
            
            if embedding_id >= len(blobs):
                return None
            
            blob = sorted(blobs, key=lambda x: x.name)[embedding_id]
            data = np.load(io.BytesIO(blob.download_as_bytes()))
            
            return data["embedding"]
        except Exception as e:
            logger.error(f"GCS load failed: {e}")
            return None
