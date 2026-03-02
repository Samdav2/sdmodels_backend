from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Testimonial(SQLModel, table=True):
    __tablename__ = "testimonials"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    author: str
    company: Optional[str] = None
    text: str
    rating: int = 5
    verified: bool = False
    featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
