from typing import Optional, List
import json
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator


class ModelBase(BaseModel):
    title: str
    description: str
    price: float = 0.0
    is_free: bool = False
    category: str
    tags: List[str] = []


class ModelCreate(ModelBase):
    file_url: str
    thumbnail_url: str
    preview_images: List[str] = []
    file_size: int
    file_formats: List[str]
    poly_count: int
    vertex_count: int
    texture_resolution: Optional[str] = None
    has_animations: bool = False
    has_rigging: bool = False
    has_materials: bool = True
    has_textures: bool = True


class ModelUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_free: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ModelResponse(ModelBase):
    id: UUID
    creator_id: UUID
    creator_username: Optional[str] = None  # Added creator username
    file_url: str
    thumbnail_url: str
    preview_images: List[str]
    file_size: int
    file_formats: List[str]
    poly_count: int
    vertex_count: int
    texture_resolution: Optional[str]
    has_animations: bool
    has_rigging: bool
    has_materials: bool
    has_textures: bool
    views: int
    likes: int
    downloads: int
    rating: float
    rating_count: int
    status: str
    is_featured: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime
    
    @field_validator('tags', 'preview_images', 'file_formats', mode='before')
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v is not None else []
    
    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    models: List[ModelResponse]
    total: int
    page: int
    limit: int


class ModelCommentCreate(BaseModel):
    content: str
    parent_id: Optional[UUID] = None


class ModelCommentResponse(BaseModel):
    id: UUID
    user_id: UUID
    model_id: UUID
    content: str
    parent_id: Optional[UUID]
    likes: int
    created_at: datetime
    
    class Config:
        from_attributes = True
