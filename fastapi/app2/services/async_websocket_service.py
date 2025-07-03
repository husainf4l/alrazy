"""
Async WebSocket Service for the Al Razy Pharmacy Security System.
Improved with better async patterns and error handling.
"""
import asyncio
import json
import time
import logging
from typing import Dict, Set, Any, Optional, List
import weakref
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    connection_type: str
    client_id: str
    connected_at: float
    last_heartbeat: float = 0
    
class AsyncConnectionManager:
    """Async WebSocket connection manager with heartbeat and proper cleanup."""
    
    def __init__(self):
        # Use weak references to avoid memory leaks
        self.connections: Dict[str, Dict[str, ConnectionInfo]] = {
            "camera_streams": {},
            "motion_detection": {},
            "system_status": {},
            "security_alerts": {},
            "recordings": {}
        }
        
        # Active streaming tasks
        self.streaming_tasks: Dict[str, asyncio.Task] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 60  # seconds
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_background_tasks()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_all()
        
    async def start_background_tasks(self):
        """Start background maintenance tasks."""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("🔄 Started WebSocket background tasks")
        
    async def connect(self, websocket: WebSocket, connection_type: str, 
                     client_id: Optional[str] = None) -> str:
        """Connect a new WebSocket client."""
        await websocket.accept()
        
        # Generate client ID if not provided
        if not client_id:
            client_id = f"{connection_type}_{int(time.time() * 1000)}_{id(websocket)}"
        
        # Create connection info
        connection_info = ConnectionInfo(
            websocket=websocket,
            connection_type=connection_type,
            client_id=client_id,
            connected_at=time.time(),
            last_heartbeat=time.time()
        )
        
        # Store connection
        if connection_type not in self.connections:
            self.connections[connection_type] = {}
            
        self.connections[connection_type][client_id] = connection_info
        
        # Update statistics
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = sum(
            len(conns) for conns in self.connections.values()
        )
        
        logger.info(f"✅ New {connection_type} connection: {client_id}")
        logger.info(f"   Total {connection_type} connections: {len(self.connections[connection_type])}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "connection_type": connection_type,
            "timestamp": time.time()
        }, websocket)
        
        return client_id
        
    async def disconnect(self, websocket: WebSocket, connection_type: str, 
                        client_id: Optional[str] = None):
        """Disconnect a WebSocket client."""
        try:
            # Find and remove connection
            if connection_type in self.connections:
                if client_id and client_id in self.connections[connection_type]:
                    del self.connections[connection_type][client_id]
                else:
                    # Find by websocket if client_id not provided
                    to_remove = None
                    for cid, conn_info in self.connections[connection_type].items():
                        if conn_info.websocket == websocket:
                            to_remove = cid
                            break
                    
                    if to_remove:
                        del self.connections[connection_type][to_remove]
                        client_id = to_remove
            
            # Stop any associated streaming tasks
            if client_id and client_id in self.streaming_tasks:
                task = self.streaming_tasks[client_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.streaming_tasks[client_id]
            
            # Update statistics
            self.stats["active_connections"] = sum(
                len(conns) for conns in self.connections.values()
            )
            
            logger.info(f"❌ Disconnected {connection_type}: {client_id or 'unknown'}")
            logger.info(f"   Remaining {connection_type} connections: {len(self.connections.get(connection_type, {}))}")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.stats["errors"] += 1
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> bool:
        """Send a message to a specific client."""
        try:
            message_json = json.dumps(message, default=str)
            await websocket.send_text(message_json)
            self.stats["messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.stats["errors"] += 1
            return False
    
    async def broadcast_to_type(self, message: Dict[str, Any], connection_type: str) -> int:
        """Broadcast a message to all clients of a specific type."""
        if connection_type not in self.connections:
            return 0
            
        connections = list(self.connections[connection_type].values())
        if not connections:
            return 0
        
        # Send messages concurrently
        tasks = []
        for conn_info in connections:
            task = asyncio.create_task(
                self._send_with_error_handling(message, conn_info)
            )
            tasks.append(task)
        
        # Wait for all sends to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful sends
        successful = sum(1 for result in results if result is True)
        
        if successful > 0:
            logger.debug(f"📡 Broadcast to {connection_type}: {successful}/{len(connections)} successful")
        
        return successful
    
    async def _send_with_error_handling(self, message: Dict[str, Any], 
                                      conn_info: ConnectionInfo) -> bool:
        """Send message with error handling and automatic cleanup."""
        try:
            await self.send_personal_message(message, conn_info.websocket)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {conn_info.client_id}: {e}")
            # Schedule cleanup for failed connection
            asyncio.create_task(
                self._cleanup_dead_connection(conn_info)
            )
            return False
    
    async def _cleanup_dead_connection(self, conn_info: ConnectionInfo):
        """Clean up a dead connection."""
        try:
            await self.disconnect(
                conn_info.websocket, 
                conn_info.connection_type, 
                conn_info.client_id
            )
        except Exception as e:
            logger.error(f"Error cleaning up dead connection: {e}")
    
    async def start_camera_stream(self, client_id: str, camera_id: int, 
                                fps: int = 10) -> bool:
        """Start streaming camera frames to a specific client."""
        try:
            # Find connection
            conn_info = self._find_connection(client_id)
            if not conn_info:
                logger.error(f"Connection not found for client: {client_id}")
                return False
            
            # Stop existing stream if any
            if client_id in self.streaming_tasks:
                await self.stop_camera_stream(client_id)
            
            # Start new stream
            stream_task = asyncio.create_task(
                self._camera_stream_loop(conn_info, camera_id, fps)
            )
            self.streaming_tasks[client_id] = stream_task
            
            logger.info(f"📹 Started camera stream for {client_id}: camera {camera_id} @ {fps} FPS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera stream: {e}")
            return False
    
    async def stop_camera_stream(self, client_id: str) -> bool:
        """Stop camera stream for a specific client."""
        try:
            if client_id in self.streaming_tasks:
                task = self.streaming_tasks[client_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.streaming_tasks[client_id]
                
                logger.info(f"⏹️ Stopped camera stream for {client_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop camera stream: {e}")
            return False
    
    async def _camera_stream_loop(self, conn_info: ConnectionInfo, 
                                camera_id: int, fps: int):
        """Camera streaming loop."""
        frame_delay = 1.0 / fps
        consecutive_failures = 0
        max_failures = 5
        
        try:
            while True:
                try:
                    # Get camera frame
                    frame_data = await self._get_camera_frame(camera_id)
                    
                    if frame_data:
                        # Send frame to client
                        message = {
                            "type": "camera_frame",
                            "camera_id": camera_id,
                            "frame": frame_data,
                            "timestamp": time.time()
                        }
                        
                        success = await self.send_personal_message(
                            message, conn_info.websocket
                        )
                        
                        if success:
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                    else:
                        consecutive_failures += 1
                    
                    # Check for too many failures
                    if consecutive_failures >= max_failures:
                        logger.warning(f"Too many failures for {conn_info.client_id}, stopping stream")
                        break
                    
                    await asyncio.sleep(frame_delay)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in camera stream loop: {e}")
                    consecutive_failures += 1
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Fatal error in camera stream: {e}")
        finally:
            logger.info(f"📹 Camera stream ended for {conn_info.client_id}")
    
    async def _get_camera_frame(self, camera_id: int) -> Optional[str]:
        """Get camera frame (to be implemented with actual camera service)."""
        try:
            # Import here to avoid circular imports
            from app.core.dependencies import get_camera_service
            
            camera_service = get_camera_service()
            if camera_service:
                return await camera_service.get_camera_frame(camera_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get camera frame: {e}")
            return None
    
    def _find_connection(self, client_id: str) -> Optional[ConnectionInfo]:
        """Find connection info by client ID."""
        for connection_type_dict in self.connections.values():
            if client_id in connection_type_dict:
                return connection_type_dict[client_id]
        return None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to maintain connections."""
        while True:
            try:
                current_time = time.time()
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": current_time
                }
                
                # Send heartbeat to all connection types
                for connection_type in self.connections:
                    await self.broadcast_to_type(heartbeat_message, connection_type)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale connections."""
        while True:
            try:
                current_time = time.time()
                
                # Check for stale connections
                for connection_type, connections in self.connections.items():
                    stale_clients = []
                    
                    for client_id, conn_info in connections.items():
                        # Check if connection is stale
                        if (current_time - conn_info.last_heartbeat) > self.connection_timeout:
                            stale_clients.append(client_id)
                    
                    # Remove stale connections
                    for client_id in stale_clients:
                        conn_info = connections[client_id]
                        logger.warning(f"Removing stale connection: {client_id}")
                        await self.disconnect(
                            conn_info.websocket, 
                            connection_type, 
                            client_id
                        )
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)
    
    async def cleanup_all(self):
        """Cleanup all connections and tasks."""
        logger.info("🧹 Cleaning up WebSocket manager")
        
        # Cancel background tasks
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all streaming tasks
        for task in list(self.streaming_tasks.values()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.streaming_tasks.clear()
        
        # Close all connections
        for connection_type, connections in self.connections.items():
            for client_id, conn_info in list(connections.items()):
                try:
                    await conn_info.websocket.close()
                except Exception:
                    pass
        
        self.connections.clear()
        
        logger.info("✅ WebSocket manager cleanup completed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        active_by_type = {
            conn_type: len(conns) 
            for conn_type, conns in self.connections.items()
        }
        
        return {
            **self.stats,
            "active_by_type": active_by_type,
            "active_streams": len(self.streaming_tasks),
            "uptime": time.time() - self.stats["start_time"]
        }


# Global connection manager
_connection_manager = None

async def get_async_connection_manager() -> AsyncConnectionManager:
    """Get or create the global async connection manager."""
    global _connection_manager
    
    if _connection_manager is None:
        _connection_manager = AsyncConnectionManager()
        await _connection_manager.start_background_tasks()
    
    return _connection_manager

async def cleanup_connection_manager():
    """Cleanup the global connection manager."""
    global _connection_manager
    
    if _connection_manager:
        await _connection_manager.cleanup_all()
        _connection_manager = None
