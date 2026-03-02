from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Community(SQLModel, table=True):
    __tablename__ = "communities"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    icon: str  # emoji or image URL
    banner_gradient: str  # CSS gradient
    category: str
    creator_id: UUID = Field(foreign_key="users.id")
    member_count: int = Field(default=0)
    post_count: int = Field(default=0)
    status: str = Field(default="active")  # pending, active, suspended
    is_private: bool = Field(default=False)
    require_approval: bool = Field(default=False)
    rules: str = Field(default="[]")  # JSON array
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CommunityMember(SQLModel, table=True):
    __tablename__ = "community_members"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    community_id: UUID = Field(foreign_key="communities.id")
    user_id: UUID = Field(foreign_key="users.id")
    role: str = Field(default="member")  # member, moderator, admin
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class CommunityPost(SQLModel, table=True):
    __tablename__ = "community_posts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    community_id: UUID = Field(foreign_key="communities.id")
    author_id: UUID = Field(foreign_key="users.id")
    content: str
    
    # Media attachments
    image_url: Optional[str] = None
    model_url: Optional[str] = None
    
    # Engagement
    reactions: str = Field(default='{"like":0,"love":0,"wow":0,"fire":0}')
    comment_count: int = Field(default=0)
    share_count: int = Field(default=0)
    is_pinned: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PostReaction(SQLModel, table=True):
    __tablename__ = "post_reactions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    post_id: UUID = Field(foreign_key="community_posts.id")
    user_id: UUID = Field(foreign_key="users.id")
    reaction_type: str  # like, love, wow, fire
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostComment(SQLModel, table=True):
    __tablename__ = "post_comments"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    post_id: UUID = Field(foreign_key="community_posts.id")
    author_id: UUID = Field(foreign_key="users.id")
    content: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="post_comments.id")
    likes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CommentLike(SQLModel, table=True):
    __tablename__ = "comment_likes"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    comment_id: UUID = Field(foreign_key="post_comments.id")
    user_id: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
