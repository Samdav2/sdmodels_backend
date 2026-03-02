from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_collections(
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get collections list"""
    from sqlalchemy import select, func
    from app.models.collection import Collection
    
    # Build query
    query = select(Collection)
    count_query = select(func.count()).select_from(Collection)
    
    if user_id:
        query = query.where(Collection.user_id == user_id)
        count_query = count_query.where(Collection.user_id == user_id)
    
    # Only show public collections if not filtering by user
    if not user_id:
        query = query.where(Collection.is_public == True)
        count_query = count_query.where(Collection.is_public == True)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated collections
    query = query.offset((page - 1) * limit).limit(limit).order_by(Collection.created_at.desc())
    result = await session.execute(query)
    collections = result.scalars().all()
    
    return {
        "collections": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "is_public": c.is_public,
                "user_id": c.user_id,
                "created_at": c.created_at
            } for c in collections
        ],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.post("")
async def create_collection(
    name: str,
    description: Optional[str] = None,
    is_public: bool = True,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create new collection"""
    return {"message": "Collection created", "id": 1}


@router.get("/{collection_id}")
async def get_collection(
    collection_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get collection details"""
    return {"id": collection_id, "name": "My Collection"}


@router.put("/{collection_id}")
async def update_collection(
    collection_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update collection"""
    return {"message": "Collection updated"}


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete collection"""
    return {"message": "Collection deleted"}


@router.post("/{collection_id}/follow")
async def follow_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Follow collection"""
    return {"message": "Collection followed"}


@router.get("/{collection_id}/models")
async def get_collection_models(
    collection_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get models in collection"""
    return {"models": [], "page": page, "limit": limit}


@router.post("/{collection_id}/add-model")
async def add_model_to_collection(
    collection_id: UUID,
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add model to collection"""
    return {"message": "Model added to collection"}


@router.delete("/{collection_id}/remove-model/{model_id}")
async def remove_model_from_collection(
    collection_id: UUID,
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove model from collection"""
    return {"message": "Model removed from collection"}
