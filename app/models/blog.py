from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class BlogPost(SQLModel, table=True):
    __tablename__ = "blog_posts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    author_id: UUID = Field(foreign_key="users.id")
    title: str = Field(index=True)
    content: str  # Markdown content
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    category: str = Field(index=True)  # tutorials, news, updates
    tags: str = Field(default="[]")  # JSON array
    
    # Engagement
    views: int = Field(default=0)
    likes: int = Field(default=0)
    comment_count: int = Field(default=0)
    read_time: int = Field(default=5)  # minutes
    
    # Status
    status: str = Field(default="draft")  # draft, published
    is_featured: bool = Field(default=False)
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BlogComment(SQLModel, table=True):
    __tablename__ = "blog_comments"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    post_id: UUID = Field(foreign_key="blog_posts.id")
    author_id: UUID = Field(foreign_key="users.id")
    content: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="blog_comments.id")
    likes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BlogLike(SQLModel, table=True):
    __tablename__ = "blog_likes"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    post_id: UUID = Field(foreign_key="blog_posts.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
