from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Course(SQLModel, table=True):
    __tablename__ = "courses"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    description: str
    instructor_id: UUID = Field(foreign_key="users.id")
    thumbnail_url: str
    video_url: str
    duration: int  # in minutes
    difficulty: str  # beginner, intermediate, advanced
    is_free: bool = Field(default=True)
    price: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
