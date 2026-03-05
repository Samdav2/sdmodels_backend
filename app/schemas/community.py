from typing import Optional, List
from datetime import datetime
from uuid import UUID
import json
from pydantic import BaseModel, field_validator


class CommunityBase(BaseModel):
    name: str
    description: str
    icon: str
    category: str


class CommunityCreate(CommunityBase):
    banner_gradient: str = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    is_private: bool = False
    require_approval: bool = False
    rules: List[str] = []


class CommunityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    banner_gradient: Optional[str] = None
    category: Optional[str] = None
    is_private: Optional[bool] = None
    require_approval: Optional[bool] = None
    rules: Optional[List[str]] = None


class MemberInfo(BaseModel):
    """Member information for community"""
    id: UUID
    user_id: UUID
    username: str
    avatar: str
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


class CommunityResponse(CommunityBase):
    id: UUID
    banner_gradient: str
    creator_id: UUID
    member_count: int
    post_count: int
    status: str
    is_private: bool
    require_approval: bool
    rules: List[str]
    is_member: bool = False  # Whether current user is a member
    user_role: Optional[str] = None  # User's role if member (admin, moderator, member)
    created_at: datetime
    updated_at: datetime
    
    @field_validator('rules', mode='before')
    @classmethod
    def parse_rules(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v is not None else []
    
    class Config:
        from_attributes = True


class CommunityDetailResponse(CommunityResponse):
    """Extended community response with members and posts"""
    top_members: List[MemberInfo] = []
    recent_posts: List['PostResponse'] = []


class CommunityListResponse(BaseModel):
    communities: List[CommunityResponse]
    total: int
    page: int
    limit: int


class PostCreate(BaseModel):
    content: str
    image_url: Optional[str] = None
    model_url: Optional[str] = None


class PostUpdate(BaseModel):
    content: Optional[str] = None


class ModelData(BaseModel):
    """Expanded model data for posts"""
    id: UUID
    title: str
    file_url: str
    thumbnail_url: str
    file_formats: List[str]
    category: str
    poly_count: int


class PostResponse(BaseModel):
    id: UUID
    community_id: UUID
    author_id: UUID
    author_username: str = "Unknown"
    author_avatar: str = "👤"
    content: str
    image_url: Optional[str]
    model_url: Optional[str]
    model: Optional[ModelData] = None  # Expanded model data
    reactions: dict
    comment_count: int
    share_count: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    
    @field_validator('reactions', mode='before')
    @classmethod
    def parse_reactions(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}
    
    class Config:
        from_attributes = True


class PostReactionCreate(BaseModel):
    reaction_type: str  # like, love, wow, fire


class PostCommentCreate(BaseModel):
    content: str
    parent_id: Optional[UUID] = None


class PostCommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    author_id: UUID
    author_username: str = "Unknown"  # Author's username
    author_avatar: str = "👤"  # Author's avatar
    content: str
    parent_id: Optional[UUID]
    likes: int
    user_has_liked: bool = False  # Whether current user has liked this comment
    replies: List['PostCommentResponse'] = []  # Nested replies
    created_at: datetime
    
    class Config:
        from_attributes = True


# Enable forward references for recursive model
PostCommentResponse.model_rebuild()
CommunityDetailResponse.model_rebuild()


class ReportCreate(BaseModel):
    reason: str
