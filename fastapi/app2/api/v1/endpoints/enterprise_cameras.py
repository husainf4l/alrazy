"""
Enterprise Camera API endpoints for the Al Razy Pharmacy Security System.
Advanced camera management with multi-user access control.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import (
    Camera, CameraCreate, CameraUpdate, CameraPublic, 
    CameraUserAccess, CameraTestResult
)
from app.models.user import User
from app.core.database import get_session
from app.core.dependencies import get_current_active_user
from app.services.camera_crud_service import CameraCRUDService


router = APIRouter(prefix="/cameras/enterprise", tags=["enterprise-cameras"])


def get_camera_crud_service(session: AsyncSession = Depends(get_session)) -> CameraCRUDService:
    """Get camera CRUD service."""
    return CameraCRUDService(session)


@router.post("/add", response_model=Dict[str, Any])
async def add_enterprise_camera(
    camera_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Add a new enterprise camera with advanced user access management.
    
    Fields:
    - name: Camera name
    - rtsp_url: RTSP camera URL
    - location: Camera location
    - user_ids: List of user IDs to grant access (optional)
    - company_id: Company ID (optional, defaults to current user's company)
    - admin_user_id: Admin user ID for this camera (optional, defaults to current user)
    """
    try:
        # Extract required fields
        name = camera_data.get("name")
        rtsp_url = camera_data.get("rtsp_url")
        location = camera_data.get("location")
        user_ids = camera_data.get("user_ids", [])
        company_id = camera_data.get("company_id", current_user.company_id)
        admin_user_id = camera_data.get("admin_user_id", current_user.id)
        
        # Validate required fields
        if not name:
            raise HTTPException(status_code=400, detail="Camera name is required")
        if not rtsp_url:
            raise HTTPException(status_code=400, detail="RTSP URL is required")
        if not location:
            raise HTTPException(status_code=400, detail="Camera location is required")
        
        # Test camera connection first
        camera_service = CameraCRUDService(session)
        test_result = await camera_service.test_camera_connection(rtsp_url)
        
        if not test_result.success:
            return {
                "success": False,
                "step": "connection_test",
                "message": "Camera connection failed - camera not added",
                "test_result": {
                    "rtsp_url": rtsp_url,
                    "error": test_result.message,
                    "error_details": test_result.error_details
                },
                "recommendations": [
                    "Check if the RTSP URL is correct",
                    "Verify camera IP address and port",
                    "Check username/password credentials",
                    "Ensure camera is online and accessible",
                    "Test the URL in VLC or another media player first"
                ]
            }
        
        # Create camera object
        camera_create = CameraCreate(
            name=name,
            rtsp_url=rtsp_url,
            location=location,
            admin_user_id=admin_user_id,
            user_ids=user_ids
        )
        
        # Add optional fields if provided
        for field in ["description", "camera_type", "username", "password", "ip_address", "port"]:
            if field in camera_data:
                setattr(camera_create, field, camera_data[field])
        
        # Create camera in database
        camera = await camera_service.create_camera(
            user_id=current_user.id,
            camera_create=camera_create,
            company_id=company_id
        )
        
        # Grant access to specified users
        access_grants = []
        if user_ids:
            for user_id in user_ids:
                try:
                    # Create access record
                    access_record = CameraUserAccess(
                        camera_id=camera.id,
                        user_id=user_id,
                        access_level="viewer",
                        granted_by=current_user.id
                    )
                    session.add(access_record)
                    access_grants.append({
                        "user_id": user_id,
                        "access_level": "viewer",
                        "status": "granted"
                    })
                except Exception as e:
                    access_grants.append({
                        "user_id": user_id,
                        "access_level": "viewer", 
                        "status": "failed",
                        "error": str(e)
                    })
            
            await session.commit()
        
        return {
            "success": True,
            "step": "camera_added",
            "message": "Enterprise camera added successfully with user access control",
            "camera": {
                "id": camera.id,
                "name": camera.name,
                "rtsp_url": camera.rtsp_url,
                "location": camera.location,
                "admin_user_id": camera.admin_user_id,
                "company_id": camera.company_id,
                "is_active": camera.is_active,
                "created_at": camera.created_at.isoformat()
            },
            "access_control": {
                "total_users_granted": len([g for g in access_grants if g["status"] == "granted"]),
                "user_access_grants": access_grants
            },
            "test_result": {
                "resolution": test_result.resolution,
                "frame_shape": test_result.frame_shape,
                "connection_successful": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "step": "unexpected_error",
            "message": "Unexpected error occurred",
            "error": str(e),
            "recommendation": "Please check your request and try again."
        }


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_enterprise_cameras(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    """List all enterprise cameras with access control information."""
    try:
        # Get cameras owned by user or user has access to
        query = """
        SELECT DISTINCT c.*, ca.access_level, ca.granted_by, ca.granted_at
        FROM cameras c
        LEFT JOIN camera_user_access ca ON c.id = ca.camera_id
        WHERE c.user_id = :user_id 
           OR ca.user_id = :user_id 
           OR c.company_id = :company_id
        ORDER BY c.created_at DESC
        """
        
        result = await session.execute(
            query, 
            {
                "user_id": current_user.id, 
                "company_id": current_user.company_id
            }
        )
        
        cameras = []
        for row in result.fetchall():
            camera_dict = dict(row._mapping)
            cameras.append({
                "id": camera_dict["id"],
                "name": camera_dict["name"],
                "location": camera_dict["location"],
                "is_active": camera_dict["is_active"],
                "admin_user_id": camera_dict["admin_user_id"],
                "company_id": camera_dict["company_id"],
                "access_level": camera_dict.get("access_level", "owner"),
                "created_at": camera_dict["created_at"].isoformat(),
                "rtsp_url": "***" if camera_dict.get("access_level") == "viewer" else camera_dict["rtsp_url"]
            })
        
        return cameras
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing enterprise cameras: {str(e)}"
        )


@router.post("/{camera_id}/grant-access")
async def grant_camera_access(
    camera_id: int,
    user_id: int,
    access_level: str = "viewer",
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Grant access to a camera for a specific user."""
    try:
        # Check if current user owns the camera or is admin
        camera = await session.get(Camera, camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        if camera.user_id != current_user.id and camera.admin_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to grant access to this camera")
        
        # Check if access already exists
        existing_access = await session.execute(
            "SELECT * FROM camera_user_access WHERE camera_id = :camera_id AND user_id = :user_id",
            {"camera_id": camera_id, "user_id": user_id}
        )
        
        if existing_access.fetchone():
            return {
                "success": False,
                "message": "User already has access to this camera"
            }
        
        # Grant access
        access_record = CameraUserAccess(
            camera_id=camera_id,
            user_id=user_id,
            access_level=access_level,
            granted_by=current_user.id
        )
        session.add(access_record)
        await session.commit()
        
        return {
            "success": True,
            "message": f"Access granted to user {user_id}",
            "camera_id": camera_id,
            "user_id": user_id,
            "access_level": access_level,
            "granted_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error granting camera access: {str(e)}"
        )


@router.delete("/{camera_id}/revoke-access/{user_id}")
async def revoke_camera_access(
    camera_id: int,
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Revoke access to a camera for a specific user."""
    try:
        # Check if current user owns the camera or is admin
        camera = await session.get(Camera, camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        if camera.user_id != current_user.id and camera.admin_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to revoke access to this camera")
        
        # Revoke access
        result = await session.execute(
            "DELETE FROM camera_user_access WHERE camera_id = :camera_id AND user_id = :user_id",
            {"camera_id": camera_id, "user_id": user_id}
        )
        
        if result.rowcount == 0:
            return {
                "success": False,
                "message": "User doesn't have access to this camera"
            }
        
        await session.commit()
        
        return {
            "success": True,
            "message": f"Access revoked for user {user_id}",
            "camera_id": camera_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error revoking camera access: {str(e)}"
        )
