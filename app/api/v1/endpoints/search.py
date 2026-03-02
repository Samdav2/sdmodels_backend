from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    type: str = Query("models", regex="^(models|users|communities|courses)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Global search across platform"""
    return {
        "query": q,
        "type": type,
        "results": [],
        "total": 0,
        "page": page,
        "limit": limit
    }
