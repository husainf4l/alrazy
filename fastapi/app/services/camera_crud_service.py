"""
Camera CRUD service for RazZ Backend Security System.

Database operations and business logic for camera management.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.camera import (
    Camera, CameraCreate, CameraUpdate, CameraPublic, CameraStatus, CameraTestResult
)


class CameraCRUDService:
    """Camera CRUD service for database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_camera(self, user_id: int, camera_create: CameraCreate, company_id: Optional[int] = None) -> Camera:
        """Create a new camera for a user."""
        # Extract user_ids and admin_user_id from camera_create
        user_ids = camera_create.user_ids or []
        admin_user_id = camera_create.admin_user_id
        
        # Create camera data without the extra fields
        camera_data = camera_create.dict(exclude={"user_ids", "admin_user_id"})
        
        db_camera = Camera(
            **camera_data,
            user_id=user_id,
            company_id=company_id,
            admin_user_id=admin_user_id,
            created_at=datetime.utcnow()
        )
        
        self.session.add(db_camera)
        await self.session.commit()
        await self.session.refresh(db_camera)
        
        # Create user access entries for additional users
        if user_ids:
            from app.models.camera import CameraUserAccess
            for uid in user_ids:
                if uid != user_id:  # Don't duplicate the owner
                    user_access = CameraUserAccess(
                        camera_id=db_camera.id,
                        user_id=uid,
                        access_level="viewer",
                        granted_by=user_id,
                        granted_at=datetime.utcnow()
                    )
                    self.session.add(user_access)
            
            await self.session.commit()
        
        return db_camera
        return db_camera

    async def get_camera(self, camera_id: int, user_id: int) -> Optional[Camera]:
        """Get camera by ID for a specific user."""
        result = await self.session.execute(
            select(Camera).where(
                and_(Camera.id == camera_id, Camera.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_user_cameras(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Camera]:
        """Get all cameras for a user."""
        result = await self.session.execute(
            select(Camera)
            .where(Camera.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_company_cameras(self, company_id: int, skip: int = 0, limit: int = 100) -> List[Camera]:
        """Get all cameras for a company."""
        result = await self.session.execute(
            select(Camera)
            .where(Camera.company_id == company_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_camera(self, camera_id: int, user_id: int, camera_update: CameraUpdate) -> Optional[Camera]:
        """Update a camera."""
        camera = await self.get_camera(camera_id, user_id)
        if not camera:
            return None

        update_data = camera_update.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            for field, value in update_data.items():
                setattr(camera, field, value)
            
            await self.session.commit()
            await self.session.refresh(camera)
        
        return camera

    async def delete_camera(self, camera_id: int, user_id: int) -> bool:
        """Delete a camera."""
        camera = await self.get_camera(camera_id, user_id)
        if not camera:
            return False

        await self.session.delete(camera)
        await self.session.commit()
        return True

    async def update_camera_connection_status(self, camera_id: int, last_connected_at: datetime) -> bool:
        """Update camera's last connected timestamp."""
        result = await self.session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        
        if camera:
            camera.last_connected_at = last_connected_at
            await self.session.commit()
            return True
        
        return False

    async def test_camera_connection(self, rtsp_url: str) -> CameraTestResult:
        """Test camera connection without saving to database."""
        try:
            import cv2
            import time
            
            # Test connection with different backends
            backends = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(rtsp_url, backend)
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                    
                    if cap.isOpened():
                        ret, frame = cap.read()
                        cap.release()
                        
                        if ret and frame is not None:
                            return CameraTestResult(
                                success=True,
                                rtsp_url=rtsp_url,
                                message="Camera connection successful",
                                resolution=f"{frame.shape[1]}x{frame.shape[0]}",
                                frame_shape=list(frame.shape)
                            )
                        else:
                            cap.release()
                            continue
                    else:
                        cap.release()
                        continue
                        
                except Exception as e:
                    continue
            
            return CameraTestResult(
                success=False,
                rtsp_url=rtsp_url,
                message="Could not connect to camera with any backend",
                error_details="Connection failed with all available backends"
            )
            
        except Exception as e:
            return CameraTestResult(
                success=False,
                rtsp_url=rtsp_url,
                message=f"Camera test failed: {str(e)}",
                error_details=str(e)
            )

    async def get_camera_count_by_user(self, user_id: int) -> int:
        """Get total camera count for a user."""
        result = await self.session.execute(
            select(Camera).where(Camera.user_id == user_id)
        )
        cameras = result.scalars().all()
        return len(cameras)

    async def get_active_cameras_by_user(self, user_id: int) -> List[Camera]:
        """Get all active cameras for a user."""
        result = await self.session.execute(
            select(Camera).where(
                and_(Camera.user_id == user_id, Camera.is_active == True)
            )
        )
        return result.scalars().all()
