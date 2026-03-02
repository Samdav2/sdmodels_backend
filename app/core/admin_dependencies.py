from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.security import verify_token
from app.repositories.admin_user_repository import AdminUserRepository
from app.models.admin_user import AdminUser

admin_security = HTTPBearer()


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(admin_security),
    session: AsyncSession = Depends(get_session)
) -> AdminUser:
    """
    Get current admin user from token
    
    This is completely separate from regular user authentication
    """
    token = credentials.credentials
    
    try:
        payload = verify_token(token, "access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    admin_id = payload.get("sub")
    is_admin = payload.get("is_admin", False)
    
    if not admin_id or not is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an admin token"
        )
    
    admin_repo = AdminUserRepository(session)
    admin = await admin_repo.get_by_id(int(admin_id))
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated"
        )
    
    return admin


async def require_permission(permission: str):
    """
    Dependency to check specific admin permissions
    
    Usage: admin = Depends(require_permission("can_manage_users"))
    """
    async def permission_checker(
        admin: AdminUser = Depends(get_current_admin_user)
    ) -> AdminUser:
        if not getattr(admin, permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin does not have permission: {permission}"
            )
        return admin
    
    return permission_checker


async def require_superadmin(
    admin: AdminUser = Depends(get_current_admin_user)
) -> AdminUser:
    """Require superadmin role"""
    if admin.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return admin
