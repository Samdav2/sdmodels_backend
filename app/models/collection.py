from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class Collection(SQLModel, table=True):
    __tablename__ = "collections"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_id: UUID = Field(foreign_key="users.id")
    name: str
    description: Optional[str] = None
    is_public: bool = Field(default=True)
    
    # Stats
    model_count: int = Field(default=0)
    views: int = Field(default=0)
    followers: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CollectionModel(SQLModel, table=True):
    __tablename__ = "collection_models"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID = Field(foreign_key="collections.id")
    model_id: UUID = Field(foreign_key="models.id")
    order: int = Field(default=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)


class CollectionFollower(SQLModel, table=True):
    __tablename__ = "collection_followers"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    collection_id: UUID = Field(foreign_key="collections.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
