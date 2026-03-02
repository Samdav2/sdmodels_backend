from uuid import UUID
from typing import Optional
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.core.security import get_password_hash


class AdminUserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, admin_data: AdminUserCreate) -> AdminUser:
        """Create a new admin user"""
        admin = AdminUser(
            email=admin_data.email,
            username=admin_data.username,
            full_name=admin_data.full_name,
            password_hash=get_password_hash(admin_data.password)
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return admin
    
    async def get_by_id(self, admin_id: UUID) -> Optional[AdminUser]:
        """Get admin by ID"""
        return await self.db.get(AdminUser, admin_id)
    
    async def get_by_email(self, email: str) -> Optional[AdminUser]:
        """Get admin by email"""
        query = select(AdminUser).where(AdminUser.email == email)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_username(self, username: str) -> Optional[AdminUser]:
        """Get admin by username"""
        query = select(AdminUser).where(AdminUser.username == username)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[AdminUser]:
        """Get all admin users"""
        query = select(AdminUser).offset(skip).limit(limit).order_by(AdminUser.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, admin_id: UUID, admin_data: AdminUserUpdate) -> Optional[AdminUser]:
        """Update admin user"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        update_data = admin_data.model_dump(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        for key, value in update_data.items():
            setattr(admin, key, value)
        
        admin.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(admin)
        return admin
    
    async def update_last_login(self, admin_id: UUID) -> None:
        """Update last login timestamp"""
        admin = await self.get_by_id(admin_id)
        if admin:
            admin.last_login = datetime.utcnow()
            await self.db.commit()
    
    async def delete(self, admin_id: UUID) -> bool:
        """Delete admin user"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False
        
        await self.db.delete(admin)
        await self.db.commit()
        return True
    
    async def deactivate(self, admin_id: UUID) -> Optional[AdminUser]:
        """Deactivate admin user"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        admin.is_active = False
        admin.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(admin)
        return admin
