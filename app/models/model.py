from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Model(SQLModel, table=True):
    __tablename__ = "models"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    creator_id: UUID = Field(foreign_key="users.id")
    title: str = Field(index=True)
    description: str
    price: float = Field(default=0.0)
    is_free: bool = Field(default=False)
    category: str = Field(index=True)
    tags: str = Field(default="[]")  # JSON array
    
    # File information
    file_url: str  # Main model file (GLB/GLTF)
    thumbnail_url: str
    preview_images: str = Field(default="[]")  # JSON array of image URLs
    file_size: int  # in bytes
    file_formats: str = Field(default="[]")  # ["GLB", "FBX", "OBJ"]
    
    # Model specifications
    poly_count: int
    vertex_count: int
    texture_resolution: Optional[str] = None
    has_animations: bool = Field(default=False)
    has_rigging: bool = Field(default=False)
    has_materials: bool = Field(default=True)
    has_textures: bool = Field(default=True)
    
    # Engagement metrics
    views: int = Field(default=0)
    likes: int = Field(default=0)
    downloads: int = Field(default=0)
    rating: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    
    # Status
    status: str = Field(default="pending")  # pending, approved, rejected
    is_featured: bool = Field(default=False)
    is_published: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModelLike(SQLModel, table=True):
    __tablename__ = "model_likes"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    model_id: UUID = Field(foreign_key="models.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelComment(SQLModel, table=True):
    __tablename__ = "model_comments"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    model_id: UUID = Field(foreign_key="models.id")
    content: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="model_comments.id")
    likes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
